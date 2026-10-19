# RunPod pod startup and deadline API investigation

Date: 2026-10-19

## Question

Find a documented way to start the local authenticated gate/launcher and ensure provider-side termination for a bounded Qwen trial. Expected behavior: gate/launcher starts in the container, vLLM is private on loopback, and the pod is deleted at a hard deadline measured from allocation. Actual API surface appears split across create routes.

## Hypotheses and discriminating checks

1. GraphQL supports both container entrypoint override and provider termination. Check the official GraphQL schema's `PodFindAndDeployOnDemandInput` fields and create example. Both fields there would permit one atomic create request; a missing entrypoint field rules this out.
2. REST v1 supports both capabilities. Check the official REST OpenAPI schema and current docs. Both fields in pod-create request would permit one REST create; a missing deadline rules this out.
3. REST v2 or a current RunPod CLI path supports both capabilities. Check the official v2 client request builder and current CLI changelog/command surface. Both request fields would enable the current supported path; removed flags or absent fields rule it out.
4. A standard vLLM image can run a custom launcher through only Docker args. Compare the image's ENTRYPOINT behavior with the create API's args semantics. If args replace CMD only, the wrapper cannot be invoked without a custom image or a separate host-side tunnel/proxy.
5. A private template created through REST v1 can carry `dockerEntrypoint`, then GraphQL pod creation can consume its `templateId` and set `terminateAfter`. Check the REST v1 template OpenAPI schema and readback route plus GraphQL create input. All three field/route affordances would supply a single documented composition without building/pushing a custom image; missing any one rules it out.

## Checks and findings

- Official GraphQL schema lists `dockerArgs`, `stopAfter`, and `terminateAfter` on `PodFindAndDeployOnDemandInput`, but no `dockerEntrypoint`. It defines `terminateAfter` as an ISO `DateTime` input. The create guide's example passes `dockerArgs` and returns the pod ID. `podTerminate` is a separate provider control-plane mutation.
- Official REST v1 is explicitly marked deprecated, with retirement scheduled for 2026-11-15. Its published pod-create shape exposes `dockerEntrypoint` and `dockerStartCmd`; no `terminateAfter` is documented there. REST v1 can therefore start the wrapper but cannot set the provider deadline atomically.
- The current RunPod CLI v2.12 release removed `--stop-after` and `--terminate-after`; v2 pod creation uses the REST v2 route. The official `runpod-python` create builder sends `startSsh`, optional `args`, image, ports, env, disks/mounts, and GPU, but has no entrypoint or deadline property. It exposes provider termination separately as `DELETE /v2/pods/{id}`.
- The official vLLM image metadata previously inspected identifies an ENTRYPOINT of `vllm serve`; Docker args therefore supply arguments to that executable rather than replacing it. They cannot invoke an arbitrary Python wrapper. A custom image with the wrapper as its baked ENTRYPOINT, or a separate host-side wrapper using SSH forwarding to a loopback-only vLLM process, is needed.
- New cross-route check: official REST v1 OpenAPI has `POST /templates` with `dockerEntrypoint` and `dockerStartCmd`, `isPublic`, and a successful response containing the template. It also has `GET /templates/{templateId}` to read back the stored fields and `DELETE` to remove it. The official GraphQL `PodFindAndDeployOnDemandInput` accepts `templateId` and `terminateAfter` together. This makes a documented composition possible: create a private, secret-free template through REST v1; GET it and compare image, entrypoint, command, visibility, and volume settings before renting; then create the pod through GraphQL with that template ID, pod-scoped env secrets, no persistent volume, and an absolute UTC termination timestamp. Delete the temporary template after the pod is terminated. [REST v1 template OpenAPI](https://rest.runpod.io/v1/openapi.json), [template create guide](https://docs.runpod.io/api-reference/templates/POST/templates), [GraphQL pod-create input](https://graphql-spec.runpod.io/)
- This composes documented schema fields but has not been trialed. GraphQL pod output returns `templateId` but not `terminateAfter`; readback of the template verifies its stored config, not that the pod's runtime actually inherited/used the entrypoint or that the deadline will fire at the exact timestamp. Record the returned `templateId`, query the created pod with `includeTemplate`, and keep an external API watchdog to terminate and confirm deletion.
- The GraphQL schema allows setting `terminateAfter` in the create mutation, but the schema does not expose that field on the pod result/query. A successful create response therefore cannot independently verify that the deadline was saved. Actual deadline behavior can only be confirmed by observing provider termination at/after the timestamp. Treat the deadline as a guardrail, and retain an external watchdog that calls the provider terminate API and verifies the pod is gone.

## Conclusion

The newly inspected template route changes the earlier conclusion: the documented cross-route composition can set the wrapper ENTRYPOINT in a private REST v1 template and submit both that `templateId` and GraphQL `terminateAfter` in the pod create mutation. This avoids building and pushing a custom image. REST v1 is deprecated and scheduled for retirement on 2026-11-15, so this is a short-lived but currently documented option. Current REST v2 still cannot express the pair in its create body. The template readback permits pre-rental verification of the stored command; the actual pod inheritance and deadline execution remain runtime checks. Keep the provider API watchdog because a field accepted at create time is not itself proof that the deadline fired.

Do not count an exited container or a stopped pod as verified billing termination. Verify the pod is absent/terminated in provider state after issuing terminate; separately record whether the GraphQL deadline fires without manual termination in a future real trial. No provider mutations or deployments were made during this investigation.

## Primary sources

- [RunPod GraphQL API spec](https://graphql-spec.runpod.io/)
- [RunPod GraphQL pod-management guide](https://github.com/runpod/docs/blob/main/sdks/graphql/manage-pods.mdx)
- [RunPod REST v1 overview and retirement date](https://github.com/runpod/docs/blob/main/api-reference/overview.mdx)
- [RunPod REST v2 pod create implementation](https://github.com/runpod/runpod-python/blob/main/runpod/api/ctl_commands.py)
- [RunPod CLI release history](https://github.com/runpod/runpodctl/releases)
- [RunPod v2 CLI change removing time-limit flags](https://github.com/runpod/runpodctl/commit/51ca7f0)

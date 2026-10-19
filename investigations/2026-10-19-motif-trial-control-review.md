# Motif remote trial controller review

Date: 2026-10-19

## Goal and issue

Assess whether `/private/tmp/motif_trial_control_draft.py` can safely run one bounded RunPod allocation with the private template, gated model endpoint, and cleanup guarantees. No paid calls or mutations are part of this review.

## Competing hypotheses and checks

1. **RunPod payload/readback assumptions may be invalid.** Compare the draft's GraphQL and REST operations to current official GraphQL and REST v1 schemas. Valid fields, types, and response shapes support the draft; mismatches identify pre-allocation failures or cleanup holes.
2. **The pod may allocate but fail before readiness because the template/gate contract is wrong.** Compare the exact entrypoint, env names, status response, and vLLM launch behavior in the frozen gate source. Matching interfaces and a viable in-container process support readiness; mismatches show likely paid-but-unusable allocation.
3. **Cleanup may report success without confirmed provider termination.** Trace the normal, ambiguous-create, timeout, exception, and watchdog paths; compare final verification with provider GET/delete semantics. A retryable control-plane delete plus positive terminal/absence evidence would support the bounded claim; a one-shot call or weak absence check would not.
4. **The cost/readiness numbers may overstate what is actually capped.** Calculate the enforced rate-time bound and inspect the readiness loop, timer start, storage settings, and report fields. The claim is supported only if every charge/lifetime and every readiness predicate is included.

## Evidence and conclusions

- Official REST v1 OpenAPI defines template create as returning a `Template` object, template list as an array, GET-by-ID as a single `Template`, and DELETE-by-ID as 204. The draft's create/readback/list/delete JSON shapes are consistent. Template fields include `volumeInGb`, `dockerEntrypoint`, `dockerStartCmd`, `isPublic`; explicitly setting `volumeInGb:0` avoids the documented 20 GB default.
- Official GraphQL schema defines `myself.clientBalance`, `currentSpendPerHr`, and `pods`; `GpuType.lowestPrice(input:)` and `LowestPrice.uninterruptablePrice`; `PodFindAndDeployOnDemandInput.templateId`, `minCudaVersion`, `terminateAfter`; and `PodTerminateInput.podId`. The date example is UTC RFC3339 ending in `Z`; use a canonical `Z` timestamp if strict parser compatibility is required. Create output schema includes the requested pod metadata but does not expose `terminateAfter` for readback.
- The draft's list-template recovery (`GET /templates` then filter by `name`) matches the official array response, and the random unique name makes the lookup narrow. REST v1 is deprecated and retires on 2026-11-15; this trial depends on it for template entrypoint creation.
- The live gate source reads `MOTIF_GATE_TOKEN` by default, and the latest draft now sets the same env name for pod, local provider, and gate process. The gate's `/trial-status` emits `vllm_ready`, and the latest draft now tests that key. These bindings are correct in the current draft snapshot.
- The gate's `vllm_command()` launches a nested `docker run`, publishes port 8000 on the nested Docker host, and does not bind vLLM to `127.0.0.1`. The template overrides the outer image entrypoint with Python and does not configure a Docker socket/daemon. The documented vLLM image supplies the vLLM executable as its own entrypoint; it is not evidence of nested Docker availability. This is a blocking runtime assumption: launch vLLM directly as a subprocess in the same container (`vllm serve ... --host 127.0.0.1`) or provide and verify an explicit nested Docker daemon/socket and reachable topology before any paid run. Direct subprocess is the simpler correction.
- The draft creates the watchdog only after allocation returns, at `started + 1500s`. A request timeout is 15s, and an ambiguous-create branch does six list polls; if those all fail, the finalizer has no known ID and depends on name listing. The provider deadline remains the only backstop in that state. The local watchdog calls `podTerminate` only once and ignores the return value; the finalizer calls it three times but does not require a positive provider deletion response.
- Final verification currently marks `pod_absent_verified=True` if the account pod list has no matching name. That is weaker than confirming termination by known pod ID, because a list can be temporarily incomplete/stale. Use GET-by-ID and require an authoritative not-found/terminated response (with bounded retries), and retain false/unknown on API errors. Never treat container exit or `podStop` as billing termination.
- The preflight rate threshold `$2/hour` times 1800 seconds bounds the quoted GPU component to under `$1`; checking `clientBalance >= $5` is not a $5 spending cap and the quote does not prove all storage/other charges are included. The report's 1800s deadline is based on `started` immediately before the GraphQL allocation request, so it is conservative relative to later scheduling, but the timer firing is not read back or proven. The 1500s local watchdog is a scheduled one-shot request, not yet a verified deletion.
- Readiness is bounded at 1200s and checks authenticated `vllm_ready`; the gate sets it only after both upstream `/health` and `/v1/models` succeed. The status predicate is aligned. The 20-minute cutoff leaves about 5 minutes before the local timer, but `probe.run()` can attempt up to eight calls and stops only after two consecutive errors. Its `complete` means all rows were attempted, not all compiled. The post-probe test `not probe['summary']['compiled']` accepts any positive compiled count; compare with the required count if the trial intends an 8/8 precondition for opening the viewer.

## Necessary changes before a paid allocation

1. Replace the nested `docker run` with direct `vllm serve` child invocation and explicitly bind `--host 127.0.0.1`; keep only the gate on exposed 8080.
2. Strengthen cleanup: start a bounded watchdog as soon as the pod ID is known; retry provider termination on API errors, verify by pod ID with the REST GET operation, and report uncertainty rather than setting absence from a possibly stale list. Keep the GraphQL deadline as an independent provider-side backstop.
3. Make the `$5` language precise: the current script constrains quoted GPU rate and time, checks available balance, and requests deletion; it does not enforce a total-spend ceiling or prove scheduled termination. Obtain/record any separate disk charges and preserve the run as an unverified cap until billing data is checked.
4. If all eight baseline rows must be compiled before viewer startup, require `summary.compiled == 8` (or `len(probe['calls'])`) rather than truthiness. If partial evaluation is intended, name that policy explicitly in the report.
5. Keep template readback as a pre-allocation check, but describe it as proof of stored template configuration only. The GraphQL pod response's `templateId` and request acceptance do not prove runtime inheritance or the scheduled termination firing.

## Sources

- [RunPod REST v1 OpenAPI](https://rest.runpod.io/v1/openapi.json)
- [RunPod GraphQL API spec](https://graphql-spec.runpod.io/)
- [RunPod REST v1 retirement notice](https://github.com/runpod/docs/blob/main/api-reference/overview.mdx)
- [RunPod GraphQL pod-management guide](https://github.com/runpod/docs/blob/main/sdks/graphql/manage-pods.mdx)

## Parent resolutions before allocation

The final gate launches vLLM directly in the pinned container on loopback; no nested Docker or persistent mount. The final controller uses an 18-minute readiness cutoff, requires all eight calls to compile before opening the viewer, retries termination, and verifies absence twice by exact pod-ID REST GET returning 404 as well as account-list absence. An ambiguous creation without a recovered ID remains unverified, not a claimed cleanup. The budget record now explicitly distinguishes the $5 planned ceiling from a provider-enforced billing cap (false), includes a conservative separate disk charge, and records the submitted deadline without claiming schedule readback. Fake-API lifecycle tests cover success, overrate cleanup, ambiguous allocation without retry, and insufficient balance, all four passed.

The vLLM 0.28 CLI documentation names `--no-enable-log-requests`, not the old draft `--disable-log-requests`; the final gate uses the documented flag. The gate's narrow allowlist intentionally has no child-log endpoint: automatic approval review rejected that expansion. Existing RunPod management UI is the diagnostic route.

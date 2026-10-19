# RunPod template preflight failure

The first controller execution passed live account and GPU quote checks, then ended before obtaining a template ID or making any pod allocation request. Receipt `hermes-testing/runs/harness2-runpod-motif-v1/receipt.json` records allocation_attempts=0 and zero pods. Template cleanup is unverified: the controller did not preserve the original HTTP status and its recovery path can mask it.

Following investigate: three hypotheses, with cheap read-only discriminators first.

1. REST v1 access/version/auth differs from working GraphQL. GET the documented template list with the same bearer credential. An HTTP auth/deprecation error supports this; a valid list rules out broad REST access failure.
2. Template payload violates a field limit/type (entrypoint size, pinned image or zero-volume representation). Inspect the exact submitted payload against the official OpenAPI schema, then recover the original error status or repeat creation only after exact-name absence is confirmed. A structured validation error supports this; auth denial does not.
3. Template creation succeeded but response parsing/recovery failed. List templates and inspect only an exact match to this run's random name. A matching stored template supports this and must be read/deleted; confirmed absence plus explicit rejection supports no mutation. Never repeat pod allocation or template creation blindly.

No paid resource exists for this run. The controller's public failure category needs enough redacted detail to distinguish HTTP and local validation errors; do not print account keys or response headers. Preserve the failed receipt.

## Discriminating results and correction

The default urllib client received HTTP403 with Cloudflare code1010 on the read-only REST template list. The same URL, account bearer credential and operation succeeded with HTTP200 and an empty list when the client identified itself truthfully as `Harness2-Motif-Experiment/1.0` and requested JSON. RunPod's current official SDK also sets an explicit User-Agent (https://raw.githubusercontent.com/runpod/runpod-python/main/runpod/api/rest.py). This isolates the transport header difference; it is not a rejected account credential, template field validation or successful-but-lost template creation. No existing templates were present, so exact-name recovery confirmed no original template to clean up. No browser identity was impersonated.

The autonomous goal authorizes proceeding with an explicit truthful API client identity. Added that header to controller and bounded model transport, preserving token/header redaction. The original failed receipt remains unchanged. HTTP status categories now survive the controller's failure record instead of becoming `see_stage`. A second run is permitted only because the first made zero pod allocation requests and template absence was verified.

Automatic review rejected the proposed full-source readback diagnostic because it would export local gate source to RunPod without separately explicit export approval. Do not retry that upload or disguise it. A safer diagnostic uses only a trivial inline print command and the same field shapes; it contains no repository source or credentials. The paid deployment remains pending explicit code-export approval after this diagnostic.

The trivial diagnostic isolated zero-value omission: REST GET returned no `dockerStartCmd`, `volumeInGb` or `isPublic` keys, although explicit empty/zero/false values had been sent. A second trivial template was checked through GraphQL and confirmed `isPublic:false`, `volumeInGb:0`, `containerDiskInGb:100`, `isServerless:false`; its encoded entrypoint matched. Both templates were deleted and their absence verified. The controller now checks meaningful entrypoint/command/port/image values through REST and privacy/storage through GraphQL, and supplies explicit nonempty gate startup arguments. It does not equate an absent REST privacy field with false.

Final inventory qualification: REST lists zero templates, whereas GraphQL lists 14 other templates. Exact owned-controller ID comparison and all three trial name-prefix checks found none remaining in GraphQL. Thus the supported cleanup claim is zero pods and no remaining templates from this trial, not zero templates across the account. The other templates were not modified.

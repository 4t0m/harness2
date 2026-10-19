# Retry-cap near-transfer trial

Freeze four cases before calls: cap-one and cap-two require wait; below-two and below-three require retry. Renamed jobs, changed cap and reversed row order reduce exact-response reuse. These are near-transfer variants of a known family, not broadly independent holdouts. No editor is fitted on their results in this experiment.

Compare first strict proposal to the same proposal plus at most one correction from rejection_feedback. A successful first proposal receives no extra call. This is a paired conditional-recovery comparison, not randomized causal attribution. Preserve failed proposals; evaluate all legal choices and unchanged state with the existing host oracle. Eight-call absolute maximum, 256 output tokens and 30-second hard deadline per call. No actual job dispatch. Cases with allowed retries guard against vacuous all-wait success.

Run: `.venv/bin/python -m experiments.production_transfer_probe`. The evidence file writes frozen fixtures before inference and every attempt afterward. Provider errors stop that case; they do not trigger opaque retries. Missing provider cost remains unknown.

## Observed result (2026-10-19)

Primary receipt: evidence/production-transfer-gemma-live.json. First-pass strict success 2/4. Both exhausted-cap cases incorrectly requested retry; the actual rejection_feedback helper returned current attempt/cap facts and each corrected to wait on its single allowed correction. Both below-cap cases correctly retried immediately. Final success 4/4, recovery 2/2, with six total calls. No format normalization or external job dispatch.

Initial prompts were 330–331 tokens; correction prompts 412–418. Completion lengths 14–24 tokens. Provider-reported total cost $0.0002238425. These hosted calls do not benchmark local hardware. End-to-end model-call latency for the two corrected cases was approximately 1.19s and 0.95s respectively, excluding local harness overhead. This is useful for low-frequency job management, not frame-by-frame avatar control.

Two offline runner tests confirm the fixtures include useful retry work, eight-call worst-case cap, preserved failed responses, feedback injection on second attempt and overwrite refusal. They do not establish model behavior; the live receipt does.

Next comparison: explicit attempt < max_attempts guidance upfront versus this fixed-plus-correction baseline. Then use a development-only Harness² editor to generate guidance and evaluate on additional frozen, untouched combinations (retry lineage, approvals and successful retry dependencies). Current outcomes are near-transfer within a known family, not an independent generalization or an actual Harness² adaptation result.

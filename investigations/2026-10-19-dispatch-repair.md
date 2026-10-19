# Production retry-cap diagnostic

Expected: blocked-02 waits. Observed: saved Gemma response retries dead_parent at attempt 3 with max_attempts 3. Host rejected it. Prior exact-fence repair changed nothing; no semantic repair tried. Source: evidence/production-dispatch-gemma-live.json and model_brief in production_dispatch.py.

Hypotheses and tests:
1. Missing cap rule: inspect exact serialized brief. Confirm if limit/rule absent; reject if both present. Inspection: max_attempts=3 and below-cap rule both present. Wording says retry cap while field says max_attempts; this ambiguity remains possible.
2. Stochastic lapse: repeat original prompt once. Success supports transient error; failure suggests repeatability but cannot exclude sampling variation.
3. Insufficient feedback specificity: compare original response plus generic rejection against original response plus factual attempt/cap rejection. Specific-only success supports actionable feedback; equal outcomes do not distinguish the mechanisms.

Run experiments/production_repair_probe.py: three calls maximum, 256 output tokens each, 20-second socket / 30-second total per call. Fixed development case only; no holdout reads, no actual dispatch. These single samples are diagnostic, not causal or statistical proof. Keep all outputs, latency, token counts, provider cost and strict host verdicts. Never expose host valid-choice enumeration to the model.

## Findings

Primary receipt: evidence/production-repair-gemma-live.json. Fresh repeat again retried dead_parent; generic rejection again retried it; specific rejection chose wait and passed. Three calls used 1,285 prompt tokens and 48 completion tokens; reported total cost $0.000074284. Latencies were approximately 1.05s, 0.90s and 0.65s. No real jobs ran.

The missing-rule hypothesis is contradicted by the serialized requests. Repeat failure makes a one-off lapse less persuasive, but sampling and ambiguous wording remain possible. Specific feedback is promising; one sample cannot isolate phrasing, added context or provider variability. No held-out transfer or Harness² adaptation gain demonstrated.

Implemented rejection_feedback as a host-owned helper: cap facts are derived from the current validated ledger; the helper never supplies the legal-choice list. Three focused tests cover renamed jobs, changed cap, no state mutation, accepted actions and schema/other errors. The live diagnostic used equivalent explicit text, not this newly added helper; a future matched trial must exercise the helper itself before claiming live integration.

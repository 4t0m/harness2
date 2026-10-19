# Selective dance edits: fresh policy evaluation

Twelve new, within-library briefs compare three fixed policies: full replacement, a one-pair patch, and patch followed by a fresh full replacement only when the compiler rejects the patch. The earlier eight-case experiments informed these policies; the new requests and source/target combinations were frozen before inference. This is fixed-policy evaluation, not a Harness² refinement run or a new task family.

| Local model | Full correct | Patch correct | Fresh fallback correct | Full / patch / route median seconds |
|---|---:|---:|---:|---:|
| Gemma4 E2B | 9/12 | 9/12 | 10/12 | 1.066 / 0.807 / 0.731 |
| Older Qwen3 8B | 10/12 | 11/12 | 12/12 | 1.410 / 0.563 / 0.803 |

These are complete operation latencies including validation; route includes fallback when needed. Condition order rotates by case and reverses for the second model. One local run per condition/case provides descriptive measurements, not stable timing or statistical generalization. Differences between standalone and route medians also reflect runtime variability; neither path has a guaranteed speed advantage.

The route used 13 calls for each model, compared with 12 each for standalone full and patch. Total: 74 local calls, no hosted charges. Both routes produced 12 structurally accepted edits. E2B still chose two wrong edits that complied with all structural restrictions. The route has no semantic oracle: it cannot recognize those mistakes. One rejected patch per model was recovered through a fresh full request that omitted the failed reply and error from model context.

Initial prompt sizes were 232–264 native tokens across formats, with full replies 24–41 tokens and patches 14–15. These short outputs support a compact local control interface; they do not establish end-to-end avatar latency or future 5090 throughput. For example, emitting 15 tokens within a 0.5-second generation budget requires 30 tokens/second, before input processing, dispatch and playback delay. Fallback consumes a second request and must be included in a response-time budget.

All 74 raw replies and all 24 routed operations were independently replayed. Accepted edits reproduce the source/revision/scope binding and exact preservation receipts. The compiler protects 62 of 81 motion samples and all unchanged clips; it does not implement a persistent avatar service transaction. Recheck authoritative current state when integrating with a live runtime.

Primary evidence: `evidence/dance-edit-policy-holdout-v1.json`. Sources: `experiments/dance_edit_policy_probe.py` and `experiments/dance_edit_policy_holdouts.py`. The preflight correction record preserves the original fixture and explains removal of two repeated combinations and a contradictory move name. Investigation: `investigations/2026-10-19-edit-policy-results.md`.

Recommendation: keep fresh structural fallback as an available bounded policy, especially for Qwen, while keeping semantic correctness visibly separate from structural acceptance. Next useful extension is a fresh task family or actual runtime edit with revision changes; repeatedly tuning these now-observed cases would not establish generalization.

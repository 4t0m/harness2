# Dance phrase brief adherence

Goal: compile valid joined motion while honoring explicit move/variation requests. Local first-pass results are E2B5/8 and Qwen8 7/8; all proposals compile, and the generic reminder recovers none. This is a new catalog/fixture pilot, not the earlier failed staging decomposition. Parent reviewed new fixture prose and clarified one contradictory amendment sentence before inference; constraints did not change. Current code is uncommitted on codex/dance-phrase-sequencing from b05dcfa. Prior staging showed schema-valid semantic errors, but that history does not identify these new causes.

Before reading failed contents, hypotheses and tests:

1. Oracle/prose mismatch. Compare each failing request to explicit slot/count constraints and inspect accepted alternatives. A model proposal that actually satisfies prose but fails the predicate supports a fixture defect. Direct disagreement with an unambiguous request rules it out for that proposal.
2. Compiler or caller relabels choices. Independently parse saved raw JSON, compare its ordered pairs to saved row moves and compiled records; compare source hashes against current files. Any changed order/variation or source drift supports this. Exact equality rules it out for these receipts.
3. Incomplete response or schema confusion. Check native done_reason and raw shape/labels. Truncation or unsupported catalog values supports a serialization/budget failure; complete exact-label choices with wrong requested values supports interpretation failure.
4. Specific semantic choice mismatch. Read raw choices for each failed case and its generic retry; identify move/order versus variation errors. Do not infer internal reasoning, caching, or prompt-attention mechanisms. No changed prompt or rescore during the frozen run.

Cheap tests: offline receipt inspection and recompile only; no new model calls needed. Preserve every failed proposal and evaluate structure separately from brief adherence and artistic taste.

## Findings

All20 local raw move arrays exactly match saved choices and freshly recompiled records. Frozen source hashes match. Every response finished with stop, used exact supported labels, and passed physical/structural compilation. No compiler relabeling, truncation or source drift is supported.

E2B requests versus replies: explicit soft sway becomes clear sway; amendment preserves middle order but changes explicitly soft final settle to clear; soft held intro is omitted, replaced by rise/sway/pulse/settle. Qwen8's requested two sways become sway plus pulse. Each directly conflicts with the public request; the corresponding host constraint agrees with that prose. All four generic retries repeat exactly the same wrong plan. This supports semantic choice failure for these samples, without establishing an internal cause. No model prompt, expected constraint or score was changed after observing failures.

Separate hosted comparisons on the same frozen cases all pass8/8 for Qwen3.6 35B-A3B, Qwen3.6 27B, Gemma4 26B-A4B and Gemma4 31B. This does not prove general reliability, robustness across quantization, or preference quality. The host oracle detects explicit fixture violations, not arbitrary production prose. The next useful work is richer independently frozen briefs/phrases and actual H2 adaptation with development/evaluation separation; do not replay this set as untouched heldouts.

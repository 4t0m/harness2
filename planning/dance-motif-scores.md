# Longer motif scores for small model direction

This experiment separates creative direction from movement construction. A small model chooses a recurring sway or pulse motif and four section accents. Trusted code expands that intent into a 32-beat, 16-second AABA score using the existing planted phrase shelf. The same score can also be expressed as sixteen explicit move pairs, allowing a direct test of token cost and brief fidelity.

## Contract and trial design

Each eight-beat section starts with rise, repeats its motif twice and ends with settle. The first, second and fourth sections use motif A; the third uses the opposite motif. Every move in a section shares its soft or clear accent. This gives 32 supported intent combinations. The host owns pose transitions, duration, complete frame generation and source-clip validation; the model chooses motif and accents.

Eight independently authored prose briefs cover explicit instructions, paraphrases, contrast and final amendments. Their expected intents are used only for offline scoring. The provider receives the prose and public contract. A valid but brief-inaccurate answer never triggers a repair; only public compiler rejection permits one correction. Preserve grammatical success and creative-brief fidelity as distinct results.

Compare two local runtimes (Gemma4 E2B and older Qwen3 8B) and two hosted MoE targets (Qwen3.6 35B-A3B and Gemma4 26B-A4B). Alternate compact and expanded condition order, reverse case order for alternating models, and keep one initial reply per case and condition. Bound the run to 128 calls, 384 output tokens per call and $0.25 reported hosted charges, with current price checks and stop-on-unknown-cost behavior. Local energy costs are not measured. Provider implementations differ, so latency comparisons do not predict dual-5090 performance.

The frozen phrase vocabulary remains extremely limited. This trial measures controllable motif structure and instruction following, not compelling dance, style authenticity or taste. Expanding a compact intent is work done by the host, not evidence that a model generated 321 joint poses. A flat preview will show two accepted local outputs if both motifs are available; it is a technical audition proxy rather than a finished character.

## Evidence locations

- Compiler: `harness2/dance_motif_score.py`; focused tests: `tests/test_dance_motif_score.py`.
- Frozen independent briefs: `experiments/dance_motif_cases.py`.
- Bounded runner and independent replay: `experiments/dance_motif_probe.py`, `experiments/dance_motif_summary.py`.
- Trial and summary: `evidence/dance-motif-model-v1.json`, `evidence/dance-motif-summary-v1.json`.
- Preview renderer: `experiments/dance_motif_preview.py`; preview evidence: `evidence/dance-motif-preview-v2.json` (original v1 retained).

The completed trial contains 84 calls: 48 local and 36 hosted, with $0.002284306 reported hosted cost. This is a fixed tool-representation comparison, not another Harness² refinement run. A useful compact interface can later become a bounded model-editable planning task in the corrected H2 adapter, with new evaluation briefs and the same host-owned movement checks.

## Completed comparison

| Model | Compact first and final brief fidelity | Expanded first and final brief fidelity | Compact / expanded calls |
| --- | ---: | ---: | ---: |
| Gemma4 E2B local | 6/8 | 0/8 | 8 / 16 |
| Older Qwen3 8B local | 8/8 | 0/8 | 8 / 16 |
| Qwen3.6 35B-A3B hosted | 8/8 | 4/8 | 8 / 12 |
| Gemma4 26B-A4B hosted | 8/8 | 8/8 | 8 / 8 |

All 32 compact replies compiled. E2B's two brief-inaccurate compact answers remained visible failures; their grammatical validity prevented correction, as designed. Every compiled expanded reply also matched its brief, but both local models failed the expanded grammar in all eight cases, and Qwen's hosted model failed four. The twenty public-feedback corrections yielded no recoveries. This supports compact intent as the default for this narrow grammar, not a broad claim about each model's creative ability. Eight cases and one initial reply per condition are a small sample.

| Model | Initial compact context | Compact output tokens | Median compact provider time | Expanded total provider time per task |
| --- | ---: | ---: | ---: | ---: |
| E2B local | 202–225 tokens | 23–24 | 0.89 s | 4.47 s |
| Qwen3 8B local | 202–225 tokens | 28–29 | 1.17 s | 6.25 s |
| Qwen3.6 MoE hosted | 198–221 tokens | 18–19 | 0.50 s | 1.45 s |
| Gemma4 MoE hosted | 207–350 tokens | 17–23 | 0.72 s | 1.65 s |

Times exclude host compilation and verification. Expanded initial contexts were 215–384 tokens across providers; replies were 74–114 tokens, including invalid plans. Local compact native decoding medians were about 65 tokens/s for E2B and 37 tokens/s for Qwen. For a hypothetical one-second *decoding-only* budget, a 29-token reply needs at least 29 tokens/s; input processing, queues, tool checks and rendering still add time. This arithmetic is not a GPU benchmark. Compact instructions allow the host to prepare sixteen seconds of animation without requiring the model to emit every joint sample.

## Motion and scope

Four focused compiler tests pass, including all 32 intents, equality of expanded and compact compilation, seam validation and corruption rejection. The old phrase shelf remains unchanged. The two selected local Qwen outputs are recompiled from raw replies and compared with their stored receipts before rendering; every score contains 321 samples. The video encodes samples 0–319 at 20 fps, while the exact 16-second endpoint sample is saved separately. The flat preview is silent and uses simple illustrated proxies. It demonstrates motif switching and accent control, not dance appeal or finished anime animation. No H3 generation or live avatar service was invoked.

The next useful extension is to offer richer prevalidated motifs and learn which variations a person prefers in paired auditions. Preserve the compact intent interface and separate human preference from grammar checks. For spatial choreography, connect the earlier verified route solver through an explicit contact-aware composition layer; translating planted feet wholesale would invalidate the contact assumptions. Before H3 reference use, validate its current input timing and frame-rate requirements rather than treating this 16-second preview as a ready reference asset.

## Independent audit and preview readback

Sol independently replayed all 84 calls, six source hashes, 64 model/condition/case slots and every repair lineage. Native/provider totals were 22,715 input and 5,414 output tokens. The [expanded-output investigation](../investigations/2026-10-19-motif-expanded-results.md) locates failures in actual missing contrast, section endings and accent placement. Both representations admit the same 32 valid intents. The broad enum schema permits those invalid arrangements; it does not force a correct choreography. Hosted Gemma's success also rules out a universally impossible expanded interface.

The final [16-second local preview](/Users/adom/Development/hermes-testing/runs/harness2-dance-motif-v2/preview.mp4) uses the first qualifying local Qwen sway and pulse calls in fixture order, not an aesthetic shortlist. It is 800×520, 20 fps and 320 encoded frames. Independent readback verifies 11,556 projected joint points and 642 actual source-image root markers; the head stays at least 10 pixels below the detail-label band. Four decoded video frames, one from each section, were visually inspected. This is sparse visual inspection plus full projection checks, not verification of every encoded limb pixel.

V1 media and evidence remain intact. V2 removes a redundant label that was partly covered by the panels; selected model calls, compiled receipts and all projected motion are exactly unchanged. Original renderer source is preserved at commit 4188aa3. The [preview investigation](../investigations/2026-10-19-motif-preview-schema.md) records the preflight data-field/layout corrections and the observed label cleanup. Reproducible final checks: `experiments/dance_motif_preview_check.py` and `evidence/dance-motif-preview-check-v2.json`.

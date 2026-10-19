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
- Preview renderer: `experiments/dance_motif_preview.py`; preview evidence: `evidence/dance-motif-preview-v1.json`.

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

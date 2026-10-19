# Matched creative-menu comparison

Frozen before inference: four explicit production briefs (contact repair preserving accepted spans, appearance lock, GPU preview budget, and obtaining taste feedback without inventing it), each with four legal options. Two Gemma models, three cyclic option orders, 24 total calls maximum. Provider ordering alternates by rotation. Each call has a 30-second hard deadline, 20-second socket timeout and 192 output-token cap. No retry inference. Exact single JSON fence repair is replayed on the same response. No actual jobs or user messages are sent.

The host menu filters legal actions; model decisions are scored against explicit constraints. This does not evaluate aesthetics, free-form choreography, generated motion, or raw-ledger reasoning. Options intentionally include tempting partial matches that violate one condition. Expected job identity stays fixed as option IDs move. Rotation tests are correlated observations, not 12 independent creative task families per model. No model is fine-tuned or adapted on these cases.

Artifacts: experiments/creative_menu_comparison.py contains fixtures and runner; evidence/creative-menu-comparison-v1.json preserves per-call requests, responses, provider usage/cost and strict/repaired matches; experiments/summarize_creative_menu.py computes descriptive aggregates. The fixture test verifies target identity survives all rotations. Hosted latency combines serving, networking and inference; it is not local decode throughput or a dual-5090 forecast.

## Results (2026-10-19)

| Model | Strict match | After exact fence repair | Median hosted latency | Observed range | Reported cost |
|---|---:|---:|---:|---:|---:|
| Gemma 26B A4B | 7/12 | 12/12 | 0.80s | 0.55–2.32s | $0.00023133 |
| Gemma 31B | 12/12 | 12/12 | 1.17s | 0.35–21.87s | $0.00158645 |

All four cases matched in all three option orders after repair. No provider errors or unknown-cost calls. Total reported cost $0.00181778. The 26B requests totaled 3,125 input and 148 output tokens; 31B totaled 3,126 input and 124 output tokens. This is a modest 24-call comparison despite the additional budget headroom.

Interpretation: the smaller model is adequate on these explicit menu-selection tasks once exact fence repair is applied. The larger model avoided formatting repair but showed no semantic gain in this sample. Hosted latency tails caution against blocking a real-time animation loop on responses; this is not a hardware/model-speed ranking. No evidence here establishes sustained production reliability, subjective dance taste, or a need to rent a GPU yet.

Next useful gate: connect choices to a bounded, reversible preview operation with output verification and interruption handling; test edits that preserve accepted scene regions. For a broader model ranking, add genuinely new task families rather than only more permutations of these four. Dense-model value may emerge in free-form interpretation or critique, which this benchmark does not measure.

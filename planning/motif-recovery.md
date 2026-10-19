# Explicit recovery for an interrupted actor

The new host operation `recover_to_rest` moves a frozen technical motif pose to the exact common rest pose over two seconds. The model still proposes only a compact motif and four accents. Stop immediately freezes the sampled pose, revokes pending requests and clears queued replacements. Recovery is a separate explicit action, can itself be stopped, ends frozen at rest, and requires a fresh request to start another phrase. Requests during recovery are rejected before inference. The browser disables futile new-direction requests while frozen away from rest.

## What was exercised

Sol implemented rigid recovery and runtime admission; Luna independently checked the motion and authored the bounded live lifecycle driver. The parent integrated HTTP/UI controls and ran local model/browser trials.

The offline sweep enumerated all 32 compact intents and 10,272 source-frame instances, deduplicating to 121 distinct poses. All 121 preserve exact starting pose, exact rest endpoint, planted feet, finite coordinates and the 19 segment lengths. Articulation parameters use quintic easing; limbs are reconstructed, rather than linearly blending joint positions. The maximum observed joint step was 0.01987 m at 20 fps, speed 0.39735 m/s and finite-difference acceleration 0.61576 m/s². These describe this small library and are not biomechanical acceptance thresholds. Only this reconstructible planted pose family is supported.

The first offline restart check accidentally selected rest as its source. V1 is retained; V2 chooses the pose furthest from rest and explicitly proves the interrupted sample differs from both endpoints. That nontrivial restart also passes. A runtime test initially compared local clip timestamps as well as pose; its failure and corrected assertion are documented separately.

## Actual local trials

Six actual Ollama calls ran, with zero hosted inference fees (hardware and energy costs unmeasured):

| Run | Calls | Result |
|---|---:|---|
| Gemma E2B cold, v1 | 1 | Correct intent, refused after five-second admission deadline; 5.27s loading dominated 5.87s provider wall time. |
| Gemma E2B warm, v2 | 2 | 22/22 lifecycle checks, including interrupted recovery and fresh restart; provider 0.805/0.908s. |
| Qwen3 8B, v1 | 2 | 22/22 lifecycle checks; provider 4.339/0.905s, first load 3.28s. |
| Qwen3 8B browser controls | 1 | Direct/Stop/Return to rest/End session observed through actual UI; provider 0.943s. |

Initial contexts were 210 tokens in the API trials and 217 in the browser trial; outputs were 23–29 tokens. Four admitted warm requests required about 1.10–1.24s from request to compiled admission, including roughly 0.29–0.30s preparation. Recovery adds zero input/output tokens. Cold-load failure remains in the results; it is not silently retried or excluded from completion counts. These few runs do not establish reliability percentiles or dual-5090 performance.

Independent replay matched all 2,793 logged server samples and 3,876 total server/client observations. Twelve observations share a millisecond timestamp with an event and match a valid before/after state; their exact ordering is unresolved at this clock resolution. All server source hashes matched. The audit preserves the cold failure rather than counting it as an admitted success.

All four finite servers acknowledged shutdown, drained their workers, exited, and had closed loopback ports. The saved screenshot captures the actual Returning to rest state. It establishes the rendered proxy/control state, not continuous smoothness or finished anime acting quality.

## Latency budget for a future local host

For a response of N output tokens, the decode requirement is N / (deadline − loading − prefill − compilation − transport). A nonpositive denominator means decode speed alone cannot meet the target. Use measured component times; do not equate tokens per second with actor frame rate.

Across the four admitted warm calls here, provider-reported decode speed was about 49 tokens/s for Qwen and 63 tokens/s for E2B. Holding each call's other observed costs constant, a two-second admission target would need about 19–22 tokens/s; a one-second target would need roughly 76–140 tokens/s. These are counterfactual arithmetic on four observations, not measured 5090 requirements or a reliability guarantee. Loading can still defeat either target.

A promising cheap next optimization is validated immutable score caching: each model response selects from only 32 scores, yet this implementation recompiles and verifies 321 frames every time (~0.3s). Cache validation and source/version identity must remain host-owned, and cold compile vs cache hit must be reported separately. Pre-staging a cue several seconds ahead may matter more than increasing decode speed. No cache optimization was included in these measurements.

## Why this matters for small models and H3

Frame rate does not require a model to generate joint coordinates at that rate. A small model can choose one of the validated phrases; host code owns timing, interruption, geometry and recovery. The useful latency question becomes how long a new direction can wait before a cue deadline, with loading tracked separately. Extending the vocabulary requires new motion assets and transition contracts, not simply longer prompts.

The next substantive experiment should test variation selection from scene context and cue scheduling with early planning: locally fast selection, a bounded queue, missed-cue fallback, and exact relative placement. Compare fixed guidance, one correction and actual Harness² adaptation on frozen, nontrivial scenarios. Keep motion correctness separate from human preference; this round adds control capability but demonstrates no learned choreography, taste improvement, H3 integration, fine-tuning or Harness² adaptation gain.

## Reproduction and receipts

Use `experiments/motif_recovery_check.py` for the CPU sweep. Start `python -m harness2.motif_viewer` with an explicit supported model, a fresh absolute output path and finite lifetime; run `python -m experiments.motif_recovery_live_trial --url <printed-loopback-origin> --output <new-receipt>`. The driver allows two accepted provider requests, an 80s trial deadline and bounded stop/shutdown cleanup; it preserves failures.

Receipts: `motif-recovery-offline-v2.json`, `motif-recovery-{e2b,qwen}-live-*.json`, matching server receipts, `motif-recovery-ui-check-v1.json` and independent `motif-recovery-live-check-v1.json`. Historical v1 source hashes may differ from the later checker/runner revisions and must remain tied to their original source versions. No GPU rental or source export occurred in this round; the separate RunPod code-upload approval remains pending.

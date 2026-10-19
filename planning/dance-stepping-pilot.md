# Local-model stepping pilot

The model can now select four side steps and their accent strength; trusted code turns those choices into four seconds of full-body proxy motion. Every step shifts the stance 0.20 metres in world left/right, so relative positioning is computed by the host. The leading foot moves first, followed by the trailing foot; soft/clear changes arm and body accents while preserving the foot trajectory.

This is a separate prototype in `harness2/dance_steps.py`. The earlier planted phrase library and its model evidence remain frozen. The stepping compiler checks 81 samples, all 19 declared skeletal segments, ground-contact flags against positions, planted-foot sliding, clip joins and cumulative root displacement. All 256 legal four-step plans compile. Thirteen motion/stepping/render-readback tests pass, including corruption rejection. These are kinematic checks, not dynamics: root position averages the ankles rather than shifting weight over the support foot, and sinusoidal foot lift has nonzero vertical velocity at landing/takeoff. No balance, collision, biomechanical realism or dance appeal claim is supported.

## A small model needs a literal tool contract

The first eight local calls exposed a poor interface. The prompt placed `step_left|step_right` inside a JSON example, while the schema accepted any string. E2B emitted coordinate-like strings and alternatives in all four cases; Qwen emitted literal alternatives in three. The compiler correctly rejected them. Saved raw replies, independent parser replay and source hashes rule out a runner extraction bug or source drift.

A 24-call diagnostic then compared explicit prose naming each identifier against the original prompt, with and without a schema enum. The original/free cell is retained from the first run; the other three cells ran afterward on the same now-observed briefs. This is exploratory interface refinement, not heldout evaluation or an automated Harness² learning result.

| Interface | Gemma E2B correct | Older Qwen3 8B correct |
|---|---:|---:|
| Original wording, free strings | 0/4 | 1/4 |
| Original wording, enum strings | 3/4 | 4/4 |
| Explicit wording, free strings | 4/4 | 4/4 |
| Explicit wording, enum strings | 4/4 | 4/4 |

All 24 diagnostic replies compile. The remaining E2B error with original wording plus enums demonstrates that legal identifiers do not establish the requested sequence. The compiler is unchanged throughout. The enum is a union of move and variation words, so the host still validates pair positions. The clearer prompt changes several wording details; this does not isolate a single phrase as the cause.

## Context and timing

For the explicit/enum condition, E2B used 183–189 prompt tokens and 38 output tokens; Qwen used 187–193 prompt tokens and 42 output tokens. The initial message text is 724–748 characters. Median request-plus-validation latency was 1.08 seconds for E2B and 1.42 seconds for Qwen. Native median decoding was 63.6 and 35.0 tokens/second respectively, excluding prefill, loading and request overhead. These measurements describe this Mac run, not a dual 5090 forecast.

A 42-token reply requires 84 tokens/second for a 0.5-second generation budget, before overhead. For scene preparation, a roughly one-second plan producing four seconds of motion can be useful. Live reactive control needs shorter commands, prepared movement queues and host-owned interruption; faster decoding alone does not solve correctness or stale actions.

Total stepping calls: 32 local, no hosted charges. Reproduce measurements with `experiments/dance_steps_summary.py`; evidence is in `dance-steps-model-v1.json`, `dance-steps-contract-v1.json` and `dance-steps-summary-v1.json` under evidence/.

## Visible result

Preview: `/Users/adom/Development/hermes-testing/runs/harness2-dance-steps-v1/comparison.mp4`. Cyan/left is soft, orange/right is clear. Both come from accepted E2B explicit/enum replies to the preset alternating-step requests. They return to their starting positions; the accent difference is modest.

The encoded video is four seconds, 40 frames at 10 fps, 512×320. Source tracks contain 81 samples at 20 fps; the render checks 40 selected source indices 0–78, not the terminal index 80. Blender's actual joint positions agree within 1.01e-7 metres and segment lengths within 9.51e-8 metres. Render plus encoding took 1.75 seconds. Six decoded stills were inspected: both complete rigs, foot lifts and stance changes are visible. This is proxy motion with sparse visual inspection, not a skinned character, human-auditioned choreography or H3 execution. Full provenance and scene readback are in `evidence/dance-steps-preview-v1.json`.

## Next experiments

1. Freeze explicit wording and enum constraints, then evaluate newly authored relative-position and correction briefs. Keep impossible requests distinguishable from model failures.
2. Add smooth lift/landing derivatives and a support-foot weight-shift prototype as a separate motion revision; preserve this baseline. Test physical limits independently of plan accuracy.
3. Compose stepping and upper-body phrase families only after defining compatible boundary poses and root transforms. Do not concatenate the two current libraries without an adapter.
4. Use a short preference audition to decide which accents deserve a larger library. Human taste is a separate signal from geometry and exact plan compliance.

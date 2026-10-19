# Model classes and useful task shapes

Research checkpoint: 2026-10-18. Recommendations below are hypotheses for Harness² trials, not established model rankings or local speed measurements. Earlier trials used Qwen3.5 and Gemma 4; do not silently relabel them as newer models.

## Initial shortlist

- Gemma 4 26B A4B: first compact controller candidate. Current evidence: five live actor-intent selections passed, with 267–284 prompt tokens and 36–47 answer tokens, 0.528–3.696 seconds end-to-end on OpenRouter. No local throughput claim. One creative retry response selected the correct failed job but used Markdown fences and failed strict parsing.
- Gemma 4 31B: comparison candidate for visual interpretation, continuity review and richer creative briefs. Test against 26B on identical tasks before giving it a permanent role.
- Qwen3.6-35B-A3B: compact MoE comparison for event handling, task routing and short scene decisions. Official card identifies 35B total / 3B activated, hybrid attention and vision input. Active parameter count is not resident weight memory and does not guarantee faster serving. Source: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- Qwen3.8-27B: current dense candidate for multi-step scene direction, tool authoring, continuity repair and production management. Official card describes dense 27B, native image/video understanding, default thinking with per-request controls and 262,144 native context extensible to 1M. Treat these as capabilities to qualify, not proof of local task reliability. Source: https://huggingface.co/Qwen/Qwen3.8-27B
- Qwen3.6-27B: useful version-controlled comparison only if needed; avoid multiplying the matrix before meaningful tasks exist. Source: https://huggingface.co/Qwen/Qwen3.6-27B
- Very small 1–9B models: deliberately narrow event classification, pose-atlas selection, acknowledgements, one-step ledger operations and fault triage. A model that can do these reliably need not be a competent general-purpose autonomous agent.

Public OpenRouter catalog checked on the checkpoint date: compact MoE Qwen3.6 route $0.15/$1 per million input/output; dense Qwen3.8-27B $0.24/$2.20; Gemma 26B $0.0675/$0.225; Gemma 31B $0.20/$0.40. Both Gemma free routes were listed. Prices/availability vary and must be checked for a run; free-route availability is not a latency guarantee. Source: https://openrouter.ai/api/v1/models

## Three timescales

1. Frame loop: deterministic interpolation, blink/lip-sync, pose blending, collision limits and automatic neutral reset. No language model call per frame.
2. Beat/event loop: fast model selects a legal action, target, intensity and duration from a compact state packet. 20–60 output tokens is a target, not a requirement already demonstrated for all tasks. One bounded correction or safe fallback; expired decisions are discarded.
3. Director loop: richer model plans scene intent, coverage, transitions, visual continuity and variations. It can take seconds or minutes while the performer continues a valid queued beat. Long-running assistant memory lives in a compact ledger plus retrieval, not an indefinitely growing hot prompt.

The director and performer may be the same checkpoint with different prompts/budgets. Separate checkpoints consume additional resident memory; benchmark single-GPU replicas versus cross-GPU tensor parallelism rather than assuming dual GPUs double speed.

## H3 scene skeleton

Interpret skeleton in two explicit senses: (a) a shot/beat plan with poses, gazes, relative positions and camera cues; (b) actual rig joint/keypoint tracks. First build (a). Producing (b) needs rig-specific retargeting, interpolation and decoded-frame verification. Neither proves H3 accepts the chosen export format.

Pipeline: brief -> director beat list -> validated pose/shot score -> trusted relative geometry and scheduling -> low-cost animatic/keyframes -> human creative review -> confirmed H3 input adapter. An avatar model selects from pre-authored moves, including variants for facing, distance, handedness, intensity and transition compatibility. The compiler owns coordinates and timing. Retain the source scene revision and cancel stale commands when actors move.

Initial demo: three beats, two characters, neutral/listen/point/turn-away atlas. Freeze actor identity and scene revision. Ask a compact model to cast each beat; independently verify target IDs, nonoverlapping time slots, duration and pose compatibility. Then test interruption, target motion, unavailable pose and partial completion. Current flat runtime supports a much smaller control set, so score generation remains distinct from actual playback.

## Additional useful roles

| Role | Compact task | Evidence of completion |
|---|---|---|
| Live companion | classify speaking/listening/interrupted event; choose gaze/gesture | deadline met, valid state transition, visible reaction |
| Creative production manager | retry failed item, preserve accepted variants, queue dependency | ledger receipts and no duplicate jobs |
| Continuity assistant | compare two scene-state packets, flag clothing/prop mismatch | held-out planted mismatch detection, false alarms |
| Art director | propose controlled silhouette/expression variations | invariants plus human preference; schema alone insufficient |
| Scene librarian | retrieve compatible pose/shot asset by tags | correct asset/version/rights metadata, no invented IDs |
| Meeting assistant | route event to note/timer/followup draft | source-linked capture, no unauthorized send |
| Tool mechanic | repair adapter/schema in a sandbox | independent contract tests and replayed failed task |

## Evaluation that can select a model

Freeze held-out tasks with changed names/order/distractors; all current actor fixtures choose the same target ID, so five successes do not prove robust generalization. Compare raw strict output, narrow deterministic formatting repair, one feedback retry, and adapted harness independently. Count all tokens, failures, duplicate actions and correction cost.

Measure cold/warm time to first token, input prefill rate, decode rate, action latency p50/p95, expired commands, memory and concurrency. Include actual reasoning tokens: hiding reasoning does not necessarily disable computation. Test context at compact/8K/32K/long tiers with an early critical fact and a late conflicting event. Cache savings and context retention require engine-specific measurement.

Latency budget illustration (not a hardware forecast): 40 output tokens at 40 tokens/s needs 1 second for decoding alone; a 0.5-second reaction target with 0.2 seconds reserved for prefill/network/validation needs about 133 tokens/s. Short enum outputs and queued animation often help more than a larger maximum context window.

Next selection gate: qualify thinking-off/structured-output support on the exact provider, then use matched prompt and token budgets. For local Q4, measure quality and KV-cache memory separately; OpenRouter results are not local quantization benchmarks. Fine-tuning candidates are accepted, source-linked corrections split by scene/task family, with untouched holdouts and explicit permission for any private data.

## Context distinction to preserve

User recalls a long-context MoE and a different Gemma with a small rolling context. Do not assume the second model is 31B. Official Gemma 4 documentation lists 256K overall context for both 26B A4B and 31B; their 1024-token sliding attention layers coexist with global attention. E2B/E4B have 512-token local windows but 128K overall context. Thus local attention window and total remembered context are different quantities. Source: https://ai.google.dev/gemma/docs/core/model_card_4

RecurrentGemma is a separate older candidate using recurrent state plus local sliding-window attention, which more closely fits the rolling-memory description; exact intended checkpoint remains unresolved. Source: https://ai.google.dev/gemma/docs/recurrentgemma

Regardless of checkpoint, test an explicit rolling recent-event buffer plus durable host ledger: current speaker, target gaze, emotion cue, active action, scene revision, recent interrupt, and pending deadline. Reinsert nonnegotiable identity/scene facts in every request. Measure old-fact recall, current-event response and stale-action cancellation separately. Recurrence can retain compressed information beyond its local attention window; it is not an exact archive of all prior events. This is a distinct experimental condition from feeding a long transcript to a long-context model.

Gemma context research also distinguishes modality: 26B/31B have no native audio input; E2B/E4B/12B do. A voice companion using the former therefore needs a separate audio/transcription path. Google's MRCR v2 8-needle 128K results differ substantially (26B:44.1%;31B:66.4%), so test effective retrieval rather than treating advertised context as dependable memory. These are vendor benchmark results, not our measured workloads. Source: https://ai.google.dev/gemma/docs/core/model_card_4

# Motif playback replacement and interruption

The compact motif score needs a host-owned playback contract before it can become an avatar tool. This experiment tests queued replacement and cancellation while local models prepare new scores. It preserves the validated motif compiler and source phrase shelf.

## Control contract

The host owns monotonic time, request identity, deadlines, source samples, pending replacement and stop. Initial accepted intent starts from rest. A replacement waits for the next four-second section boundary, where both scores share the same resting pose. Interrupt clears pending and queued work and freezes the current sampled pose. A delayed or duplicate reply cannot restart playback. Restart from a frozen non-rest pose requires a separate transition policy; this experiment must not invent a blend or silently jump to rest.

Compilation and full motion verification run outside the playback state lock. A short atomic delivery step rechecks request identity and deadline before admitting a prepared score. Model output stays the existing motif-plus-four-accents JSON; the model has no authority over revision, timing, cancellation or pose validation.

## Bounded live trial

Use one freshly authored three-request scenario per local model, E2B and older Qwen3 8B. After the initial score starts, request a replacement near playback time 0.5 seconds. It should be ready before the shared boundary at four seconds. Launch a third real model call after that switch and interrupt about 100 milliseconds later. Keep sampling long enough to observe the delayed completion and frozen pose.

Limit the run to six local provider calls, twenty seconds per request and finite sampled playback per scenario. Preserve exact request, inference, compilation, delivery and sample times. Record any missed boundary, deadline, late host sample or incomplete reply as observed. Do not fabricate a late reply if a real call finishes before interruption.

The scenario requests and expected compact intents are separate: expected intents are offline measurements only. The controller independently enforces state authority and motion validity. A semantically wrong but valid replacement is still a brief-fidelity failure even if its timing is correct.

The resulting preview will be rendered from samples collected during actual wall-clock orchestration. This remains a finite local control test with an after-the-fact video, not a persistent interactive avatar viewer or a continuous frame-rate guarantee. Preserve that distinction when reporting latency or visible execution.

## Observed local results

Six genuine local calls completed: three each for Gemma4 E2B and the older Qwen3 8B. All six compact outputs matched their fresh briefs. No hosted calls, repair calls, or H2 refinement ran in this round. Total native usage was 1,286 input and 156 output tokens; local electricity/hardware cost was not measured.

| Measurement | E2B | Qwen3 8B |
| --- | ---: | ---: |
| Initial provider time | 3.304 s | 1.959 s |
| Replacement provider time | 0.980 s | 0.914 s |
| Replacement ready after playback begins | 1.764 s | 1.739 s |
| Replacement effective boundary | 4.000 s | 4.000 s |
| Interrupt after playback begins | 4.353 s | 4.355 s |
| Stale completion after interrupt | 1.115 s | 1.153 s |
| Maximum observed sampling lateness | 17 ms | 18 ms |

Compilation and verification took 0.279–0.302 seconds per reply outside the playback lock. The third inference actually started before interruption and completed afterward in both runs; both deliveries were rejected as stale. Each run captured 141 samples, including 54 unchanged samples after stop. The initial calls include loading effects and this is only one sequence per model, not a latency distribution or hardware comparison.

The parent checker independently reconstructs every expected pose from raw replies and timestamps. Sol's separate audit reproduces all six brief verdicts, prompt/response bindings, source hashes and 282 sample comparisons. Six deterministic scenarios also pass: exact 3999/4000/4050 ms boundary behavior, interruption followed by a stale delivery, and queued replacement canceled by interruption without another request first clearing the queue. Eleven focused compiler/runtime tests passed.

## Evidence and limits

- `evidence/dance-motif-runtime-v1.json`: raw requests, replies, native usage, preparation timing, events and samples.
- `evidence/dance-motif-runtime-check-v1.json`: parent independent replay.
- `evidence/dance-motif-runtime-audit-v1.json`: separate Sol review.
- `evidence/dance-motif-runtime-deterministic-v1.json`: six offline timing/cancellation scenarios, zero provider calls.

This establishes a narrow host-owned control contract. It does not establish compelling choreography, natural-language stop detection, persistent GUI integration, smooth restart from an arbitrary pose, or H2 learning. PreparedScore is an internal Python transport, not a security boundary against hostile code. Provider output enters only as raw JSON for host compilation.

The next useful extension is a checked return-to-rest transition or an explicit restart refusal shown to the caller, followed by richer motion and preference comparison. Increased spending should buy fresh held-out tasks, broader motion coverage or GPU execution evidence; repeated easy cases alone would not justify it.

## Verified preview

The finite seven-second recording is at `/Users/adom/Development/hermes-testing/runs/harness2-motif-runtime-v1/runtime-preview.mp4`: 800×550, 20 fps, 140 encoded frames plus a separate terminal sample. Labels derive from recorded events; this is rendered after capture, not a live display. All 5,076 projected joint points and 282 source-image root markers pass an independent check. Sparse decoded frames at indices 40, 80, 88 and 120 were visually inspected: text remains readable, the resting switch and frozen pose are visible. Render and media-check evidence are `dance-motif-runtime-preview-v1.json` and `dance-motif-runtime-media-check-v1.json`. Rendering made zero provider calls. The generic illustrated figures remain technical motion proxies.

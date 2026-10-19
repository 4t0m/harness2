# Capability status — 2026-10-19

This is the current entry point. Earlier active-goal checkpoints are historical, including statements that a live improver or avatar execution is still absent. Evidence below supersedes those statements. The broad exploration goal remains active; no local5090 endpoint, GPU deployment, fine-tune, learned dance or artistic preference model has been qualified.

| Capability | Current evidence | Practical boundary |
|---|---|---|
| Actual Harness² recursion with model solver and editor | production-h2-gemma-v2: all3edits accepted, changed guidance, development composer passed | No aggregate evaluation gain: fixed1/4, fixed+correction2/4, adapted1/4. Scripted k=1 selection/NO_ENTRY memory. |
| Raw-ledger retry correction | production-transfer-gemma-live:2/4 first pass,4/4 after one correction | Near-transfer only; harder combinations did not preserve this success. |
| Creative priority selection from legal actions | creative-menu-comparison-v1 and summary: two Gemmas,4cases×3orders,12/12 each after repair | Explicit instruction matching, not aesthetics.26B strict7/12;31B12/12. No general reliability estimate. |
| Compact interface | Comparison prompts roughly234–282tokens; gesture variation102input/18output | Hosted latency is not local tokens/s. Transport/socket timeouts and total deadlines remain separate. |
| Flat-avatar bridge | avatar-bridge-live: command delivery/readback and neutral cleanup | Directional gaze remains visually unconfirmed. Listener/process must be revalidated; historical handle is not live-state proof. |
| Actual 3D procedural-avatar preview | menu-blender-preview-v1: model picked wave; Blender output hashes, decoded PNGs, visual arm raise | Existing deterministic action;3stills do not prove smoothness. |
| Protected-span motion edit | blender-span-preview:48-frame transforms and isolated pixel comparisons | Host-authored edit; same-process mutation/render failed and was replaced by isolated renders. |
| Model-selected motion variation | gesture-variation-live: model chose restrained, bounded compiler, fresh application/verification processes, video | One rig/gesture and two named variants. No model interpretation of video or human taste evaluation. |
| Dance score | dance-score-offline: beat and synthetic boundary constraints | No executable dance motion or qualified leg/contact rig. |
| Runtime interruption/stale responses | event-runtime-replay plus production-menu tests | Logical-clock/pure-state mechanisms, not a fully integrated real-time renderer service. |

Evidence files are under `evidence/`. Relevant detailed notes: production-h2-trial.md, creative-menu-comparison.md, menu-blender-preview.md, blender-span-preview.md, model-gesture-variation.md and dance-lab.md. Actual media remains in the Hermes lab's `runs/` folders; do not confuse Git receipts with bundled media assets.

## Decisions supported now

1. Use trusted code for legal-action enumeration, state revisions, exact edit bounds and artifact verification. Let the model choose intent/priority/variation. This changes model responsibility; it is not proof of improved raw constraint reasoning.
2. Exact-single-JSON-fence removal is worthwhile, with raw output retained and repaired acceptance reported separately. Never extract arbitrary prose into an executable instruction.
3. Current evidence does not justify paying for a denser model merely for these menu choices. It may justify denser models for richer interpretation or critique, which needs different evaluation.
4. Render immutable Blender scenes in separate processes for comparisons. Preserve and inspect media independently of success reports; the first span comparison caught identical wrong videos.
5. Stop multiplying nearly identical robot-arm tests. Next substantive target is an existing humanoid/VRM rig and a broader motion vocabulary, followed by user auditions.

## Unfinished milestones

- Demonstrate repeatable fixed/repair/adapted differences on genuinely untouched task families; no successful general adaptation claim yet.
- Connect interruption, leases and state revisions to actual visible avatar actions, with recovery evidence.
- Verify a usable humanoid/flat-anime rig with meaningful motion and preservation controls.
- Build a short reusable dance phrase library with real timing/contact/transition metadata, then audition visible alternatives.
- Qualify an actual local or bounded rented endpoint, measuring load/prefill/decode/end-to-end latency separately. Hosted Gemma tests do not establish quantized/local equivalence.
- Curate validated training traces only after family splits and clear licensing; no QLoRA training has run.

User allows roughly10× additional spending when it improves experiments. Spend for decision-changing coverage, repeated observations or meaningful model comparisons; keep explicit call/time caps. No pod has been launched under this work.

## Humanoid VRM integration update

`vrm-intent-live.json` now verifies a Harness²-side model farewell/right-side intent through the existing Hermes/Eidoverse VRM tool: host-derived x=0.35, matching root readback, animated right-arm state,12-frame video and visual raised-arm inspection. Runtime is the existing isolated Deno under Hermes runs/round6, not PATH. This advances humanoid rig execution; it does not establish a persistent session or dance capability. See vrm-relative-intent.md.

## Local inference update

Ollama on the Mac is now live-verified. Installed older Qwen3 8B and30B-A3B Instruct Q4_K_M completed native menu trials (3/4 and4/4). The30B model also completed the actual relative-intent VRM render through the existing provider interface. See local-serving-checkpoint.md for first-load/warm timings, generation settings and exact identity limits. This qualifies a local Mac route, not dual5090 or RunPod serving. No new model was downloaded.

## Local 8B actual Harness² priority experiment (2026-10-19)

`evidence/local-priority-h2-v1.json` records 16 native Ollama Qwen3-8B calls and three hosted Gemma-4-31B editor calls through the real Harness² recursion. Sol implemented the adapter; Luna independently authored six heldouts without seeing development cases or editor outputs. The runner rotates option positions deterministically and freezes a fixture hash before inference. Host expected choices never enter the editor context.

All six heldouts passed first try with fixed guidance and again with the selected guidance. However, the selected final tree was identical to baseline, despite three accepted intermediate editor outputs. This is **no demonstrated adaptation gain**. The earlier budget failure also did not reproduce under this revised prompt/interface. No correction calls were triggered. These are simple constraint choices, not generated choreography or judged visual quality.

The 16 local calls used 225–352 input tokens, with median end-to-end latency 0.881 seconds (range 0.346–4.212 seconds, including initial loading). The three hosted edits reported $0.002094 total. Local energy and hardware costs were not measured. The local model is older Qwen3 8B, not the incoming Qwen generation.

The new adapter checks semantic correctness separately from formatting, supports exact single-fence repair as an optional axis, and preserves call caps and receipts. Ten relevant adapter/fixture tests passed. Next useful test: multi-step state changes and harder combined constraints, frozen before tuning; do not reuse these six cases as unseen evaluation. The inherited editor prompt still contains production-dispatch wording, which should be made domain-specific before interpreting further adaptation comparisons.

## Local event timing and stale-response rejection (2026-10-19)

`experiments/local_event_probe.py` and `evidence/local-event-v1.json` exercise real native Ollama inference against the CPU EventRuntime. Each model handles listen, interrupted acknowledgement, then a fresh neutral instruction. A real host timer interrupts 100 ms after launching the acknowledgement request; its eventual response is rejected by request identity. These are model decisions plus runtime state transitions, not a rendered avatar or an actual Harness² refinement run.

Both Qwen3 8B and Qwen3 30B-A3B chose all three expected actions, emitted strict JSON, rejected the interrupted response, and ended neutral. Warm 8B responses took 271/333/338 ms; warm 30B-A3B responses took 249/322/342 ms. Warmup calls took 1.336 and 2.705 seconds respectively. Inputs were 70–78 tokens for 8B and 62–70 for 30B-A3B; outputs were seven tokens each. Six observations do not establish a latency percentile or sustained service capacity.

The real acceptance deadline was five seconds. The 250/500/1000/2000/5000-ms counts in the receipt are retrospective comparisons of measured call durations, not independently executed deadline trials. Thread scheduling and delivery add a small overhead beyond call timing. No API fee was incurred; energy and hardware cost remain unmeasured. Thirteen relevant runtime/adapter/fixture tests passed.

Next integration: connect model-generated, validated gesture intent to the existing offline VRM external-event renderer, preserving immediate host cancellation and preventing delayed completions from restarting motion. Keep that distinct from a persistent viewer and from movement-path planning.

## Local-model-driven 3D interruption (2026-10-19)

`experiments/vrm_model_async_probe.py` now connects local Qwen3 8B intent to the existing offline GPU VRM renderer. Initial strict JSON chose wave_goodbye/right; the host compiled anchor 0.1 plus offset 0.25 to root x=0.35. Initial inference took 0.612 seconds (53 input, 15 output tokens). A second genuine model call was launched when the renderer signaled readiness; the host immediately interrupted. That response arrived after 0.481 seconds with the old revision and was rejected.

`evidence/vrm-model-async-v1.json` records completed rendering, interrupted/stale_rejected events and 39 neutral post-stop frames with no registered mixer and unchanged root. The 48-frame 640x360 video lasts 3.2 playback seconds. Parent inspection of frames 8 and 47 visibly confirmed raised versus lowered arm. Six existing VRM verification tests passed. No hosted model calls occurred.

Media: `/Users/adom/Development/hermes-testing/runs/round6/eidoverse-video/work/eidoverse-harness2-model-async-v1/avatar_probe.mp4`. Source remains the pinned Eidoverse revision. This is a technical character, not a selected production design.

Boundary: frame 12 deliberately waits for the delayed response with a 25-second cap, so inference can be observed in a finite offline render. This synchronization is not continuous real-time playback or an end-to-end interactive latency benchmark. Cancellation restores a sampled neutral pose abruptly, without blending. Relative placement is a root offset, not collision-aware walking. The model only chooses a validated named clip; it does not create choreography. This trial uses trusted host orchestration rather than an additional Harness² adaptation run.

## Small Gemma context and constrained-output trial (2026-10-19)

`experiments/gemma_event_context_probe.py` compares three avatar events under short and synthetic archived context, using installed `gemma4:e2b` and `gemma4:e4b` Q4_K_M models. Exact digests and installed metadata are in the evidence files. This is text-only: no claims about audio windows, transcription, multimodal inputs or maximum context.

| Model | Prompt-only strict correct | After constrained JSON schema | Bare-text-aware semantic baseline (analysis only) |
|---|---:|---:|---:|
| Gemma E2B | 2/6 | 6/6 | 5/6 |
| Gemma E4B | 5/6 | 6/6 | 6/6 |

The bare-text-aware column recognizes an exact known action word for diagnosis; the executor does not accept bare text. E2B's long-context listen case returned neutral, a semantic error beyond formatting. Schema-constrained decoding corrected it in the repeated run, but these twelve pairs are a pilot, not a reliability estimate or unseen generalization test. No prompt or model fine-tuning occurred.

Short prompts were 78–84 input tokens; long prompts were 2176–2182, with 64 explicitly obsolete events. First long-context prefill took 2.670 seconds on E2B and 4.542 seconds on E4B. Later repeated-prefix requests had much shorter prompt evaluation, so cache effects prevent a simple context-length latency claim. First load costs were 7.496/18.781 seconds. The schema run was warm: E2B total 0.518–0.713 seconds, E4B 0.610–0.742 seconds. Do not attribute the baseline-to-schema speed difference to constrained output.

Evidence: `gemma-event-context-v1.json`, `gemma-event-context-schema-v1.json`. Original failures preserved. Candidate default for future small-model trials: constrained output schema plus independent semantic validation and compact authoritative event state. Still test null/unsupported intents separately; the present action enum does not cover arbitrary creative requests.

### Gemma E2B to actual 3D renderer

`experiments/vrm_model_async_probe.py --gemma-e2b` completed the same bounded offline VRM demo with schema-constrained gesture/side intent. Both calls selected wave_goodbye/right; host compiled root x=0.35. Initial inference took 3.712 seconds; delayed inference 0.646 seconds, each 47 input and 16 output tokens. The stale reply was rejected after cancellation; 39 post-stop frames remained neutral. The resulting video hash exactly matches the visually inspected Qwen-driven counterpart because both selected the same motion and cancellation frame. Six VRM verification tests passed.

Evidence: `vrm-gemma-async-v1.json`; media `/Users/adom/Development/hermes-testing/runs/round6/eidoverse-video/work/eidoverse-harness2-gemma-async-v1/avatar_probe.mp4`. Same limitations: finite offline render, bounded frame synchronization, abrupt neutral reset, root-offset placement, technical test character. No audio, walking, learned choreography, continuous viewer, or Harness² adaptation gain is established. All calls this round were local; energy/hardware cost unmeasured.

## Capability limits and executable motion (2026-10-19)

A fresh eight-case action-scope pilot exposed semantic failures despite constrained JSON. Sol authored the runner and four offline tests. Each model saw the same host policy, catalog and requests; at most one generic correction included its previous answer without revealing the expected action. No avatar actions were executed in this pilot.

| Model | First correct | After at most one correction |
|---|---:|---:|
| Gemma E2B | 4/8 | 5/8 |
| Gemma E4B | 7/8 | 7/8 |
| Qwen3 8B | 7/8 | 7/8 |

E2B returned neutral for dance (corrected), look_right for walking, neutral for ambiguous direction, and nod for ambiguous referent. E4B/Qwen classified ambiguous direction as unsupported rather than asking clarification. All other cases passed. These results establish that format enforcement does not reliably enforce capability boundaries; do not blindly dispatch schema-valid intent. Thirty total local calls, no API charges; 135–168 input tokens on first attempts. Timings may overlap a short Blender render, so this batch is not a clean speed benchmark. Evidence: `avatar-capability-v1.json`. Next adaptation candidate: priority between missing referents and absent capabilities, with freshly authored heldouts.

Separately, a real procedural full-body motion prototype now produces two amplitude variants and a four-second side-by-side stick-rig video. Five motion tests and render verification passed; details and limitations are in dance-lab.md. It is not yet model choreography, retargeted avatar motion, or an H3-compatible export.

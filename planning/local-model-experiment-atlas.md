# Local-model experiment atlas

Working map, 2026-10-18. Broad coverage rather than a claim that every possible experiment is listed. New ideas should fill a missing task, failure, model or harness dimension. These are proposed experiments unless an evidence link says otherwise.

## Research question

What useful work can a local model reliably finish when the harness supplies compact state, suitable tools, explicit feedback and recovery? Measure useful accepted outcomes per unit of latency, compute and human attention, not token production or plausible self-reports.

Model classes: **T** tiny/very small controller (roughly1–4B); **S** small general model (roughly4–9B); **M** compact-active MoE (Gemma26BA4B/Qwen35BA3B candidates); **D** dense27–31B director/reviewer; **A** audio-capable model or dedicated ASR; **V** vision-capable model. These are experimental roles, not capability guarantees. See model-task-portfolio.md for verified checkpoint names. A model may occupy several roles.

Cost tiers: **C0** CPU simulator/replay only; **C1** bounded hosted model calls before local deployment; **C2** short local inference on prepared hardware; **C3** short rendering/audio work; **C4** GPU training or prolonged evaluation, deferred until justified. Do not run the full Cartesian product.

## 1. Performer and avatar control

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| ACT01 | Natural intent -> pose-atlas ID | T/S/M | Correct variant; unseen names and synonyms |
| ACT02 | Target-relative gaze | T/S/M | Trusted direction; mirrored scene and distractor |
| ACT03 | Approach/stop beside target | S/M | Footprint clearance, moving target, route blocked |
| ACT04 | Gesture intensity and social distance | S/M | Requested intensity bounds; human appropriateness |
| ACT05 | Speaking/listening/interrupted state controller | T/S | Legal transition, interruption deadline |
| ACT06 | Select transition between two poses | T/S | Atlas compatibility; reject impossible blend |
| ACT07 | Left/right handed gesture selection | T/S | Actor-local versus screen-local frames |
| ACT08 | Two-character turn taking | S/M | No simultaneous exclusive speech/action leases |
| ACT09 | Express emotion without changing identity | S/M | Allowed controls only; human acting judgment |
| ACT10 | Recover after renderer disconnect | T/S | Reset/reconnect receipt; no repeated stale action |
| ACT11 | Repair exactly one beat in six | S/M/D | Untouched beats byte/semantic preservation |
| ACT12 | Choose between 2D and 3D available action sets | S/M | Unsupported action explicit, no invented capability |

ACT01/02 have limited live intent evidence; live rendered behavior is a separate gate. ACT03 requires path and third-actor collision checks beyond the existing endpoint preview.

## 2. H3 scene skeleton and animation preparation

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| SCN01 | Brief -> three/six-beat symbolic score | S/M/D | Required dramatic beats and valid score |
| SCN02 | Score -> shot coverage suggestions | M/D | Every required beat covered; human composition |
| SCN03 | Select camera from fixed shot library | S/M | Framing constraints, line-of-action continuity |
| SCN04 | Retarget score to different character rig | S/M + deterministic tool | Bone/pose mapping, decoded joint tracks |
| SCN05 | Select expression variant per spoken phrase | S/M | Timing alignment and human congruence |
| SCN06 | Generate low-cost 2D animatic | S/M | Frames actually decode; timings match score |
| SCN07 | Export rig keypoints/pose reference frames | S/M + compiler | Coordinate convention and visible pose match |
| SCN08 | Preserve props, eyelines and costume across cuts | V/M/D | Planted discontinuities, missed/false alarms |
| SCN09 | Reschedule a beat after dialogue timing changes | S/M | No overlap; required causal order preserved |
| SCN10 | H3 input pack with chosen references and cue text | M/D | Verify actual supported H3 interface first |
| SCN11 | Compare H3 output with intended blocking | V/D | Blind human review + measurable layout |
| SCN12 | Repair only failed shot in a scene | M/D | Preserve accepted shots and asset provenance |

A scene skeleton can mean a narrative/shot scaffold or skeletal joint tracks. Keep these separate in results. Current scene_score is a compressed symbolic fixture, not a rendered animatic or an H3 adapter.

## 3. Listening and live assistance

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| AUD01 | Short speech clip -> transcript | A | Word error, names, accents, quiet speech |
| AUD02 | Stitch overlapping clip transcripts | S/M | No duplicated/dropped words at boundaries |
| AUD03 | Speech chunk -> intent/event | A/S | Correct timing, cancellation vs new request |
| AUD04 | End-of-turn prediction with pause handling | T/S/A | Premature responses vs unnecessary latency |
| AUD05 | Barge-in cancels pending speech/action | T/S | Actual cancellation latency and neutral fallback |
| AUD06 | Maintain speaker-linked compact notes | S/M | Attribution, corrections, explicit uncertainty |
| AUD07 | Separate quote/read-aloud from actionable request | S/M | No action on quoted or background instructions |
| AUD08 | Streaming caption + avatar listener response | A + T/S | Caption lag, dropped segments, visible response |
| AUD09 | Audio-only versus transcript-only understanding | A/M | Matched examples, emotion/prosody information loss |
| AUD10 | Chunked audio with long-text context ledger | A/S/M | Earlier facts retained without replaying raw audio |

Audio clip limits, total token context, sliding attention and persistent harness memory are independent dimensions. Start from synthetic or explicitly approved recordings; no ambient microphone recording by default.

## 4. Creative designer and art-production manager

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| ART01 | Brief -> independent design axes | S/M/D | Separate silhouette, palette, materials, persona |
| ART02 | Generate controlled variation requests | S/M | Fixed camera/pose while chosen axis varies |
| ART03 | Choose next audition to reduce uncertainty | M/D | Human preference discovery vs repetitive options |
| ART04 | Asset inventory + provenance ledger | T/S | Exact IDs/hashes; no invented source/license |
| ART05 | Queue/retry failed render only | T/S/M | Preserve accepted artifacts and lineage |
| ART06 | Track budget and stop before next paid job | T/S + host ledger | Actual host enforcement, including retries |
| ART07 | Compare variants against fixed brief | V/M/D | Blind human agreement; separate taste/fidelity |
| ART08 | Convert feedback into a minimal revision | M/D | Requested delta only; preserve identity |
| ART09 | Prevent design drift across ten iterations | M/D | Canonical identity anchors, independent review |
| ART10 | Package layers/rig-ready parts checklist | S/M/V | Inspect actual assets, not model claims |
| ART11 | Schedule parallel art jobs with dependencies | S/M | No duplicate submissions; deterministic recovery |
| ART12 | Build a review packet from completed jobs | S/M | Complete inventory, correct labels, no cherry-picking |

Creative quality needs human judgment. A schema-valid brief is not attractive art. Current job-board budget is metadata; ART06 is unfinished until the dispatcher enforces spending.

## 5. Memory, context and retrieval

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| MEM01 | Recent-event ring buffer + durable scene ledger | T/S/M | Latest revision wins; no forgotten hard constraints |
| MEM02 | Summary versus exact retrieved fact packet | S/M/D | Source fidelity, latency, answerability |
| MEM03 | Long-context versus compact retrieval | M/D | Early critical facts, distractors, late correction |
| MEM04 | Repeated identity/persona consistency | S/M | Explicit traits stable; no invented history |
| MEM05 | Forget revoked instructions and stale plans | S/M | Removal propagates to next action |
| MEM06 | Resume after process/model restart | S/M | Replay receipts without repeating side effects |
| MEM07 | Retrieve compatible move/asset by semantics | S/M | Exact asset exists and fits runtime |
| MEM08 | Confidence-based retrieval/escalation | T/S/M | Calibration, unnecessary lookups, missed uncertainty |

## 6. Productivity and bounded computer work

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| OPS01 | Organize synthetic files by typed plan | T/S | No overwrite; manifest and rollback |
| OPS02 | Reconcile inventory and totals | S/M | Independent arithmetic and duplicate detection |
| OPS03 | Extract tasks/dates from notes | S/M | No invented deadline or assignee |
| OPS04 | Draft a schedule under constraints | S/M/D | Conflicts, travel/setup time, source-backed dates |
| OPS05 | Triage tool errors to known recovery playbook | T/S | Correct fault class; bounded retry |
| OPS06 | Fill local mock forms | S/M/V | Correct fields; no unintended submission |
| OPS07 | Read-only local research assistant | S/M/D | Citation accuracy and useful source coverage |
| OPS08 | Produce reproducible small report/chart | S/M/D | Source numbers match artifact and labels |
| OPS09 | Maintain project status from receipts | S/M | Observed vs claimed completion distinction |
| OPS10 | Batch rename/caption assets in sandbox | T/S/V | Stable IDs, dry-run preview and undo |

Start in fixtures/local mocks. External messages, accounts and destructive operations retain their own authorization boundaries; model confidence does not grant permission.

## 7. Tool learning and harness adaptation

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| HRN01 | Tool descriptions: terse vs verbose | T/S/M | Accuracy per input token; same tool semantics |
| HRN02 | One combined tool vs primitive operations | T/S/M | Completion, flexibility, correction expense |
| HRN03 | Strict output vs exact formatting repair | T/S/M | Preserve first failure; no semantic rewriting |
| HRN04 | Structured constraints vs free-form JSON prompting | T/S/M | Provider support, valid-but-wrong frequency |
| HRN05 | Field-specific feedback vs whole-task retry | S/M | Recovery without unrelated field changes |
| HRN06 | Small model proposes, deterministic verifier checks | T/S/M | Independent oracle cannot be model-edited |
| HRN07 | Small model proposes, larger model reviews | S/M/D | Added value beyond deterministic checks; correlated errors |
| HRN08 | Model-backed Harness² improver | M/D | Frozen dev/test split, actual edits, untouched holdouts |
| HRN09 | Adaptation transfer to new model/quantization | T/S/M/D | Gain survives changed checkpoint and tokenizer |
| HRN10 | Learn when to abstain or escalate | T/S/M | Useful completion vs reject-everything policy |
| HRN11 | Semantic repeat detector and loop breaker | T/S/M | Stop cycling without cutting off recoverable work |
| HRN12 | Versioned tool schema migration | S/M | Detect old schema, no silent parameter reinterpretation |

## 8. Reliability and fault injection

| ID | Experiment and deliverable | Candidate | Independent check / stress case |
|---|---|---|---|
| REL01 | Lost response after successful operation | Any | Idempotency prevents duplicate side effect |
| REL02 | Timeout during avatar command | Any | Lease expires; neutral verified independently |
| REL03 | Tool receipt says success, artifact missing | Any | Completion rejected by artifact check |
| REL04 | Stale scene snapshot races actor movement | Any | Revision mismatch rejects old command |
| REL05 | Malformed, duplicate-key, nonfinite response | Any | Rejected without execution |
| REL06 | Untrusted asset text asks to change goals | Any | Data remains data; no extra tool authority |
| REL07 | Model/server dies mid-plan | Any | Resume only unfinished work from durable ledger |
| REL08 | Concurrent workers contend for one actor | Any | Single lease owner and cancellation ordering |
| REL09 | Corrupt or unavailable asset | Any | Explicit fallback and preserved error |
| REL10 | Slow-but-correct response misses deadline | Any | Discard late action; score as expired, not success |

Injected failures and naturally observed failures must have different labels. Recovery that only passes mocked faults is not deployment reliability.

## 9. Serving and hardware experiments

- SYS01: oneGPU model versus twoGPU tensor parallel, same checkpoint/quant/context; measure latency, memory and useful throughput.
- SYS02: independent workers on two GPUs; include interference and concurrent long-prefill/short-action load.
- SYS03: Q4/Q5/Q8 or supported equivalents with heldout quality, memory and actual completion cost.
- SYS04: prefix caching on/off; identical prefix versus changed scene facts; ensure stale cache cannot change semantics.
- SYS05: MTP/speculative decoding where supported; measure accepted draft tokens and total speed, not claimed multiplier.
- SYS06: reasoning on/off with adequate output budgets; count hidden/reasoning tokens and incomplete answers.
- SYS07: cold load/warm decode, prompt lengths compact/8K/32K/long; separate prefill from output speed.
- SYS08: constrained decoding overhead versus formatting repair; schema compliance is not semantic accuracy.
- SYS09: sustained30min event stream with a bounded test workload; memory growth, latency tails, restart and cleanup.
- SYS10: CPU fallback/tiny resident controller while main GPU is busy rendering; deadline and quality degradation.

All require a known endpoint and current deployment recipe. Do not extrapolate OpenRouter latency to5090 performance. Begin with a finite trial cap and actual resource termination verification when renting.

## 10. Fine-tuning and distillation

- FT01: QLoRA on accepted tool calls; compare against unchanged base with same harness.
- FT02: Train explicit corrections, including negative examples; keep initial failure and reason.
- FT03: Pose intent adapter versus general tool-use adapter; test interference and forgetting.
- FT04: Distill director decisions into a tiny performer policy; novel scenes and names held out.
- FT05: Teach unsupported/ambiguous/expired decisions; avoid teaching blanket refusal.
- FT06: Tune compact output grammar; test whether reduced tokens preserve useful choices.
- FT07: Personal creative preferences with separate consented preference data; human blind comparison.
- FT08: Cross-quantization and cross-harness transfer; detect improvement that exists only on training setup.

Training is not yet configured. Split by full scene/task families before generating traces; avoid near-duplicate leakage. Record training compute separately from per-task inference savings.

## Shared experiment contract

Each run declares: hypothesis, useful output, task IDs/split, checkpoint and quant, serving version, prompt/tool schema/harness revision, allowed actions, token/time/cost caps, rollback/cleanup, independent acceptance, evidence paths and stop rule.

Compare fixed minimal, deterministic repair, one feedback retry, actual Harness² adaptation, and later fine-tuning as separate arms. Use the same untouched heldouts. Randomize model/order where practical. Preserve original failed outputs. Record first-pass/repaired/exhausted/unsupported/expired/false-completion separately; do not treat unsupported controls as successful avatar work.

For a first screen use6–12 varied cases/model, then expand to30–100 cases only where outcomes could change selection. Small perfect runs do not establish high reliability. Use repeated trials and uncertainty intervals before deployment claims. Include known-easy cases so rejecting everything cannot win, and known-impossible cases so reckless execution cannot win.

Latency: report cold/warm TTFT, prefill/decode, end-to-end p50/p95, retries and deadline misses. Cost: input/output/reasoning/cache tokens, wall time, energy if measured, provider cost, GPU startup/download/idle/teardown and human review time. Quality: artifact validity, semantic fidelity, visible execution, creative appeal and human acceptance remain separate.

## Initial sequence and stop rules

1. **Finish live bridge qualification (ACT02/REL02):** current relay absent; failed delivery preserved. Restore only the owned test runtime, inspect pixels and neutral reset. Stop on uncertain ownership or cleanup.
2. **Small-model event controller (ACT05/MEM01/REL04):** synthetic event stream, compact state, cancellations; no rendering required. Compare T/S/M and1feedback retry.
3. **Scene-score expansion (SCN01/SCN09):** three->six beats with selective revision and changed cast; current symbolic Gemma success is a baseline only.
4. **Creative manager (ART05/ART11/REL01):** failed jobs, dependencies, duplicate receipts and restart. Current bounded formatting repair provides a natural failure case.
5. **Model-backed improver (HRN08):** adapt only when genuine task failures exist; keep oracle frozen and improve dev cases before holdout evaluation. No need to manufacture a misleading gain on tasks already solved.
6. **Audio boundary experiment (AUD02/AUD10):** approved short clips, boundary words and transcript ledger; qualify exact audio-capable checkpoint first.
7. **Local deployment (SYS01/03/07):** transfer validated contracts; tiny finite trials before sustained rendering or training.
8. **Animatic and H3 (SCN06/10):** verify actual artifact/output interface, then human scene review.

Defer always-on microphone capture, large GPU sweeps, whole-model fine-tunes, expensive video loops and broad autonomous desktop agents until smaller tests provide a concrete reason. Stop expanding a family when another run would not change tool/model/task selection; record the remaining uncertainty rather than burning tokens for activity.

## Evidence anchors

- actor-intent-live.json and actor-holdout-gemma.json: live Gemma selection, no runtime action.
- creative-retry-live.json / creative-retry-repaired-replay.json: natural formatting failure and deterministic replay recovery.
- scene-score-live.json: one live symbolic score, no frames/H3 execution.
- gemma-actor-loop.json: actual Harness² solver loop, scripted improver, no demonstrated adaptation gain.
- runs/live-avatar/receipt.json: local failed bridge attempt, no confirmed delivery or cleanup; ignored local receipt.

All evidence filenames above are under evidence/ unless otherwise specified. Source model facts remain in model-task-portfolio.md; this atlas is our proposed experimental design.

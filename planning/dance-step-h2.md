# Harness² refinement for constrained steps

The first actual step-planning refinement run did not improve small-model completion. It also exposed two integration gaps: our composer omitted staged candidate evidence, and the generic k=1 selector admitted a delivered proposal even when our host rejected its task constraints. Preserve that run as a failed baseline; a corrected pipeline needs fresh evaluation before promotion.

## Frozen first trial

One observed development task drove actual sequential k=1 Harness² recursion with Gemma4 E2B as solver and OpenRouter Gemma4 31B as editor. Eight independently prepared, feasible within-family tasks were frozen before inference. Each local model used fixed guidance with at most one public-feedback correction and a single reply under the selected adapted guidance. The fixed prompt adds short guidance to the older task contract, so its scores are not directly interchangeable with the earlier raw-contract trial.

| Model | Fixed first | Fixed with correction | Adapted composed prompt |
| --- | ---: | ---: | ---: |
| Gemma4 E2B | 2/8 | 2/8 | 1/8 |
| Older Qwen3 8B | 2/8 | 2/8 | 2/8 |

All 48 local replies were valid four-pair JSON and compiled as local motion; task constraints rejected most plans. All twelve correction replies repeated their preceding answer byte-for-byte. The host's separate finite search found valid plans for all eight cases. That is a deterministic solver result, not model learning.

There were 51 calls: four local development executions, three hosted editor calls and 44 local evaluation calls. Reported hosted cost was $0.00173442; local inference cost and energy were not measured. Local totals were 21,619 input and 1,963 output tokens.

| Model and condition | Initial input tokens | Output tokens | Median first provider time | Median total provider time per task |
| --- | ---: | ---: | ---: | ---: |
| E2B fixed | 414–428 | 38–39 | 1.27 s | 2.58 s |
| E2B adapted | 444–458 | 38–41 | 1.27 s | 1.27 s |
| Qwen fixed | 391–404 | 42 | 1.79 s | 3.90 s |
| Qwen adapted | 421–434 | 42 | 1.79 s | 1.79 s |

Times exclude host validation. These are Mac/provider observations, not dual-5090 predictions. The two local runtimes have different tokenizers; token counts are native provider counts.

## Why the pipeline needed correction

The development base and final composed prompt failed. Both intermediate prompts passed. Upstream selected the sole composed final because it delivered a proposal file; that selection does not check our custom task verdict. Separately, upstream had staged both intermediate prompt diffs and successful rollouts in its composer pool, but our HTTP editor context collector omitted that directory. The composer could not read files merely because its mission mentioned their paths. This was our integration omission, not an intrinsic absence of compose evidence in Harness².

The independent replay in [the investigation](../investigations/2026-10-19-step-h2-results.md) verifies all eleven source hashes, all raw proposal verdicts and the exact editor requests. The final candidate lost one E2B held-out success and gained none; neither intermediate was evaluated on those cases.

A new pure host admission gate checks each candidate's task, request and guidance hashes, completion status and replayed raw verdict. Its fixed priority is final, later intermediate, earlier intermediate, base. With the original development receipts it selects the later intermediate, using zero additional calls. This is a post-trial policy replay, not a retrospective change to the original result or evidence of generalization.

## Evidence and next evaluation

- [Original trial](../evidence/dance-step-h2-v1.json), [recomputed summary](../evidence/dance-step-h2-summary-v1.json) and [post-trial admission replay](../evidence/dance-guidance-admission-v1.json).
- Adapter and admission tests cover actual scripted H2 execution, request binding, invalid plans and forged verdicts. Scripted tests establish wiring, not model ability.
- The separate step-specific editor now includes bounded development candidate diffs and rollouts, preserving all first-trial source files. The completed corrected run applied host admission before freezing guidance and used eight new within-family cases. Results follow below.

The practical division remains promising: let trusted code solve small exact route problems, and use a model for expressive choices and creative direction. Future dance work needs richer variation and subjective audition; passing these endpoint and slot constraints does not establish physical balance, dance appeal or finished anime acting.

## Corrected composer and fresh evaluation

The step-specific editor passes exactly the two development candidates' prompt diffs and rollouts to composition, with path and byte bounds and hashes of each file and the exact sent user message. It preserves the shared proposer/collector and original evidence. Two focused tests include an actual scripted H2 run, successful candidate feedback reaching composition, excluded held-out data, unsafe paths and receipt preservation. Together with the adapter and gate suites, 16 focused tests passed across the implementation work.

The corrected live run made 53 calls: four local development, three hosted editing, and 46 local evaluation calls. The final composed prompt passed the development task; the base and both intermediates failed. Host admission selected the final prompt before evaluation. The editor saw the failed intermediate evidence this time; the first trial's successful intermediate outputs were not replayed into this new run. Hosted cost was $0.00186565. All 50 local calls used 23,066 input and 2,464 output tokens.

| Model | Fixed first | Fixed with correction | Admitted adapted prompt | Paired changes |
| --- | ---: | ---: | ---: | --- |
| Gemma4 E2B | 0/8 | 0/8 | 0/8 | No successes |
| Older Qwen3 8B | 2/8 | 2/8 | 2/8 | One gained, one lost |

The host solver separately finds and compiles valid plans for all eight cases. All fourteen fixed-prompt corrections repeated the original raw reply. Adaptation did not improve aggregate completion, and development success did not establish transfer. The fixtures differ from the first trial, so E2B's 2/8 versus 0/8 fixed scores cannot be attributed to the pipeline change. The first two editor requests were byte-identical across runs, yet hosted outputs differed despite temperature zero; this is not an isolated causal test of the context fix. The admission gate chose the final candidate in the corrected run, so its fallback path was tested by receipt replay and unit tests, not exercised during this live evaluation.

| Model and condition | Initial input tokens | Output tokens | Median first provider time | Median total provider time per task |
| --- | ---: | ---: | ---: | ---: |
| E2B fixed | 412–431 | 38 | 1.27 s | 2.57 s |
| E2B adapted | 476–495 | 85–91 | 2.04 s | 2.04 s |
| Qwen fixed | 388–407 | 42 | 1.81 s | 3.83 s |
| Qwen adapted | 448–467 | 42 | 1.83 s | 1.83 s |

E2B's longer output is formatted JSON with extra whitespace, not more moves or a reasoning trace. Thus output formatting itself can materially affect token demand without adding useful capability. Independent Sol review matched all 13 source hashes, all raw local verdicts, the exact composer user-message hash and each included pool-file hash. All 50 local replies parsed and compiled; failures were task-constraint failures. Trial and replay: [raw corrected evidence](../evidence/dance-step-h2-v2.json), [summary](../evidence/dance-step-h2-summary-v2.json), and [runner](../experiments/dance_step_h2_probe_v2.py). The revised prompts and fresh cases are now observed.

## Next useful dance experiment

Keep the corrected evidence path and admission gate, but do not promote this prompt as a reliable route planner. Move exact position solving into the existing bounded host search. Give a small model a compact menu of verified routes and expressive choices, then measure whether it follows creative direction without losing geometric correctness. Count host completion, model choice fidelity, fallback use and human taste separately.

A concrete next prototype is a 32-beat motif score: introduce a motif, repeat it with a controlled accent change, add a contrasting phrase, and return to a resolved ending. Keep relative placement and protected joints host-owned. Compare direct choice, one bounded correction, and an admitted H2 choice policy on new briefs; render a small A/B audition only after structural checks. The synthetic phrase library limits the available movement vocabulary, so a successful prototype would prepare the control and audition workflow rather than establish compelling choreography. Richer generated motion and human preference learning remain separate lanes.

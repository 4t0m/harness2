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
- A separate step-specific editor will include bounded development candidate diffs and rollouts, preserving all first-trial source files. The corrected run will apply host admission before freezing guidance and use eight new within-family cases. Its combined result will not isolate the contribution of context repair from admission.

The practical division remains promising: let trusted code solve small exact route problems, and use a model for expressive choices and creative direction. Future dance work needs richer variation and subjective audition; passing these endpoint and slot constraints does not establish physical balance, dance appeal or finished anime acting.

# Position-constrained step tasks

A new host task layer checks four-step plans against an approved world-space start, endpoint, root lane, and per-slot direction/accent requirements. It accepts any satisfying plan. This replaces an exact-answer comparison with constraints a live controller could enforce. The task fields are supplied as authoritative structured data in this experiment; extracting them correctly from free-form user requests is not established.

## Fresh local trial

An independent fixture author prepared eight feasible and four impossible tasks before inference. Exhaustive integer enumeration examined 256 possible plans per task. Feasible cases have 16,16,8,8,8,8,4,4 solutions; all four impossible cases have none. Every one of the 72 feasible plans also passed full motion compilation and sampled world-position verification.

| Local model | First attempt | After one correction | Calls | Median first / complete operation |
|---|---:|---:|---:|---:|
| Gemma4 E2B | 2/8 | 2/8 | 14 | 1.22 / 2.32 seconds |
| Older Qwen3 8B | 2/8 | 3/8 | 14 | 1.79 / 3.48 seconds |

These requests are harder than the earlier four directly specified step sequences. Models now have to choose missing directions while meeting simultaneous constraints. The result does not contradict the earlier 4/4 result; it shows its narrow scope. Correction feedback contained only the violated public task constraint, such as an incorrect endpoint or required slot. The single Qwen recovery was the offset-start case later selected for the flat preview. Failed proposals were rejected, not executed.

All four impossible requests were screened before model calls: an unreachable target parity, a target beyond the lane, forced moves leaving the lane, and fully specified directions contradicting the requested endpoint. This is host feasibility detection, not evidence that either model recognizes impossible instructions.

Initial prompts were 377–396 native tokens for E2B and 356–377 for Qwen, with 1,347–1,442 message-text characters. Replies were 38 and 42 tokens respectively. Across corrections, total prompt/output tokens were 5,867/532 and 5,597/588. The 28 local calls incurred no hosted-provider charges. One short run supplies descriptive timing; it does not predict 5090 speed or interactive latency.

## What trusted code now checks

`harness2/dance_step_task.py` validates a bounded task schema and returns detached task facts. It binds receipts to the task hash and the local motion hash. Compilation verifies each required move/accent, exact integer endpoint arithmetic, all 81 sampled world root positions against the lane, and the existing foot/segment checks. Reverification detects task, placement, motion and receipt changes. Nine targeted task/stepping tests pass, including a path with the correct endpoint that leaves the lane midway.

The lane bounds the pelvis/root, not every limb or collisions. Sampling and the procedural clip's monotonic root paths underpin this prototype; there is no dynamics, obstacle avoidance, live avatar transaction or human taste guarantee. World placement is recorded separately from local joint coordinates so a renderer or runtime must apply the supplied start offset. No silent correction of a model's invalid route is performed by compilation.

## A zero-model baseline matters

The same exhaustive search can select the first feasible plan, compile it and produce a valid receipt for all eight supported cases, while rejecting all four impossible cases with zero provider calls. `dance-step-task-summary-v1.json` records these actual compilations, along with replay of all 28 raw model replies.

This solver is deliberately small and domain-specific. It establishes that assigning this finite geometric search to a language model is unnecessary. Its lexicographically selected accents have no aesthetic merit claim. A useful next interface can expose valid route choices and leave expression, narrative fit and preferences to the model, retaining the host's geometric guarantee. That would be a changed task allocation, not evidence that the model learned the original arithmetic problem.

## Next refinement experiment

Use natural failures from this trial as development material for an actual Harness² guidance refinement, then evaluate independently authored new constraints. Keep a fixed baseline and one-correction comparator, include total tokens/latency, and freeze the host validator. A separate constrained-choice condition should expose only host-feasible routes; score task completion separately from preference quality. Do not tune on these now-observed cases and call them a heldout gain.

Primary artifacts: `experiments/dance_step_task_cases.py`, `experiments/dance_step_task_probe.py`, `evidence/dance-step-task-model-v1.json`, `evidence/dance-step-task-summary-v1.json`, and `investigations/2026-10-19-step-task-results.md`. The frozen stepping and earlier phrase modules remain unchanged.

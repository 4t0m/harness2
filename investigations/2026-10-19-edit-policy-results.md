# Dance edit policy holdout results investigation

## Step 1: frame

Goal: determine whether the frozen 12-case selective-edit evidence accurately measures standalone full-plan, standalone patch, and patch-then-fresh-full policies. Expected behavior is one in-scope source-pair change, all protected source pairs and motion retained, and route fallback triggered only by structural patch rejection. Actual results must be counted from raw accepted outputs, not narrative summaries.

No inference, fixture, code, or commit changes are authorized. This investigation will write only this note.

## Step 2: context

A prior independent review covered the earlier eight-case probe and route. The current task supplies a new 74-call policy evidence file. No prior model outputs will be used as a baseline; the frozen fixtures, current runner/router/compiler source, and raw current evidence are primary.

## Step 3: competing hypotheses

1. **Fixture/evaluation mismatch:** one or more requests do not uniquely justify their expected edits, or expected targets violate source scope. Check all 12 request/expected pairs against source and editable slots. Confirmation: a contradiction, ambiguous target, or non-single permitted change. Falsification: every prose request points to its exact one-pair target and every non-target pair remains protected.
2. **Evidence/source binding or replay defect:** reported results may not match raw calls, source revisions, or compiler decisions. Check evidence case/source hashes, replay every raw proposal through `dance_phrase_edit`, and recompute accepted expected-vs-actual outcomes and receipts. Confirmation: hash mismatch, replay disagreement, or inconsistent correctness/acceptance fields. Falsification: hashes and replayed decisions/receipts match throughout.
3. **Prompt/protocol contamination:** full, patch, or routed calls may have received the wrong schema, hidden expected plans, or inconsistent request/source data. Inspect all prompts and payloads for source, request, allowed slots, protocol, and absence of expected answers. Confirmation: schema mismatch or oracle leakage. Falsification: payloads match the intended condition and contain no expected plan.
4. **Fallback is semantically oracle-driven rather than structural:** route may be selecting full retry based on expected answer quality. Inspect router implementation and each fallback trigger/attempt. Confirmation: expected correctness determines fallback or is passed into router. Falsification: fallback occurs only after structural patch rejection, with no oracle access.
5. **Protection claims overstate acceptance guarantees:** accepted edits may not preserve source binding or protected motion. Recompute acceptance receipts and protected-frame/clip/seam/source hashes. Confirmation: any accepted edit fails a preservation assertion. Falsification: all accepted edits replay and preserve all stated invariants.

## Step 4: diagnostic plan

1. Read `experiments/dance_edit_policy_holdouts.py`, the 74-call JSON, `experiments/dance_phrase_edit_probe.py`, `experiments/dance_edit_route_fresh_probe.py`, `harness2/dance_edit_route.py`, and `harness2/dance_phrase_edit.py`; inspect relevant recent Git history for the evidence/runner edits.
2. Use a deterministic offline script to report case counts, trial/policy counts, accepted and exact-target counts, latency/token ranges, failure categories, and source-binding/hash checks.
3. Compare every public request with its exact expected one-pair change, plus editable-slot scope; compare the current 12 triples against the previously frozen eight only to catch accidental duplicates, not to read their model outputs.
4. Replay every raw full plan or patch using the frozen source/revision/scope and compiler; compare replay accept/reject and receipt with logged results. Then recompute accepted-output correctness from expected plans, listing all incorrect or rejected cases.
5. Inspect each prompt and route attempt: verify condition-specific response contract, source/request/scope parity, no expected answer in model-visible content, and whether any retry is actually invoked after structural rejection. Distinguish route policy from standalone experiment prompts.
6. Independently inspect router inputs/branches to determine whether it can access expected moves or semantic scoring.
7. Summarize conclusions with evidence boundaries; no model calls or file changes beyond this note.

## Step 5: diagnostic results

### Test 1 — source hashes, case inventory, and fixture semantics

The evidence is complete and records 12 cases, two local models, three policies, 74 calls, and 72 policy results. Its six frozen source hashes all match the current files: `dance_phrases.py`, `dance_phrase_edit.py`, `dance_edit_route.py`, the original probe, the 12-case holdout fixture, and the policy runner. The evidence's embedded cases exactly equal the frozen fixture. I checked each request against its source and target: each target changes exactly one pair in an editable slot, all other pairs are unchanged, and each of the 24 source/target plans compiles. The 12 source/scope/target triples are unique within the fixture and against the earlier eight-case fixture. The prose is consistent with the exact expected target for all 12 cases; in particular, references to first/last, later middle item, preserved identity/variation, and final correction resolve from the source and request. This is a manual semantic review backed by the compiled/source-scope assertions, not a formal language proof.

### Test 2 — raw proposal replay and expected-vs-actual outcomes

Audit correction (2026-10-19): the first draft incorrectly described Qwen full on `final_correction_changes_only_third_pair` as changing multiple pairs. Raw replay shows zero changed pairs; all failure descriptions below were checked against actual raw changed-slot counts.

I replayed all 74 raw proposal contents through the frozen patch/full compiler functions. For all 72 policy results, acceptance/rejection, exact accepted plan, receipt, and `correct` flag matched the raw evidence. For all 24 route results, replaying the recorded provider replies through `route_edit` reproduced the attempt sequence, per-attempt structural reasons, accepted status, plan, and receipt. There were no replay mismatches.

| Model | Policy | Structurally accepted | Exact expected result |
|---|---|---:|---:|
| gemma4:e2b | full | 10/12 | 9/12 |
| gemma4:e2b | patch | 11/12 | 9/12 |
| gemma4:e2b | fresh route | 12/12 | 10/12 |
| hermes-lab-qwen3-8b:latest | full | 10/12 | 10/12 |
| hermes-lab-qwen3-8b:latest | patch | 11/12 | 11/12 |
| hermes-lab-qwen3-8b:latest | fresh route | 12/12 | 12/12 |

Every failure was inspected. E2B full was structurally rejected for editing an out-of-scope slot in `middle_pulse_to_sway_preserving_softness` and `middle_variation_match_first_not_final`; its accepted result in `later_of_two_editable_slots_by_reference` changed only the later pulse variation, leaving the pulse identity instead of the requested sway. E2B patch was rejected for `slot_two_pulse_to_sway_not_variation_change` because the proposed slot-1 pair exactly matched the source, yielding zero changed pairs; its accepted results for `later_of_two_editable_slots_by_reference` and `final_correction_changes_only_third_pair` were wrong. In the former it changed only the pulse variation and left its identity unchanged; in the latter it changed only the third-slot sway variation and left sway in place instead of producing the requested pulse. Its route recovered the structurally rejected first case, but still returned the two structurally accepted wrong edits for the other cases.

Qwen full was rejected for `final_correction_changes_only_third_pair` because its proposed plan exactly matched the source (zero changed pairs), and for `slot_two_pulse_to_sway_not_variation_change` because its only change was at slot 2, outside editable slot 1. Qwen patch was rejected for `later_of_two_editable_slots_by_reference` because it chose an unpermitted slot. Qwen's route accepted all 12; its fallback converted that same rejected patch into a correct full plan. These are observed case-level results, not a claim of generalization beyond the 12-case fixture.

### Test 3 — prompt/protocol and expected-answer isolation

All 74 calls use the same frozen public source plan, request, and permitted slots as the corresponding fixture. Every system prompt matches the runner's mode-specific `COMMON + OUTPUT[mode]`; the selected response format is the corresponding patch or full JSON schema. No model-visible message contains an expected plan or `expected_moves`. The runner evaluates accepted results against the host-side expected plan only after the route/standalone operation returns. There is no schema or fixture mismatch in the logged calls.

### Test 4 — fallback trigger and oracle access

`route_edit` receives only the snapshot, current source/revision/scope, and provider callback. Its first patch result is passed to structural `apply_patch`; only a `ValueError` causes a full-format call. A structurally valid edit returns immediately even when it does not meet the expected plan. The two observed route fallbacks were both triggered by structural rejections: E2B `slot_two_pulse_to_sway_not_variation_change` (“edit must change exactly one move pair”) and Qwen `later_of_two_editable_slots_by_reference` (“edit slot outside permitted scope”). The callback's full-attempt prompt excludes both the previous response and rejection text in the model-visible messages; those are retained only in audit fields. Thus this route recovers from these two structural failures without a semantic oracle; it does not repair structurally accepted wrong edits. No oracle is passed into or used by the router.

### Test 5 — source binding and preservation

For every accepted standalone and route operation, recomputed receipts match the stored receipt, including accepted revision, permitted scope, source-plan hash, source-sequence hash, and result hashes. The accepted receipt flags for exact outside frames, unchanged other clips, exact seam endpoints, and source immutability are true and reproduce on replay. This verifies the compiler's bounded edit transaction against the frozen source for these accepted proposals; it does not prove a persistent service transaction or actual avatar execution.

### Test 6 — latency and token observations

Values below are per raw call from the local runner's `wall_seconds`, `prompt_eval_count`, and `eval_count`; route statistics include its extra full attempts. They are descriptive observations from this run, not stable performance guarantees.

| Model | Policy | Calls | Wall seconds (sum; min–max) | Prompt tokens (min–max) | Generated tokens (min–max) |
|---|---|---:|---:|---:|---:|
| gemma4:e2b | full | 12 | 14.65; 0.91–3.66 | 232–252 | 26–32 |
| gemma4:e2b | patch | 12 | 9.04; 0.64–0.78 | 244–264 | 14–15 |
| gemma4:e2b | fresh route | 13 | 9.25; 0.62–1.04 | 242–264 | 14–32 |
| hermes-lab-qwen3-8b:latest | full | 12 | 16.49; 1.06–1.59 | 233–252 | 24–41 |
| hermes-lab-qwen3-8b:latest | patch | 12 | 6.94; 0.48–0.75 | 244–263 | 14–15 |
| hermes-lab-qwen3-8b:latest | fresh route | 13 | 10.95; 0.51–2.02 | 244–263 | 14–41 |

## Step 6: assessment

The strongest supported explanation is that the policies behaved as implemented: all raw attempts replay, the fixture and source hashes match, and fallback occurs only after structural compiler rejection. Hypotheses about fixture drift, raw-evidence mismatch, oracle-triggered route fallback, and failed protection checks were ruled out by the checks above. On these 12 cases, the route raises structural acceptance to 12/12 for both models by making one full-format attempt after patch rejection. Exact expected-plan accuracy is model-dependent: 10/12 for E2B and 12/12 for Qwen. E2B shows why structural acceptance is not semantic correctness: two wrong plans passed the compiler and were returned without fallback. The route is not a semantic verifier, service-level atomic commit, or persistent avatar execution layer. The experiment is a fixed, local, within-shelf comparison with no H2 adaptation or new motion capability; the results do not establish broad task generalization or causal benefit beyond this setup.

# Local dance patch no-op

Goal: one authorized semantic edit with exact protected motion. The frozen paired trial gives E2B full8/8, patch7/8, with its one generic patch repair still rejected as no change. Qwen passes both formats8/8. This is a new edit task on the previously tested shelf; no prior remedy has been applied. Current topic branch starts from8dd5b14. Expected outcomes are independently authored and both protocols enforce exactly one authorized pair change.

Before inspecting raw failed replies:

1. Patch application/indexing defect: parse raw patch and manually substitute its pair into frozen source, compare with API outcome. A raw requested change that API loses supports this; raw/source identity at the selected slot rules it out.
2. Invalid/truncated serialization: inspect finish reason and exact JSON fields. Truncation/unsupported labels supports this; complete well-formed unchanged values rules it out.
3. Request/oracle contradiction: compare source/request/expected for failed case, including zero-based slot correspondence. A valid interpretation rejected by oracle supports a fixture defect; an unchanged requested target does not.
4. Correct target but wrong edit value: inspect whether output retains the existing move rather than requested substitution. This supports model selection failure, not an internal-mechanism claim.

Tests: offline parse and reapply all accepted receipts; source-hash checks; compare one failed raw proposal and retry against public request. Preserve original evidence unchanged. If failure is truly host-detectable no-op, a separate bounded patch-first/full-fallback trial can test recovery without oracle-triggered routing. It will reuse observed cases, not new holdouts; at most two calls per case, no semantic oracle inside routing, no deployment claim.

## Raw diagnosis and first fallback

The E2B patch selects correct slot2 but repeats existing pulse/soft instead of requested sway/soft. Its retry is identical. Completed strict JSON and stop finish; manual substitution leaves source unchanged. Public request and expected target agree, so no indexing/oracle/compiler defect is supported. All accepted paired receipts independently reproduce and source hashes match.

The separate live patch-first/full-fallback trial completes9calls on8observed cases. It still passes7/8: the same rejected patch is followed by an unchanged full plan when prior bad answer and rejection are included in conversation. No mutation escapes the compiler. This differs from standalone full8/8.

Next discriminating comparison: run exactly the same structural router/cases/options, but use the fresh full-plan system + original public task on fallback, omitting prior answer and rejection only from model context. Retain both attempts in audit evidence. No new prompt tuning or expected-answer hints. This tests bundled prior-answer/error-context influence, not an internal psychological mechanism. Also verify full fallback prompt equals the original paired full prompt, source hashes match, and check repeated patch outputs for sampling/runtime drift. A recovery supports fresh-context fallback in this small observed sample; no recovery would leave semantic/backend variability unresolved. At most16localcalls, only E2B. Preserve v1 files and receipts.

## Fresh-context comparison result

Fresh full fallback recovers the one rejected E2B case:8/8 in9calls. All8initial patch prompts and outputs exactly match the original paired patch condition in BOTH routing runs. Fresh fallback messages and its output exactly match the successful standalone full condition; retained-context fallback messages/output differ and preserve the no-op. The two routing runs use unchanged compiler/source/fixture hashes. This supports a context-sensitive fallback difference for this one observed failure, without identifying the model's internal mechanism or establishing a new-task reliability gain. Full standalone already passed8/8; route complexity is justified only if its shorter common-path output matters and fresh evaluation sustains the result. Keep both failures and success. No further prompt tuning this round.

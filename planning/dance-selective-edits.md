# Selective dance edits — 2026-10-19

The new edit API protects approved movement while a model revises one phrase. A frozen host snapshot binds source choices, generated motion hash, revision and allowed slots. Both full-plan and patch paths require exactly one changed pair in scope. They reject no-ops, stale facts (even without a revision bump), changed permissions, malformed values and incompatible transitions. Every accepted edit preserves the other three source clips and62of81motion samples exactly, including both shared endpoints. It is an offline validated proposal, **not** an atomic write to a persistent avatar service; an integration must recheck live state when committing.

Sol authored the edit API and bounded router; Luna independently authored8new edit briefs before model calls. Cases cover a single variation, sway/pulse substitution, repeated moves, ordinal/referential targets and final-wins amendments. Parent checked source/target compilability and exact one-slot changes. These are within the existing five-move shelf; expected plans remain host-only.13targeted edit/router/readback tests pass, including stale-before-provider, invalid full fallback, transport failure, protected-span corruption and a structurally valid semantic mistake that must not trigger an oracle-free retry.

## Paired local experiment

Condition order alternated by case and reversed by model. Both conditions use the same source, permissions and request; schemas and response instructions differ, so this compares complete interfaces rather than isolating output length alone. At most one same-format correction was allowed. The paired runner can use its experimental semantic oracle to trigger a generic reminder, although only a structural no-op retry occurred in this batch; this is separate from the oracle-free router below.33local calls completed.

| Model / output | First correct | After correction | Median first wall | Initial input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|
| E2B full |8/8|8/8|1.06s|239–269|26–31|
| E2B patch |7/8|7/8|0.80s|251–281|14–15|
| Qwen3 8B full |8/8|8/8|1.34s|240–268|24–40|
| Qwen3 8B patch |8/8|8/8|0.76s|251–279|14–15|

Full initial message text912–1048characters; patch951–1087. Patch savings are in generated output, not initial context. Single runs, loading/cache/time effects and different schemas limit causal/performance conclusions. Fifteen output tokens need3.75decode tokens/s for a4-second lookahead, excluding input processing and other work; not a5090forecast.

E2B's failed patch chooses the right third slot but repeats pulse/soft instead of changing it to sway/soft. The host rejects the no-op. Same-format repair repeats it. Raw proposals, compiled choices, request and oracle were checked; no indexing/source/fixture discrepancy explains the failure.

## Structural fallback, with failures retained

A separate router tries patch first, then full only if the compiler rejects the patch. It never sees expected moves. Transport/incomplete replies do not become structural fallback triggers, stale snapshots fail before provider calls, and accepted-but-semantically-wrong edits terminate normally for external evaluation.

On the now-observed8cases, a live E2B route that included the rejected answer/error in the full prompt still scored7/8 in9calls. The full fallback copied the unchanged source. A second live run omitted that failed answer/error from the model context, retaining both in the audit trail, and scored8/8 in9calls. Allinitial patch prompts/outputs matched across runs; the successful fresh full prompt/output exactly matched standalone full. The one fallback took1.84seconds including both calls; median routed task time was0.84seconds. This is one recovered observed failure, not fresh-heldout evidence or learned Harness² adaptation.

Recommendation: Qwen patch is a useful next candidate; E2B full is the stronger simple baseline here. Keep fresh-context fallback experimental until tested on new briefs. It is worth exploring as a general host strategy, but not worth claiming a broad gain from one example. Total51localcalls, no paid-provider calls; hardware/energy cost unmeasured.

## Motion and next steps

A real accepted E2B patch replaces only the second phrase's soft sway with soft pulse. Source and edited tracks render side by side into40frames/4seconds. Scene-joint readback agrees within1.08e-7m; segment error below1.29e-7m. Parent inspected decoded frames0/12/17/30: planted figures and arm states visible, the soft substitution subtle. This checks joint objects plus sparse pixels, not every bone-mesh endpoint/pixel, physical realism or taste. Video: `/Users/adom/Development/hermes-testing/runs/harness2-dance-phrase-edit-v1/comparison.mp4`.

Evidence: `dance-phrase-edit-model-v1.json`, `dance-edit-route-v1.json`, `dance-edit-route-fresh-v1.json`, `dance-phrase-edit-summary-v1.json`, `dance-phrase-edit-preview-v1.json`. Previous failed outputs remain untouched.

Next: test the fixed full/patch/fresh-fallback policies on independently frozen new tasks before any adaptive selection. An actual H2 comparison can then expose only development cases to the editor and preserve heldout policy evaluation. Separately broaden expressive motion; [dance-generation-backend-candidate.md](dance-generation-backend-candidate.md) records primary-source research on music-conditioned EDGE, its real motion outputs, legacy environment, dependency restrictions and unresolved checkpoint provenance. No GPU rental, weight download, backend execution or H3 submission occurred this round.

Independent Luna replay reproduced every attempted proposal and accepted receipt, confirmed allreported rates, and verified that fallback routing never receives expected plans.

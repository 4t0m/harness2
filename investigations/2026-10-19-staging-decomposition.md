# Four-question staging result diagnosis

Goal: test whether separate placement and cue extraction improves small-model task completion. Early frozen-run E2B results instead regress on cases that pass one-shot. Preserve the full planned comparison; no prompt changes mid-run. The assembly module passes equivalence tests over the twelve cases; those tests cannot prove live model semantics.

Hypotheses and diagnostic plan, before inspecting failed reply contents:

1. Host assembly assigns pieces to wrong slots or maps labels incorrectly. Independently reconstruct each result from saved placement and cue reply JSON, then compare canonical plan and source call part labels against expected slot order. A discrepancy between reconstruction and stored result supports this; exact equality with host-assigned labels rules it out for that case.
2. Calls are incomplete or schema-mismatched. Inspect native done_reason, token cap, strict parse status, and missing pieces. Truncation/invalid shape supports it; complete parseable pieces with accepted compilation rule it out.
3. Individual cue extraction misreads the full request or target ordinal. Compare each raw cue against its host-only expected cue, classifying actor/gesture/variation mismatches separately; inspect whether responses repeat another valid cue. Complete but wrong field values support a semantic extraction failure. No attribution to model internals is justified by the mismatch alone.
4. Placement extraction is the bottleneck. Compare placement accuracy and cue accuracy separately. Correct cues with wrong placement support it; cue-only failures rule it out for those cases.

Cheap checks: read completed receipts from evidence/actor-staging-steps-v1.json, independently reconstruct, and record field-level counts. Do not treat a compiler pass as semantic acceptance. Do not modify fixtures or call schemas after seeing results. Any treatment would be a separate exploratory run on now-observed cases.

## Early findings and next discriminating probe

Independent reconstruction matches every completed assembled plan inspected. E2B failures are complete schema-valid replies with wrong cue fields; placement is correct in these inspected failures. Several cue1/2 replies repeat cue0. Qwen's first three completed split cases also repeat cue0 for later targets. This supports extraction/targeting failure rather than assembly or invalid shape.

Additional hypothesis: the target question is actually lost or not differentiated in serialization, versus its position reducing instruction following. Before changing the protocol, inspect distinct serialized question fields/request hashes. Current runner uses sorted keys, placing question before request and scene. After the main frozen trial finishes, compare exactly the same cue question at the start versus end of the JSON object's field order. Use two observed cases, slots1/2, both models, both orders (16 calls), alternate order; same strings, schema and options. Score each cue against the host oracle. This can support a prompt-order effect in this bounded sample; it cannot establish an internal cache or attention mechanism. No whole-scene success claim from a cue-only probe.

## Completed evidence

All120 planned main calls completed. Both models got placement12/12 in the split condition. E2B per-slot accuracy was9/12,6/12,9/12; Qwen12/12,3/12,4/12. All24 assembled outputs compiled, but only7 were semantically correct. Independently reconstructed replies match host assembly. Qwen's three one-shot compiler failures are complete responses using `softly`/`clearly` instead of allowed `soft`/`clear`, not truncation. Do not silently normalize and rescore them as original successes.

The16-call field-order diagnostic completed with the exact same cue-question strings, schemas and generation settings. E2B early2/4 vs late3/4; Qwen early0/4 vs late2/4. This supports a field-order effect on these observed cues, while later-question placement still fails. It does not identify an internal attention/cache mechanism, establish whole-plan reliability, or replace a fresh evaluation. Raw replies also passed strict duplicate-key/nonfinite parsing during summary generation. Native load/cache effects prevent a clean latency comparison from these16 calls. The main failed decomposition remains unchanged.

Decision: retain the assembler as a tested optional interface, but do not promote four independent full-request queries as a reliability or efficiency improvement. Move substantive exploration toward typed reusable dance phrases and explicit transition constraints. Evidence and reproducible derived metrics: actor-staging-steps-v1.json, actor-staging-question-order-v1.json, actor-staging-steps-summary-v1.json.

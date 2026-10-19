# Constant answers in local geometric vision pilot

Expected: distinguish the strong inward arm edit, swap side when flipped, and recognize identical protected poses. Observed: E2B same on6/6;E4B left on6/6. JSON allvalid. E2B4/6overall merely matches the always-same baseline;E4B1/6matches always-left. Inputs correctly decoded and inspected; source frames10/70exactjoint equality,frame40sum lateral wrist offsets1.08m versus0.59818m. No artistic judgment involved.

Hypotheses:
1. Image payload is ignored or incorrectly handled. Diagnostic: two grossly different generated red/blue color cards, same prompt/schema/options and native image body. Correct different color responses demonstrate at least some image dependence; constant responses leave transport/preprocessing/model interpretation unresolved. Do not infer broken provider from a difficult comparison alone.
2. Forced-choice schema/question elicits a constant prior despite useful visual processing. Diagnostic: ask for a short unconstrained description of normal/flipped accent comparison for each model. Image-dependent descriptions with correct changed side support this; still-constant or wrong descriptions fail to support it.
3. Fine geometric comparison is beyond these models/resolution or the question is ambiguous. If color cards pass but free-form motion comparison fails, this is more plausible than a wholly ignored image. It still does not distinguish capacity, visual encoding, phrasing and resolution without further heldout tests.

Run at most8additional local calls:2colorcards and2comparison descriptions permodel. Keep same generation settings except free-form removes output schema and raises output cap to128. Preserve raw text and timing; do not retrofit pilot scores. No repairs or taste labels. This diagnosis is not an adaptation result.


Results: both models correctly identified both color cards. This rules out a wholly absent image signal for the simple-card path, not every preprocessing or spatial-understanding issue. Both free-text descriptions got the relative width direction right in the normal accent image, with imprecise/exaggerated limb descriptions. E2B still described the right figure as inward on the flipped image; E4B called flipped hand widths similar. Removing the schema is therefore not a sufficient repair. Finer spatial interpretation/orientation sensitivity remains unresolved; no provider fault inferred. Do not promote this pilot to an autonomous visual acceptance oracle. Primary raw calls are in dance-vision-diagnostic-v1.json; explicit parent review separate. No baseline score rewritten.

## Cropped treatment follow-up

Single-actor treatment returned narrow for all12crops permodel, leaving bothpaircomparisons at the always-same baseline4/6. Absolute narrow/wide vocabulary adds a possible interpretation threshold confound, so2/12host-label accuracy is not a general spatial capability score.

Next discriminating check: keep identical image bytes, system/user prompts, model and generation parameters, but swap the schema enum from [narrow,wide,unclear] to [wide,narrow,unclear]. Four matched crops permodel (normal/flipped accent, bothactors),8calls total. If answers switch with enum order, decoding/option-order sensitivity contributes; if they remain narrow, this perturbation does not support that explanation and wording/visual interpretation remains unresolved. This is an in-place diagnosis on reused examples, not a new heldout trial. Do not alter the original results.


Enum-order result: all8repeated crops still returned narrow, with complete stop responses. Swapping the first two enum options did not alter any answer; this test does not support an option-order explanation. Interpretation threshold and geometric perception remain unresolved. The hosted26B-A4B and31B comparison both detected the edited side in2/2orientations but falsely reported right on all4unchanged controls, so larger models do not yet solve acceptance either. Stop retuning on this fixture; require fresh poses and explicit task definitions before promotion.

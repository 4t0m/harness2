# Compact staging failure classification

Goal: shorter replies preserve staging choices and semantic correctness. During the frozen full/compact comparison, E2B compact gallery case failed its first attempt. Leave the experiment unchanged while collecting all planned calls.

Context: full protocol previously scored 3/4 initial and 4/4 with one repair on these same four cases. Ten compiler tests now pass; exhaustive representation equivalence is recorded by the live runner. This is the first compact model trial, not an attempted fix.

Hypotheses and discriminating checks (before inspecting failed content):

1. Truncation/transport: inspect done_reason, output cap, raw response and error_type in evidence/actor-staging-compact-v1.json. A length stop or transport error supports it; complete native stop with parsed reply rules it out for that call.
2. Invalid compact shape/catalog: parse the raw reply with compile_compact and inspect the exact validator result. Wrong tuple length, unknown actor, gesture or variation supports this; successful compilation rules it out.
3. Valid but wrong staging semantics: compare compiled actors/cues with independently authored expected plan. Specific actor, side, order or variation mismatch with successful compilation supports it; exact canonical equality rules it out.
4. Comparator/compiler error: independently expand raw compact choices into the original full protocol and run compile_staging. Equality with compact output plus an actual difference from the expected plan rules out a compact-only compiler error. Equality to expected despite reported failure supports comparator error.

Read raw receipts only after this plan is written. Preserve failures and correction outcome. Do not change prompts during this batch; causal explanation for model mistakes may remain unknown even after classifying their locus.

## First diagnostic findings

The first three failed compact receipts (E2B gallery initial/correction and quiet initial) all stopped normally, compiled successfully, and matched an independently expanded full-protocol compilation exactly. This rules out truncation, invalid shape/catalog, and compact-only compiler mismatch for these receipts. All three swap the first two requested cues; the first returned cue belongs to the left actor. Gallery repeats the same error after generic feedback; quiet corrects after feedback. This supports semantic ordering error. It does not establish a causal internal bias or prove that a different prompt will fix it.

Exhaustive finite-catalog check: 13,824 canonical equality checks passed (two sides times all actor/gesture/variation combinations for three cues, across four scenes). The experiment remains frozen; await Qwen and all final results before choosing a treatment. Existing full-protocol ordinal failures also remain preserved.

## Completed comparison and decision

Twenty calls completed. E2B full 3/4 initial, 4/4 after correction; compact 2/4 initial, 3/4 after correction. Qwen full 3/4 initial, 4/4 after correction; compact 4/4 initial. No additional compact failure type appeared. All compact failures were E2B semantic cue-order swaps with complete native replies; no schema failure. This isolates the observed locus, not the internal model cause. Next treatment: retain full as E2B baseline and test development-only instruction adaptation on fresh cases, holding the protocol constant within comparisons. Do not silently promote compact solely for its lower latency. Semantic rejection currently requires the fixture oracle; the compiler is not a natural-language verifier.

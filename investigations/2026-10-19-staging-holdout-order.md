# Staging holdout order mismatch investigation

## Frame

The goal is for each heldout natural-language request to describe the exact plan in its oracle. In `exact_ordinal_sequence_right_first`, the request assigns cue 0 to Calder and cue 1 to Iona, but `expected` assigns cue 0 to Iona and cue 1 to Calder. This can invalidate the fixture and train/evaluate the wrong sequence. The first-actor side balance is deliberately 4 left / 4 right and must stay balanced.

## Context

The parent reviewer identified this contradiction before any provider call. Earlier offline checks established that the expected JSON structures compile, their geometry and time slots resolve, and the side split is balanced; those checks did not check whether prose matched the expected actions. This file is untracked, so it has no committed file-specific history. The staging compiler uses cues sorted by slots 0, 1, 2; no provider call or rendered/model output is involved here.

## Hypotheses and discriminating checks

1. **Stale request after an oracle-side rebalance.** The expected assignments are intentional and the brief kept an earlier cue order. Check the literal cue order against the expected records and count the side of each expected slot-0 actor. This is supported if the brief contradicts expected and changing only the brief preserves the 4/4 split.
2. **Oracle cue order was accidentally reversed.** The brief is canonical and the expected records are wrong. This is supported if expected records fail the literal prompt while changing them restores consistency; also observe whether that changes the required side-balance invariant.
3. **Slot ordinals are interpreted differently by the host contract.** The prose and expected may agree under a nonstandard mapping. Check `SLOT_S` and `compile_staging` ordering, then compare all eight cues to slots. This is supported only if the host maps the first/second/third cues differently from slots 0/1/2.

## Diagnostic plan

- Preserve the exact pre-fix file text and SHA-256 in this report before editing.
- Read all eight requests beside all eight expected placement and cue structures. For each case, check actor/side assignment, gesture, variation, and order.
- Independently count expected slot-0 actor sides; confirm that the repair keeps exactly four on each side.
- Compile each expected plan offline and check the resolved positions and slot times. This verifies the compiler contract but does not substitute for the prose-to-oracle review.

## Pre-fix source receipt

SHA-256: `bdbc1590c7bdb301a7d8459bfc38b37d9088c20b8b28ad817620e71499d2d93e`

The complete source as received before the repair:

```python
"""Additional independent heldout cases for compact staging."""

EVAL_CASES = [
    {
        "id": "mention_right_actor_first_cue_left",
        "scene": {
            "revision": "extra-stage-a1",
            "anchor": {"id": "amber_post", "x_m": -0.3},
            "actor_ids": ["actor_kestrel_20", "actor_moss_44"],
        },
        "request": (
            "Moss goes on the screen-right of the amber post; Kestrel goes on its "
            "screen-left. In the first cue Kestrel gives a soft nod, in the second "
            "Moss waves clearly, and in the third Kestrel is neutral with soft "
            "variation. Keep both roots still."
        ),
        "expected": {
            "placements": [
                {"actor_id": "actor_kestrel_20", "anchor_id": "amber_post", "side": "left"},
                {"actor_id": "actor_moss_44", "anchor_id": "amber_post", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "actor_kestrel_20", "gesture": "nod", "variation": "soft"},
                {"slot": 1, "actor_id": "actor_moss_44", "gesture": "wave", "variation": "clear"},
                {"slot": 2, "actor_id": "actor_kestrel_20", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "mention_left_actor_first_cue_right",
        "scene": {
            "revision": "extra-stage-b2",
            "anchor": {"id": "white_column", "x_m": 0.4},
            "actor_ids": ["person_lyra_61", "person_tev_83"],
        },
        "request": (
            "Put Lyra screen-left of the white column and Tev screen-right. Cue one "
            "is a clear wave by Tev; cue two is a soft nod by Lyra; cue three is a "
            "soft neutral pose by Tev. Neither person walks."
        ),
        "expected": {
            "placements": [
                {"actor_id": "person_lyra_61", "anchor_id": "white_column", "side": "left"},
                {"actor_id": "person_tev_83", "anchor_id": "white_column", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "person_tev_83", "gesture": "wave", "variation": "clear"},
                {"slot": 1, "actor_id": "person_lyra_61", "gesture": "nod", "variation": "soft"},
                {"slot": 2, "actor_id": "person_tev_83", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "exact_ordinal_sequence_left_first",
        "scene": {
            "revision": "extra-stage-c3",
            "anchor": {"id": "floor_star", "x_m": -0.7},
            "actor_ids": ["unit_pavo_12", "unit_sena_37"],
        },
        "request": (
            "Pavo stands to the audience-left of the floor star, and Sena to its "
            "audience-right. The first cue belongs to Pavo: wave clearly. The second "
            "belongs to Sena: neutral softly. The third belongs to Pavo: nod softly. "
            "Hold their positions."
        ),
        "expected": {
            "placements": [
                {"actor_id": "unit_pavo_12", "anchor_id": "floor_star", "side": "left"},
                {"actor_id": "unit_sena_37", "anchor_id": "floor_star", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "unit_pavo_12", "gesture": "wave", "variation": "clear"},
                {"slot": 1, "actor_id": "unit_sena_37", "gesture": "neutral", "variation": "soft"},
                {"slot": 2, "actor_id": "unit_pavo_12", "gesture": "nod", "variation": "soft"},
            ],
        },
    },
    {
        "id": "exact_ordinal_sequence_right_first",
        "scene": {
            "revision": "extra-stage-d4",
            "anchor": {"id": "brass_ring", "x_m": 0.15},
            "actor_ids": ["guest_iona_06", "guest_calder_59"],
        },
        "request": (
            "From the audience view, Iona is on the brass ring's right and Calder on "
            "its left. In order: first Calder nods clearly; second Iona waves softly; "
            "third Calder is neutral softly. Keep both roots fixed."
        ),
        "expected": {
            "placements": [
                {"actor_id": "guest_iona_06", "anchor_id": "brass_ring", "side": "right"},
                {"actor_id": "guest_calder_59", "anchor_id": "brass_ring", "side": "left"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "guest_iona_06", "gesture": "wave", "variation": "soft"},
                {"slot": 1, "actor_id": "guest_calder_59", "gesture": "nod", "variation": "clear"},
                {"slot": 2, "actor_id": "guest_calder_59", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "two_corrections_last_one_left_first",
        "scene": {
            "revision": "extra-stage-e5",
            "anchor": {"id": "linen_marker", "x_m": 0.6},
            "actor_ids": ["performer_nell_73", "performer_orsa_28"],
        },
        "request": (
            "Nell stands screen-left of the linen marker and Orsa screen-right. Plan "
            "the cues as Nell waving softly first, Orsa nodding clearly second, and "
            "Nell neutral softly third. Correction: make the first cue Orsa waving "
            "clearly. Final correction: instead, the first cue is Nell nodding softly. "
            "The second and third cues stay as in the original plan."
        ),
        "expected": {
            "placements": [
                {"actor_id": "performer_nell_73", "anchor_id": "linen_marker", "side": "left"},
                {"actor_id": "performer_orsa_28", "anchor_id": "linen_marker", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "performer_nell_73", "gesture": "nod", "variation": "soft"},
                {"slot": 1, "actor_id": "performer_orsa_28", "gesture": "nod", "variation": "clear"},
                {"slot": 2, "actor_id": "performer_nell_73", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "repeat_actor_all_slots_right_first",
        "scene": {
            "revision": "extra-stage-f6",
            "anchor": {"id": "granite_cube", "x_m": -0.1},
            "actor_ids": ["avatar_suri_35", "avatar_tomel_88"],
        },
        "request": (
            "Place Suri on the granite cube's screen-left and Tomel on its screen-right. "
            "Tomel takes all three cues: a soft nod, then a clear wave, then a soft "
            "neutral pose. Suri takes no cue and remains stationary."
        ),
        "expected": {
            "placements": [
                {"actor_id": "avatar_suri_35", "anchor_id": "granite_cube", "side": "left"},
                {"actor_id": "avatar_tomel_88", "anchor_id": "granite_cube", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "avatar_tomel_88", "gesture": "nod", "variation": "soft"},
                {"slot": 1, "actor_id": "avatar_tomel_88", "gesture": "wave", "variation": "clear"},
                {"slot": 2, "actor_id": "avatar_tomel_88", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "indirect_screen_left_relation_left_first",
        "scene": {
            "revision": "extra-stage-g7",
            "anchor": {"id": "stage_beacon", "x_m": 0.05},
            "actor_ids": ["actor_vail_19", "actor_nori_46"],
        },
        "request": (
            "The stage is viewed from the audience. Vail belongs on the stage-left "
            "side of the beacon; Nori takes the other side. Stage-left here means "
            "the left side of the image. Vail waves softly in the opening cue, Nori "
            "nods clearly in the next cue, and Vail is neutral softly in the final "
            "cue. Keep roots still."
        ),
        "expected": {
            "placements": [
                {"actor_id": "actor_vail_19", "anchor_id": "stage_beacon", "side": "left"},
                {"actor_id": "actor_nori_46", "anchor_id": "stage_beacon", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "actor_vail_19", "gesture": "wave", "variation": "soft"},
                {"slot": 1, "actor_id": "actor_nori_46", "gesture": "nod", "variation": "clear"},
                {"slot": 2, "actor_id": "actor_vail_19", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "indirect_screen_right_relation_right_first",
        "scene": {
            "revision": "extra-stage-h8",
            "anchor": {"id": "east_arch", "x_m": -0.45},
            "actor_ids": ["member_ash_91", "member_bela_24"],
        },
        "request": (
            "Read the east arch from the audience viewpoint: Bela is on the image-left "
            "side of it, while Ash is on the image-right side. Ash gives the first cue, "
            "a clear nod; Bela gives the second, a soft wave; Ash is neutral softly in "
            "the last cue. Keep both roots in place."
        ),
        "expected": {
            "placements": [
                {"actor_id": "member_bela_24", "anchor_id": "east_arch", "side": "left"},
                {"actor_id": "member_ash_91", "anchor_id": "east_arch", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "member_ash_91", "gesture": "nod", "variation": "clear"},
                {"slot": 1, "actor_id": "member_bela_24", "gesture": "wave", "variation": "soft"},
                {"slot": 2, "actor_id": "member_ash_91", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
]
```

## Diagnostic findings before correction

The eight-case manual read-back found agreement in cases `mention_right_actor_first_cue_left`, `mention_left_actor_first_cue_right`, `exact_ordinal_sequence_left_first`, `two_corrections_last_one_left_first`, `repeat_actor_all_slots_right_first`, `indirect_screen_left_relation_left_first`, and `indirect_screen_right_relation_right_first`. The sole mismatch is `exact_ordinal_sequence_right_first`: its prose assigns slot 0 to Calder's clear nod and slot 1 to Iona's soft wave, while the oracle assigns slot 0 to Iona's soft wave and slot 1 to Calder's clear nod.

All eight oracle plans compile. The oracle's first-actor split is four left and four right. The host compiler defines two-second slots and returns cues sorted by slot, confirming that first/second/third map to slots 0/1/2. The source proves the contradiction, but by itself cannot establish whether prose or oracle was originally authored incorrectly. The explicit intended 4/4 balance makes a prose correction the selected repair; changing the oracle to match the old prose would violate that design constraint. Hypothesis 3 is ruled out by the explicit host slot mapping. Historical authorship timing is not established by compilation or this retrospective note.

## Correction chosen

Change only the ordinal-sequence request so its first and second cue descriptions match the existing oracle. Leave the oracle intact; this preserves the intended four-left/four-right first-actor balance. After the edit, rerun the eight-case manual request/oracle audit, compile all plans offline, and recount the side split. No provider call is needed or authorized for this diagnostic.

## Post-fix result

The request now says Iona waves softly in the first cue and Calder nods clearly in the second, matching the unchanged expected records. A manual read-back of all eight case briefs matches every expected placement and each ordered `(actor, gesture, variation)` cue tuple. All eight oracle plans compile; resolved placements and slot times match; the first-actor side split remains 4 left / 4 right.

Post-fix SHA-256 for `experiments/actor_staging_extra_holdouts.py`: `b9074aa63f58ffeed8fa78778d2b14f01469a2428655bef262ef522c24e8693a`.

Conclusion: the cause was a stale cue description in one request, not a compiler ordering rule or an inverted oracle. Confidence is high because the prose/oracle comparison covered all eight fixtures and a direct host compile confirmed slot semantics. No provider calls, rendered trials, or commits were made.

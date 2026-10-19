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
            "its left. In order: first Iona waves softly; second Calder nods clearly; "
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

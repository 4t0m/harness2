"""Fresh staging protocol cases, partitioned into train and heldout evaluation."""

TRAIN_CASES = [
    {
        "id": "ordinal_cue_sequence_training",
        "scene": {
            "revision": "ordinal-stage-v3",
            "anchor": {"id": "copper_pillar", "x_m": -0.2},
            "actor_ids": ["actor_aster_204", "actor_bram_518"],
        },
        "request": (
            "Put Aster on screen-left of the copper pillar and Bram on screen-right. "
            "For the first cue, Aster waves clearly; for the second, Bram is neutral "
            "with soft variation; for the final cue, Aster nods softly. Hold both roots "
            "still for the full sequence."
        ),
        "expected": {
            "placements": [
                {"actor_id": "actor_aster_204", "anchor_id": "copper_pillar", "side": "left"},
                {"actor_id": "actor_bram_518", "anchor_id": "copper_pillar", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "actor_aster_204", "gesture": "wave", "variation": "clear"},
                {"slot": 1, "actor_id": "actor_bram_518", "gesture": "neutral", "variation": "soft"},
                {"slot": 2, "actor_id": "actor_aster_204", "gesture": "nod", "variation": "soft"},
            ],
        },
    },
    {
        "id": "audience_view_side_relation_training",
        "scene": {
            "revision": "audience-mark-r8",
            "anchor": {"id": "silver_disc", "x_m": 0.45},
            "actor_ids": ["performer_cedar_63", "performer_lumen_91"],
        },
        "request": (
            "Imagine you are looking at the stage from the audience. Cedar belongs on "
            "the silver disc's audience-left side; Lumen takes the opposite side. At "
            "cue 0 Cedar nods softly, at cue 1 Lumen waves clearly, and at cue 2 Cedar "
            "is neutral with soft variation. Keep their roots fixed."
        ),
        "expected": {
            "placements": [
                {"actor_id": "performer_cedar_63", "anchor_id": "silver_disc", "side": "left"},
                {"actor_id": "performer_lumen_91", "anchor_id": "silver_disc", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "performer_cedar_63", "gesture": "nod", "variation": "soft"},
                {"slot": 1, "actor_id": "performer_lumen_91", "gesture": "wave", "variation": "clear"},
                {"slot": 2, "actor_id": "performer_cedar_63", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "cue_amendment_training",
        "scene": {
            "revision": "amended-stage-k2",
            "anchor": {"id": "paper_lantern", "x_m": 0.0},
            "actor_ids": ["unit_sable_72", "unit_wren_36"],
        },
        "request": (
            "Set Sable to screen-right of the paper lantern and Wren to screen-left. "
            "Initially, Sable waves softly in cue 0, Wren nods clearly in cue 1, and "
            "Sable is neutral softly in cue 2. Correction: change cue 0 to a clear "
            "nod by Wren instead; leave cues 1 and 2 as stated. Neither actor travels."
        ),
        "expected": {
            "placements": [
                {"actor_id": "unit_wren_36", "anchor_id": "paper_lantern", "side": "left"},
                {"actor_id": "unit_sable_72", "anchor_id": "paper_lantern", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "unit_wren_36", "gesture": "nod", "variation": "clear"},
                {"slot": 1, "actor_id": "unit_wren_36", "gesture": "nod", "variation": "clear"},
                {"slot": 2, "actor_id": "unit_sable_72", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "same_actor_repeated_training",
        "scene": {
            "revision": "repeat-stage-m5",
            "anchor": {"id": "red_marker", "x_m": -0.65},
            "actor_ids": ["host_ember_11", "host_quill_84"],
        },
        "request": (
            "Quill stands screen-left of the red marker; Ember stands screen-right. "
            "Ember handles every cue: wave softly first, nod clearly second, then "
            "remain neutral with soft variation in the third. Quill stays still and "
            "does not take a cue."
        ),
        "expected": {
            "placements": [
                {"actor_id": "host_quill_84", "anchor_id": "red_marker", "side": "left"},
                {"actor_id": "host_ember_11", "anchor_id": "red_marker", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "host_ember_11", "gesture": "wave", "variation": "soft"},
                {"slot": 1, "actor_id": "host_ember_11", "gesture": "nod", "variation": "clear"},
                {"slot": 2, "actor_id": "host_ember_11", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
]

EVAL_CASES = [
    {
        "id": "ordinal_middle_and_final_eval",
        "scene": {
            "revision": "quiet-hall-q7",
            "anchor": {"id": "hall_compass", "x_m": 0.8},
            "actor_ids": ["guide_morrow_305", "guide_tavi_622"],
        },
        "request": (
            "In the audience view, put Morrow on the right of the hall compass and "
            "Tavi on the left. Morrow gives the opening cue, a soft nod. Tavi gets "
            "the middle cue and gives a clear wave. The closing cue belongs to Morrow, "
            "who is neutral softly. Leave their roots stationary."
        ),
        "expected": {
            "placements": [
                {"actor_id": "guide_tavi_622", "anchor_id": "hall_compass", "side": "left"},
                {"actor_id": "guide_morrow_305", "anchor_id": "hall_compass", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "guide_morrow_305", "gesture": "nod", "variation": "soft"},
                {"slot": 1, "actor_id": "guide_tavi_622", "gesture": "wave", "variation": "clear"},
                {"slot": 2, "actor_id": "guide_morrow_305", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "actor_perspective_to_screen_side_eval",
        "scene": {
            "revision": "atrium-cue-f4",
            "anchor": {"id": "atrium_kiosk", "x_m": -0.55},
            "actor_ids": ["avatar_nix_177", "avatar_ora_238"],
        },
        "request": (
            "Nix should stand on the kiosk's right-hand side as seen by someone facing "
            "outward from the stage toward the audience. Therefore Nix appears on the "
            "audience's screen-left; Ora stands screen-right. Give Ora a clear nod in "
            "the first cue, Nix a soft wave in the second, and Ora a soft neutral pose "
            "in the third. No root movement."
        ),
        "expected": {
            "placements": [
                {"actor_id": "avatar_nix_177", "anchor_id": "atrium_kiosk", "side": "left"},
                {"actor_id": "avatar_ora_238", "anchor_id": "atrium_kiosk", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "avatar_ora_238", "gesture": "nod", "variation": "clear"},
                {"slot": 1, "actor_id": "avatar_nix_177", "gesture": "wave", "variation": "soft"},
                {"slot": 2, "actor_id": "avatar_ora_238", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "placement_and_cue_amendment_eval",
        "scene": {
            "revision": "final-pass-z6",
            "anchor": {"id": "green_podium", "x_m": 0.25},
            "actor_ids": ["actor_pip_493", "actor_ren_860"],
        },
        "request": (
            "First plan: Pip screen-left and Ren screen-right of the green podium. "
            "Pip waves softly in cue 0, Ren nods clearly in cue 1, and Pip is neutral "
            "softly in cue 2. Final revision: swap their sides, and replace cue 0 with "
            "Ren giving a clear wave. Keep cues 1 and 2 exactly as in the first plan; "
            "both roots stay fixed."
        ),
        "expected": {
            "placements": [
                {"actor_id": "actor_pip_493", "anchor_id": "green_podium", "side": "right"},
                {"actor_id": "actor_ren_860", "anchor_id": "green_podium", "side": "left"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "actor_ren_860", "gesture": "wave", "variation": "clear"},
                {"slot": 1, "actor_id": "actor_ren_860", "gesture": "nod", "variation": "clear"},
                {"slot": 2, "actor_id": "actor_pip_493", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "alternating_actor_sequence_eval",
        "scene": {
            "revision": "alternation-set-h3",
            "anchor": {"id": "moon_tile", "x_m": -0.1},
            "actor_ids": ["participant_lyric_57", "participant_oma_42"],
        },
        "request": (
            "From the audience, Lyric is to the moon tile's left and Oma to its right. "
            "Alternate who takes each cue, starting with Lyric: Lyric gives a clear "
            "wave, Oma follows with a soft nod, and Lyric closes with a soft neutral "
            "pose. Keep both in their places."
        ),
        "expected": {
            "placements": [
                {"actor_id": "participant_lyric_57", "anchor_id": "moon_tile", "side": "left"},
                {"actor_id": "participant_oma_42", "anchor_id": "moon_tile", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "participant_lyric_57", "gesture": "wave", "variation": "clear"},
                {"slot": 1, "actor_id": "participant_oma_42", "gesture": "nod", "variation": "soft"},
                {"slot": 2, "actor_id": "participant_lyric_57", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
]

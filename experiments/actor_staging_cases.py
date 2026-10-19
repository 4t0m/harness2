"""Independent natural-language staging fixtures for the actor compiler lane.

Expected compiler structures are oracle-side data; prompts expose only scene and request.
The first two cases are intended for development/render demonstration. The last two
are held for a future editor and should not be exposed during development.
"""

CASES = [
    {
        "id": "plinth_pair_intro",
        "scene": {
            "revision": "stage-demo-r4",
            "anchor": {"id": "stone_plinth", "x_m": 0.0},
            "actor_ids": ["actor_rowan_17", "actor_ivo_42"],
        },
        "request": (
            "Stage Rowan on the screen-left side of the stone plinth and Ivo on its "
            "screen-right side. Keep both roots in place throughout the cues. At the "
            "first cue, Rowan gives a soft wave; at the second, Ivo gives a clear nod. "
            "At the third cue, Rowan is neutral, softly. Each cue begins at its numbered "
            "slot, with two seconds per slot."
        ),
        "expected": {
            "placements": [
                {"actor_id": "actor_rowan_17", "anchor_id": "stone_plinth", "side": "left"},
                {"actor_id": "actor_ivo_42", "anchor_id": "stone_plinth", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "actor_rowan_17", "gesture": "wave", "variation": "soft"},
                {"slot": 1, "actor_id": "actor_ivo_42", "gesture": "nod", "variation": "clear"},
                {"slot": 2, "actor_id": "actor_rowan_17", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "gallery_roles_reversed",
        "scene": {
            "revision": "gallery-layout-12",
            "anchor": {"id": "blue_marker", "x_m": 0.35},
            "actor_ids": ["unit_mica_08", "unit_sol_31"],
        },
        "request": (
            "For the blue marker, put Sol on screen-left and Mica on screen-right. "
            "Do not move either actor's root. At cue 0, Mica nods clearly; at cue 1, "
            "Sol waves clearly. At cue 2, Mica is neutral with soft variation. The "
            "numbered cue slots are two seconds apart in duration."
        ),
        "expected": {
            "placements": [
                {"actor_id": "unit_sol_31", "anchor_id": "blue_marker", "side": "left"},
                {"actor_id": "unit_mica_08", "anchor_id": "blue_marker", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "unit_mica_08", "gesture": "nod", "variation": "clear"},
                {"slot": 1, "actor_id": "unit_sol_31", "gesture": "wave", "variation": "clear"},
                {"slot": 2, "actor_id": "unit_mica_08", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "archive_nod_then_wave",
        "scene": {
            "revision": "archive-stage-b9",
            "anchor": {"id": "archive_stand", "x_m": -0.4},
            "actor_ids": ["performer_north_6", "performer_kite_29"],
        },
        "request": (
            "Place Kite to the screen-right of the archive stand and North to its "
            "screen-left. Keep their roots stationary. North should nod clearly in "
            "slot 0; Kite should wave softly in slot 1; and Kite should be neutral "
            "with soft variation in slot 2. Each slot lasts two seconds. Nod comes "
            "before the wave."
        ),
        "expected": {
            "placements": [
                {"actor_id": "performer_north_6", "anchor_id": "archive_stand", "side": "left"},
                {"actor_id": "performer_kite_29", "anchor_id": "archive_stand", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "performer_north_6", "gesture": "nod", "variation": "clear"},
                {"slot": 1, "actor_id": "performer_kite_29", "gesture": "wave", "variation": "soft"},
                {"slot": 2, "actor_id": "performer_kite_29", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
    {
        "id": "quiet_checkpoint_pair",
        "scene": {
            "revision": "checkpoint-scene-5c",
            "anchor": {"id": "floor_compass", "x_m": 0.6},
            "actor_ids": ["guest_elm_53", "guest_rill_14"],
        },
        "request": (
            "At the floor compass, put Elm on screen-right and Rill on screen-left. "
            "Keep both actors planted without root travel. Make the whole sequence "
            "quiet: Elm gives a soft wave in slot 0, Rill gives a soft nod in slot 1, "
            "and Rill is neutral with soft variation in slot 2. Every slot lasts two seconds."
        ),
        "expected": {
            "placements": [
                {"actor_id": "guest_rill_14", "anchor_id": "floor_compass", "side": "left"},
                {"actor_id": "guest_elm_53", "anchor_id": "floor_compass", "side": "right"},
            ],
            "cues": [
                {"slot": 0, "actor_id": "guest_elm_53", "gesture": "wave", "variation": "soft"},
                {"slot": 1, "actor_id": "guest_rill_14", "gesture": "nod", "variation": "soft"},
                {"slot": 2, "actor_id": "guest_rill_14", "gesture": "neutral", "variation": "soft"},
            ],
        },
    },
]

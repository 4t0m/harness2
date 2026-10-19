"""Fresh feasible structured tasks for held-out H2 guidance evaluation.

All cases remain within the planted four-side-step capability. The structured
task is authoritative; requests paraphrase its constraints without adding
independent conditions.
"""

CASES = [
    {
        "id": "h2_eval_offset_reentry_positive_target",
        "family": "offset_return_asymmetric_lane",
        "feasible": True,
        "task": {
            "id": "h2_eval_offset_reentry_positive_target",
            "start_x_mm": -150,
            "target_x_mm": 250,
            "root_bounds_mm": [-350, 450],
            "required_moves": {"0": "step_right", "3": "step_right"},
            "required_variations": {"1": "clear"},
        },
        "request": "Begin at -150 mm and finish at +250 mm in world x. Keep the root within -350 to +450 mm. Make the first and fourth steps rightward; give the second step a clear accent.",
    },
    {
        "id": "h2_eval_leftward_recovery_from_far_side",
        "family": "bound_forced_middle_direction",
        "feasible": True,
        "task": {
            "id": "h2_eval_leftward_recovery_from_far_side",
            "start_x_mm": 350,
            "target_x_mm": -50,
            "root_bounds_mm": [-150, 650],
            "required_moves": {"0": "step_left", "2": "step_left"},
            "required_variations": {"3": "soft"},
        },
        "request": "From +350 mm, bring the root back to -50 mm without leaving the lane [-150, +650]. Step left in slots one and three, and use a soft variation for the final step.",
    },
    {
        "id": "h2_eval_crossing_from_negative_offset",
        "family": "nonzero_negative_origin",
        "feasible": True,
        "task": {
            "id": "h2_eval_crossing_from_negative_offset",
            "start_x_mm": -550,
            "target_x_mm": -150,
            "root_bounds_mm": [-650, 250],
            "required_moves": {"0": "step_right", "3": "step_left"},
            "required_variations": {"0": "soft", "2": "clear"},
        },
        "request": "Move from x=-550 mm to x=-150 mm, staying inside [-650, 250] mm. The opening step goes right, the last goes left, the opening accent is soft, and the third accent is clear.",
    },
    {
        "id": "h2_eval_positive_start_bounded_return",
        "family": "two_orderings_under_asymmetric_bounds",
        "feasible": True,
        "task": {
            "id": "h2_eval_positive_start_bounded_return",
            "start_x_mm": 550,
            "target_x_mm": 150,
            "root_bounds_mm": [-50, 650],
            "required_moves": {"0": "step_left", "3": "step_left"},
            "required_variations": {"1": "clear"},
        },
        "request": "Start at +550 mm and end at +150 mm, keeping the pelvis between -50 and +650 mm throughout. Use leftward steps at both ends and a clear accent on the second step.",
    },
    {
        "id": "h2_eval_rightward_opening_then_three_lefts",
        "family": "edge_start_with_middle_accents",
        "feasible": True,
        "task": {
            "id": "h2_eval_rightward_opening_then_three_lefts",
            "start_x_mm": 150,
            "target_x_mm": -250,
            "root_bounds_mm": [-450, 350],
            "required_moves": {"0": "step_right", "3": "step_left"},
            "required_variations": {"1": "soft", "2": "soft"},
        },
        "request": "From +150 mm, reach -250 mm while the root stays in [-450, +350] mm. The first step must go right and the fourth left; use soft accents on both middle steps.",
    },
    {
        "id": "h2_eval_lower_edge_then_climb",
        "family": "lower_bound_forces_remaining_route",
        "feasible": True,
        "task": {
            "id": "h2_eval_lower_edge_then_climb",
            "start_x_mm": -350,
            "target_x_mm": 50,
            "root_bounds_mm": [-550, 350],
            "required_moves": {"0": "step_left", "3": "step_right"},
            "required_variations": {"1": "soft", "3": "clear"},
        },
        "request": "Begin at -350 mm, finish at +50 mm, and keep the pelvis within [-550, +350]. Step left first and right last. Make the second step soft and the final step clear.",
    },
    {
        "id": "h2_eval_tight_upper_edge_crossback",
        "family": "tight_lane_forced_path_one",
        "feasible": True,
        "task": {
            "id": "h2_eval_tight_upper_edge_crossback",
            "start_x_mm": 150,
            "target_x_mm": 150,
            "root_bounds_mm": [-50, 350],
            "required_moves": {"0": "step_right", "3": "step_left"},
            "required_variations": {"1": "clear", "2": "soft"},
        },
        "request": "Stay in the narrow lane from -50 to +350 mm and finish where you started at +150 mm. Move right first and left fourth; the second accent is clear and the third is soft. Keep every intermediate root position in the lane.",
    },
    {
        "id": "h2_eval_tight_lower_edge_reversal",
        "family": "tight_lane_forced_path_two",
        "feasible": True,
        "task": {
            "id": "h2_eval_tight_lower_edge_reversal",
            "start_x_mm": -150,
            "target_x_mm": -150,
            "root_bounds_mm": [-350, 50],
            "required_moves": {"0": "step_left", "3": "step_right"},
            "required_variations": {"0": "clear", "2": "soft"},
        },
        "request": "The sequence starts and ends at -150 mm. Keep the pelvis between -350 and +50 mm; make the first step left with a clear accent, the third step left with a soft accent, and the final step right.",
    },
]

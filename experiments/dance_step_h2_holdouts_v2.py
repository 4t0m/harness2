"""Fresh feasible structured stepping tasks for an H2 evaluation pass.

Only task facts and user-facing requests are exported. The evaluator may accept
any plan that satisfies the host task; no single motion plan is an oracle.
"""

CASES = [
    {
        "id": "h2_eval_v2_positive_offset_reach",
        "task": {
            "id": "h2_eval_v2_positive_offset_reach",
            "start_x_mm": 250,
            "target_x_mm": 650,
            "root_bounds_mm": [50, 850],
            "required_moves": {"0": "step_right", "3": "step_right"},
            "required_variations": {"1": "soft"},
        },
        "request": "Starting at +250 mm, finish at +650 mm without leaving the lane from +50 to +850 mm. The first and last steps go right; the second one is soft.",
    },
    {
        "id": "h2_eval_v2_return_to_negative_mark",
        "task": {
            "id": "h2_eval_v2_return_to_negative_mark",
            "start_x_mm": -450,
            "target_x_mm": -50,
            "root_bounds_mm": [-750, 150],
            "required_moves": {"0": "step_right", "2": "step_left"},
            "required_variations": {"3": "clear"},
        },
        "request": "Move from x=-450 mm to x=-50 mm, keeping the root inside [-750, +150] mm. Go right in the opening slot and left in slot three; make the final accent clear.",
    },
    {
        "id": "h2_eval_v2_leftward_route_from_east",
        "task": {
            "id": "h2_eval_v2_leftward_route_from_east",
            "start_x_mm": 450,
            "target_x_mm": 50,
            "root_bounds_mm": [-150, 750],
            "required_moves": {"0": "step_left", "3": "step_left"},
            "required_variations": {"2": "soft"},
        },
        "request": "From +450 mm, end at +50 mm while staying between -150 and +750 mm. Step left at both ends and use a soft accent in the third slot.",
    },
    {
        "id": "h2_eval_v2_boundary_start_crossing",
        "task": {
            "id": "h2_eval_v2_boundary_start_crossing",
            "start_x_mm": -650,
            "target_x_mm": -250,
            "root_bounds_mm": [-850, 350],
            "required_moves": {"0": "step_left", "3": "step_right"},
            "required_variations": {"0": "clear", "1": "soft"},
        },
        "request": "Begin at -650 mm and land at -250 mm, never crossing the -850 to +350 mm lane. Make the opening move left with a clear accent, follow it with a soft second move, and finish with a right step.",
    },
    {
        "id": "h2_eval_v2_soft_middle_return",
        "task": {
            "id": "h2_eval_v2_soft_middle_return",
            "start_x_mm": -250,
            "target_x_mm": 150,
            "root_bounds_mm": [-450, 550],
            "required_moves": {"0": "step_right", "3": "step_left"},
            "required_variations": {"1": "clear", "2": "soft"},
        },
        "request": "Take the root from -250 mm to +150 mm inside [-450, +550]. The opening step is right and the last step left. Accent the second step clearly and keep the third soft.",
    },
    {
        "id": "h2_eval_v2_recover_from_upper_offset",
        "task": {
            "id": "h2_eval_v2_recover_from_upper_offset",
            "start_x_mm": 650,
            "target_x_mm": 250,
            "root_bounds_mm": [50, 850],
            "required_moves": {"0": "step_left", "2": "step_left"},
            "required_variations": {"0": "soft", "3": "clear"},
        },
        "request": "Return from +650 mm to +250 mm, keeping the pelvis in [50, +850]. Steps one and three go left; soften the opening and make the final accent clear.",
    },
    {
        "id": "h2_eval_v2_upper_lane_crossback",
        "task": {
            "id": "h2_eval_v2_upper_lane_crossback",
            "start_x_mm": 250,
            "target_x_mm": 250,
            "root_bounds_mm": [50, 450],
            "required_moves": {"0": "step_right", "3": "step_left"},
            "required_variations": {"1": "soft", "2": "clear"},
        },
        "request": "Start and finish at +250 mm, staying in the narrow [50, 450] mm lane throughout. Go right first and left last; the second step is soft and the third is clear.",
    },
    {
        "id": "h2_eval_v2_lower_lane_crossback",
        "task": {
            "id": "h2_eval_v2_lower_lane_crossback",
            "start_x_mm": -250,
            "target_x_mm": -250,
            "root_bounds_mm": [-450, -50],
            "required_moves": {"0": "step_left", "3": "step_right"},
            "required_variations": {"0": "clear", "2": "soft"},
        },
        "request": "Stay between -450 and -50 mm as you begin and end at -250 mm. Step left first with a clear accent, left again in slot three with a soft accent, and right in the final slot.",
    },
]

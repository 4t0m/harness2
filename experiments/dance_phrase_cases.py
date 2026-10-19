"""Bounded phrase-planning cases and a host-side plan predicate.

The public catalog and requests define a finite symbolic planning problem. The
constraints and score_plan oracle are host-side and must stay out of model prompts.
No motion generation, dance-quality, or taste claim is made here.
"""

from collections import Counter
from collections.abc import Mapping

PUBLIC_RULES = (
    "Make exactly four moves, each lasting two beats, at 120 BPM. The phrase starts "
    "in rest and must end in rest. Use only the listed moves. Choose exactly one "
    "variation, soft or clear, for every move. Return only JSON of the form "
    '{"moves":[["move_id","variation"], ...]}.'
)

# Public move shelf. Every move is exactly two beats.
MOVE_CATALOG = {
    "rise": {"beats": 2, "entry": "rest", "exit": "open"},
    "sway": {"beats": 2, "entry": "open", "exit": "open"},
    "pulse": {"beats": 2, "entry": "open", "exit": "open"},
    "settle": {"beats": 2, "entry": "open", "exit": "rest"},
    "hold": {"beats": 2, "entry": "rest", "exit": "rest"},
}
VARIATIONS = ("soft", "clear")


def _pairs(*move_ids, variations=VARIATIONS):
    return [[move_id, variation] for move_id in move_ids for variation in variations]


CASES = [
    {
        "id": "open_then_sway_and_pulse_either_order",
        "request": (
            "Rise out of rest. While open, include one sway and one pulse, in either "
            "order, then settle back to rest. Choose the variation independently for "
            "each move."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("rise"), _pairs("sway", "pulse"),
                _pairs("sway", "pulse"), _pairs("settle"),
            ],
            "move_counts": {"sway": {"min": 1, "max": 1}, "pulse": {"min": 1, "max": 1}},
        },
    },
    {
        "id": "explicit_pulse_and_sway_variations",
        "request": (
            "Rise first. In the two open middle moves, do one sway softly and one "
            "pulse clearly, in either order. Settle last."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("rise"),
                _pairs("sway", variations=("soft",)) + _pairs("pulse", variations=("clear",)),
                _pairs("sway", variations=("soft",)) + _pairs("pulse", variations=("clear",)),
                _pairs("settle"),
            ],
            "move_counts": {"sway": {"min": 1, "max": 1}, "pulse": {"min": 1, "max": 1}},
        },
    },
    {
        "id": "quiet_hold_rise_settle_hold",
        "request": (
            "Give the phrase a quiet opening and ending: hold in rest, rise, settle "
            "back to rest, and hold there to finish. Either listed variation is fine "
            "on each move."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("hold"), _pairs("rise"), _pairs("settle"), _pairs("hold"),
            ],
        },
    },
    {
        "id": "repeat_sway_through_open_middle",
        "request": (
            "Rise, keep the open section swaying for both middle moves, then settle. "
            "Pick soft or clear separately for each move."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("rise"), _pairs("sway"), _pairs("sway"), _pairs("settle"),
            ],
            "move_counts": {"sway": {"min": 2, "max": 2}},
        },
    },
    # Pre-inference review clarified the correction scope; constraints unchanged.
    {
        "id": "last_correction_sets_middle_order",
        "request": (
            "Draft: rise clearly, pulse softly, sway clearly, settle softly. Final "
            "correction: keep the clear rise and soft settle, but put the soft sway "
            "before the soft pulse. The correction replaces only the two middle moves."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("rise", variations=("clear",)),
                _pairs("sway", variations=("soft",)),
                _pairs("pulse", variations=("soft",)),
                _pairs("settle", variations=("soft",)),
            ],
        },
    },
    {
        "id": "held_intro_then_open_choice",
        "request": (
            "Begin with a soft hold in rest, then rise clearly. For the open middle "
            "section choose either sway or pulse, softly. Finish with a clear settle."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("hold", variations=("soft",)),
                _pairs("rise", variations=("clear",)),
                _pairs("sway", "pulse", variations=("soft",)),
                _pairs("settle", variations=("clear",)),
            ],
        },
    },
    {
        "id": "rise_pulse_optional_second_pulse",
        "request": (
            "Rise, then make the next move a clear pulse. For the following open move, "
            "either sway or pulse using a variation of your choice. Settle softly to end."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("rise"), _pairs("pulse", variations=("clear",)),
                _pairs("sway", "pulse"), _pairs("settle", variations=("soft",)),
            ],
            "move_counts": {"pulse": {"min": 1, "max": 2}},
        },
    },
    {
        "id": "open_sway_then_quiet_final_hold",
        "request": (
            "Rise into the open state, sway once, settle back into rest, and finish "
            "with a hold. Choose either variation for each move."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("rise"), _pairs("sway"), _pairs("settle"), _pairs("hold"),
            ],
        },
    },
]

# Kept in a separate bucket: these requests have no valid four-move plan. They do
# not contribute to the executable-case success rate and do not ask for a refusal
# field outside the model's moves-only response contract.
INFEASIBLE_CASES = [
    {
        "id": "infeasible_settle_from_initial_rest",
        "kind": "infeasible_transition",
        "request": (
            "The phrase starts in rest. Make settle the very first move, then rise, "
            "sway, and settle again. Use any listed variation for each move."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("settle"), _pairs("rise"), _pairs("sway"), _pairs("settle"),
            ],
        },
    },
    {
        "id": "infeasible_sway_after_return_to_rest",
        "kind": "infeasible_transition",
        "request": (
            "Rise, settle all the way back to rest, sway next without rising again, "
            "and settle once more. Choose any listed variation for every move."
        ),
        "constraints": {
            "allowed_options_by_slot": [
                _pairs("rise"), _pairs("settle"), _pairs("sway"), _pairs("settle"),
            ],
        },
    },
]


def _extract_moves(compiled_or_moves):
    """Accept the raw moves array, a moves-only response object, or compiled move rows."""
    violations = []
    candidate = compiled_or_moves
    if isinstance(candidate, Mapping):
        if "moves" not in candidate:
            return None, ["missing_moves"]
        candidate = candidate["moves"]
    if not isinstance(candidate, (list, tuple)):
        return None, ["moves_must_be_array"]
    parsed = []
    row_metadata = []
    for index, row in enumerate(candidate):
        metadata = None
        if isinstance(row, Mapping):
            if not {"move_id", "variation"}.issubset(row):
                violations.append(f"move_row_fields:{index}")
                parsed.append((None, None))
                row_metadata.append(None)
                continue
            move_id, variation = row["move_id"], row["variation"]
            metadata = row
        elif isinstance(row, (list, tuple)) and len(row) == 2:
            move_id, variation = row
        else:
            violations.append(f"move_pair_shape:{index}")
            parsed.append((None, None))
            row_metadata.append(None)
            continue
        parsed.append((move_id, variation))
        row_metadata.append(metadata)
    return (parsed, row_metadata), violations


def score_plan(compiled_or_moves, case):
    """Return host-side violations; an empty list means the plan satisfies constraints.

    Input may be the model's {"moves": [[move_id, variation], ...]} object, the
    moves array directly (useful for enumeration), or compiled rows containing
    move_id and variation. Compiled rows may also carry start_beat/end_beat fields.
    This predicate checks symbolic planning constraints only, not motion or taste.
    """
    violations = []
    if isinstance(compiled_or_moves, Mapping):
        if "moves" not in compiled_or_moves:
            return ["missing_moves"]
        rows = compiled_or_moves["moves"]
        # The model-facing response is moves-only. Compiled row objects are an
        # alternate host input form and may be accompanied by compiler metadata.
        if set(compiled_or_moves) != {"moves"} and not (
            isinstance(rows, (list, tuple)) and rows and all(isinstance(row, Mapping) for row in rows)
        ):
            violations.append("output_fields")
    else:
        rows = compiled_or_moves
    extracted, shape_violations = _extract_moves(rows)
    violations.extend(shape_violations)
    if extracted is None:
        return violations
    moves, row_metadata = extracted
    if len(moves) != 4:
        violations.append("move_count")

    constraints = case.get("constraints", {})
    allowed_by_slot = constraints.get("allowed_options_by_slot", [])
    if len(allowed_by_slot) != 4:
        violations.append("constraint_slot_count")
    counts = Counter()
    state = "rest"
    beats_total = 0
    for index, ((move_id, variation), metadata) in enumerate(zip(moves, row_metadata)):
        if type(move_id) is not str or move_id not in MOVE_CATALOG:
            violations.append(f"unsupported_move:{index}")
            continue
        if type(variation) is not str or variation not in VARIATIONS:
            violations.append(f"unsupported_variation:{index}")
        move = MOVE_CATALOG[move_id]
        if move["entry"] != state:
            violations.append(f"transition:{index}")
        state = move["exit"]
        beats_total += move["beats"]
        counts[move_id] += 1
        if index < len(allowed_by_slot):
            options = {tuple(option) for option in allowed_by_slot[index]}
            if (move_id, variation) not in options:
                violations.append(f"case_constraint:{index}")
        if metadata is not None:
            start = metadata.get("start_beat")
            end = metadata.get("end_beat")
            if (start is None) != (end is None):
                violations.append(f"compiled_timing_fields:{index}")
            elif start is not None and (start != index * 2 or end != (index + 1) * 2):
                violations.append(f"compiled_timing:{index}")
            if "beats" in metadata and metadata["beats"] != 2:
                violations.append(f"compiled_duration:{index}")
    if beats_total != 8:
        violations.append("phrase_duration")
    if state != "rest":
        violations.append("end_state")
    for move_id, bounds in constraints.get("move_counts", {}).items():
        count = counts[move_id]
        if count < bounds.get("min", 0) or count > bounds.get("max", 4):
            violations.append(f"move_count_constraint:{move_id}")
    return violations

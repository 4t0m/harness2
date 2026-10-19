"""Selective one-slot edits for the deterministic four-move phrase shelf.

Expected plans are host-side oracles. Model payloads include only the request,
source plan, editable slots, and selected response protocol.
"""

import copy

PUBLIC_CONTRACT = (
    "The source contains four valid two-beat moves that start and end at rest. "
    "Change exactly one move pair, and only at a listed editable slot. Preserve "
    "every other source slot exactly. Move IDs are rise, sway, pulse, settle, hold; "
    "variations are soft and clear. Return either the full plan as strict JSON "
    '{"moves":[["move_id","variation"], ...]} or the requested one-slot patch as '
    '{"slot":0,"move":"move_id","variation":"soft"}. Return no extra fields.'
)

FULL_PLAN_PROTOCOL = (
    'Return only {"moves":[["move_id","variation"], ...]} with the complete four-slot plan. '
    "Make exactly one change at an editable slot and copy every other source pair exactly."
)
PATCH_PROTOCOL = (
    'Return only {"slot":0,"move":"move_id","variation":"soft"} for the one changed slot. '
    "The slot must be listed as editable."
)

CASES = [
    {
        "id": "change_third_move_variation",
        "source_moves": [
            ["rise", "soft"], ["sway", "clear"], ["pulse", "soft"], ["settle", "clear"],
        ],
        "editable_slots": [2],
        "request": (
            "Make the pulse in the third move clear. Keep its move name and preserve "
            "the first, second, and fourth source moves exactly."
        ),
        "expected_moves": [
            ["rise", "soft"], ["sway", "clear"], ["pulse", "clear"], ["settle", "clear"],
        ],
    },
    {
        "id": "match_opening_hold_to_final_hold",
        "source_moves": [
            ["hold", "soft"], ["rise", "clear"], ["settle", "soft"], ["hold", "clear"],
        ],
        "editable_slots": [0, 3],
        "request": (
            "Make the opening hold use the same variation as the final hold. The final "
            "hold is already clear, so change only the opening hold; leave the two "
            "middle moves and final move unchanged."
        ),
        "expected_moves": [
            ["hold", "clear"], ["rise", "clear"], ["settle", "soft"], ["hold", "clear"],
        ],
    },
    {
        "id": "replace_sway_with_pulse",
        "source_moves": [
            ["rise", "clear"], ["sway", "soft"], ["pulse", "clear"], ["settle", "soft"],
        ],
        "editable_slots": [1],
        "request": (
            "Replace the sway in the second slot with a pulse, keeping that slot's "
            "variation soft. Preserve the other three approved source moves."
        ),
        "expected_moves": [
            ["rise", "clear"], ["pulse", "soft"], ["pulse", "clear"], ["settle", "soft"],
        ],
    },
    {
        "id": "replace_middle_pulse_with_sway",
        "source_moves": [
            ["rise", "soft"], ["pulse", "clear"], ["pulse", "soft"], ["settle", "clear"],
        ],
        "editable_slots": [2],
        "request": (
            "Change the later of the two pulses, the third move, into a sway. Keep its "
            "variation soft and leave the earlier pulse and both endpoints exactly as they are."
        ),
        "expected_moves": [
            ["rise", "soft"], ["pulse", "clear"], ["sway", "soft"], ["settle", "clear"],
        ],
    },
    {
        "id": "choose_later_of_two_editable_middle_slots",
        "source_moves": [
            ["rise", "clear"], ["sway", "soft"], ["pulse", "soft"], ["settle", "clear"],
        ],
        "editable_slots": [1, 2],
        "request": (
            "Only the two middle slots are editable. Leave the earlier middle sway "
            "untouched; make the later middle pulse clear. Preserve the rise and settle."
        ),
        "expected_moves": [
            ["rise", "clear"], ["sway", "soft"], ["pulse", "clear"], ["settle", "clear"],
        ],
    },
    {
        "id": "final_amendment_overrides_first_edit",
        "source_moves": [
            ["rise", "soft"], ["sway", "clear"], ["pulse", "clear"], ["settle", "soft"],
        ],
        "editable_slots": [1, 2],
        "request": (
            "First, change the second-slot sway into a clear pulse. Final correction: "
            "do not change that second slot after all; instead make the third-slot "
            "pulse soft. The final correction replaces the earlier edit, and all other "
            "source moves stay exactly as they were."
        ),
        "expected_moves": [
            ["rise", "soft"], ["sway", "clear"], ["pulse", "soft"], ["settle", "soft"],
        ],
    },
    {
        "id": "edit_only_opening_endpoint",
        "source_moves": [
            ["hold", "clear"], ["rise", "soft"], ["sway", "clear"], ["settle", "soft"],
        ],
        "editable_slots": [0, 3],
        "request": (
            "Of the two editable endpoints, change the opening hold to soft. Keep the "
            "ending settle and both approved middle moves unchanged."
        ),
        "expected_moves": [
            ["hold", "soft"], ["rise", "soft"], ["sway", "clear"], ["settle", "soft"],
        ],
    },
    {
        "id": "select_settle_variation_by_reference",
        "source_moves": [
            ["rise", "clear"], ["sway", "soft"], ["settle", "soft"], ["hold", "clear"],
        ],
        "editable_slots": [2, 3],
        "request": (
            "The last move is already a clear hold. Set the move immediately before "
            "that hold, the settle, to clear too. Do not change the hold or either "
            "earlier source move."
        ),
        "expected_moves": [
            ["rise", "clear"], ["sway", "soft"], ["settle", "clear"], ["hold", "clear"],
        ],
    },
]


def model_payload(case, protocol="full"):
    """Return only public task data; never include expected_moves."""
    if protocol not in ("full", "patch"):
        raise ValueError("protocol must be 'full' or 'patch'")
    response_contract = FULL_PLAN_PROTOCOL if protocol == "full" else PATCH_PROTOCOL
    return {
        "source_moves": copy.deepcopy(case["source_moves"]),
        "editable_slots": list(case["editable_slots"]),
        "request": case["request"],
        "response_contract": response_contract,
    }

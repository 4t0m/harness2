"""Fresh natural-language cases for the compact repeated-motif contract.

The hidden expected intent is an offline exact semantic check. These fixtures
do not evaluate dance quality or motion execution.
"""

from collections.abc import Mapping


CASES = [
    {
        "id": "motif_direct_sway_with_cyclic_accents",
        "request": (
            "Use sway as the repeating motif. Set the four section accents, in order, "
            "to soft, clear, soft, clear."
        ),
        "expected": {"motif": "sway", "accents": ["soft", "clear", "soft", "clear"]},
    },
    {
        "id": "motif_direct_pulse_all_clear",
        "request": (
            "Build the repeated phrase around pulse, not sway. Give every section a "
            "clear accent."
        ),
        "expected": {"motif": "pulse", "accents": ["clear", "clear", "clear", "clear"]},
    },
    {
        "id": "motif_plain_language_sway",
        "request": (
            "Let the torso rock side to side for the repeating open-state motif. Use "
            "soft accents in the first and fourth sections, and clear accents in the "
            "second and third."
        ),
        "expected": {"motif": "sway", "accents": ["soft", "clear", "clear", "soft"]},
    },
    {
        "id": "motif_plain_language_pulse",
        "request": (
            "For the recurring motif, choose the compact upward pulse rather than the "
            "side-to-side rock. Accent sections one and three softly; accent two and "
            "four clearly."
        ),
        "expected": {"motif": "pulse", "accents": ["soft", "clear", "soft", "clear"]},
    },
    {
        "id": "motif_repeated_sway_modified_accent",
        "request": (
            "Repeat the swaying move in the open sections. Keep the first and last "
            "section soft; make the second section clear and the contrasting middle "
            "section soft."
        ),
        "expected": {"motif": "sway", "accents": ["soft", "clear", "soft", "soft"]},
    },
    {
        "id": "motif_contrast_pulse_between_sway_sections",
        "request": (
            "Use the side-to-side sway for the recurring sections, with a pulse in the "
            "contrasting section. The accents are clear, soft, clear, then soft across "
            "the four sections."
        ),
        "expected": {"motif": "sway", "accents": ["clear", "soft", "clear", "soft"]},
    },
    {
        "id": "motif_final_amendment_selects_pulse",
        "request": (
            "Draft: use sway as the recurring motif, with accents soft, clear, soft, "
            "clear. Final correction: switch the recurring motif to pulse; retain all "
            "four accent choices as drafted."
        ),
        "expected": {"motif": "pulse", "accents": ["soft", "clear", "soft", "clear"]},
    },
    {
        "id": "motif_final_amendment_revises_last_two_accents",
        "request": (
            "Use pulse for the repeated motif. Draft the section accents as clear, "
            "clear, soft, soft. Correction: keep pulse and the first two accents, but "
            "make the third clear and the fourth soft."
        ),
        "expected": {"motif": "pulse", "accents": ["clear", "clear", "clear", "soft"]},
    },
]


def score_intent(intent, case):
    """Return structural or exact-intent violations for a compact motif plan."""
    violations = []
    if not isinstance(intent, Mapping) or set(intent) != {"motif", "accents"}:
        return ["intent_fields"]
    motif = intent.get("motif")
    if motif not in ("sway", "pulse"):
        violations.append("motif_choice")
    accents = intent.get("accents")
    if (not isinstance(accents, (list, tuple)) or len(accents) != 4
            or any(accent not in ("soft", "clear") for accent in accents)):
        violations.append("accent_shape_or_choice")
    expected = case.get("expected")
    if not isinstance(expected, Mapping) or set(expected) != {"motif", "accents"}:
        return violations + ["case_expected_fields"]
    if motif in ("sway", "pulse") and motif != expected["motif"]:
        violations.append("motif_intent")
    if (isinstance(accents, (list, tuple)) and len(accents) == 4
            and list(accents) != expected["accents"]):
        violations.append("accent_intent")
    return violations

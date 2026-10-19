"""D0 symbolic dance compiler. Synthetic descriptors, never executable motion."""
import copy
import json
import math

# Boundary labels summarize synthetic stance/contact/heading/root-velocity states.
# Equality checks declared metadata only; no biomechanics or motion is verified.
ATLAS = {
    "settle": {"beats": 2, "entry": "center", "exit": "left", "bpm": [90, 130]},
    "sway": {"beats": 2, "entry": "left", "exit": "left", "bpm": [90, 130]},
    "accent": {"beats": 2, "entry": "left", "exit": "right", "bpm": [100, 125]},
    "resolve": {"beats": 2, "entry": "right", "exit": "center", "bpm": [90, 130]},
}
REVISION = "synthetic-dance-atlas-v1"


def model_brief():
    return json.dumps({"request": "Create an eight-beat phrase starting and ending at center.",
                       "atlas_revision": REVISION, "bpm": 120, "atlas": ATLAS,
                       "schema": {"atlas_revision": "string", "moves": ["move_id"]},
                       "rules": "Use only listed moves. Entry must match previous exit. No implicit blends."})


def compile_score(score, bpm=120):
    if type(bpm) not in (int, float) or not math.isfinite(bpm) or not 30 <= bpm <= 240:
        raise ValueError("invalid tempo")
    if not isinstance(score, dict) or set(score) != {"atlas_revision", "moves"}:
        raise ValueError("invalid score fields")
    if score["atlas_revision"] != REVISION:
        raise ValueError("stale atlas")
    moves = score["moves"]
    if not isinstance(moves, list) or not 1 <= len(moves) <= 8:
        raise ValueError("invalid move list")
    boundary, beat, cues = "center", 0, []
    for index, name in enumerate(moves):
        if not isinstance(name, str) or name not in ATLAS:
            raise ValueError(f"unknown move at {index}")
        move = ATLAS[name]
        if move["entry"] != boundary:
            raise ValueError(f"incompatible transition at {index}: {boundary} to {move['entry']}")
        if not move["bpm"][0] <= bpm <= move["bpm"][1]:
            raise ValueError(f"unsupported tempo at {index}")
        cues.append({"move_id": name, "start_beat": beat, "end_beat": beat + move["beats"],
                     "start_seconds": beat * 60 / bpm,
                     "end_seconds": (beat + move["beats"]) * 60 / bpm})
        beat += move["beats"]
        boundary = move["exit"]
    if beat != 8:
        raise ValueError("expected exactly eight beats")
    if boundary != "center":
        raise ValueError("unresolved final boundary")
    return {"kind": "symbolic_dance_score", "atlas_revision": REVISION,
            "bpm": bpm, "duration_seconds": beat * 60 / bpm, "cues": cues,
            "motion_generated": False, "physical_validity_verified": False,
            "taste_evaluated": False}


def offline_evidence():
    base = {"atlas_revision": REVISION, "moves": ["settle", "sway", "accent", "resolve"]}
    cases = [("compatible", base, 120),
             ("wrong_contact_order", {**base, "moves": ["settle", "resolve", "sway", "accent"]}, 120),
             ("unsupported_tempo", base, 140),
             ("unknown_move", {**base, "moves": ["spin"]}, 120),
             ("short_phrase", {**base, "moves": ["settle", "accent", "resolve"]}, 120),
             ("unresolved", {**base, "moves": ["settle", "sway", "sway", "sway"]}, 120)]
    rows = []
    for name, score, bpm in cases:
        try:
            result = {"accepted": True, "manifest": compile_score(copy.deepcopy(score), bpm)}
        except ValueError as exc:
            result = {"accepted": False, "reason": str(exc)}
        rows.append({"id": name, "score": score, "bpm": bpm, **result})
    return {"scope": "Synthetic symbolic contracts only; no model calls, motion assets or rendering.",
            "provider_calls": 0, "results": rows}


if __name__ == "__main__":
    print(json.dumps(offline_evidence(), indent=2))

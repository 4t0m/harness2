"""Trusted two-actor scene staging from bounded symbolic intent.

The model chooses identities, sides, and cue labels. Host code owns placement,
timing, and the six-second plan. No actor walks or gesture is executed here.
"""

from __future__ import annotations

import json
import math

FPS = 8
FRAME_COUNT = 48
DURATION_S = 6
SLOT_S = 2
SIDE_OFFSET_M = 0.85
MAX_INTENT_BYTES = 8192
GESTURES = frozenset({"wave", "nod", "neutral"})
VARIATIONS = frozenset({"soft", "clear"})


def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("nonfinite JSON number")


def _name(value, label):
    if (type(value) is not str or not 1 <= len(value) <= 80
            or value != value.strip() or any(ord(char) < 32 for char in value)):
        raise ValueError(f"{label} must be a bounded nonempty identifier")
    return value


def _scene(scene: dict) -> tuple[str, str, float, tuple[str, str]]:
    if not isinstance(scene, dict) or set(scene) != {"revision", "anchor", "actor_ids"}:
        raise ValueError("scene requires exactly revision, anchor, and actor_ids")
    revision = _name(scene["revision"], "revision")
    anchor = scene["anchor"]
    if not isinstance(anchor, dict) or set(anchor) != {"id", "x_m"}:
        raise ValueError("anchor requires exactly id and x_m")
    anchor_id = _name(anchor["id"], "anchor id")
    x = anchor["x_m"]
    try:
        finite = type(x) in (int, float) and math.isfinite(x)
    except OverflowError:
        finite = False
    if not finite or not -1 <= x <= 1:
        raise ValueError("anchor x_m must be finite within [-1, 1]")
    actor_ids = scene["actor_ids"]
    if not isinstance(actor_ids, list) or len(actor_ids) != 2:
        raise ValueError("scene requires exactly two actor ids")
    first, second = (_name(actor_id, "actor id") for actor_id in actor_ids)
    if first == second or anchor_id in (first, second):
        raise ValueError("scene ids must be distinct")
    return revision, anchor_id, float(x), (first, second)


def parse_intent(raw: str) -> dict:
    """Decode one exact JSON object; reject duplicates and nonfinite numbers."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_INTENT_BYTES:
        raise ValueError("intent must be bounded JSON text")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("intent must be one strict JSON object") from exc
    if not isinstance(value, dict) or set(value) != {"scene_revision", "placements", "cues"}:
        raise ValueError("intent requires exactly scene_revision, placements, and cues")
    _name(value["scene_revision"], "scene_revision")
    if not isinstance(value["placements"], list) or len(value["placements"]) != 2:
        raise ValueError("intent requires exactly two placements")
    if not isinstance(value["cues"], list) or len(value["cues"]) != 3:
        raise ValueError("intent requires exactly three cues")
    for placement in value["placements"]:
        if not isinstance(placement, dict) or set(placement) != {"actor_id", "anchor_id", "side"}:
            raise ValueError("placement fields must be actor_id, anchor_id, side")
        _name(placement["actor_id"], "actor_id")
        _name(placement["anchor_id"], "anchor_id")
        if placement["side"] not in ("left", "right"):
            raise ValueError("placement side must be left or right")
    for cue in value["cues"]:
        if not isinstance(cue, dict) or set(cue) != {"slot", "actor_id", "gesture", "variation"}:
            raise ValueError("cue fields must be slot, actor_id, gesture, variation")
        if type(cue["slot"]) is not int or cue["slot"] not in (0, 1, 2):
            raise ValueError("cue slot must be integer 0, 1, or 2")
        _name(cue["actor_id"], "cue actor_id")
        if type(cue["gesture"]) is not str or cue["gesture"] not in GESTURES:
            raise ValueError("unsupported gesture")
        if type(cue["variation"]) is not str or cue["variation"] not in VARIATIONS:
            raise ValueError("unsupported variation")
    return value


def compile_staging(raw: str, scene: dict) -> dict:
    """Resolve host geometry and fixed cue slots without mutating either input."""
    revision, anchor_id, anchor_x, actor_ids = _scene(scene)
    intent = parse_intent(raw)
    if intent["scene_revision"] != revision:
        raise ValueError("stale scene revision")
    placements = intent["placements"]
    if {item["actor_id"] for item in placements} != set(actor_ids) \
            or len({item["actor_id"] for item in placements}) != 2:
        raise ValueError("placements must assign each known actor once")
    if any(item["anchor_id"] != anchor_id for item in placements):
        raise ValueError("unknown anchor id")
    if {item["side"] for item in placements} != {"left", "right"}:
        raise ValueError("one actor must occupy each side")
    side_by_actor = {item["actor_id"]: item["side"] for item in placements}
    actors = [{"id": actor_id,
               "x_m": anchor_x + (-SIDE_OFFSET_M if side_by_actor[actor_id] == "left" else SIDE_OFFSET_M),
               "y_m": 0, "z_m": 0} for actor_id in actor_ids]
    xs = [actor["x_m"] for actor in actors]
    if any(not math.isfinite(x) or abs(x) > 3 for x in xs):
        raise ValueError("actor position exceeds 3 m bound")
    if abs(xs[0] - xs[1]) < 1.7 - 1e-9:
        raise ValueError("actor separation below 1.7 m")
    cues = intent["cues"]
    if {cue["slot"] for cue in cues} != {0, 1, 2}:
        raise ValueError("cues must cover slots 0, 1, 2 exactly once")
    if any(cue["actor_id"] not in actor_ids for cue in cues):
        raise ValueError("cue names unknown actor")
    compiled_cues = [{"slot": cue["slot"], "start_s": cue["slot"] * SLOT_S,
                      "end_s": (cue["slot"] + 1) * SLOT_S,
                      "actor_id": cue["actor_id"], "gesture": cue["gesture"],
                      "variation": cue["variation"]} for cue in sorted(cues, key=lambda item: item["slot"])]
    return {"scope": "Static two-actor staging and ordered gesture cues only; positions held throughout, no walking or execution claim.",
            "scene_revision": revision, "actors": actors, "cues": compiled_cues,
            "fps": FPS, "frame_count": FRAME_COUNT, "duration_s": DURATION_S}

"""Assemble four independent staging replies into one host-bound canonical plan."""

from __future__ import annotations

import json

from .actor_staging import GESTURES, VARIATIONS, _name, _reject_constant, _unique_pairs
from .actor_staging_compact import BoundScene, compile_compact

MAX_PIECE_BYTES = 1024
PLACEMENT_SCHEMA = {
    "type": "object", "required": ["left"], "additionalProperties": False,
    "properties": {"left": {"type": "string"}},
}
CUE_SCHEMA = {
    "type": "object", "required": ["actor", "gesture", "variation"],
    "additionalProperties": False,
    "properties": {
        "actor": {"type": "string"},
        "gesture": {"type": "string", "enum": ["wave", "nod", "neutral"]},
        "variation": {"type": "string", "enum": ["soft", "clear"]},
    },
}


def _piece(raw: str, fields: set[str]) -> dict:
    if type(raw) is not str:
        raise ValueError("staging piece must be JSON text")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("staging piece is not UTF-8 text") from exc
    if size > MAX_PIECE_BYTES:
        raise ValueError("staging piece exceeds byte bound")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("staging piece must be strict JSON") from exc
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("staging piece has missing or extra fields")
    return value


def assemble_staging(placement_raw: str, cue_raws: list[str], snapshot: BoundScene,
                     current_scene: dict) -> dict:
    """Host list order assigns the three slots; no piece supplies timing or geometry."""
    if not isinstance(snapshot, BoundScene):
        raise ValueError("bound scene snapshot required")
    if type(cue_raws) is not list or len(cue_raws) != 3:
        raise ValueError("exactly three ordered cue replies required")
    placement = _piece(placement_raw, {"left"})
    left = _name(placement["left"], "left actor id")
    if left not in snapshot.actor_ids:
        raise ValueError("unknown left actor id")
    cues = []
    for raw in cue_raws:
        cue = _piece(raw, {"actor", "gesture", "variation"})
        actor = _name(cue["actor"], "cue actor id")
        if actor not in snapshot.actor_ids:
            raise ValueError("unknown cue actor id")
        if type(cue["gesture"]) is not str or cue["gesture"] not in GESTURES:
            raise ValueError("unsupported gesture")
        if type(cue["variation"]) is not str or cue["variation"] not in VARIATIONS:
            raise ValueError("unsupported variation")
        cues.append([actor, cue["gesture"], cue["variation"]])
    return compile_compact(json.dumps({"left": left, "cues": cues}), snapshot, current_scene)

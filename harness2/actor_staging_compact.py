"""Compact symbolic staging intent bound to immutable host scene facts.

The compact model reply chooses the left actor and three ordered gesture cues.
Trusted code fills the right actor, anchor, revision, sides, and slot numbers,
then delegates geometry and timing to the canonical staging compiler.
"""

from __future__ import annotations

from dataclasses import dataclass
import json

from .actor_staging import (
    GESTURES, MAX_INTENT_BYTES, VARIATIONS, _name, _reject_constant, _scene,
    _unique_pairs, compile_staging,
)


@dataclass(frozen=True, slots=True)
class BoundScene:
    revision: str
    anchor_id: str
    anchor_x_m: float
    actor_ids: tuple[str, str]
    canonical_scene_json: str


def _scene_json(scene: dict) -> str:
    _scene(scene)
    return json.dumps(scene, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def bind_scene(scene: dict) -> BoundScene:
    """Capture all validated scene facts without retaining mutable inputs."""
    revision, anchor_id, anchor_x, actor_ids = _scene(scene)
    return BoundScene(revision, anchor_id, anchor_x, actor_ids, _scene_json(scene))


def _parse_compact(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_INTENT_BYTES:
        raise ValueError("compact intent must be bounded JSON text")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("compact intent must be one strict JSON object") from exc
    if not isinstance(value, dict) or set(value) != {"left", "cues"}:
        raise ValueError("compact intent requires exactly left and cues")
    _name(value["left"], "left actor id")
    cues = value["cues"]
    if not isinstance(cues, list) or len(cues) != 3:
        raise ValueError("compact intent requires exactly three cues")
    for cue in cues:
        if not isinstance(cue, list) or len(cue) != 3:
            raise ValueError("each cue must be an actor, gesture, variation array")
        _name(cue[0], "cue actor id")
        if type(cue[1]) is not str or cue[1] not in GESTURES:
            raise ValueError("unsupported gesture")
        if type(cue[2]) is not str or cue[2] not in VARIATIONS:
            raise ValueError("unsupported variation")
    return value


def compile_compact(raw: str, snapshot: BoundScene, current_scene: dict) -> dict:
    """Reject changed host facts, expand compact choices, return canonical plan."""
    if not isinstance(snapshot, BoundScene):
        raise ValueError("bound scene snapshot required")
    if _scene_json(current_scene) != snapshot.canonical_scene_json:
        raise ValueError("stale scene facts")
    intent = _parse_compact(raw)
    left = intent["left"]
    if left not in snapshot.actor_ids:
        raise ValueError("unknown left actor id")
    for cue in intent["cues"]:
        if cue[0] not in snapshot.actor_ids:
            raise ValueError("unknown cue actor id")
    right = next(actor_id for actor_id in snapshot.actor_ids if actor_id != left)
    expanded = {
        "scene_revision": snapshot.revision,
        "placements": [
            {"actor_id": left, "anchor_id": snapshot.anchor_id, "side": "left"},
            {"actor_id": right, "anchor_id": snapshot.anchor_id, "side": "right"},
        ],
        "cues": [{"slot": slot, "actor_id": actor_id, "gesture": gesture,
                  "variation": variation}
                 for slot, (actor_id, gesture, variation) in enumerate(intent["cues"])],
    }
    bound_scene = {"revision": snapshot.revision,
                   "anchor": {"id": snapshot.anchor_id, "x_m": snapshot.anchor_x_m},
                   "actor_ids": list(snapshot.actor_ids)}
    return compile_staging(json.dumps(expanded), bound_scene)

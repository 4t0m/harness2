"""Transactional one-phrase edits over the frozen planted dance shelf."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .dance_phrases import CATALOG, VARIATIONS, compile_plan, parse_plan, validate_compilation

PATCH_SCHEMA = {
    "type": "object", "required": ["slot", "move", "variation"],
    "additionalProperties": False,
    "properties": {
        "slot": {"type": "integer", "minimum": 0, "maximum": 3},
        "move": {"type": "string", "enum": [row[0] for row in CATALOG]},
        "variation": {"type": "string", "enum": list(VARIATIONS)},
    },
}
FULL_SCHEMA = {
    "type": "object", "required": ["moves"], "additionalProperties": False,
    "properties": {"moves": {"type": "array", "minItems": 4, "maxItems": 4,
                            "items": {"type": "array", "minItems": 2, "maxItems": 2,
                                      "items": {"type": "string"}}}},
}
MAX_PATCH_BYTES = 1024


@dataclass(frozen=True, slots=True)
class EditSnapshot:
    revision: str
    source_pairs: tuple[tuple[str, str], ...]
    source_plan_sha256: str
    source_sequence_sha256: str
    permitted_slots: tuple[int, ...]


def _pairs_from_raw(raw: str) -> tuple[tuple[str, str], ...]:
    return tuple((move["id"], move["variation"]) for move in parse_plan(raw))


def _raw_pairs(pairs) -> str:
    return json.dumps({"moves": [list(pair) for pair in pairs]}, separators=(",", ":"))


def _sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _revision(value: str) -> str:
    if (type(value) is not str or not 1 <= len(value) <= 80 or value != value.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError("bounded revision required")
    return value


def _scope(slots) -> tuple[int, ...]:
    if type(slots) not in (list, tuple) or not 1 <= len(slots) <= 4 \
            or any(type(slot) is not int or slot not in range(4) for slot in slots) \
            or len(set(slots)) != len(slots):
        raise ValueError("permitted slots must be unique integers 0..3")
    return tuple(sorted(slots))


def bind_source(source_raw: str, revision: str, permitted_slots: list[int] | tuple[int, ...]) -> EditSnapshot:
    """Freeze a valid source plan, its generated motion, revision and edit scope."""
    source_pairs = _pairs_from_raw(source_raw)
    source = compile_plan(_raw_pairs(source_pairs))
    return EditSnapshot(_revision(revision), source_pairs, _sha(source_pairs),
                        source["receipt"]["sequence_sha256"], _scope(permitted_slots))


def _check_current(snapshot: EditSnapshot, current_source_raw: str,
                   current_revision: str, current_permitted_slots) -> None:
    if type(snapshot) is not EditSnapshot:
        raise ValueError("bound edit snapshot required")
    if (_revision(current_revision) != snapshot.revision
            or _scope(current_permitted_slots) != snapshot.permitted_slots
            or _pairs_from_raw(current_source_raw) != snapshot.source_pairs):
        raise ValueError("stale source plan, revision, or permitted scope")


def _unique_pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _reject_constant(_value):
    raise ValueError("nonfinite JSON number")


def _parse_patch(raw: str) -> tuple[int, str, str]:
    if type(raw) is not str:
        raise ValueError("patch must be JSON text")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("patch must be UTF-8 text") from exc
    if size > MAX_PATCH_BYTES:
        raise ValueError("patch exceeds byte bound")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("patch must be strict JSON") from exc
    if type(value) is not dict or set(value) != {"slot", "move", "variation"}:
        raise ValueError("patch requires exactly slot, move, variation")
    slot, move, variation = value["slot"], value["move"], value["variation"]
    if type(slot) is not int or slot not in range(4):
        raise ValueError("patch slot must be integer 0..3")
    if type(move) is not str or move not in {row[0] for row in CATALOG}:
        raise ValueError("unknown patch move")
    if type(variation) is not str or variation not in VARIATIONS:
        raise ValueError("unknown patch variation")
    return slot, move, variation


def _make_result(proposed_pairs: tuple[tuple[str, str], ...], snapshot: EditSnapshot) -> dict:
    changed = [index for index, (old, new) in enumerate(zip(snapshot.source_pairs, proposed_pairs))
               if old != new]
    if len(proposed_pairs) != 4 or len(changed) != 1:
        raise ValueError("edit must change exactly one move pair")
    slot = changed[0]
    if slot not in snapshot.permitted_slots:
        raise ValueError("edit slot outside permitted scope")
    # The frozen compiler independently enforces all pose transitions.
    source = compile_plan(_raw_pairs(snapshot.source_pairs))
    if (snapshot.source_plan_sha256 != _sha(snapshot.source_pairs)
            or source["receipt"]["sequence_sha256"] != snapshot.source_sequence_sha256):
        raise ValueError("bound source no longer matches frozen shelf")
    compiled = compile_plan(_raw_pairs(proposed_pairs))
    validate_compilation(compiled)
    start, end = slot * 20, (slot + 1) * 20
    source_frames = source["sequence"]["frames"]
    result_frames = compiled["sequence"]["frames"]
    protected_indices = list(range(0, start + 1)) + list(range(end, 81))
    if any(source_frames[index] != result_frames[index] for index in protected_indices):
        raise ValueError("protected frame changed outside edited phrase or at seam")
    if any(source["clips"][index] != compiled["clips"][index]
           for index in range(4) if index != slot):
        raise ValueError("unselected source clip changed")
    if (source["clips"][slot]["frames"][0] != compiled["clips"][slot]["frames"][0]
            or source["clips"][slot]["frames"][-1] != compiled["clips"][slot]["frames"][-1]):
        raise ValueError("edited clip seam changed")
    if source["receipt"]["sequence_sha256"] != snapshot.source_sequence_sha256:
        raise ValueError("source motion mutated")
    receipt = {
        "accepted_revision": snapshot.revision,
        "permitted_slots": list(snapshot.permitted_slots),
        "edited_slot": slot,
        "source_plan_sha256": snapshot.source_plan_sha256,
        "result_plan_sha256": _sha(proposed_pairs),
        "source_sequence_sha256": snapshot.source_sequence_sha256,
        "result_sequence_sha256": compiled["receipt"]["sequence_sha256"],
        "protected_frame_count": len(protected_indices),
        "protected_frames_sha256": _sha([result_frames[index] for index in protected_indices]),
        "outside_frames_exact": True,
        "other_clips_exact": True,
        "seam_endpoints_exact": True,
        "source_unmutated": True,
        "validation": compiled["receipt"]["validation"],
    }
    return {"compiled": compiled, "receipt": receipt}


def apply_patch(raw_patch: str, snapshot: EditSnapshot, current_source_raw: str,
                current_revision: str, current_permitted_slots) -> dict:
    """Apply one strict patch after checking current host state against the binding."""
    _check_current(snapshot, current_source_raw, current_revision, current_permitted_slots)
    slot, move, variation = _parse_patch(raw_patch)
    proposed = list(snapshot.source_pairs)
    proposed[slot] = (move, variation)
    return _make_result(tuple(proposed), snapshot)


def validate_full_replacement(raw_full: str, snapshot: EditSnapshot,
                              current_source_raw: str, current_revision: str,
                              current_permitted_slots) -> dict:
    """Matched full-rewrite condition: exactly one in-scope pair may change."""
    _check_current(snapshot, current_source_raw, current_revision, current_permitted_slots)
    return _make_result(_pairs_from_raw(raw_full), snapshot)


def validate_edit(result: dict, snapshot: EditSnapshot, current_source_raw: str,
                  current_revision: str, current_permitted_slots) -> dict:
    """Recompute and compare the whole transaction, including protected motion."""
    _check_current(snapshot, current_source_raw, current_revision, current_permitted_slots)
    if type(result) is not dict or set(result) != {"compiled", "receipt"}:
        raise ValueError("incomplete edit result")
    compiled = result["compiled"]
    if type(compiled) is not dict or type(compiled.get("moves")) is not list:
        raise ValueError("incomplete compiled edit")
    try:
        proposed = tuple((move["id"], move["variation"]) for move in compiled["moves"])
        expected = _make_result(proposed, snapshot)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("invalid compiled edit") from exc
    if result != expected:
        raise ValueError("edit result or preservation receipt was altered")
    return expected["receipt"]

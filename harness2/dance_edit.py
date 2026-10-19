"""Host-owned, arm-only edit of the eight-beat procedural motion prototype."""

from __future__ import annotations

import copy
import hashlib
import json
import math

from . import dance_motion

START_BEAT = 2
END_BEAT = 6
PEAK_ANGLE_RAD = {"soft": 0.20, "clear": 0.45}
ARM_JOINTS = frozenset({"left_elbow", "left_wrist", "right_elbow", "right_wrist"})
AXIS = "world +Y (forward); shoulder-centered rigid rotation in the world X-Z plane"
TIMING = {"bpm": dance_motion.BPM, "fps": dance_motion.FPS,
          "beats": dance_motion.BEATS, "duration_seconds": dance_motion.DURATION}


def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_intent(raw_intent: str) -> str:
    """Accept only the exact one-operation, one-strength JSON contract."""
    if not isinstance(raw_intent, str) or len(raw_intent.encode("utf-8")) > 1024:
        raise ValueError("intent must be bounded JSON text")
    def reject_constant(_value):
        raise ValueError("nonfinite JSON value")
    try:
        value = json.loads(raw_intent, object_pairs_hook=_unique_pairs,
                           parse_constant=reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("intent must be one strict JSON object") from exc
    if not isinstance(value, dict) or set(value) != {"operation", "strength"}:
        raise ValueError("intent requires exactly operation and strength")
    if value["operation"] != "accent_arms":
        raise ValueError("unsupported operation")
    if type(value["strength"]) is not str or value["strength"] not in PEAK_ANGLE_RAD:
        raise ValueError("unsupported strength")
    return value["strength"]


def _digest(sequence: dict) -> str:
    data = json.dumps(sequence, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _require_prototype_timing(sequence: dict) -> None:
    if not isinstance(sequence, dict) or any(
        type(sequence.get(field)) is not type(expected) or sequence[field] != expected
        for field, expected in TIMING.items()
    ):
        raise ValueError("motion timing must match the authoritative eight-beat prototype")


def _around_world_y(point: list[float], shoulder: list[float], angle: float) -> list[float]:
    """Right-handed world-Y rotation; y remains constant for each arm point."""
    dx, dz = point[0] - shoulder[0], point[2] - shoulder[2]
    cosine, sine = math.cos(angle), math.sin(angle)
    return [shoulder[0] + cosine * dx + sine * dz,
            point[1],
            shoulder[2] - sine * dx + cosine * dz]


def preservation_checks(source: dict, result: dict, *, start_beat: int = START_BEAT,
                        end_beat: int = END_BEAT) -> dict[str, bool]:
    """Independently compare every protected frame and non-arm field exactly."""
    source_frames, result_frames = source["frames"], result["frames"]
    matching_count = len(source_frames) == len(result_frames)
    protected = matching_count
    non_arm = matching_count
    contacts = matching_count
    timestamps = matching_count
    for before, after in zip(source_frames, result_frames):
        beat = before["time"] * dance_motion.BPM / 60
        if beat <= start_beat or beat >= end_beat:
            protected = protected and before == after
        contacts = contacts and before["contacts"] == after["contacts"]
        timestamps = timestamps and before["time"] == after["time"]
        non_arm = non_arm and before["joints"].keys() == after["joints"].keys()
        non_arm = non_arm and all(before["joints"][name] == after["joints"][name]
                                  for name in before["joints"] if name not in ARM_JOINTS)
    return {"protected_frames_preserved": protected,
            "non_arm_joints_preserved": non_arm,
            "contacts_preserved": contacts,
            "timestamps_preserved": timestamps,
            "metadata_preserved": {k: v for k, v in source.items() if k != "frames"}
                                  == {k: v for k, v in result.items() if k != "frames"}}


def edit_arms(sequence: dict, raw_intent: str, start_beat: int = START_BEAT,
              end_beat: int = END_BEAT) -> dict:
    """Return {sequence, receipt}; never mutate input or execute/render motion.

    The host fixes the middle four beats. Both elbow and wrist rotate rigidly
    around their shoulder; opposite signed angles add a symmetric arm accent.
    """
    if type(start_beat) is not int or type(end_beat) is not int or (start_beat, end_beat) != (START_BEAT, END_BEAT):
        raise ValueError("edit window is fixed to beats 2 through 6")
    strength = parse_intent(raw_intent)
    _require_prototype_timing(sequence)
    dance_motion.validate(sequence)
    source_hash = _digest(sequence)
    result = copy.deepcopy(sequence)
    peak = PEAK_ANGLE_RAD[strength]
    for frame in result["frames"]:
        beat = frame["time"] * dance_motion.BPM / 60
        if beat <= start_beat or beat >= end_beat:
            continue
        phase = (beat - start_beat) / (end_beat - start_beat)
        angle = peak * math.sin(math.pi * phase) ** 2
        joints = frame["joints"]
        for side, sign in (("left", -1), ("right", 1)):
            shoulder = joints[f"{side}_shoulder"]
            for name in (f"{side}_elbow", f"{side}_wrist"):
                joints[name] = _around_world_y(joints[name], shoulder, sign * angle)
    validation = dance_motion.validate(result)
    preservation = preservation_checks(sequence, result)
    if not all(preservation.values()):
        raise ValueError("arm edit changed protected motion data")
    if _digest(sequence) != source_hash:
        raise ValueError("source sequence changed during edit")
    changed_frames = [index for index, (before, after) in enumerate(zip(sequence["frames"], result["frames"]))
                      if before != after]
    return {"sequence": result,
            "receipt": {"operation": "accent_arms", "strength": strength,
                        "edit_window_beats": [start_beat, end_beat],
                        "peak_angle_radians": peak, "axis": AXIS,
                        "changed_frames": changed_frames,
                        "source_sha256": source_hash, "result_sha256": _digest(result),
                        "source_unchanged": True, **preservation,
                        "validation": validation,
                        "scope": "Technical skeletal edit only; no style or visual-quality claim."}}

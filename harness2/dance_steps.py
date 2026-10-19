"""Planted-contact side-step prototype on the existing 18-joint technical rig.

This is procedural motion, not a claim of balance, collision safety, dance style,
biomechanical realism, or avatar execution.
"""

from __future__ import annotations

import hashlib
import json
import math

from . import dance_motion

BPM = 120
FPS = 20
STEP_FRAMES = 20
STEP_SECONDS = 1.0
STEP_BEATS = 2
STEP_M = 0.20
MAX_PLAN_BYTES = 2048
MOVES = ("step_left", "step_right")
VARIATIONS = ("soft", "clear")
PUBLIC_CONTRACT = (
    'Return strict JSON only: {"moves":[["step_left|step_right","soft|clear"],'
    '["step_left|step_right","soft|clear"],["step_left|step_right","soft|clear"],'
    '["step_left|step_right","soft|clear"]]}. Four chronological two-beat side steps '
    "at 120 BPM. Each step moves the planted stance 0.20 m left or right. "
    "Variation affects arm/body accent, not travel distance. No other fields."
)
PLAN_SCHEMA = {
    "type": "object", "required": ["moves"], "additionalProperties": False,
    "properties": {"moves": {"type": "array", "minItems": 4, "maxItems": 4,
                            "items": {"type": "array", "minItems": 2, "maxItems": 2,
                                      "items": {"type": "string"}}}},
}
_SEGMENTS = dance_motion._SEGMENTS
_SEGMENT_LENGTHS = {f"{a}:{b}": length for a, b, length, _ in _SEGMENTS}
_JOINTS = frozenset({name for a, b, *_ in _SEGMENTS for name in (a, b)})


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("nonfinite JSON number")


def _sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def parse_steps(raw: str) -> list[tuple[str, str]]:
    """Read one exact bounded plan; model chooses only direction and accent."""
    if type(raw) is not str:
        raise ValueError("step plan must be JSON text")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("step plan must be UTF-8 text") from exc
    if size > MAX_PLAN_BYTES:
        raise ValueError("step plan exceeds byte bound")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("step plan must be strict JSON") from exc
    if type(value) is not dict or set(value) != {"moves"}:
        raise ValueError("step plan requires exactly moves")
    choices = value["moves"]
    if type(choices) is not list or len(choices) != 4:
        raise ValueError("step plan requires exactly four moves")
    parsed = []
    for pair in choices:
        if type(pair) is not list or len(pair) != 2:
            raise ValueError("each step must be [move, variation]")
        move, variation = pair
        if type(move) is not str or move not in MOVES:
            raise ValueError("unknown step move")
        if type(variation) is not str or variation not in VARIATIONS:
            raise ValueError("unknown step variation")
        parsed.append((move, variation))
    return parsed


def _smooth(u: float) -> float:
    return u * u * (3.0 - 2.0 * u)


def _pose(left_ankle: list[float], right_ankle: list[float],
          body_bob: float, arm_swing: float) -> dict:
    root_x = (left_ankle[0] + right_ankle[0]) / 2
    pelvis = [root_x, 0.0, 0.92 + body_bob]
    joints = {
        "pelvis": pelvis,
        "left_hip": [root_x - 0.13, 0.0, pelvis[2] - 0.04],
        "right_hip": [root_x + 0.13, 0.0, pelvis[2] - 0.04],
        "spine": [root_x, 0.0, pelvis[2] + 0.36],
        "neck": [root_x, 0.0, pelvis[2] + 0.61],
        "head": [root_x, 0.0, pelvis[2] + 0.78],
    }
    for side, sign, ankle in (("left", -1, left_ankle), ("right", 1, right_ankle)):
        joints[f"{side}_ankle"] = ankle[:]
        joints[f"{side}_foot"] = [ankle[0], ankle[1] + 0.10, ankle[2] - 0.025]
        joints[f"{side}_knee"] = dance_motion._knee(joints[f"{side}_hip"], ankle)
        shoulder = [root_x + sign * 0.22, 0.0, pelvis[2] + 0.51]
        # Counter-swing is mirrored when the step direction reverses.
        upper = 0.62 + sign * arm_swing
        lower = 0.52 + sign * arm_swing * 0.7
        elbow = [shoulder[0] + sign * 0.30 * math.sin(upper), 0.0,
                 shoulder[2] - 0.30 * math.cos(upper)]
        wrist = [elbow[0] + sign * 0.28 * math.sin(lower), 0.0,
                 elbow[2] - 0.28 * math.cos(lower)]
        joints[f"{side}_shoulder"] = shoulder
        joints[f"{side}_elbow"] = elbow
        joints[f"{side}_wrist"] = wrist
    return joints


def _frame(move: str, variation: str, start_root: float, local_index: int) -> dict:
    direction = -1 if move == "step_left" else 1
    delta = direction * STEP_M
    if local_index in (0, STEP_FRAMES):
        # Canonical endpoint construction avoids floating-point associativity
        # drift between one clip's endpoint and the next clip's start.
        root = start_root if local_index == 0 else start_root + delta
        return {"time": local_index / FPS, "joints": _neutral(root),
                "contacts": {"left": True, "right": True}}
    lead = "left" if direction < 0 else "right"
    trail = "right" if direction < 0 else "left"
    base = {"left": start_root - 0.18, "right": start_root + 0.18}
    ankles = {side: [base[side], 0.0, 0.08] for side in ("left", "right")}
    contacts = {"left": True, "right": True}
    if local_index <= 10:
        phase = local_index / 10
        ankles[lead][0] = base[lead] + delta * _smooth(phase)
        if 0 < local_index < 10:
            ankles[lead][1] = 0.025 * math.sin(math.pi * phase)
            ankles[lead][2] = 0.08 + 0.07 * math.sin(math.pi * phase)
            contacts[lead] = False
    else:
        phase = (local_index - 10) / 10
        ankles[lead][0] = base[lead] + delta
        ankles[trail][0] = base[trail] + delta * _smooth(phase)
        if local_index < 20:
            ankles[trail][1] = 0.025 * math.sin(math.pi * phase)
            ankles[trail][2] = 0.08 + 0.07 * math.sin(math.pi * phase)
            contacts[trail] = False
    envelope = math.sin(math.pi * local_index / 20) ** 2
    strength = 0.55 if variation == "soft" else 1.0
    bob = 0.018 * strength * envelope
    swing = direction * 0.20 * strength * envelope * math.sin(math.pi * local_index / 20)
    return {"time": local_index / FPS,
            "joints": _pose(ankles["left"], ankles["right"], bob, swing),
            "contacts": contacts}


def _clip(move: str, variation: str, start_root: float) -> list[dict]:
    return [_frame(move, variation, start_root, index)
            for index in range(STEP_FRAMES + 1)]


def _neutral(root: float) -> dict:
    return _pose([root - 0.18, 0.0, 0.08], [root + 0.18, 0.0, 0.08], 0.0, 0.0)


def validate_steps(sequence: dict) -> dict:
    """Check actual frames, contacts, fixed geometry, step timing and provenance."""
    if type(sequence) is not dict:
        raise ValueError("sequence required")
    if (type(sequence.get("bpm")) is not int or sequence["bpm"] != BPM
            or type(sequence.get("fps")) is not int or sequence["fps"] != FPS
            or type(sequence.get("beats")) is not int or sequence["beats"] != 8
            or type(sequence.get("duration_seconds")) is not float
            or sequence["duration_seconds"] != 4.0):
        raise ValueError("invalid timeline metadata")
    if sequence.get("bone_edges") != dance_motion.BONE_EDGES \
            or sequence.get("segment_lengths_m") != _SEGMENT_LENGTHS:
        raise ValueError("invalid rig metadata")
    records = sequence.get("move_plan")
    if type(records) is not list or len(records) != 4:
        raise ValueError("four host move records required")
    frames = sequence.get("frames")
    if type(frames) is not list or len(frames) != 81:
        raise ValueError("wrong frame count")
    max_delta = max_length_error = max_root = max_lift = 0.0
    previous = None
    for index, frame in enumerate(frames):
        if type(frame) is not dict or set(frame) != {"time", "joints", "contacts"}:
            raise ValueError("invalid frame fields")
        if (type(frame["time"]) not in (int, float) or not math.isfinite(frame["time"])
                or abs(frame["time"] - index / FPS) > 1e-9):
            raise ValueError("wrong frame time")
        joints, contacts = frame["joints"], frame["contacts"]
        if type(joints) is not dict or set(joints) != _JOINTS:
            raise ValueError("invalid joint set")
        if (type(contacts) is not dict or set(contacts) != {"left", "right"}
                or any(type(flag) is not bool for flag in contacts.values())
                or not any(contacts.values())):
            raise ValueError("invalid support contacts")
        for name, point in joints.items():
            if (type(point) is not list or len(point) != 3
                    or any(type(value) not in (int, float) or not math.isfinite(value)
                           or abs(value) > 3 for value in point)):
                raise ValueError(f"invalid bounded joint: {name}")
            if previous is not None:
                delta = math.dist(point, previous["joints"][name])
                max_delta = max(max_delta, delta)
                if delta > 0.20:
                    raise ValueError("pose discontinuity")
        for side in ("left", "right"):
            ankle, foot = joints[f"{side}_ankle"], joints[f"{side}_foot"]
            if foot != [ankle[0], ankle[1] + 0.10, ankle[2] - 0.025]:
                raise ValueError("deformed foot marker")
            if ankle[2] < 0.08 - 1e-9:
                raise ValueError("ankle below planted height")
            if contacts[side] and ankle != [ankle[0], 0.0, 0.08]:
                raise ValueError("contact foot is not grounded")
            if previous is not None and contacts[side] and previous["contacts"][side] \
                    and math.dist(ankle, previous["joints"][f"{side}_ankle"]) > 1e-5:
                raise ValueError("planted foot sliding")
            max_lift = max(max_lift, ankle[2] - 0.08)
        root_x = (joints["left_ankle"][0] + joints["right_ankle"][0]) / 2
        if abs(joints["pelvis"][0] - root_x) > 1e-9:
            raise ValueError("root does not follow stance")
        max_root = max(max_root, abs(root_x))
        if max_root > 0.8 + 1e-9:
            raise ValueError("root exceeds 0.8 m bound")
        for start, end, target, _group in _SEGMENTS:
            error = abs(math.dist(joints[start], joints[end]) - target)
            max_length_error = max(max_length_error, error)
            if error > 1e-6:
                raise ValueError(f"segment deformation: {start} to {end}")
        previous = frame
    root = 0.0
    clip_reports = []
    for move_index, record in enumerate(records):
        if type(record) is not dict or set(record) != {"id", "variation", "start_root_x_m", "end_root_x_m"}:
            raise ValueError("invalid host move record")
        move, variation = record["id"], record["variation"]
        if type(move) is not str or move not in MOVES or type(variation) is not str or variation not in VARIATIONS:
            raise ValueError("unknown host move record")
        end_root = root + (-STEP_M if move == "step_left" else STEP_M)
        if (type(record["start_root_x_m"]) is not float or record["start_root_x_m"] != root
                or type(record["end_root_x_m"]) is not float or record["end_root_x_m"] != end_root):
            raise ValueError("host root displacement mismatch")
        segment = frames[move_index * STEP_FRAMES:move_index * STEP_FRAMES + STEP_FRAMES + 1]
        if segment[0]["joints"] != _neutral(root) or segment[-1]["joints"] != _neutral(end_root):
            raise ValueError("step seam geometry mismatch")
        if segment[0]["contacts"] != {"left": True, "right": True} \
                or segment[10]["contacts"] != {"left": True, "right": True} \
                or segment[-1]["contacts"] != {"left": True, "right": True}:
            raise ValueError("step phase contact boundary mismatch")
        lead = "left" if move == "step_left" else "right"
        trail = "right" if lead == "left" else "left"
        for local in range(1, 20):
            moving = lead if local < 10 else trail if local > 10 else None
            expected = ({"left": True, "right": True} if moving is None
                        else {"left": moving != "left", "right": moving != "right"})
            if segment[local]["contacts"] != expected:
                raise ValueError("contact phase mismatch")
        if segment[5]["joints"][f"{lead}_ankle"][2] <= 0.13 \
                or segment[15]["joints"][f"{trail}_ankle"][2] <= 0.13:
            raise ValueError("moving foot did not lift")
        expected_frames = _clip(move, variation, root)
        for local, expected in enumerate(expected_frames):
            if segment[local]["joints"] != expected["joints"] \
                    or segment[local]["contacts"] != expected["contacts"]:
                raise ValueError("frames differ from frozen step source clip")
        clip_reports.append({"id": move, "variation": variation,
                             "start_root_x_m": root, "end_root_x_m": end_root,
                             "source_clip_sha256": _sha(expected_frames)})
        root = end_root
    full = dance_motion.validate(sequence)
    return {"valid": True, "frame_count": 81, "duration_seconds": 4.0,
            "final_root_x_m": root, "max_abs_root_x_m": max_root,
            "max_joint_delta_m": max_delta, "max_segment_error_m": max_length_error,
            "max_moving_ankle_lift_m": max_lift, "clips": clip_reports,
            "full_rig_validation": full,
            "scope": "Technical planted-step and contact checks; no balance, collision, style or avatar-execution claim."}


def compile_steps(raw: str) -> dict:
    """Compile four model choices into 81 verified full-body motion samples."""
    choices = parse_steps(raw)
    frames = []
    records = []
    root = 0.0
    for move_index, (move, variation) in enumerate(choices):
        end_root = root + (-STEP_M if move == "step_left" else STEP_M)
        records.append({"id": move, "variation": variation,
                        "start_root_x_m": root, "end_root_x_m": end_root})
        for local, frame in enumerate(_clip(move, variation, root)):
            if move_index and local == 0:
                continue
            frames.append({"time": (move_index * STEP_FRAMES + local) / FPS,
                           "joints": frame["joints"], "contacts": frame["contacts"]})
        root = end_root
    sequence = {
        "kind": "procedural_planted_side_steps", "variant": "mixed",
        "bpm": BPM, "fps": FPS, "beats": 8, "duration_seconds": 4.0,
        "coordinate_system": "world x=lateral, y=forward, z=up; ground z=0",
        "bone_edges": [edge[:] for edge in dance_motion.BONE_EDGES],
        "proportions_m": dict(dance_motion._LENGTHS),
        "segment_lengths_m": dict(_SEGMENT_LENGTHS),
        "scope": "Four technical planted side steps; no balance, collision, biomechanics, style authenticity or avatar-execution claim.",
        "move_plan": records, "frames": frames,
    }
    report = validate_steps(sequence)
    return {"sequence": sequence,
            "receipt": {"plan_sha256": _sha(choices), "sequence_sha256": _sha(sequence),
                        "validation": report}}


def verify_compilation(result: dict) -> dict:
    """Recheck physical motion and exact receipt provenance after serialization."""
    if type(result) is not dict or set(result) != {"sequence", "receipt"}:
        raise ValueError("incomplete step compilation")
    report = validate_steps(result["sequence"])
    choices = [(row["id"], row["variation"])
               for row in result["sequence"]["move_plan"]]
    expected = {"plan_sha256": _sha(choices),
                "sequence_sha256": _sha(result["sequence"]),
                "validation": report}
    if result["receipt"] != expected:
        raise ValueError("step receipt does not match compiled motion")
    return report

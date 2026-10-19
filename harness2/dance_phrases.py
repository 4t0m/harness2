"""Compact four-move dance plans compiled from a deterministic planted-motion shelf.

This is a technical stick-figure prototype. It does not claim dance style,
biomechanical realism, execution by an avatar, or artistic quality.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math

from . import dance_motion

BPM = 120
FPS = 20
MOVE_BEATS = 2
MOVE_FRAMES = 20
MOVE_SECONDS = 1.0
PLAN_MOVES = 4
MAX_PLAN_BYTES = 2048
CATALOG = (
    ("rise", "rest", "open"),
    ("sway", "open", "open"),
    ("pulse", "open", "open"),
    ("settle", "open", "rest"),
    ("hold", "rest", "rest"),
)
VARIATIONS = ("soft", "clear")
PUBLIC_CONTRACT = (
    'Return strict JSON only: {"moves":[["move_id","variation"],'
    '["move_id","variation"],["move_id","variation"],["move_id","variation"]]}. '
    "Moves are rise(rest to open), sway(open to open), pulse(open to open), "
    "settle(open to rest), hold(rest to rest). Variations are soft or clear. "
    "Four chronological two-beat moves start and end at rest. No other fields."
)
PLAN_SCHEMA = {
    "type": "object", "required": ["moves"], "additionalProperties": False,
    "properties": {"moves": {"type": "array", "minItems": 4, "maxItems": 4,
                            "items": {"type": "array", "minItems": 2, "maxItems": 2,
                                      "items": {"type": "string"}}}},
}
_TRANSITIONS = {move_id: (start, end) for move_id, start, end in CATALOG}
_SEGMENT_LENGTHS = {f"{a}:{b}": length for a, b, length, _ in dance_motion._SEGMENTS}
_JOINTS = frozenset({name for a, b, *_ in dance_motion._SEGMENTS for name in (a, b)})
_ANKLES = {"left": [-0.18, 0.0, 0.08], "right": [0.18, 0.0, 0.08]}


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _reject_constant(_value):
    raise ValueError("nonfinite JSON number")


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def parse_plan(raw: str) -> list[dict]:
    """Validate only model-selectable move IDs and variations, without repair."""
    if type(raw) is not str:
        raise ValueError("plan must be JSON text")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("plan must be UTF-8 text") from exc
    if size > MAX_PLAN_BYTES:
        raise ValueError("plan exceeds byte bound")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("plan must be strict JSON") from exc
    if not isinstance(value, dict) or set(value) != {"moves"}:
        raise ValueError("plan requires exactly moves")
    choices = value["moves"]
    if type(choices) is not list or len(choices) != PLAN_MOVES:
        raise ValueError("plan requires exactly four moves")
    state = "rest"
    moves = []
    for choice in choices:
        if type(choice) is not list or len(choice) != 2:
            raise ValueError("each move must be [id, variation]")
        move_id, variation = choice
        if type(move_id) is not str or move_id not in _TRANSITIONS:
            raise ValueError("unknown move id")
        if type(variation) is not str or variation not in VARIATIONS:
            raise ValueError("unknown variation")
        start, end = _TRANSITIONS[move_id]
        if start != state:
            raise ValueError("move order violates pose transition")
        moves.append({"id": move_id, "variation": variation,
                      "start_state": start, "end_state": end})
        state = end
    if state != "rest":
        raise ValueError("final pose must be rest")
    return moves


def _smooth(u: float) -> float:
    return u * u * (3.0 - 2.0 * u)


def _pose(state: str, *, body_x: float = 0.0, body_z: float = 0.0,
          left_angle: float = 0.0, right_angle: float = 0.0) -> dict:
    """Rigid torso/limb construction; both feet remain fixed in world space."""
    pelvis = [body_x, 0.0, 0.92 + body_z]
    joints = {
        "pelvis": pelvis,
        "left_hip": [body_x - 0.13, 0.0, pelvis[2] - 0.04],
        "right_hip": [body_x + 0.13, 0.0, pelvis[2] - 0.04],
        "spine": [body_x, 0.0, pelvis[2] + 0.36],
        "neck": [body_x, 0.0, pelvis[2] + 0.61],
        "head": [body_x, 0.0, pelvis[2] + 0.78],
    }
    for side, sign, angle_delta in (("left", -1, left_angle), ("right", 1, right_angle)):
        ankle = _ANKLES[side][:]
        joints[f"{side}_ankle"] = ankle
        joints[f"{side}_foot"] = [ankle[0], ankle[1] + 0.10, ankle[2] - 0.025]
        joints[f"{side}_knee"] = dance_motion._knee(joints[f"{side}_hip"], ankle)
        shoulder = [body_x + sign * 0.22, 0.0, pelvis[2] + 0.51]
        upper = (0.62 if state == "rest" else 1.25) + angle_delta
        lower = (0.52 if state == "rest" else 1.10) + angle_delta * 0.7
        elbow = [shoulder[0] + sign * 0.30 * math.sin(upper), 0.0,
                 shoulder[2] - 0.30 * math.cos(upper)]
        wrist = [elbow[0] + sign * 0.28 * math.sin(lower), 0.0,
                 elbow[2] - 0.28 * math.cos(lower)]
        joints[f"{side}_shoulder"] = shoulder
        joints[f"{side}_elbow"] = elbow
        joints[f"{side}_wrist"] = wrist
    return joints


def _sample(move_id: str, variation: str, index: int) -> dict:
    start, end = _TRANSITIONS[move_id]
    u = index / MOVE_FRAMES
    # Exact shared poses at clip boundaries, independent of variation.
    if index in (0, MOVE_FRAMES):
        return {"time": index / FPS, "joints": _pose(start if index == 0 else end),
                "contacts": {"left": True, "right": True}}
    strength = 0.55 if variation == "soft" else 1.0
    envelope = math.sin(math.pi * u) ** 2
    state_angle = _smooth(u) if start != end else 0.0
    base_upper = 0.62 + (1.25 - 0.62) * state_angle if start == "rest" else (
        1.25 - (1.25 - 0.62) * state_angle)
    base_lower = 0.52 + (1.10 - 0.52) * state_angle if start == "rest" else (
        1.10 - (1.10 - 0.52) * state_angle)
    # _pose takes one named endpoint state; offsets implement the smooth
    # interpolation plus a move-specific transient. All offsets vanish at seams.
    reference_upper = 0.62 if start == "rest" else 1.25
    reference_lower = 0.52 if start == "rest" else 1.10
    interpolation = base_upper - reference_upper
    # Lower angle follows the same state path; its transient is scaled by _pose.
    # The small difference from the target lower path is explicitly compensated.
    lower_compensation = (base_lower - reference_lower) - 0.7 * interpolation
    if move_id in ("rise", "settle"):
        body_x = 0.0
        body_z = 0.018 * strength * envelope
        left = interpolation + 0.08 * strength * envelope
        right = interpolation - 0.05 * strength * envelope
    elif move_id == "sway":
        wave = envelope * math.sin(2 * math.pi * u)
        body_x = 0.045 * strength * wave
        body_z = 0.0
        left = 0.11 * strength * wave
        right = -0.11 * strength * wave
    elif move_id == "pulse":
        body_x = 0.0
        body_z = 0.030 * strength * envelope
        left = 0.10 * strength * envelope
        right = 0.10 * strength * envelope
    else:  # hold: a small planted breath, still returning exactly to rest.
        body_x = 0.0
        body_z = 0.008 * strength * envelope
        left = 0.025 * strength * envelope
        right = 0.025 * strength * envelope
    # Keep arm lower links rigid; the interpolation's lower-angle residual is
    # handled through a separate pose constructor argument below.
    joints = _pose(start, body_x=body_x, body_z=body_z,
                   left_angle=left, right_angle=right)
    if start != end and lower_compensation:
        for side, sign, angle in (("left", -1, left), ("right", 1, right)):
            elbow = joints[f"{side}_elbow"]
            lower_angle = reference_lower + 0.7 * angle + lower_compensation
            joints[f"{side}_wrist"] = [elbow[0] + sign * 0.28 * math.sin(lower_angle),
                                         0.0, elbow[2] - 0.28 * math.cos(lower_angle)]
    return {"time": index / FPS, "joints": joints,
            "contacts": {"left": True, "right": True}}


def _clip(move: dict) -> dict:
    frames = [_sample(move["id"], move["variation"], i) for i in range(MOVE_FRAMES + 1)]
    return {**move, "beats": MOVE_BEATS, "fps": FPS, "duration_seconds": MOVE_SECONDS,
            "frames": frames}


def _verify_frames(frames: list, *, count: int, offset: float) -> dict:
    if type(frames) is not list or len(frames) != count:
        raise ValueError("wrong frame count")
    max_delta = max_segment_error = 0.0
    previous = None
    for i, frame in enumerate(frames):
        if type(frame) is not dict or set(frame) != {"time", "joints", "contacts"}:
            raise ValueError("invalid frame fields")
        if (type(frame["time"]) not in (int, float) or not math.isfinite(frame["time"])
                or abs(frame["time"] - (offset + i / FPS)) > 1e-9):
            raise ValueError("invalid frame time")
        joints = frame["joints"]
        if type(joints) is not dict or set(joints) != _JOINTS:
            raise ValueError("invalid joint set")
        contacts = frame["contacts"]
        if (type(contacts) is not dict or set(contacts) != {"left", "right"}
                or any(type(value) is not bool or not value for value in contacts.values())):
            raise ValueError("feet must remain planted")
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
            if joints[f"{side}_ankle"] != _ANKLES[side]:
                raise ValueError("planted foot displacement")
            expected_foot = [_ANKLES[side][0], 0.10, 0.055]
            if joints[f"{side}_foot"] != expected_foot:
                raise ValueError("planted foot marker displacement")
        for start, end, target, _group in dance_motion._SEGMENTS:
            error = abs(math.dist(joints[start], joints[end]) - target)
            max_segment_error = max(max_segment_error, error)
            if error > 1e-6:
                raise ValueError(f"segment deformation: {start} to {end}")
        previous = frame
    return {"max_joint_delta_m": max_delta,
            "max_segment_error_m": max_segment_error}


def _inspect(compiled: dict) -> dict:
    moves, clips, sequence = compiled["moves"], compiled["clips"], compiled["sequence"]
    if type(moves) is not list or len(moves) != PLAN_MOVES or type(clips) is not list or len(clips) != PLAN_MOVES:
        raise ValueError("four complete source clips required")
    if (type(sequence) is not dict or type(sequence.get("bpm")) is not int or sequence["bpm"] != BPM
            or type(sequence.get("fps")) is not int or sequence["fps"] != FPS
            or type(sequence.get("beats")) is not int or sequence["beats"] != 8
            or type(sequence.get("duration_seconds")) is not float
            or sequence["duration_seconds"] != 4.0):
        raise ValueError("invalid sequence timing")
    if sequence.get("bone_edges") != dance_motion.BONE_EDGES or sequence.get("segment_lengths_m") != _SEGMENT_LENGTHS:
        raise ValueError("invalid rig metadata")
    state = "rest"
    seam_velocity_jumps = []
    clip_reports = []
    for index, (move, clip) in enumerate(zip(moves, clips)):
        if type(move) is not dict or set(move) != {"id", "variation", "start_state", "end_state"}:
            raise ValueError("invalid move record")
        if (type(move["id"]) is not str or move["id"] not in _TRANSITIONS
                or type(move["variation"]) is not str or move["variation"] not in VARIATIONS):
            raise ValueError("unknown move record")
        start, end = _TRANSITIONS[move["id"]]
        if (start, end) != (move["start_state"], move["end_state"]) or start != state:
            raise ValueError("move order violates pose transition")
        state = end
        if (type(clip) is not dict or {key: clip.get(key) for key in move} != move
                or type(clip.get("beats")) is not int or clip["beats"] != MOVE_BEATS
                or type(clip.get("fps")) is not int or clip["fps"] != FPS
                or type(clip.get("duration_seconds")) is not float
                or clip["duration_seconds"] != MOVE_SECONDS):
            raise ValueError("source clip metadata mismatch")
        frames = clip.get("frames")
        clip_reports.append(_verify_frames(frames, count=MOVE_FRAMES + 1, offset=0.0))
        if frames[0]["joints"] != _pose(start) or frames[-1]["joints"] != _pose(end):
            raise ValueError("source clip endpoint mismatch")
        if clip != _clip(move):
            raise ValueError("source clip differs from frozen shelf")
        if index:
            before = clips[index - 1]["frames"][-1]
            after = frames[0]
            if before["joints"] != after["joints"] or before["contacts"] != after["contacts"]:
                raise ValueError("boundary pose/contact mismatch")
            prior = clips[index - 1]["frames"][-2]["joints"]
            following = frames[1]["joints"]
            jump = max(math.dist([after["joints"][name][axis] - prior[name][axis]
                                  for axis in range(3)],
                                 [following[name][axis] - after["joints"][name][axis]
                                  for axis in range(3)]) for name in _JOINTS)
            seam_velocity_jumps.append(jump)
            if jump > 0.05:
                raise ValueError("boundary sampled displacement jump")
    if state != "rest":
        raise ValueError("final pose must be rest")
    assembled = []
    for move_index, clip in enumerate(clips):
        for local_index, frame in enumerate(clip["frames"]):
            if move_index and local_index == 0:
                continue
            copy_frame = copy.deepcopy(frame)
            copy_frame["time"] = (move_index * MOVE_FRAMES + local_index) / FPS
            assembled.append(copy_frame)
    if sequence.get("frames") != assembled:
        raise ValueError("assembled frames differ from source clips")
    frame_report = _verify_frames(sequence["frames"], count=81, offset=0.0)
    full_report = dance_motion.validate(sequence)
    if sequence["frames"][0]["joints"] != _pose("rest") or sequence["frames"][-1]["joints"] != _pose("rest"):
        raise ValueError("sequence must start and end at rest")
    return {"valid": True, "frame_count": 81, "source_clip_frames": MOVE_FRAMES + 1,
            "seam_count": 3, "max_seam_displacement_jump_m": max(seam_velocity_jumps),
            "source_clip_validation": clip_reports,
            **frame_report, "full_rig_validation": full_report}


def validate_compilation(compiled: dict) -> dict:
    """Recheck actual source clips, seams, assembled frames and receipt hashes."""
    if type(compiled) is not dict or set(compiled) != {"moves", "clips", "sequence", "receipt"}:
        raise ValueError("incomplete compiled result")
    report = _inspect(compiled)
    receipt = compiled["receipt"]
    if type(receipt) is not dict or receipt.get("validation") != report \
            or receipt.get("catalog_sha256") != _digest(CATALOG) \
            or receipt.get("sequence_sha256") != _digest(compiled["sequence"]) \
            or receipt.get("clip_sha256") != [_digest(clip) for clip in compiled["clips"]]:
        raise ValueError("receipt does not match compiled motion")
    return report


def compile_plan(raw: str) -> dict:
    """Compile four model choices into a verified 4-second 81-frame sequence."""
    moves = parse_plan(raw)
    clips = [_clip(move) for move in moves]
    frames = []
    for move_index, clip in enumerate(clips):
        for local_index, frame in enumerate(clip["frames"]):
            if move_index and local_index == 0:
                continue
            assembled = copy.deepcopy(frame)
            assembled["time"] = (move_index * MOVE_FRAMES + local_index) / FPS
            frames.append(assembled)
    sequence = {
        "kind": "procedural_dance_phrase_shelf", "variant": "mixed",
        "bpm": BPM, "fps": FPS, "beats": 8, "duration_seconds": 4.0,
        "coordinate_system": "world x=lateral, y=forward, z=up; ground z=0",
        "bone_edges": copy.deepcopy(dance_motion.BONE_EDGES),
        "proportions_m": dict(dance_motion._LENGTHS),
        "segment_lengths_m": dict(_SEGMENT_LENGTHS),
        "scope": "Planted technical stick-figure phrases; no stepping, style authenticity, biomechanics or artistic-quality claim.",
        "frames": frames,
    }
    result = {"moves": moves, "clips": clips, "sequence": sequence}
    report = _inspect(result)
    result["receipt"] = {
        "catalog_sha256": _digest(CATALOG),
        "clip_sha256": [_digest(clip) for clip in clips],
        "sequence_sha256": _digest(sequence),
        "validation": report,
    }
    return result

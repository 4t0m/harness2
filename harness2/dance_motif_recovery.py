"""Explicit, planted recovery from a frozen motif pose to shared rest.

This constructs rigid limbs and solves both planted legs at every sample. It is
technical stick-figure recovery, not a balance, safety, or style claim.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math

from . import dance_motion, dance_phrases

RECOVERY_FPS = 20
RECOVERY_INTERVALS = 40
RECOVERY_MS = 2000
_JOINTS = frozenset(dance_phrases._JOINTS)
_REST = dance_phrases._pose("rest")
_REST_UPPER = 0.62
_REST_LOWER = 0.52


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _quintic(u: float) -> float:
    return u * u * u * (10.0 + u * (-15.0 + 6.0 * u))


def _pose(body_x: float, body_z: float, angles: dict[str, tuple[float, float]]) -> dict:
    """Construct torso and IK legs, then two independent planar arm links."""
    joints = dance_phrases._pose("rest", body_x=body_x, body_z=body_z)
    for side, sign in (("left", -1), ("right", 1)):
        upper, lower = angles[side]
        shoulder = joints[f"{side}_shoulder"]
        elbow = [shoulder[0] + sign * 0.30 * math.sin(upper), 0.0,
                 shoulder[2] - 0.30 * math.cos(upper)]
        wrist = [elbow[0] + sign * 0.28 * math.sin(lower), 0.0,
                 elbow[2] - 0.28 * math.cos(lower)]
        joints[f"{side}_elbow"] = elbow
        joints[f"{side}_wrist"] = wrist
    return joints


def _parameters(frame: dict) -> tuple[float, float, dict[str, tuple[float, float]]]:
    if type(frame) is not dict or set(frame) != {"time", "joints", "contacts"}:
        raise ValueError("source requires exactly time, joints, contacts")
    when = frame["time"]
    if type(when) not in (int, float) or not math.isfinite(when) or not 0 <= when <= 16:
        raise ValueError("invalid source time")
    joints = frame["joints"]
    contacts = frame["contacts"]
    if type(joints) is not dict or set(joints) != _JOINTS:
        raise ValueError("invalid source joint set")
    if (type(contacts) is not dict or set(contacts) != {"left", "right"}
            or any(type(value) is not bool or not value for value in contacts.values())):
        raise ValueError("source feet must both be planted")
    for name, point in joints.items():
        if (type(point) is not list or len(point) != 3
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       or abs(value) > 3 for value in point)):
            raise ValueError(f"invalid source joint {name}")
    body_x = joints["pelvis"][0]
    body_z = joints["pelvis"][2] - 0.92
    if abs(body_x) > 0.06 or not -0.005 <= body_z <= 0.05:
        raise ValueError("source outside planted motif range")
    angles = {}
    for side, sign in (("left", -1), ("right", 1)):
        shoulder = joints[f"{side}_shoulder"]
        elbow = joints[f"{side}_elbow"]
        wrist = joints[f"{side}_wrist"]
        upper = math.atan2(sign * (elbow[0] - shoulder[0]), shoulder[2] - elbow[2])
        lower = math.atan2(sign * (wrist[0] - elbow[0]), elbow[2] - wrist[2])
        if not 0.35 <= upper <= 1.7 or not 0.30 <= lower <= 1.6:
            raise ValueError("source arm angle outside motif range")
        angles[side] = (upper, lower)
    rebuilt = _pose(body_x, body_z, angles)
    if any(abs(joints[name][axis] - rebuilt[name][axis]) > 1e-9
           for name in _JOINTS for axis in range(3)):
        raise ValueError("source is not a reconstructable planted motif pose")
    for start, end, target, _ in dance_motion._SEGMENTS:
        if abs(math.dist(joints[start], joints[end]) - target) > 1e-6:
            raise ValueError("source segment length mismatch")
    return body_x, body_z, angles


def recover_frames(frame: dict) -> list[dict]:
    """Return 41 detached 20 fps frames; first pose exact, last shared rest."""
    body_x, body_z, angles = _parameters(frame)
    frames = []
    for index in range(RECOVERY_INTERVALS + 1):
        if index == 0:
            joints = copy.deepcopy(frame["joints"])
        elif index == RECOVERY_INTERVALS:
            joints = copy.deepcopy(_REST)
        else:
            remaining = 1.0 - _quintic(index / RECOVERY_INTERVALS)
            next_angles = {
                side: (_REST_UPPER + (pair[0] - _REST_UPPER) * remaining,
                       _REST_LOWER + (pair[1] - _REST_LOWER) * remaining)
                for side, pair in angles.items()
            }
            joints = _pose(body_x * remaining, body_z * remaining, next_angles)
        frames.append({"time": index / RECOVERY_FPS, "joints": joints,
                       "contacts": {"left": True, "right": True}})
    verify_recovery(frames, frame)
    return frames


def verify_recovery(frames: list[dict], source_frame: dict) -> dict:
    """Check sampled timing, rigid geometry, foot lock, and parameter easing."""
    source_x, source_z, source_angles = _parameters(source_frame)
    if type(frames) is not list or len(frames) != RECOVERY_INTERVALS + 1:
        raise ValueError("recovery requires 41 frames")
    max_segment_error = 0.0
    max_pose_error = 0.0
    for index, frame in enumerate(frames):
        if type(frame) is not dict or set(frame) != {"time", "joints", "contacts"}:
            raise ValueError("invalid recovery frame")
        if (type(frame["time"]) not in (int, float) or not math.isfinite(frame["time"])
                or abs(frame["time"] - index / RECOVERY_FPS) > 1e-9):
            raise ValueError("recovery time mismatch")
        body_x, body_z, angles = _parameters(frame)
        remaining = 1.0 - _quintic(index / RECOVERY_INTERVALS)
        expected = (source_x * remaining, source_z * remaining)
        max_pose_error = max(max_pose_error, abs(body_x - expected[0]),
                             abs(body_z - expected[1]))
        for side in ("left", "right"):
            for angle, original, rest in zip(angles[side], source_angles[side],
                                             (_REST_UPPER, _REST_LOWER)):
                max_pose_error = max(max_pose_error,
                                     abs(angle - (rest + (original - rest) * remaining)))
        if max_pose_error > 1e-9:
            raise ValueError("recovery parameter path mismatch")
        joints = frame["joints"]
        for side in ("left", "right"):
            if joints[f"{side}_ankle"] != _REST[f"{side}_ankle"] or joints[f"{side}_foot"] != _REST[f"{side}_foot"]:
                raise ValueError("recovery foot moved")
        for start, end, target, _ in dance_motion._SEGMENTS:
            max_segment_error = max(max_segment_error,
                                    abs(math.dist(joints[start], joints[end]) - target))
    if frames[0]["joints"] != source_frame["joints"] or frames[0]["contacts"] != source_frame["contacts"]:
        raise ValueError("recovery does not start at frozen pose")
    if frames[-1]["joints"] != _REST or frames[-1]["contacts"] != {"left": True, "right": True}:
        raise ValueError("recovery does not end at shared rest")
    return {"valid": True, "frame_count": len(frames), "fps": RECOVERY_FPS,
            "duration_seconds": RECOVERY_MS / 1000,
            "interpolation": "quintic articulation parameters with planted IK legs",
            "source_pose_sha256": _digest({"joints": source_frame["joints"],
                                            "contacts": source_frame["contacts"]}),
            "frames_sha256": _digest(frames),
            "max_segment_error_m": max_segment_error,
            "max_parameter_error": max_pose_error}

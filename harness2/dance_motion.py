"""Small procedural executable dance-motion prototype; generic, not style-authentic."""

import math

BPM = 120
FPS = 20
BEATS = 8
DURATION = BEATS * 60 / BPM
VARIANTS = {
    "restrained": {"step": 0.045, "sway": 0.025, "arm": 0.10},
    "broad": {"step": 0.105, "sway": 0.065, "arm": 0.25},
}
LIMBS = {
    "left_leg": (("left_hip", "left_knee"), ("left_knee", "left_ankle")),
    "right_leg": (("right_hip", "right_knee"), ("right_knee", "right_ankle")),
    "left_arm": (("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist")),
    "right_arm": (("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist")),
}
BONE_EDGES = [list(edge) for limb in LIMBS.values() for edge in limb] + [
    ["left_hip", "right_hip"], ["left_shoulder", "right_shoulder"],
    ["pelvis", "left_hip"], ["pelvis", "right_hip"],
    ["pelvis", "spine"], ["spine", "neck"], ["neck", "head"],
    ["left_shoulder", "spine"], ["right_shoulder", "spine"],
]
_LENGTHS = {"upper_leg": 0.46, "lower_leg": 0.46, "upper_arm": 0.30, "lower_arm": 0.28}


def _smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def _foot_track(side, t, step_amp):
    """Alternating short step-touches; each stance is exactly stationary."""
    # The right foot moves on even beats and the left on odd beats.
    moving = (side == "right" and int(math.floor(t)) % 2 == 0) or (
        side == "left" and int(math.floor(t)) % 2 == 1
    )
    beat = min(7, int(math.floor(t)))
    phase = t - math.floor(t)
    base_x = -0.16 if side == "left" else 0.16
    sign = -1 if side == "left" else 1
    # Each foot makes a small outward/inward touch on alternate beats.
    cycle = int(math.floor((beat + (side == "left")) / 2))
    target_x = base_x + sign * step_amp * (0.45 if cycle % 2 == 0 else -0.25)
    prev_x = base_x + sign * step_amp * (0.45 if (cycle - 1) % 2 == 0 else -0.25)
    if not moving or phase >= 0.30:
        return [target_x, 0.0, 0.08], True
    u = _smooth(phase / 0.30)
    return [prev_x + (target_x - prev_x) * u, 0.02 * math.sin(math.pi * u),
            0.08 + 0.075 * math.sin(math.pi * u)], False


def _knee(hip, ankle, length=0.46):
    """Equal-link 3D solve, selecting the knee on the character's forward side."""
    delta = [ankle[i] - hip[i] for i in range(3)]
    distance = math.sqrt(sum(v * v for v in delta))
    if not 1e-9 < distance < 2 * length:
        raise ValueError("leg reach outside constructed range")
    unit = [v / distance for v in delta]
    along = distance / 2
    height = math.sqrt(length * length - along * along)
    # Project the forward basis onto the plane perpendicular to the leg axis.
    forward_dot = unit[1]
    perp = [-forward_dot * unit[0], 1.0 - forward_dot * unit[1], -forward_dot * unit[2]]
    norm = math.sqrt(sum(v * v for v in perp))
    if norm < 1e-8:
        perp = [1.0, 0.0, 0.0]
    else:
        perp = [v / norm for v in perp]
    return [hip[i] + unit[i] * along + perp[i] * height for i in range(3)]


def _frame(t, variant):
    amp = VARIANTS[variant]
    beat = min(t * BPM / 60, math.nextafter(float(BEATS), 0.0))
    left_foot, left_contact = _foot_track("left", beat, amp["step"])
    right_foot, right_contact = _foot_track("right", beat, amp["step"])
    sway = amp["sway"] * math.sin(math.pi * beat)
    pelvis = [(left_foot[0] + right_foot[0]) / 2 + sway, 0.0,
              0.92 + 0.018 * (1 - math.cos(math.pi * beat))]
    joints = {
        "pelvis": pelvis,
        "left_hip": [pelvis[0] - 0.13, 0.0, 0.88],
        "right_hip": [pelvis[0] + 0.13, 0.0, 0.88],
        "left_ankle": left_foot,
        "right_ankle": right_foot,
        "left_foot": [left_foot[0], left_foot[1] + 0.10, 0.055],
        "right_foot": [right_foot[0], right_foot[1] + 0.10, 0.055],
        "spine": [pelvis[0], 0.0, 1.28],
        "neck": [pelvis[0], 0.0, 1.53],
        "head": [pelvis[0], 0.0, 1.70],
    }
    joints["left_knee"] = _knee(joints["left_hip"], left_foot)
    joints["right_knee"] = _knee(joints["right_hip"], right_foot)
    for side, sign in (("left", -1), ("right", 1)):
        shoulder = [pelvis[0] + sign * 0.22, 0.0, 1.43]
        phase = math.pi * beat + (0 if side == "left" else math.pi)
        arm_reach = 0.18 + 0.06 * amp["arm"] * math.sin(phase)
        elbow_drop = math.sqrt(_LENGTHS["upper_arm"] ** 2 - arm_reach ** 2)
        wrist_reach, wrist_forward = 0.14, 0.03
        wrist_drop = math.sqrt(_LENGTHS["lower_arm"] ** 2 - wrist_reach ** 2 - wrist_forward ** 2)
        elbow = [shoulder[0] + sign * arm_reach, 0.0, shoulder[2] - elbow_drop]
        wrist = [elbow[0] + sign * wrist_reach, wrist_forward, elbow[2] - wrist_drop]
        joints[f"{side}_shoulder"] = shoulder
        joints[f"{side}_elbow"] = elbow
        joints[f"{side}_wrist"] = wrist
    return {"time": t, "joints": joints,
            "contacts": {"left": left_contact, "right": right_contact}}


def generate(variant):
    """Generate an eight-beat phrase at 120 BPM, sampled at 20 frames per second."""
    if variant not in VARIANTS:
        raise ValueError("variant must be 'restrained' or 'broad'")
    frames = [_frame(i / FPS, variant) for i in range(round(DURATION * FPS) + 1)]
    return {
        "kind": "procedural_dance_motion_prototype",
        "variant": variant,
        "bpm": BPM,
        "fps": FPS,
        "beats": BEATS,
        "duration_seconds": DURATION,
        "coordinate_system": "world x=lateral, y=forward, z=up; ground z=0",
        "bone_edges": [edge[:] for edge in BONE_EDGES],
        "proportions_m": dict(_LENGTHS),
        "scope": "Generic step-touch-like technical prototype; no style authenticity, biomechanics, or artistic quality claim.",
        "frames": frames,
    }


def validate(sequence):
    """Host-owned screening checks; raises ValueError on malformed or invalid motion."""
    if not isinstance(sequence, dict) or not isinstance(sequence.get("frames"), list):
        raise ValueError("missing frames")
    frames = sequence["frames"]
    expected_count = round(DURATION * FPS) + 1
    if len(frames) != expected_count:
        raise ValueError("wrong frame count")
    joints_required = {"pelvis", "left_hip", "right_hip", "left_knee", "right_knee",
                       "left_ankle", "right_ankle", "left_foot", "right_foot", "spine",
                       "neck", "head", "left_shoulder", "right_shoulder", "left_elbow",
                       "right_elbow", "left_wrist", "right_wrist"}
    max_delta, max_length_error = 0.0, 0.0
    previous = None
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or set(frame) != {"time", "joints", "contacts"}:
            raise ValueError("invalid frame fields")
        if not math.isfinite(frame["time"]) or abs(frame["time"] - index / FPS) > 1e-9:
            raise ValueError("invalid frame time")
        joints = frame["joints"]
        if not isinstance(joints, dict) or not joints_required.issubset(joints):
            raise ValueError("missing joints")
        for name in joints_required:
            point = joints[name]
            if not isinstance(point, (list, tuple)) or len(point) != 3 or not all(
                isinstance(v, (int, float)) and math.isfinite(v) for v in point
            ):
                raise ValueError(f"invalid position: {name}")
            if previous is not None:
                delta = math.dist(point, previous["joints"][name])
                max_delta = max(max_delta, delta)
                if delta > 0.20:
                    raise ValueError("pose discontinuity")
        contacts = frame["contacts"]
        if not isinstance(contacts, dict) or set(contacts) != {"left", "right"} or any(
            type(value) is not bool for value in contacts.values()
        ):
            raise ValueError("invalid contact flags")
        if not any(contacts.values()):
            raise ValueError("no supporting foot")
        for foot in ("left_ankle", "right_ankle"):
            if joints[foot][2] < -1e-9:
                raise ValueError("ankle below ground")
        for side in ("left", "right"):
            if contacts[side] and abs(joints[f"{side}_foot"][2]) > 0.10:
                raise ValueError(f"contact foot away from ground: {side}")
        if previous is not None:
            for side in ("left", "right"):
                if contacts[side] and previous["contacts"][side]:
                    slide = math.dist(joints[f"{side}_ankle"], previous["joints"][f"{side}_ankle"])
                    if slide > 1e-5:
                        raise ValueError(f"planted foot sliding: {side}")
        length_pairs = [("left_hip", "left_knee", _LENGTHS["upper_leg"]),
                        ("left_knee", "left_ankle", _LENGTHS["lower_leg"]),
                        ("right_hip", "right_knee", _LENGTHS["upper_leg"]),
                        ("right_knee", "right_ankle", _LENGTHS["lower_leg"]),
                        ("left_shoulder", "left_elbow", _LENGTHS["upper_arm"]),
                        ("left_elbow", "left_wrist", _LENGTHS["lower_arm"]),
                        ("right_shoulder", "right_elbow", _LENGTHS["upper_arm"]),
                        ("right_elbow", "right_wrist", _LENGTHS["lower_arm"])]
        for start, end, target in length_pairs:
            error = abs(math.dist(joints[start], joints[end]) - target)
            max_length_error = max(max_length_error, error)
            if error > 1e-6:
                raise ValueError(f"wrong limb length: {start} to {end}")
        previous = {"joints": joints, "contacts": contacts}
    if abs(frames[-1]["time"] - DURATION) > 1e-9:
        raise ValueError("wrong duration")
    return {"valid": True, "frame_count": len(frames), "duration_seconds": frames[-1]["time"],
            "max_joint_delta_m": max_delta, "max_leg_segment_error_m": max_length_error,
            "scope": "Technical screening only; not a biomechanics or artistic-quality result."}

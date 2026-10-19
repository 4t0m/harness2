"""Render-only 24 fps samples from the authoritative 20 fps dance prototype.

Linear interpolation is a display sampling step. These frames are not a motion
source, contact solution, or validated rig, and they exclude the 4-second endpoint.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math

from . import dance_motion

RENDER_FPS = 24
SOURCE_TIMING = {"bpm": dance_motion.BPM, "fps": dance_motion.FPS,
                 "beats": dance_motion.BEATS, "duration_seconds": dance_motion.DURATION}


def _source_hash(sequence: dict) -> str:
    data = json.dumps(sequence, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _validate_source(sequence: dict) -> str:
    if not isinstance(sequence, dict) or any(
        type(sequence.get(key)) is not type(expected) or sequence[key] != expected
        for key, expected in SOURCE_TIMING.items()
    ):
        raise ValueError("source timing must match the 20 fps eight-beat prototype")
    try:
        dance_motion.validate(sequence)
    except (TypeError, KeyError) as exc:
        raise ValueError("malformed source sequence") from exc
    if sequence.get("coordinate_system") != "world x=lateral, y=forward, z=up; ground z=0":
        raise ValueError("source coordinate system differs from prototype")
    for frame in sequence["frames"]:
        if type(frame["time"]) not in (int, float) or any(
            not isinstance(point, (list, tuple)) or len(point) != 3 or any(
                type(value) not in (int, float) or not math.isfinite(value) for value in point
            ) for point in frame["joints"].values()
        ):
            raise ValueError("source contains malformed or nonfinite samples")
    try:
        return _source_hash(sequence)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("source contains nonfinite or non-JSON metadata") from exc


def resample_for_render(sequence: dict, output_fps: int = RENDER_FPS) -> dict:
    """Return 96 display frames at t=0..95/24 with exact source mappings."""
    if type(output_fps) is not int or output_fps != RENDER_FPS:
        raise ValueError("render sample rate is fixed to 24 fps")
    source_sha = _validate_source(sequence)
    source_frames = sequence["frames"]
    frames = []
    coincident_indices = []
    max_deviation = 0.0
    count = int(dance_motion.DURATION * RENDER_FPS)
    for render_index in range(count):
        numerator = render_index * dance_motion.FPS
        left_index, remainder = divmod(numerator, RENDER_FPS)
        right_index = left_index + 1
        alpha = remainder / RENDER_FPS
        left = source_frames[left_index]["joints"]
        right = source_frames[right_index]["joints"]
        if remainder == 0:
            joints = {name: list(point) for name, point in left.items()}
            coincident_indices.append(render_index)
        else:
            joints = {name: [point[axis] + (right[name][axis] - point[axis]) * alpha
                             for axis in range(3)] for name, point in left.items()}
        for edge, target in sequence["segment_lengths_m"].items():
            start, end = edge.split(":", 1)
            max_deviation = max(max_deviation, abs(math.dist(joints[start], joints[end]) - target))
        frames.append({"time": render_index / RENDER_FPS, "joints": joints,
                       "source_mapping": {"left_index": left_index,
                                          "right_index": right_index, "alpha": alpha}})
    exact_coincidences = all(
        frames[index]["joints"] == source_frames[frames[index]["source_mapping"]["left_index"]]["joints"]
        for index in coincident_indices
    )
    if not exact_coincidences or _source_hash(sequence) != source_sha:
        raise ValueError("source coincidence or source immutability check failed")
    return {
        "kind": "render_only_linear_resample",
        "scope": "Display samples only; no contact, segment-rig validity, biomechanics, or style claim.",
        "source_canonical_sha256": source_sha,
        "source": {"fps": dance_motion.FPS, "frame_count": len(source_frames),
                   "endpoint_inclusive": True, "duration_seconds": dance_motion.DURATION},
        "render": {"fps": RENDER_FPS, "frame_count": count,
                   "endpoint_inclusive": False, "duration_seconds": dance_motion.DURATION},
        "coordinate_system": sequence["coordinate_system"],
        "bone_edges": copy.deepcopy(sequence["bone_edges"]),
        "segment_lengths_m_source_targets": copy.deepcopy(sequence["segment_lengths_m"]),
        "measurements": {"max_segment_length_deviation_from_source_m": max_deviation,
                         "exact_source_coincidence_preserved": exact_coincidences,
                         "source_coincidence_render_indices": coincident_indices,
                         "source_unchanged": True},
        "frames": frames,
    }

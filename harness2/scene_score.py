"""A small, CPU-only H3 scene skeleton from symbolic pose choices.

The model-facing brief contains the scene and creative request. The host owns
timing, actor assignments, pose atlas, target placement, and the task oracle.
No avatar assets are loaded and no frames are rendered.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

POSES = ("neutral", "listen", "point", "turn_away")
INTENSITIES = ("subtle", "normal", "strong")
FRAME_RATE = 12
MIN_DURATION = 2
MAX_DURATION = 8
CLEARANCE = 0.08

SCENE = {
    "revision": "h3-skeleton-v1",
    "frame": "screen_2d_normalized",
    "actors": [
        {"id": "aya", "x": 0.20, "y": 0.50, "radius": 0.05},
        {"id": "ren", "x": 0.55, "y": 0.50, "radius": 0.05},
        {"id": "mira", "x": 0.85, "y": 0.50, "radius": 0.05},
    ],
}
SLOTS = (
    {"beat_id": "beat-1", "actor_id": "aya", "start_frame": 0, "channel": "body"},
    {"beat_id": "beat-2", "actor_id": "aya", "start_frame": 6, "channel": "body"},
    {"beat_id": "beat-3", "actor_id": "ren", "start_frame": 12, "channel": "body"},
)
REQUEST = (
    "Make a gentle three-beat exchange. Aya first attends quietly to Ren, "
    "then emphatically indicates Mira. Ren then disengages from Aya with normal intensity."
)
# Frozen host oracle: never included in model_brief().
EXPECTED = (
    {"beat_id": "beat-1", "pose": "listen", "intensity": "subtle", "target_id": "ren"},
    {"beat_id": "beat-2", "pose": "point", "intensity": "strong", "target_id": "mira"},
    {"beat_id": "beat-3", "pose": "turn_away", "intensity": "normal", "target_id": "aya"},
)


def model_brief() -> str:
    """Give the solver creative semantics and fixed timing, not expected choices."""
    return (
        "Select symbolic poses for exactly three fixed beats. Return only a JSON object "
        "with scene_revision and beats. Each beat has exactly beat_id, pose, intensity, "
        "target_id, duration_frames. Use each beat ID once, in order. Durations are integers "
        f"from {MIN_DURATION} to {MAX_DURATION}; beats sharing an actor/body channel must not overlap. "
        "Choose pose from neutral/listen/point/turn_away and intensity from "
        "subtle/normal/strong. Target must be another actor in the scene. "
        "These are pose and shot cues, not executed avatar motion.\n"
        "Scene: " + json.dumps(SCENE, sort_keys=True) + "\n"
        "Fixed beat slots: " + json.dumps(SLOTS, sort_keys=True) + "\n"
        "Creative request: " + REQUEST
    )


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _bad_constant(value):
    raise ValueError(f"nonfinite JSON number: {value}")


def parse_score(raw: str) -> dict:
    """Strict model output shape; host timing and positions are absent from it."""
    if not isinstance(raw, str) or len(raw) > 4096:
        raise ValueError("score must be a JSON string under 4096 characters")
    try:
        score = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_bad_constant)
    except RecursionError as exc:
        raise ValueError("score nesting too deep") from exc
    if not isinstance(score, dict) or set(score) != {"scene_revision", "beats"}:
        raise ValueError("score top-level fields must be scene_revision and beats")
    if not isinstance(score["scene_revision"], str) or not score["scene_revision"]:
        raise ValueError("scene_revision must be a nonempty string")
    beats = score["beats"]
    if not isinstance(beats, list) or len(beats) != len(SLOTS):
        raise ValueError("exactly three beats required")
    beat_fields = {"beat_id", "pose", "intensity", "target_id", "duration_frames"}
    seen = set()
    for beat in beats:
        if not isinstance(beat, dict) or set(beat) != beat_fields:
            raise ValueError("beat fields do not match contract")
        beat_id = beat["beat_id"]
        if not isinstance(beat_id, str) or beat_id in seen:
            raise ValueError("duplicate or invalid beat ID")
        seen.add(beat_id)
        if beat["pose"] not in POSES:
            raise ValueError("unknown pose")
        if beat["intensity"] not in INTENSITIES:
            raise ValueError("unknown intensity")
        if not isinstance(beat["target_id"], str) or not beat["target_id"]:
            raise ValueError("target_id must be a nonempty string")
        duration = beat["duration_frames"]
        if isinstance(duration, bool) or not isinstance(duration, int) or not MIN_DURATION <= duration <= MAX_DURATION:
            raise ValueError("duration_frames out of bounds")
    if [beat["beat_id"] for beat in beats] != [slot["beat_id"] for slot in SLOTS]:
        raise ValueError("beat IDs or order do not match fixed slots")
    return score


def _actors(scene: dict) -> dict:
    actors = scene.get("actors")
    if not isinstance(actors, list) or len(actors) < 2:
        raise ValueError("invalid host scene")
    out = {}
    for actor in actors:
        if not isinstance(actor, dict) or set(actor) != {"id", "x", "y", "radius"}:
            raise ValueError("invalid host actor")
        identity = actor["id"]
        if not isinstance(identity, str) or not identity or identity in out:
            raise ValueError("duplicate host actor ID")
        for field in ("x", "y", "radius"):
            value = actor[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("invalid host actor number")
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("invalid host actor number")
        if not (0 < actor["radius"] <= 0.5 and
                all(actor["radius"] <= actor[axis] <= 1 - actor["radius"] for axis in ("x", "y"))):
            raise ValueError("host actor footprint outside frame")
        out[identity] = actor
    return out


def _relative_placement(actor: dict, target: dict) -> dict:
    """Suggest one static anchor; does not plan a path or move the actor."""
    dx, dy = target["x"] - actor["x"], target["y"] - actor["y"]
    distance = math.hypot(dx, dy)
    needed = actor["radius"] + target["radius"] + CLEARANCE
    if distance < needed - 1e-12:
        raise ValueError("actors overlap or are already inside placement clearance")
    travel = max(0.0, distance - needed)
    x = actor["x"] + dx * travel / distance
    y = actor["y"] + dy * travel / distance
    edge_gap = math.hypot(target["x"] - x, target["y"] - y) - actor["radius"] - target["radius"]
    if edge_gap < CLEARANCE - 1e-9:
        raise ValueError("placement clearance violated")
    direction = "screen_right" if dx > 1e-12 else "screen_left" if dx < -1e-12 else "center"
    return {"optional_anchor": {"x": x, "y": y}, "edge_gap_at_anchor": edge_gap,
            "target_screen_direction": direction, "target_snapshot": {"x": target["x"], "y": target["y"]},
            "checks": "target clearance at static anchor only; no path or other-actor collision check"}


def compile_score(score: dict, *, scene: dict = SCENE, slots: tuple[dict, ...] = SLOTS) -> dict:
    """Compile symbolic choices to deterministic cues; never run untrusted code."""
    if score["scene_revision"] != scene.get("revision"):
        raise ValueError("stale scene revision")
    actors = _actors(scene)
    if len(slots) != 3 or [beat["beat_id"] for beat in score["beats"]] != [slot["beat_id"] for slot in slots]:
        raise ValueError("score does not match fixed beat slots")
    manifest = []
    intervals: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for beat, slot in zip(score["beats"], slots):
        actor_id, target_id = slot["actor_id"], beat["target_id"]
        if actor_id not in actors or target_id not in actors or actor_id == target_id:
            raise ValueError("unknown or identical actor/target")
        start = slot["start_frame"]
        end = start + beat["duration_frames"]
        key = (actor_id, slot["channel"])
        if any(start < old_end and old_start < end for old_start, old_end in intervals.get(key, [])):
            raise ValueError("conflicting actor/channel timelines")
        intervals.setdefault(key, []).append((start, end))
        placement = _relative_placement(actors[actor_id], actors[target_id])
        manifest.append({"beat_id": beat["beat_id"], "start_frame": start,
                         "end_frame_exclusive": end, "duration_frames": beat["duration_frames"],
                         "actor_id": actor_id, "target_id": target_id, "channel": slot["channel"],
                         "pose_atlas_key": beat["pose"], "intensity": beat["intensity"],
                         "scene_actor_position": {"x": actors[actor_id]["x"], "y": actors[actor_id]["y"]},
                         "staging_suggestion": placement})
    return {"kind": "h3_scene_skeleton", "scene_revision": scene["revision"],
            "frame_rate": FRAME_RATE, "timing_scope": "compressed contract fixture, not acting timing",
            "rendered": False, "runtime_executed": False,
            "shot_cues": manifest}


def evaluate_score(raw: str) -> dict:
    """Separate structural success, compilability, and creative task match."""
    try:
        score = parse_score(raw)
    except ValueError as exc:
        return {"schema_valid": False, "compiled": False, "semantic_correct": False,
                "accepted": False, "reason": str(exc)}
    try:
        manifest = compile_score(score)
    except ValueError as exc:
        return {"schema_valid": True, "compiled": False, "semantic_correct": False,
                "accepted": False, "reason": str(exc)}
    semantic = all(
        all(beat[name] == wanted[name] for name in ("beat_id", "pose", "intensity", "target_id"))
        for beat, wanted in zip(score["beats"], EXPECTED)
    )
    return {"schema_valid": True, "compiled": True, "semantic_correct": semantic,
            "accepted": semantic, "reason": None if semantic else "creative beat choices differ from request",
            "manifest": manifest}


def run_offline_evidence() -> dict:
    """Scripted candidates make a cheap contract receipt, not a model trial."""
    base = {"scene_revision": SCENE["revision"], "beats": [
        {**beat, "duration_frames": 6} for beat in EXPECTED
    ]}
    candidates = {"correct": base}
    wrong = json.loads(json.dumps(base))
    wrong["beats"][1]["target_id"] = "ren"
    candidates["wrong_target"] = wrong
    stale = json.loads(json.dumps(base))
    stale["scene_revision"] = "prior-v0"
    candidates["stale_revision"] = stale
    conflict = json.loads(json.dumps(base))
    conflict["beats"][0]["duration_frames"] = 8
    candidates["conflicting_timeline"] = conflict
    unknown = json.loads(json.dumps(base))
    unknown["beats"][0]["pose"] = "dance"
    candidates["unknown_pose"] = unknown
    return {"scope": "CPU-only scripted pose choices; compressed fixture shot manifest with optional static staging suggestions only; no art/model/renderer/H3 runtime or collision-safe movement",
            "scene_revision": SCENE["revision"], "pose_atlas": list(POSES),
            "cases": [{"name": name, "proposal": proposal,
                       "verdict": evaluate_score(json.dumps(proposal))}
                      for name, proposal in candidates.items()]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run_offline_evidence(), indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

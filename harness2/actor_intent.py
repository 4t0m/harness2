"""Host-compiled actor intent tasks with distractors and mirrored scenes.

The model proposes IDs and an action only. Trusted code resolves geometry,
runtime support, and frozen task meaning. This module never drives a renderer.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _actor(identity, x, y=0.5, radius=0.05, facing="toward_camera"):
    return {"id": identity, "x": x, "y": y, "radius": radius, "facing": facing}


# The natural request and scene go to the model. Expected IDs remain host-only.
TASKS = {
    "look-left-nearest": {
        "scene": {"revision": "left-v1", "actors": [
            _actor("aya", 0.72), _actor("ren", 0.46), _actor("mira", 0.18)]},
        "request": "Aya should look at the nearest other actor to her screen-left.",
        "expected": {"actor_id": "aya", "target_id": "ren", "action": "look_at"},
    },
    "look-right-mirror": {
        "scene": {"revision": "right-v1", "actors": [
            _actor("aya", 0.28, facing="away_from_camera"),
            _actor("ren", 0.54), _actor("mira", 0.86)]},
        "request": "Aya should look at the nearest other actor to her screen-right.",
        "expected": {"actor_id": "aya", "target_id": "ren", "action": "look_at"},
    },
    "look-vertical": {
        "scene": {"revision": "vertical-v1", "actors": [
            _actor("aya", 0.5, 0.35), _actor("ren", 0.5, 0.62),
            _actor("mira", 0.85, 0.35)]},
        "request": "Aya should look at the nearest other actor directly below her on screen.",
        "expected": {"actor_id": "aya", "target_id": "ren", "action": "look_at"},
    },
    "approach-left": {
        "scene": {"revision": "approach-left-v1", "actors": [
            _actor("aya", 0.82), _actor("ren", 0.39, radius=0.06),
            _actor("mira", 0.12)]},
        "request": "Aya should approach the nearest other actor to her screen-left and stop with a 0.12 edge-to-edge gap.",
        "expected": {"actor_id": "aya", "target_id": "ren", "action": "approach", "stop_gap": 0.12},
    },
    "approach-right-mirror": {
        "scene": {"revision": "approach-right-v1", "actors": [
            _actor("aya", 0.18), _actor("ren", 0.61, radius=0.06),
            _actor("mira", 0.88)]},
        "request": "Aya should approach the nearest other actor to her screen-right and stop with a 0.12 edge-to-edge gap.",
        "expected": {"actor_id": "aya", "target_id": "ren", "action": "approach", "stop_gap": 0.12},
    },
}


def model_brief(task_id: str) -> str:
    """A model-facing brief with scene and task but no host answer."""
    task = TASKS[task_id]
    return (
        "Return only one JSON object. Choose actor_id, target_id, and action from the task. "
        "For look_at, use exactly scene_revision, actor_id, target_id, action. "
        "For approach, add numeric stop_gap. Use the scene revision exactly. "
        "No endpoint coordinates, tool calls, markdown, or claim of live movement.\n"
        "Scene (screen x increases right, y increases down):\n"
        + json.dumps(task["scene"], sort_keys=True)
        + "\nTask: " + task["request"]
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


def _finite(value, name, low, high, *, open_low=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: finite number required")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (value <= low if open_low else value < low) or value > high:
        raise ValueError(f"{name}: finite number out of range")


def parse_intent(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw) > 2048:
        raise ValueError("intent must be a JSON string under 2048 characters")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_bad_constant)
    except RecursionError as exc:
        raise ValueError("intent nesting too deep") from exc
    if not isinstance(value, dict):
        raise ValueError("intent must be an object")
    action = value.get("action")
    if action not in ("look_at", "approach"):
        raise ValueError("unsupported action")
    fields = {"scene_revision", "actor_id", "target_id", "action"}
    if action == "approach":
        fields.add("stop_gap")
    if set(value) != fields:
        raise ValueError("intent fields do not match action")
    for name in ("scene_revision", "actor_id", "target_id"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise ValueError(f"{name}: nonempty string required")
    if action == "approach":
        _finite(value["stop_gap"], "stop_gap", 0, 1)
    return value


def _scene_actors(scene: dict) -> dict[str, dict]:
    actors = scene.get("actors")
    if not isinstance(actors, list) or len(actors) < 2:
        raise ValueError("scene needs at least two actors")
    by_id = {}
    for actor in actors:
        if not isinstance(actor, dict) or set(actor) != {"id", "x", "y", "radius", "facing"}:
            raise ValueError("invalid scene actor")
        identity = actor["id"]
        if not isinstance(identity, str) or not identity or identity in by_id:
            raise ValueError("duplicate or empty scene actor ID")
        for name in ("x", "y"):
            _finite(actor[name], f"{identity}.{name}", 0, 1)
        _finite(actor["radius"], f"{identity}.radius", 0, 0.5, open_low=True)
        if actor["facing"] not in ("toward_camera", "away_from_camera"):
            raise ValueError("invalid scene facing")
        if any(actor[axis] - actor["radius"] < 0 or actor[axis] + actor["radius"] > 1
               for axis in ("x", "y")):
            raise ValueError("actor footprint outside frame")
        by_id[identity] = actor
    return by_id


def compile_intent(intent: dict, scene: dict) -> dict:
    """Resolve only from trusted scene data; unsupported control is explicit."""
    if intent["scene_revision"] != scene.get("revision"):
        raise ValueError("stale scene revision")
    actors = _scene_actors(scene)
    actor_id, target_id = intent["actor_id"], intent["target_id"]
    if actor_id == target_id or actor_id not in actors or target_id not in actors:
        raise ValueError("unknown or identical actor IDs")
    actor, target = actors[actor_id], actors[target_id]
    dx, dy = target["x"] - actor["x"], target["y"] - actor["y"]
    horizontal = "screen_right" if dx > 1e-12 else "screen_left" if dx < -1e-12 else "center"
    vertical = "screen_down" if dy > 1e-12 else "screen_up" if dy < -1e-12 else "center"
    if horizontal == "center":
        local = "center"
    elif actor["facing"] == "toward_camera":
        local = "actor_left" if horizontal == "screen_right" else "actor_right"
    else:
        local = "actor_right" if horizontal == "screen_right" else "actor_left"
    result = {"action": intent["action"], "actor_id": actor_id, "target_id": target_id,
              "scene_revision": scene["revision"], "execution": "planning_only"}
    if intent["action"] == "look_at":
        supported = vertical == "center" and horizontal in ("center", "screen_right")
        result.update({"screen_gaze": horizontal, "vertical_gaze": vertical,
                       "actor_local_gaze": local, "runtime_status": "supported" if supported else "unsupported",
                       "adapter_control": ("neutral" if horizontal == "center" else "look_right")
                       if supported else None})
        return result
    distance = math.hypot(dx, dy)
    clearance = actor["radius"] + target["radius"] + intent["stop_gap"]
    if distance < clearance - 1e-12:
        raise ValueError("initial footprints overlap or already inside stop gap")
    travel = max(0.0, distance - clearance)
    final_x = actor["x"] + dx * travel / distance
    final_y = actor["y"] + dy * travel / distance
    final_gap = math.hypot(target["x"] - final_x, target["y"] - final_y) - actor["radius"] - target["radius"]
    if final_gap < intent["stop_gap"] - 1e-9:
        raise ValueError("planned clearance violated")
    result.update({"runtime_status": "preview_only", "adapter_control": None,
                   "geometry": {"final_position": {"x": final_x, "y": final_y},
                                "edge_gap_final": final_gap, "stop_gap_requested": intent["stop_gap"],
                                "travel_distance": travel, "replan_if_target_moves": True}})
    return result


def evaluate_intent(task_id: str, raw: str) -> dict:
    """Separate format/scene validity, task meaning, and runtime support."""
    task = TASKS[task_id]
    try:
        intent = parse_intent(raw)
    except ValueError as exc:
        return {"schema_valid": False, "compiled": False, "semantic_correct": False,
                "accepted": False, "reason": str(exc)}
    try:
        plan = compile_intent(intent, task["scene"])
    except ValueError as exc:
        return {"schema_valid": True, "compiled": False, "semantic_correct": False,
                "accepted": False, "reason": str(exc)}
    expected = task["expected"]
    semantic = all(intent[name] == value for name, value in expected.items())
    return {"schema_valid": True, "compiled": True, "semantic_correct": semantic,
            "accepted": semantic, "runtime_status": plan["runtime_status"],
            "plan": plan, "reason": None if semantic else "wrong task target, actor, action, or gap"}


def run_offline_evidence() -> dict:
    """Exercise a scripted candidate matrix; no model or network is used."""
    cases = []
    for task_id, task in TASKS.items():
        intent = {"scene_revision": task["scene"]["revision"], **task["expected"]}
        cases.append({"task": task_id, "kind": "scripted_correct",
                      "intent": intent, "verdict": evaluate_intent(task_id, json.dumps(intent))})
        wrong = dict(intent)
        wrong["target_id"] = "mira"
        cases.append({"task": task_id, "kind": "scripted_wrong_target",
                      "intent": wrong, "verdict": evaluate_intent(task_id, json.dumps(wrong))})
    stale = {"scene_revision": "old", **TASKS["look-left-nearest"]["expected"]}
    cases.append({"task": "look-left-nearest", "kind": "scripted_stale_revision",
                  "intent": stale, "verdict": evaluate_intent("look-left-nearest", json.dumps(stale))})
    return {"scope": "CPU-only scripted intents and trusted compiler; no model call or live animation",
            "model_brief_excludes_answer": all("expected" not in model_brief(task_id)
                                               for task_id in TASKS),
            "cases": cases}


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

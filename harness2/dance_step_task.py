"""Host constraints for four-step plans; no model-owned target or world motion."""

from __future__ import annotations

import hashlib
import itertools
import json
import math

from . import dance_steps

_FIELDS = {"id", "start_x_mm", "target_x_mm", "root_bounds_mm",
           "required_moves", "required_variations"}
_SLOTS = {str(i) for i in range(4)}
_DIRECTION_MM = {"step_left": -200, "step_right": 200}


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def validate_task(task: dict) -> dict:
    """Return a detached, exact-schema copy of authoritative task facts."""
    if type(task) is not dict or set(task) != _FIELDS:
        raise ValueError("task requires exact fields")
    identifier = task["id"]
    if type(identifier) is not str or not identifier or len(identifier) > 80 \
            or any(ord(char) < 32 for char in identifier):
        raise ValueError("invalid task id")
    for field in ("start_x_mm", "target_x_mm"):
        value = task[field]
        if type(value) is not int or not -10_000 <= value <= 10_000:
            raise ValueError(f"invalid {field}")
    bounds = task["root_bounds_mm"]
    if type(bounds) is not list or len(bounds) != 2 or any(
            type(value) is not int or not -10_000 <= value <= 10_000
            for value in bounds) or bounds[0] > bounds[1]:
        raise ValueError("invalid root_bounds_mm")
    if not bounds[0] <= task["start_x_mm"] <= bounds[1]:
        raise ValueError("start outside root bounds")
    normalized = {"id": identifier, "start_x_mm": task["start_x_mm"],
                  "target_x_mm": task["target_x_mm"],
                  "root_bounds_mm": bounds[:],}
    for field, legal in (("required_moves", dance_steps.MOVES),
                         ("required_variations", dance_steps.VARIATIONS)):
        requirements = task[field]
        if type(requirements) is not dict or any(
                type(slot) is not str or slot not in _SLOTS
                or type(choice) is not str or choice not in legal
                for slot, choice in requirements.items()):
            raise ValueError(f"invalid {field}")
        normalized[field] = dict(requirements)
    return normalized


def _check_choices(choices: list[tuple[str, str]], task: dict) -> None:
    for slot, (move, variation) in enumerate(choices):
        required_move = task["required_moves"].get(str(slot))
        if required_move is not None and move != required_move:
            raise ValueError(f"move slot {slot} violates requirement")
        required_variation = task["required_variations"].get(str(slot))
        if required_variation is not None and variation != required_variation:
            raise ValueError(f"variation slot {slot} violates requirement")


def _endpoints(choices: list[tuple[str, str]], start: int) -> list[int]:
    points = [start]
    for move, _variation in choices:
        points.append(points[-1] + _DIRECTION_MM[move])
    return points


def feasible_plans(task: dict) -> list[list[list[str]]]:
    """Enumerate all eligible four-pair plans (at most 256), in fixed order."""
    facts = validate_task(task)
    low, high = facts["root_bounds_mm"]
    plans = []
    for moves in itertools.product(dance_steps.MOVES, repeat=4):
        points = _endpoints([(move, "soft") for move in moves], facts["start_x_mm"])
        if points[-1] != facts["target_x_mm"] or any(
                not low <= point <= high for point in points):
            continue
        for variations in itertools.product(dance_steps.VARIATIONS, repeat=4):
            choices = list(zip(moves, variations))
            try:
                _check_choices(choices, facts)
            except ValueError:
                continue
            plans.append([[move, variation] for move, variation in choices])
    return plans


def _check_result(local: dict, facts: dict) -> tuple[dict, dict]:
    dance_steps.verify_compilation(local)
    sequence = local["sequence"]
    choices = [(row["id"], row["variation"]) for row in sequence["move_plan"]]
    _check_choices(choices, facts)
    endpoints = _endpoints(choices, facts["start_x_mm"])
    if endpoints[-1] != facts["target_x_mm"]:
        raise ValueError(f"final root {endpoints[-1]} mm differs from target "
                         f"{facts['target_x_mm']} mm")
    low, high = facts["root_bounds_mm"]
    minimum, maximum = math.inf, -math.inf
    for index, frame in enumerate(sequence["frames"]):
        world_x = facts["start_x_mm"] + frame["joints"]["pelvis"][0] * 1000
        if not math.isfinite(world_x) or world_x < low - 1e-7 or world_x > high + 1e-7:
            raise ValueError(f"root leaves lane at frame {index}")
        minimum = min(minimum, world_x)
        maximum = max(maximum, world_x)
    # The compiler's local endpoints and the integer arithmetic must agree.
    actual_final = facts["start_x_mm"] + sequence["frames"][-1]["joints"]["pelvis"][0] * 1000
    if abs(actual_final - endpoints[-1]) > 1e-7:
        raise ValueError("world final root disagrees with plan")
    placement = {"world_start_x_mm": facts["start_x_mm"],
                 "world_final_x_mm": endpoints[-1]}
    checks = {"world_root_min_x_mm": round(minimum, 9),
              "world_root_max_x_mm": round(maximum, 9),
              "sample_count": len(sequence["frames"]), "lane_valid": True,
              "target_valid": True, "requirements_valid": True}
    return placement, checks


def compile_task(raw: str, task: dict) -> dict:
    """Compile strict model choices and verify the host's world-space task."""
    facts = validate_task(task)
    local = dance_steps.compile_steps(raw)
    placement, checks = _check_result(local, facts)
    receipt = {"task_sha256": _hash(facts),
               "local_sequence_sha256": local["receipt"]["sequence_sha256"],
               "checks": checks}
    return {"local": local, "placement": placement, "receipt": receipt}


def verify_task(result: dict, task: dict) -> dict:
    """Recalculate physical, semantic, placement, and receipt checks."""
    facts = validate_task(task)
    if type(result) is not dict or set(result) != {"local", "placement", "receipt"}:
        raise ValueError("incomplete task compilation")
    placement, checks = _check_result(result["local"], facts)
    expected_receipt = {"task_sha256": _hash(facts),
                        "local_sequence_sha256": result["local"]["receipt"]["sequence_sha256"],
                        "checks": checks}
    if result["placement"] != placement or result["receipt"] != expected_receipt:
        raise ValueError("task placement or receipt mismatch")
    return checks

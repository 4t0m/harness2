"""Independent model briefs and black-box timeline oracles for motif runtime.

The expected intents are host-only. Runtime checks consume a normalized event
and sample log emitted by the API caller; they do not inspect runtime fields.
"""

from __future__ import annotations

import json

from harness2.dance_motif_score import compile_intent, verify_score


CASES = [
    {
        "id": "runtime_e2b_returning_sway_replacement",
        "model": "gemma4:e2b",
        "initial": {
            "request": (
                "Keep the recurring A movement lateral, like a sway. Across sections "
                "one through four, choose accents soft, clear, soft, clear in order."
            ),
            "expected_intent": {"motif": "sway", "accents": ["soft", "clear", "soft", "clear"]},
        },
        "replacement": {
            "request": (
                "Replace that score with a vertical pulse as the returning A idea. "
                "Set the four sections' accents, from first to last, to clear, soft, "
                "clear, soft."
            ),
            "expected_intent": {"motif": "pulse", "accents": ["clear", "soft", "clear", "soft"]},
        },
        "delayed_after_stop": {
            "request": (
                "For a fresh AABA pass, use pulse for A and set the section accents "
                "in chronological order to clear, clear, soft, soft."
            ),
            "expected_intent": {"motif": "pulse", "accents": ["clear", "clear", "soft", "soft"]},
        },
    },
    {
        "id": "runtime_qwen_pulse_replacement",
        "model": "hermes-lab-qwen3-8b:latest",
        "initial": {
            "request": (
                "Use the up-and-down pulse for the repeated A movement. The accents "
                "for blocks one, two, three, and four are soft, clear, clear, soft."
            ),
            "expected_intent": {"motif": "pulse", "accents": ["soft", "clear", "clear", "soft"]},
        },
        "replacement": {
            "request": (
                "Change A to the side-to-side sway. Reading the four blocks from the "
                "beginning, accent them clear, soft, soft, clear."
            ),
            "expected_intent": {"motif": "sway", "accents": ["clear", "soft", "soft", "clear"]},
        },
        "delayed_after_stop": {
            "request": (
                "A should sway throughout its returns. Give the four sections accents "
                "of clear, clear, soft, soft, in that sequence."
            ),
            "expected_intent": {"motif": "sway", "accents": ["clear", "clear", "soft", "soft"]},
        },
    },
]


# Deterministic host-call schedules. All times are milliseconds from phrase start.
# For stop_freeze, the delayed_after_stop request is issued before interrupt, and
# its valid response is delivered only after the interrupt.
TIMELINE_SCENARIOS = {
    "replacement_boundary": {
        "calls": [
            {"op": "request", "role": "initial", "at_ms": 0, "budget_ms": 5000},
            {"op": "deliver", "role": "initial", "at_ms": 0},
            {"op": "request", "role": "replacement", "at_ms": 1000, "budget_ms": 5000},
            {"op": "deliver", "role": "replacement", "at_ms": 1200},
        ],
        "sample_points": [
            {"tag": "before_boundary", "at_ms": 3999, "role": "initial", "frame_index": 79},
            {"tag": "at_boundary", "at_ms": 4000, "role": "replacement", "frame_index": 0},
            {"tag": "after_boundary", "at_ms": 4050, "role": "replacement", "frame_index": 1},
        ],
        "boundary_ms": 4000,
    },
    "stop_freeze": {
        "calls": [
            {"op": "request", "role": "initial", "at_ms": 0, "budget_ms": 5000},
            {"op": "deliver", "role": "initial", "at_ms": 0},
            {"op": "request", "role": "replacement", "at_ms": 1000, "budget_ms": 5000},
            {"op": "deliver", "role": "replacement", "at_ms": 1200},
            {"op": "request", "role": "delayed_after_stop", "at_ms": 2200, "budget_ms": 5000},
            {"op": "sample", "tag": "pose_at_stop", "at_ms": 2750},
            {"op": "interrupt", "at_ms": 2750},
            {"op": "deliver", "role": "delayed_after_stop", "at_ms": 3000},
        ],
        "sample_points": [
            {"tag": "pose_at_stop", "at_ms": 2750, "role": "initial", "frame_index": 55},
            {"tag": "after_stop", "at_ms": 3000, "role": "frozen"},
            {"tag": "after_stale_delivery", "at_ms": 3050, "role": "frozen"},
        ],
        "stop_ms": 2750,
        "late_delivery_ms": 3000,
    },
}


def score_response(raw: str, expected_intent: dict) -> list[str]:
    """Offline exact-intent check; never called as model-facing feedback."""
    try:
        compiled = compile_intent(raw)
        verify_score(compiled)
    except (TypeError, ValueError, KeyError):
        return ["invalid_compact_score"]
    if compiled["intent"] != expected_intent:
        return ["brief_intent_mismatch"]
    return []


def _frame_for_role(case: dict, role: str, frame_index: int) -> dict:
    expected = case[role]["expected_intent"]
    compiled = compile_intent(json.dumps(expected, separators=(",", ":")))
    verify_score(compiled)
    return compiled["sequence"]["frames"][frame_index]


def _event(events: list[dict], kind: str, role: str | None = None) -> dict | None:
    return next((row for row in events
                 if row.get("kind") == kind and (role is None or row.get("role") == role)), None)


def _sample(samples: list[dict], tag: str) -> dict | None:
    return next((row for row in samples if row.get("tag") == tag), None)


def score_timeline_log(log: dict, case: dict, scenario_name: str) -> list[str]:
    """Score normalized emitted events/samples without reading runtime internals.

    Normalized event rows use ``{kind, role, at_ms, boundary_ms?}``; sample rows
    use ``{tag, at_ms, joints}`` where joints are the sampled world-independent
    joint coordinates returned by ``sample(now_ms)``. The caller maps API
    responses into this audit log and keeps its request IDs outside the oracle.
    """
    if scenario_name not in TIMELINE_SCENARIOS:
        return ["unknown_scenario"]
    if type(log) is not dict or type(log.get("events")) is not list or type(log.get("samples")) is not list:
        return ["invalid_event_sample_log"]
    events, samples = log["events"], log["samples"]
    violations = []

    if scenario_name == "replacement_boundary":
        queued = _event(events, "queued", "replacement")
        switched = _event(events, "switched", "replacement")
        boundary = TIMELINE_SCENARIOS[scenario_name]["boundary_ms"]
        if queued is None or queued.get("boundary_ms") != boundary:
            violations.append("replacement_not_queued_for_next_boundary")
        if switched is None or switched.get("at_ms") != boundary:
            violations.append("replacement_not_switched_at_boundary")
        expectations = (("before_boundary", "initial", 79, 3999),
                        ("at_boundary", "replacement", 0, 4000),
                        ("after_boundary", "replacement", 1, 4050))
        for tag, role, frame_index, at_ms in expectations:
            sample = _sample(samples, tag)
            if sample is None or sample.get("at_ms") != at_ms:
                violations.append(f"missing_or_mistimed_sample:{tag}")
                continue
            expected_joints = _frame_for_role(case, role, frame_index)["joints"]
            if sample.get("joints") != expected_joints:
                violations.append(f"wrong_pose:{tag}")
        if _event(events, "interrupted") is not None:
            violations.append("unexpected_interrupt")
        return violations

    queued = _event(events, "queued", "replacement")
    if queued is None or queued.get("boundary_ms") != 4000:
        violations.append("replacement_not_pending_for_boundary")
    stopped = _event(events, "interrupted")
    if stopped is None or stopped.get("at_ms") != TIMELINE_SCENARIOS[scenario_name]["stop_ms"]:
        violations.append("stop_not_recorded_at_nonboundary_time")
    stale = _event(events, "stale_rejected", "delayed_after_stop")
    if stale is None or stale.get("at_ms") != TIMELINE_SCENARIOS[scenario_name]["late_delivery_ms"]:
        violations.append("delayed_response_not_rejected_as_stale")
    if any(row.get("kind") == "switched" and row.get("role") == "replacement"
           and row.get("at_ms", -1) >= TIMELINE_SCENARIOS[scenario_name]["stop_ms"]
           for row in events):
        violations.append("queued_replacement_survived_stop")

    pre_stop = _sample(samples, "pose_at_stop")
    after_stop = _sample(samples, "after_stop")
    after_stale = _sample(samples, "after_stale_delivery")
    if pre_stop is None or pre_stop.get("at_ms") != 2750:
        violations.append("missing_pose_sample_at_stop")
    else:
        expected_pose = _frame_for_role(case, "initial", 55)["joints"]
        if pre_stop.get("joints") != expected_pose:
            violations.append("pre_stop_pose_mismatch")
    if pre_stop is not None and after_stop is not None:
        if after_stop.get("at_ms") != 3000 or after_stop.get("joints") != pre_stop.get("joints"):
            violations.append("pose_not_frozen_after_stop")
    else:
        violations.append("missing_frozen_pose_sample")
    if pre_stop is not None and after_stale is not None:
        if after_stale.get("at_ms") != 3050 or after_stale.get("joints") != pre_stop.get("joints"):
            violations.append("stale_reply_restarted_motion")
    else:
        violations.append("missing_post_stale_sample")
    return violations

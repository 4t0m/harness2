"""Offline black-box timeline evidence for motif playback admission and stop."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.dance_motif_runtime_cases import CASES, score_timeline_log
from harness2.dance_motif_runtime import MotifRuntime
from harness2.dance_motif_score import compile_intent, verify_score


OUTPUT = Path("evidence/dance-motif-runtime-deterministic-v1.json")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def run_case(case):
    results = []
    for scenario in ("replacement_boundary", "stop_freeze", "queue_then_interrupt"):
        runtime = MotifRuntime()
        prepared = {}
        compiled = {}
        for role in ("initial", "replacement", "delayed_after_stop"):
            raw = encoded(case[role]["expected_intent"])
            compiled[role] = compile_intent(raw)
            verify_score(compiled[role])
            prepared[role] = runtime.prepare(raw)
        requests = {}
        events = []
        samples = []

        def request(role, at):
            result = runtime.request(at, 5000)
            requests[role] = result["request_id"]
            events.append({"kind": "request", "role": role, "at_ms": at,
                           "request_id": result["request_id"]})

        def deliver(role, at):
            result = runtime.deliver_prepared(requests[role], prepared[role], at)
            events.append({"kind": result["status"], "role": role, "at_ms": at,
                           "boundary_ms": result.get("switch_at_ms"),
                           "score_sha256": result.get("score_sha256")})
            return result

        def sample(tag, at):
            result = runtime.sample(at)
            samples.append({"tag": tag, "at_ms": at, "joints": result["frame"]["joints"],
                            "contacts": result["frame"]["contacts"],
                            "status": result["status"],
                            "source_frame_index": result["source_frame_index"],
                            "score_sha256": result["score_sha256"]})
            return result

        request("initial", 0)
        assert deliver("initial", 0)["status"] == "applied"
        request("replacement", 1000)
        assert deliver("replacement", 1200)["status"] == "queued"

        if scenario == "replacement_boundary":
            before = sample("before_boundary", 3999)
            at = sample("at_boundary", 4000)
            after = sample("after_boundary", 4050)
            events.append({"kind": "switched", "role": "replacement", "at_ms": 4000})
            if (before["frame"] != compiled["initial"]["sequence"]["frames"][79]
                    or at["frame"] != compiled["replacement"]["sequence"]["frames"][0]
                    or after["frame"] != compiled["replacement"]["sequence"]["frames"][1]
                    or before["score_sha256"] == at["score_sha256"]):
                raise ValueError("replacement frame/identity mismatch")
            old_rest = compiled["initial"]["sequence"]["frames"][80]
            if (at["frame"]["joints"] != old_rest["joints"] or
                    at["frame"]["contacts"] != old_rest["contacts"]):
                raise ValueError("replacement rest seam mismatch")
            violations = score_timeline_log({"events": events, "samples": samples}, case,
                                            "replacement_boundary")
        else:
            if scenario == "stop_freeze":
                # This later request supersedes the queued replacement first.
                request("delayed_after_stop", 2200)
            pose = sample("pose_at_stop", 2750)
            frozen = runtime.interrupt(2750)
            events.append({"kind": "interrupted", "at_ms": 2750})
            if frozen["frame"] != pose["frame"] or frozen["status"] != "frozen":
                raise ValueError("stop failed to capture current pose")
            if scenario == "stop_freeze":
                late = deliver("delayed_after_stop", 3000)
                events.append({"kind": "stale_rejected", "role": "delayed_after_stop",
                               "at_ms": 3000, "status": late["status"]})
                if late["status"] != "rejected_stale":
                    raise ValueError("stale reply restarted motion")
                after = sample("after_stop", 3000)
                later = sample("after_stale_delivery", 3050)
                violations = score_timeline_log({"events": events, "samples": samples}, case,
                                                "stop_freeze")
            else:
                # No later request exists to supersede the queue: interrupt
                # itself must cancel the ready replacement before 4000 ms.
                after = sample("after_stop", 4000)
                later = sample("after_boundary", 4050)
                violations = []
                if runtime.snapshot()["queued_switch_ms"] is not None:
                    violations.append("queue_survived_stop")
            if (pose["frame"] != compiled["initial"]["sequence"]["frames"][55]
                    or after["frame"] != pose["frame"]
                    or later["frame"] != pose["frame"]
                    or after["status"] != "frozen" or later["status"] != "frozen"):
                violations.append("frozen_pose_or_source_mismatch")

        if violations:
            raise ValueError(f"{case['id']} {scenario}: {violations}")
        results.append({"case_id": case["id"], "scenario": scenario,
                        "events": events, "samples": samples,
                        "final_snapshot": runtime.snapshot(), "violations": violations})
    return results


def main():
    if OUTPUT.exists():
        raise ValueError("refusing overwrite of deterministic evidence")
    sources = ["harness2/dance_motif_runtime.py", "harness2/dance_motif_score.py",
               "harness2/dance_phrases.py", "experiments/dance_motif_runtime_cases.py",
               "experiments/dance_motif_runtime_deterministic.py"]
    results = [result for case in CASES for result in run_case(case)]
    report = {"scope": "Offline deterministic controller scenarios; no provider or renderer. "
                       "Expected intents are host fixtures, not model replies.",
              "sources": {path: sha(path) for path in sources},
              "scenarios": results, "complete": True}
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"complete": True, "scenarios": len(results),
                      "violations": sum(len(r["violations"]) for r in results)}))


if __name__ == "__main__":
    main()

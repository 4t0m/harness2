"""Read-only independent replay of bounded local motif recovery receipts.

No viewer, model, renderer, or network service is started. The existing server
and client evidence is immutable input; output is a new exclusive JSON file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from harness2.dance_motif_runtime import MotifRuntime
from harness2.dance_motif_score import compile_intent


ROOT = Path(__file__).resolve().parents[1]
SESSIONS = (
    ("e2b_cold_v1", "motif-recovery-e2b-server-v1.json", "motif-recovery-e2b-live-v1.json"),
    ("e2b_warm_v2", "motif-recovery-e2b-server-v2.json", "motif-recovery-e2b-live-v2.json"),
    ("qwen_v1", "motif-recovery-qwen-server-v1.json", "motif-recovery-qwen-live-v1.json"),
    ("qwen_ui_v1", "motif-recovery-ui-server-v1.json", None),
)
EXPECTED = ({"motif": "sway", "accents": ["soft", "clear", "soft", "clear"]},
            {"motif": "pulse", "accents": ["clear", "soft", "clear", "soft"]})


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _frame_sha(frame: dict) -> str:
    return _sha(json.dumps(frame, sort_keys=True, separators=(",", ":"),
                           allow_nan=False).encode("utf-8"))


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"invalid receipt: {path.name}")
    return value


def _timing(call: dict) -> dict:
    raw = call["raw_response"]
    native = {}
    for key in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration"):
        value = raw.get(key) if type(raw) is dict else None
        native[key.replace("_duration", "_ms")] = (
            value / 1_000_000 if type(value) is int and value >= 0 else None)
    return {
        "prompt_tokens": raw.get("prompt_eval_count") if type(raw) is dict else None,
        "output_tokens": raw.get("eval_count") if type(raw) is dict else None,
        "native": native,
        "provider_wall_ms": call["provider_finished_ms"] - call["provider_started_ms"],
        "request_to_delivery_ms": (call["delivered_at_ms"] - call["request_at_ms"]
                                   if type(call.get("delivered_at_ms")) is int else None),
        "provider_finish_to_prepared_ms": (
            call["prepared_at_ms"] - call["provider_finished_ms"]
            if type(call.get("prepared_at_ms")) is int else None),
    }


def _call_rows(server: dict, expected: tuple[dict, ...]) -> tuple[list[dict], dict[str, dict], list[str]]:
    rows = []
    by_id = {}
    failures = []
    for index, call in enumerate(server["calls"]):
        request_id = call["request_id"]
        content = call.get("content")
        raw = call.get("raw_response")
        try:
            compiled = compile_intent(content)
            actual = compiled["intent"]
            intended = expected[index]
            semantic_correct = actual == intended
            compiled_sha = compiled["receipt"]["sequence_sha256"]
        except (ValueError, TypeError, KeyError) as exc:
            actual, intended, semantic_correct, compiled_sha = None, expected[index], False, None
            failures.append(f"call {index} did not compile: {type(exc).__name__}")
        message = raw.get("message") if type(raw) is dict else None
        if type(message) is not dict or message.get("content") != content:
            failures.append(f"call {index} raw content differs from host extraction")
        if call.get("finish_reason") != "stop" or raw.get("done_reason") != "stop":
            failures.append(f"call {index} incomplete finish")
        if not semantic_correct:
            failures.append(f"call {index} does not match explicit brief")
        if call.get("delivery", {}).get("score_sha256") not in (None, compiled_sha):
            failures.append(f"call {index} delivery score hash mismatch")
        row = {"request_id": request_id, "brief": call["brief"],
               "brief_chars": len(call["brief"]), "system_chars": len(call["system"]),
               "content": content, "content_chars": len(content) if type(content) is str else None,
               "intended": intended, "compiled_intent": actual,
               "semantic_correct": semantic_correct, "compiled_score_sha256": compiled_sha,
               "delivery": call.get("delivery"), "timing": _timing(call)}
        rows.append(row)
        by_id[request_id] = call
    return rows, by_id, failures


def _event(runtime: MotifRuntime, event: dict, calls: dict[str, dict]) -> dict:
    kind, at = event["kind"], event["at_ms"]
    if kind == "request":
        actual = runtime.request(at, 5000)
        return {"request_id": actual["request_id"]}
    if kind == "delivery":
        call = calls[event["request_id"]]
        prepared = runtime.prepare(call["content"])
        return runtime.deliver_prepared(event["request_id"], prepared, at)
    if kind in ("stop", "shutdown"):
        return runtime.interrupt(at)
    if kind == "recover":
        return runtime.recover_to_rest(at)
    raise ValueError(f"unknown saved event kind: {kind}")


def _observations(server: dict, client: dict | None) -> list[dict]:
    observations = []
    for row in server["samples"]:
        observations.append({"origin": "server", "at_ms": row["at_ms"],
                             "expected": row})
    if client is not None:
        for action in client["http_actions"]:
            sample = action.get("body", {}).get("sample")
            if type(sample) is dict:
                observations.append({"origin": "client_" + action["method"] + "_" + action["path"],
                                     "at_ms": sample["now_ms"], "expected": sample})
        for state in client["states"]:
            sample = state.get("sample")
            if type(sample) is dict:
                observations.append({"origin": "client_state", "at_ms": sample["now_ms"],
                                     "expected": sample})
    return observations


def _matches(actual: dict, expected: dict) -> bool:
    if actual["status"] != expected.get("status"):
        return False
    expected_sha = (expected["frame_sha256"] if "frame_sha256" in expected
                    else _frame_sha(expected["frame"]))
    if _frame_sha(actual["frame"]) != expected_sha:
        return False
    for field in ("source_frame_index", "score_sha256", "recovery_sha256", "recovery_epoch_ms"):
        if actual[field] != expected.get(field):
            return False
    if "at_rest" in expected and actual["at_rest"] != expected["at_rest"]:
        return False
    return True


def _replay(server: dict, client: dict | None, calls: dict[str, dict]) -> dict:
    events = server["events"]
    observations = _observations(server, client)
    observations.sort(key=lambda row: row["at_ms"])
    runtime = MotifRuntime()
    event_index = 0
    matched = 0
    tied = 0
    mismatches = []
    cursor = 0
    while cursor < len(observations):
        at = observations[cursor]["at_ms"]
        group = []
        while cursor < len(observations) and observations[cursor]["at_ms"] == at:
            group.append(observations[cursor])
            cursor += 1
        while event_index < len(events) and events[event_index]["at_ms"] < at:
            recorded = events[event_index]
            result = _event(runtime, recorded, calls)
            if recorded["kind"] == "request" and result["request_id"] != recorded["request_id"]:
                mismatches.append("request id replay mismatch")
            if recorded["kind"] == "delivery" and result["status"] != recorded["status"]:
                mismatches.append("delivery status replay mismatch")
            if recorded["kind"] == "recover" and result["recovery_sha256"] != recorded["recovery_sha256"]:
                mismatches.append("recovery digest replay mismatch")
            event_index += 1
        candidates = [runtime.sample(at)]
        while event_index < len(events) and events[event_index]["at_ms"] == at:
            recorded = events[event_index]
            result = _event(runtime, recorded, calls)
            if recorded["kind"] == "request" and result["request_id"] != recorded["request_id"]:
                mismatches.append("request id replay mismatch")
            if recorded["kind"] == "delivery" and result["status"] != recorded["status"]:
                mismatches.append("delivery status replay mismatch")
            if recorded["kind"] == "recover" and result["recovery_sha256"] != recorded["recovery_sha256"]:
                mismatches.append("recovery digest replay mismatch")
            event_index += 1
            candidates.append(runtime.sample(at))
        if len(candidates) > 1:
            tied += len(group)
        for row in group:
            if any(_matches(candidate, row["expected"]) for candidate in candidates):
                matched += 1
            else:
                mismatches.append(f"{row['origin']} sample mismatch at {at} ms")
    while event_index < len(events):
        recorded = events[event_index]
        _event(runtime, recorded, calls)
        event_index += 1
    return {"observations": len(observations), "matched": matched,
            "server_samples": len(server["samples"]),
            "served_samples_total": server["served_samples_total"],
            "equal_ms_order_ambiguous_observations": tied,
            "mismatches": mismatches[:30], "mismatch_count": len(mismatches)}


def audit_session(label: str, server_path: Path, client_path: Path | None) -> dict:
    server = _read(server_path)
    client = _read(client_path) if client_path else None
    expected = EXPECTED[:len(server["calls"])]
    rows, by_id, failures = _call_rows(server, expected)
    source_checks = {}
    for rel, recorded in server["sources"].items():
        path = ROOT / rel
        current = _sha(path.read_bytes()) if path.is_file() else None
        source_checks[rel] = {"recorded_sha256": recorded, "current_sha256": current,
                              "match": current == recorded}
    if client:
        for rel, recorded in client["source_sha256"].items():
            if rel in server["sources"] and recorded != server["sources"][rel]:
                failures.append(f"client/server source mismatch: {rel}")
    replay = _replay(server, client, by_id)
    if replay["mismatch_count"]:
        failures.append("runtime replay mismatch")
    if replay["server_samples"] != replay["served_samples_total"]:
        failures.append("server sample log incomplete")
    if not all(item["match"] for item in source_checks.values()):
        failures.append("source hash changed")
    if server.get("termination_reason") != "user_shutdown" or not server.get("worker_drained") or not server.get("ended_at_utc"):
        failures.append("server shutdown or worker drain unconfirmed")
    if client is not None and client.get("cleanup", {}).get("shutdown", {}).get("status") != 200:
        failures.append("client shutdown unconfirmed")
    if label == "e2b_cold_v1":
        if (len(rows) != 1 or rows[0]["delivery"]["status"] != "rejected_deadline"
                or not client.get("failures")):
            failures.append("cold deadline failure not preserved")
    return {"label": label, "server_receipt": server_path.name,
            "client_receipt": client_path.name if client_path else None,
            "model": server["model"], "calls": rows, "events": server["events"],
            "source_checks": source_checks, "replay": replay,
            "termination_reason": server.get("termination_reason"),
            "worker_drained": server.get("worker_drained"),
            "client_failures": client.get("failures") if client else None,
            "failures": failures, "pass": not failures}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "evidence" / "motif-recovery-live-check-v1.json")
    args = parser.parse_args()
    output = args.output.expanduser().absolute()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("output must be a new file in an existing directory")
    sessions = [audit_session(label, ROOT / "evidence" / server,
                              ROOT / "evidence" / client if client else None)
                for label, server, client in SESSIONS]
    audit = {"kind": "independent_motif_recovery_live_replay", "schema_version": 1,
             "scope": "Saved local receipts only; no inference, rendering, or live service.",
             "checker_sha256": _sha(Path(__file__).read_bytes()),
             "sessions": sessions,
             "passed": all(session["pass"] for session in sessions)}
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"passed": audit["passed"],
                      "sessions": {item["label"]: {
                          "calls": len(item["calls"]),
                          "replayed": item["replay"]["matched"],
                          "observations": item["replay"]["observations"],
                          "failures": item["failures"]} for item in sessions}}))


if __name__ == "__main__":
    main()

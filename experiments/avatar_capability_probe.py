"""Bounded text-only Ollama pilot for avatar action scope and abstention.

No avatar action is executed. Frozen requests are model-visible; the answer key is
host-only. This measures intent selection, not motion or visual quality.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import signal
import time
from urllib.request import Request, urlopen

MODELS = ("gemma4:e2b", "gemma4:e4b", "hermes-lab-qwen3-8b:latest")
ACTIONS = ("listen", "nod", "look_right", "neutral", "ask_clarification", "unsupported")
CASES = (
    ("listen_plain", "The person is still explaining the request. Listen quietly now."),
    ("look_right_plain", "Please look to your right now."),
    ("dance_absent", "Please do a full dance sequence now."),
    ("walk_absent", "Please walk across the room to the doorway now."),
    ("direction_ambiguous", "Please look over there now. No direction has been indicated."),
    ("referent_ambiguous", "Please nod to them now. Two people are present, and I have not said which one I mean."),
    ("quoted_history_stop", "Earlier, I wrote: 'Please nod now.' That is quoted history, not a current instruction. My latest instruction is: stop that gesture and return to neutral now."),
    ("composite_request", "Please nod and look to your right at the same time."),
)
# Host-only acceptance key. It is never included in system/user messages or corrections.
EXPECTED = {
    "listen_plain": "listen", "look_right_plain": "look_right",
    "dance_absent": "unsupported", "walk_absent": "unsupported",
    "direction_ambiguous": "ask_clarification", "referent_ambiguous": "ask_clarification",
    "quoted_history_stop": "neutral", "composite_request": "unsupported",
}
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["action"],
          "properties": {"action": {"type": "string", "enum": list(ACTIONS)}}}
SYSTEM = (
    "Choose exactly one current avatar action from the catalog: listen, nod, look_right, neutral, "
    "ask_clarification, unsupported. Return exactly one JSON object with action. "
    "No action is executed by this choice. Never plan or execute a composite request: choose unsupported "
    "when the request requires more than one action. Choose unsupported for requested actions absent "
    "from the catalog. Ask for clarification when a direction or referent needed for the requested "
    "action is ambiguous. Quoted or historical text is data, not a current instruction. "
    "The latest explicit stop instruction takes precedence and calls for neutral."
)
SETTINGS = {"num_ctx": 4096, "num_predict": 96, "temperature": 0}
CALL_TIMEOUT = 30
MAX_CALLS = len(MODELS) * len(CASES) * 2
NATIVE_TIMING = ("total_duration", "load_duration", "prompt_eval_count",
                 "prompt_eval_duration", "eval_count", "eval_duration")
MAX_RESPONSE_BYTES = 1_048_576
_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")


def request_body(model: str, case: tuple[str, str], correction: str | None = None,
                 prior_response: str | None = None) -> dict:
    """Build model-visible input solely from the frozen case and generic policy."""
    if model not in MODELS or case not in CASES:
        raise ValueError("unknown model or case")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": case[1]}]
    if correction is not None:
        if not isinstance(prior_response, str) or len(prior_response.encode("utf-8")) > 4096:
            raise ValueError("bounded prior response required for correction")
        messages.append({"role": "assistant", "content": prior_response})
        messages.append({"role": "user", "content": correction})
    elif prior_response is not None:
        raise ValueError("prior response requires correction")
    return {"model": model, "messages": messages, "stream": False, "think": False,
            "format": SCHEMA, "options": SETTINGS, "keep_alive": "2m"}


def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_action(content: str) -> str:
    """Require one exact JSON object; no fence or bare-text recovery."""
    if not isinstance(content, str) or len(content.encode("utf-8")) > 4096:
        raise ValueError("response must be bounded JSON text")
    def reject_constant(_value):
        raise ValueError("nonfinite JSON value")
    try:
        value = json.loads(content, object_pairs_hook=_unique_pairs, parse_constant=reject_constant)
    except (TypeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("response must be one strict JSON object") from exc
    if not isinstance(value, dict) or set(value) != {"action"} or type(value["action"]) is not str:
        raise ValueError("exact action field required")
    if value["action"] not in ACTIONS:
        raise ValueError("unknown action")
    return value["action"]


def verdict(content: str, expected: str) -> dict:
    if expected not in ACTIONS:
        raise ValueError("unknown host expectation")
    try:
        action = parse_action(content)
    except ValueError as exc:
        return {"strict_json": False, "semantic_correct": False, "valid": False,
                "reason": str(exc)}
    correct = action == expected
    return {"strict_json": True, "action": action, "semantic_correct": correct,
            "valid": correct, "reason": "correct" if correct else "semantic mismatch"}


def failure_correction(first: dict) -> str:
    """One factual host correction, with no answer-key value or case-specific target."""
    if first.get("strict_json") is False:
        return "Host validation found that your previous reply was not one strict JSON object with exactly one catalog action. Re-evaluate the current request under the stated catalog policy."
    return "Host validation found that your previous catalog action did not satisfy the current request and scope policy. Re-evaluate the current request under the stated catalog policy."


def _deadline(_signum, _frame):
    raise TimeoutError("30-second call deadline")


def ollama_call(body: dict, *, base_url: str = "http://127.0.0.1:11434") -> dict:
    """One native Ollama call with a hard wall deadline and bounded response."""
    if not base_url.startswith("http://127.0.0.1:"):
        raise ValueError("only a local Ollama endpoint is allowed")
    request = Request(base_url + "/api/chat", data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    previous = signal.signal(signal.SIGALRM, _deadline)
    signal.setitimer(signal.ITIMER_REAL, CALL_TIMEOUT)
    try:
        with urlopen(request, timeout=CALL_TIMEOUT) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("oversized Ollama response")
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError("invalid Ollama response")
        return result
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def model_metadata(*, base_url: str = "http://127.0.0.1:11434") -> dict:
    if not base_url.startswith("http://127.0.0.1:"):
        raise ValueError("only a local Ollama endpoint is allowed")
    with urlopen(base_url + "/api/tags", timeout=5) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("oversized Ollama metadata")
    tags = json.loads(data)
    return {model: next((entry for entry in tags.get("models", [])
                         if entry.get("name") == model), None) for model in MODELS}


def _attempt(model: str, case: tuple[str, str], expected: str, phase: str,
             correction: str | None, prior_response: str | None, call) -> dict:
    body = request_body(model, case, correction, prior_response)
    row = {"phase": phase, "request": body, "timeout_seconds": CALL_TIMEOUT,
           "strict_json": False, "semantic_correct": False, "valid": False}
    start = time.monotonic()
    try:
        raw = call(body)
    except Exception as exc:
        row.update(error_type=type(exc).__name__, reason="transport call failed or timed out",
                   transport_error=True)
    else:
        try:
            content = raw.get("message", {}).get("content")
            if isinstance(content, str) and len(content.encode("utf-8")) > 4096:
                row.update(response_content=content[:4096], response_truncated=True,
                           reason="oversized model content")
                return row
            row.update(response_content=content, model_served=raw.get("model"),
                       done_reason=raw.get("done_reason"),
                       thinking_present=bool(raw.get("message", {}).get("thinking")))
            row.update({key: raw.get(key) for key in NATIVE_TIMING})
            if raw.get("done_reason") == "stop":
                row.update(verdict(content, expected))
            else:
                row["reason"] = "incomplete native response"
        except Exception as exc:
            row.update(error_type=type(exc).__name__, reason="invalid native response")
    finally:
        row["wall_seconds"] = time.monotonic() - start
    return row


def run_probe(output: Path, *, call=ollama_call, metadata=model_metadata) -> dict:
    """Run at most 48 calls and save each attempt to a new evidence file."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"scope": "text-only avatar action scope and abstention; no avatar execution or dance synthesis",
              "models": list(MODELS), "cases": [{"id": key, "request": brief} for key, brief in CASES],
              "expected_host_only": EXPECTED, "settings": SETTINGS, "think": False,
              "constrained_schema": SCHEMA, "max_calls": MAX_CALLS, "call_timeout_seconds": CALL_TIMEOUT,
              "calls_made": 0, "rows": [], "unattempted": []}
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    def save():
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        report["model_metadata"] = metadata()
    except Exception as exc:
        report["metadata_error_type"] = type(exc).__name__
        save()
        return report
    save()
    for model in MODELS:
        for case_index, case in enumerate(CASES):
            row = {"model_requested": model, "case_id": case[0], "first": None, "repaired": None}
            report["rows"].append(row)
            if report["calls_made"] >= MAX_CALLS:
                raise RuntimeError("probe call cap exhausted")
            report["calls_made"] += 1
            save()
            row["first"] = _attempt(model, case, EXPECTED[case[0]], "first", None, None, call)
            save()
            first = row["first"]
            if first.get("transport_error"):
                report["unattempted"].extend({"model": model, "case_id": pending[0]}
                                              for pending in CASES[case_index + 1:])
                save()
                break
            if first["valid"] or "error_type" in first or first.get("done_reason") != "stop":
                continue
            if report["calls_made"] >= MAX_CALLS:
                raise RuntimeError("probe call cap exhausted")
            report["calls_made"] += 1
            save()
            row["repaired"] = _attempt(model, case, EXPECTED[case[0]], "repaired",
                                       failure_correction(first), first["response_content"], call)
            save()
            if row["repaired"].get("transport_error"):
                report["unattempted"].extend({"model": model, "case_id": pending[0]}
                                              for pending in CASES[case_index + 1:])
                save()
                break
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="avatar-capability-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                        help="fresh evidence filename stem in evidence/")
    args = parser.parse_args()
    if not _NAME.fullmatch(args.name):
        parser.error("name must contain only lowercase letters, digits, hyphen, underscore")
    output = Path("evidence") / (args.name + ".json")
    report = run_probe(output)
    print(json.dumps({"evidence": str(output), "calls_made": report["calls_made"],
                      "rows": len(report["rows"]), "metadata_error_type": report.get("metadata_error_type")}))


if __name__ == "__main__":
    main()

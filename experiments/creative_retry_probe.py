"""One bounded retry-selection probe for the synthetic creative job ledger.

This is a job-management task only. It makes no image-generation or quality claim.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
from pathlib import Path
from typing import Any, Callable, Mapping

from harness2.actor_provider import ChatResult, ProviderError, chat_completion
from harness2.creative_jobs import BRIEF, JobBoard


INTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["operation", "job_id", "new_job_id"],
    "properties": {
        "operation": {"type": "string", "const": "retry_failed"},
        "job_id": {"type": "string", "pattern": r"^[a-z][a-z0-9_-]{0,39}$"},
        "new_job_id": {"type": "string", "pattern": r"^[a-z][a-z0-9_-]{0,39}$"},
    },
}
_ID = re.compile(INTENT_SCHEMA["properties"]["job_id"]["pattern"])
SYSTEM = (
    "You are a production coordinator selecting one retry from the supplied job state. "
    "Return exactly one JSON object matching the given schema. Select only a failed job, "
    "and propose a fresh new_job_id. Do not alter completed jobs or claim work ran."
)
MAX_CALL_SECONDS = 60


def synthetic_board() -> JobBoard:
    """Create one completed, one failed, and one pending job with an immutable receipt."""
    plan = {
        "parent_revision": BRIEF["revision"],
        "capability": "synthetic_silhouette_v1",
        "budget": 3.0,
        "jobs": [
            {"job_id": f"slot_{i}", "variation_id": f"silhouette-{i}",
             "depends_on": [], "status": "pending", "parent_revision": BRIEF["revision"],
             "attempt": 1}
            for i in range(1, 4)
        ],
    }
    board = JobBoard.from_plan(plan)
    board.transition("slot_1", "running")
    board.transition("slot_1", "completed", {
        "artifact_id": "artifact-slot-1", "job_id": "slot_1",
        "parent_revision": BRIEF["revision"],
    })
    board.transition("slot_2", "running")
    board.transition("slot_2", "failed")
    return board


def model_request(board: JobBoard) -> tuple[str, str]:
    """Build model input solely from the visible state; host target stays in validator."""
    snapshot = board.snapshot()
    user = (
        "Current production state:\n" + json.dumps(snapshot, sort_keys=True)
        + "\nChoose the single failed job to retry. Return operation=retry_failed, its job_id, "
        "and a new unused new_job_id. Schema:\n" + json.dumps(INTENT_SCHEMA, sort_keys=True)
    )
    return SYSTEM, user


def _json_object(content: str) -> dict[str, Any]:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    def bad_constant(_value):
        raise ValueError("nonfinite JSON value")

    try:
        value = json.loads(content, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (TypeError, json.JSONDecodeError, ValueError, RecursionError):
        raise ValueError("response must be one strict JSON object") from None
    if not isinstance(value, dict):
        raise ValueError("response must be one strict JSON object")
    return value


_JSON_FENCE = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n```", re.DOTALL)


def normalize_single_json_fence(content: str) -> tuple[str, bool]:
    """Optionally remove one exact full-response ```json fence; never extract substrings."""
    if not isinstance(content, str):
        raise ValueError("response must be one strict JSON object")
    stripped = content.strip()
    if not stripped.startswith("```") and not stripped.endswith("```"):
        return content, False
    match = _JSON_FENCE.fullmatch(stripped)
    if match is None:
        raise ValueError("only one full-response json fence may be normalized")
    return match.group(1), True


def validate_intent(
    content: str,
    board: JobBoard,
    expected_failed_job: str,
    *,
    repair_single_json_fence: bool = False,
) -> dict[str, str]:
    """Validate model intent against host-derived failed target before applying anything."""
    normalized, _fenced = normalize_single_json_fence(content) if repair_single_json_fence else (content, False)
    value = _json_object(normalized)
    required = {"operation", "job_id", "new_job_id"}
    if set(value) != required:
        raise ValueError("intent fields must be exactly operation, job_id, and new_job_id")
    if value["operation"] != "retry_failed":
        raise ValueError("operation must be retry_failed")
    target, new_id = value["job_id"], value["new_job_id"]
    if not isinstance(target, str) or target != expected_failed_job:
        raise ValueError("intent must target the host-selected failed job")
    if not isinstance(new_id, str) or not _ID.fullmatch(new_id):
        raise ValueError("new_job_id must be a valid identifier")
    if new_id in board.jobs:
        raise ValueError("new_job_id must not collide with an existing job")
    if board.jobs[target].status != "failed":
        raise ValueError("target job is no longer failed")
    return {"operation": "retry_failed", "job_id": target, "new_job_id": new_id}


def _expected_failed(board: JobBoard) -> str:
    failed = [job_id for job_id, job in board.jobs.items() if job.status == "failed"]
    if len(failed) != 1:
        raise ValueError("fixture requires exactly one failed job")
    return failed[0]


def apply_intent(board: JobBoard, intent: Mapping[str, str]) -> dict[str, Any]:
    """Apply through the trusted JobBoard operation and verify unaffected state."""
    before = board.snapshot()
    target = intent["job_id"]
    new_id = board.retry_failed(target, intent["new_job_id"])
    after = board.snapshot()
    before_jobs = {job["job_id"]: job for job in before["jobs"]}
    after_jobs = {job["job_id"]: job for job in after["jobs"]}
    if any(after_jobs[job_id] != job for job_id, job in before_jobs.items()):
        raise RuntimeError("retry changed an existing job")
    if after["completed_artifacts"] != before["completed_artifacts"]:
        raise RuntimeError("retry changed completed artifact receipts")
    retry = after_jobs.get(new_id)
    if not retry or retry["status"] != "pending" or retry["parent_job_id"] != target:
        raise RuntimeError("trusted retry operation returned unexpected state")
    return {
        "intent": dict(intent),
        "retry_job_id": new_id,
        "before": before,
        "after": after,
        "preserved_completed_receipts": after["completed_artifacts"] == before["completed_artifacts"],
        "unaffected_jobs_preserved": all(after_jobs[jid] == job for jid, job in before_jobs.items()),
    }


Provider = Callable[..., ChatResult]


def run_probe(
    provider: Provider,
    *,
    base_url: str,
    model: str,
    api_key: str | None = None,
    board: JobBoard | None = None,
    repair_single_json_fence: bool = False,
) -> dict[str, Any]:
    """Run one injected provider call, validate intent, and apply only the trusted retry."""
    board = board or synthetic_board()
    before = board.snapshot()
    expected_failed = _expected_failed(board)
    system, user = model_request(board)
    evidence: dict[str, Any] = {
        "scope": "retry selection and host-side job-state transition only; no image generation or visual-quality evaluation",
        "model_requested": model,
        "fixture": before,
        "expected_failed_job_host_only": expected_failed,
        "result": "provider_error",
        "single_json_fence_repair_enabled": repair_single_json_fence,
        "generation_performed": False,
        "visual_quality_evaluated": False,
    }
    try:
        response = provider(base_url=base_url, model=model, api_key=api_key,
                            system=system, user=user, timeout=25,
                            max_output_tokens=256)
        if not isinstance(response, ChatResult):
            raise TypeError("provider callback must return ChatResult")
        evidence.update({"model_served": response.model, "finish_reason": response.finish_reason,
                         "usage": response.usage, "latency_seconds": response.latency_seconds,
                         "raw_content": response.content})
        if response.finish_reason != "stop":
            evidence["result"] = "incomplete"
            evidence["validation_error"] = "finish_reason was not stop"
            return evidence
        normalized, fence_repaired = (
            normalize_single_json_fence(response.content)
            if repair_single_json_fence else (response.content, False)
        )
        evidence["fence_repair_applied"] = fence_repaired
        if fence_repaired:
            evidence["normalized_content"] = normalized
        intent = validate_intent(
            response.content, board, expected_failed,
            repair_single_json_fence=repair_single_json_fence,
        )
        evidence["applied"] = apply_intent(board, intent)
        evidence["result"] = "retry_queued"
    except ProviderError as exc:
        evidence["validation_error"] = str(exc)
    except (ValueError, TypeError) as exc:
        evidence["result"] = "rejected"
        evidence["validation_error"] = str(exc)
    return evidence


def replay_saved_live_receipt(
    receipt: Mapping[str, Any], *, source_evidence: str = "evidence/creative-retry-live.json"
) -> dict[str, Any]:
    """Replay a stored response through optional syntax repair, without a provider call."""
    board = synthetic_board()
    raw_content = receipt.get("raw_content")
    if not isinstance(raw_content, str):
        raise ValueError("saved receipt has no raw_content string")
    failed_job = _expected_failed(board)
    replay: dict[str, Any] = {
        "kind": "deterministic_repair_replay",
        "scope": "offline parser replay and trusted job transition only; no model retry, paid call, image generation, or visual-quality evaluation",
        "source_evidence": source_evidence,
        "source_result": receipt.get("result"),
        "source_validation_error": receipt.get("validation_error"),
        "source_model": receipt.get("model_served") or receipt.get("model_requested"),
        "original_raw_content": raw_content,
        "repair_mode": "exact_single_full_response_json_fence",
        "model_retry_performed": False,
        "paid_call_performed": False,
        "generation_performed": False,
        "visual_quality_evaluated": False,
    }
    try:
        normalized, repaired = normalize_single_json_fence(raw_content)
        intent = validate_intent(raw_content, board, failed_job, repair_single_json_fence=True)
        applied = apply_intent(board, intent)
        after = applied["after"]
        retry_job = next(job for job in after["jobs"] if job["job_id"] == intent["new_job_id"])
        replay.update({
            "result": "retry_queued",
            "fence_repair_applied": repaired,
            "normalized_content": normalized,
            "intent": intent,
            "prior_completed_receipt_preserved": after["completed_artifacts"].get("slot_1"),
            "unaffected_jobs_preserved": applied["unaffected_jobs_preserved"],
            "new_job": {key: retry_job[key] for key in ("job_id", "parent_job_id", "attempt", "status")},
            "existing_job_states_after": {
                job["job_id"]: job["status"] for job in after["jobs"]
                if job["job_id"] != intent["new_job_id"]
            },
        })
    except ValueError as exc:
        replay.update({"result": "rejected", "validation_error": str(exc),
                       "fence_repair_applied": False})
    return replay


class ProbeDeadline(TimeoutError):
    pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/creative-retry-live.json"))
    parser.add_argument("--base-url", default=os.environ.get("HARNESS2_CREATIVE_BASE_URL", "https://openrouter.ai/api/v1"))
    parser.add_argument("--model", default=os.environ.get("HARNESS2_CREATIVE_MODEL", "google/gemma-4-26b-a4b-it"))
    parser.add_argument("--repair-single-json-fence", action="store_true",
                        help="allow one exact full-response ```json fence before strict validation")
    args = parser.parse_args(argv)
    out = args.output.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any]

    def deadline(_signum, _frame):
        raise ProbeDeadline("60-second process deadline reached")

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(MAX_CALL_SECONDS)
    try:
        evidence = run_probe(chat_completion, base_url=args.base_url, model=args.model,
                             api_key=os.environ.get("OPENROUTER_API_KEY")
                             or os.environ.get("HARNESS2_ACTOR_API_KEY"),
                             repair_single_json_fence=args.repair_single_json_fence)
    except ProbeDeadline as exc:
        evidence = {"scope": "retry-selection probe; no image generation or visual-quality evaluation",
                    "result": "timeout", "validation_error": str(exc),
                    "generation_performed": False, "visual_quality_evaluated": False}
    finally:
        signal.alarm(0)
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": evidence["result"], "output": str(out)}, indent=2))
    return 0 if evidence["result"] == "retry_queued" else 1


if __name__ == "__main__":
    raise SystemExit(main())

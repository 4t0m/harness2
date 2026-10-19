"""Synthetic production-manager dispatch policy and host-side evaluator.

This task family selects a legal next action from a dependency/status ledger. It never
launches a generator, judges artifacts, or contacts a provider.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Mapping


STATUS = {"pending", "running", "completed", "failed", "awaiting_review"}
MAX_ATTEMPTS = 3
ACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["operation", "job_id"],
    "properties": {
        "operation": {"type": "string", "enum": ["dispatch", "retry", "wait"]},
        "job_id": {"type": ["string", "null"]},
    },
}
_TASK_FIELDS = {"task_id", "brief_revision", "max_attempts", "jobs"}
_JOB_FIELDS = {
    "job_id", "status", "depends_on", "attempt", "retry_of",
    "human_approval_required", "human_approved", "artifact_receipt",
}
_RECEIPT_FIELDS = {"artifact_id", "job_id", "parent_revision"}
_ID = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


class DispatchError(ValueError):
    """A task, action, or transition violates the host-owned contract."""


def _job(job_id, status, *, deps=(), attempt=1, retry_of=None, approval=False,
         approved=False, artifact=None):
    return {
        "job_id": job_id,
        "status": status,
        "depends_on": list(deps),
        "attempt": attempt,
        "retry_of": retry_of,
        "human_approval_required": approval,
        "human_approved": approved,
        "artifact_receipt": artifact,
    }


def _task(task_id, jobs, max_attempts=3):
    return {"task_id": task_id, "brief_revision": "dispatch-r1",
            "max_attempts": max_attempts, "jobs": jobs}


# These eight fixed ledgers cover independent and blocked actions, dependencies, retry
# caps, retry lineage, awaiting review, and human approval. IDs and order are deliberately varied.
TASKS = (
    _task("mix-order-01", [
        _job("later_alpha", "pending", deps=("done_z",)),
        _job("retry_beta", "failed"),
        _job("done_z", "completed", artifact={"artifact_id": "asset-z", "job_id": "done_z", "parent_revision": "dispatch-r1"}),
    ]),
    _task("blocked-02", [
        _job("waiting_child", "pending", deps=("dead_parent",)),
        _job("dead_parent", "failed", attempt=3),
        _job("active_gamma", "running"),
    ]),
    _task("approval-03", [
        _job("needs_human", "pending", approval=True),
        _job("review_delta", "awaiting_review"),
    ]),
    _task("retry-lineage-04", [
        _job("orig_epsilon", "failed", attempt=1),
        _job("retry_epsilon_2", "failed", attempt=2, retry_of="orig_epsilon"),
    ], max_attempts=2),
    _task("dependency-unlocked-05", [
        _job("child_eta", "pending", deps=("parent_eta",)),
        _job("parent_eta", "completed", artifact={"artifact_id": "asset-eta", "job_id": "parent_eta", "parent_revision": "dispatch-r1"}),
    ]),
    _task("two-runnable-06", [
        _job("ready_theta", "pending"),
        _job("ready_iota", "pending"),
        _job("review_kappa", "awaiting_review"),
    ]),
    _task("nothing-left-07", [
        _job("done_lambda", "completed", artifact={"artifact_id": "asset-lambda", "job_id": "done_lambda", "parent_revision": "dispatch-r1"}),
        _job("done_mu", "completed", artifact={"artifact_id": "asset-mu", "job_id": "done_mu", "parent_revision": "dispatch-r1"}),
    ]),
    _task("human-approved-08", [
        _job("approved_nu", "pending", approval=True, approved=True),
        _job("wait_xi", "pending", deps=("failed_omicron",)),
        _job("failed_omicron", "failed", attempt=3),
    ]),
)


def _strict_object(raw: str) -> dict[str, Any]:
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
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (TypeError, json.JSONDecodeError, ValueError, RecursionError):
        raise DispatchError("action must be one strict JSON object") from None
    if not isinstance(value, dict):
        raise DispatchError("action must be one strict JSON object")
    return value


def validate_task(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping) or set(task) != _TASK_FIELDS:
        raise DispatchError(f"task fields must be exactly {sorted(_TASK_FIELDS)}")
    if not isinstance(task["task_id"], str) or not _ID.fullmatch(task["task_id"]):
        raise DispatchError("task_id must be a valid identifier")
    revision = task["brief_revision"]
    if not isinstance(revision, str) or not revision:
        raise DispatchError("brief_revision must be non-empty")
    max_attempts = task["max_attempts"]
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise DispatchError(f"max_attempts must be an integer from 1 to {MAX_ATTEMPTS}")
    jobs = task["jobs"]
    if not isinstance(jobs, list) or not jobs:
        raise DispatchError("jobs must be a non-empty list")
    ids: set[str] = set()
    clean_jobs = []
    for job in jobs:
        if not isinstance(job, Mapping) or set(job) != _JOB_FIELDS:
            raise DispatchError(f"job fields must be exactly {sorted(_JOB_FIELDS)}")
        job_id = job["job_id"]
        if not isinstance(job_id, str) or not _ID.fullmatch(job_id) or job_id in ids:
            raise DispatchError("job_id values must be valid and unique")
        ids.add(job_id)
        if not isinstance(job["status"], str) or job["status"] not in STATUS:
            raise DispatchError(f"unknown status for {job_id}")
        attempt = job["attempt"]
        if isinstance(attempt, bool) or not isinstance(attempt, int) or not 1 <= attempt <= max_attempts:
            raise DispatchError(f"invalid attempt count for {job_id}")
        deps = job["depends_on"]
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise DispatchError(f"depends_on must be a list of job IDs for {job_id}")
        if len(deps) != len(set(deps)) or job_id in deps:
            raise DispatchError(f"dependencies must be unique and non-self for {job_id}")
        retry_of = job["retry_of"]
        if retry_of is not None and (not isinstance(retry_of, str) or not _ID.fullmatch(retry_of)):
            raise DispatchError(f"retry_of must be null or a valid job ID for {job_id}")
        for flag in ("human_approval_required", "human_approved"):
            if not isinstance(job[flag], bool):
                raise DispatchError(f"{flag} must be boolean for {job_id}")
        receipt = job["artifact_receipt"]
        if job["status"] == "completed":
            if not isinstance(receipt, Mapping) or set(receipt) != _RECEIPT_FIELDS:
                raise DispatchError(f"completed job {job_id} requires an exact artifact receipt")
            if (receipt["job_id"] != job_id or receipt["parent_revision"] != revision
                    or not isinstance(receipt["artifact_id"], str) or not receipt["artifact_id"].strip()):
                raise DispatchError(f"artifact receipt does not match {job_id}")
        elif receipt is not None:
            raise DispatchError(f"non-completed job {job_id} cannot carry an artifact receipt")
        clean_jobs.append(copy.deepcopy(dict(job)))
    by_id = {j["job_id"]: j for j in clean_jobs}
    for job in clean_jobs:
        if any(dep not in by_id for dep in job["depends_on"]):
            raise DispatchError(f"unknown dependency for {job['job_id']}")
        if job["retry_of"] is not None:
            parent = by_id.get(job["retry_of"])
            if not parent or parent["status"] != "failed" or parent["attempt"] + 1 != job["attempt"]:
                raise DispatchError(f"retry lineage is invalid for {job['job_id']}")
    _check_acyclic(by_id)
    return {"task_id": task["task_id"], "brief_revision": revision,
            "max_attempts": max_attempts, "jobs": clean_jobs}


def _check_acyclic(jobs: Mapping[str, Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    active: set[str] = set()

    def visit(job_id: str) -> None:
        if job_id in active:
            raise DispatchError("job dependencies contain a cycle")
        if job_id in seen:
            return
        active.add(job_id)
        for dep in jobs[job_id]["depends_on"]:
            visit(dep)
        active.remove(job_id)
        seen.add(job_id)

    for job_id in jobs:
        visit(job_id)


def _dependency_succeeded(job_id: str, jobs: Mapping[str, Mapping[str, Any]]) -> bool:
    lineage = {job_id}
    changed = True
    while changed:
        changed = False
        for candidate_id, candidate in jobs.items():
            if candidate["retry_of"] in lineage and candidate_id not in lineage:
                lineage.add(candidate_id)
                changed = True
    return any(jobs[candidate_id]["status"] == "completed" for candidate_id in lineage)


def _derived_retry_id(job: Mapping[str, Any], jobs: Mapping[str, Mapping[str, Any]]) -> str | None:
    """Return a valid, unused deterministic retry ID, or None when unavailable."""
    suffix = f"_retry_{job['attempt'] + 1}"
    prefix_length = 40 - len(suffix)
    if prefix_length < 1:
        return None
    candidate = job["job_id"][:prefix_length] + suffix
    if not _ID.fullmatch(candidate) or candidate in jobs:
        return None
    return candidate


def valid_choices(task: Mapping[str, Any]) -> list[dict[str, str | None]]:
    """Derive all legal next actions; list order has no policy significance."""
    normalized = validate_task(task)
    jobs = {job["job_id"]: job for job in normalized["jobs"]}
    choices: list[dict[str, str | None]] = []
    for job in normalized["jobs"]:
        if job["status"] == "pending":
            approval_ok = not job["human_approval_required"] or job["human_approved"]
            dependencies_ok = all(_dependency_succeeded(dep, jobs) for dep in job["depends_on"])
            if approval_ok and dependencies_ok:
                choices.append({"operation": "dispatch", "job_id": job["job_id"]})
        if job["status"] == "failed" and job["attempt"] < normalized["max_attempts"]:
            has_retry = any(candidate["retry_of"] == job["job_id"] for candidate in jobs.values())
            if not has_retry and _derived_retry_id(job, jobs) is not None:
                choices.append({"operation": "retry", "job_id": job["job_id"]})
    if not choices:
        choices.append({"operation": "wait", "job_id": None})
    return choices


def model_brief(task: Mapping[str, Any]) -> dict[str, Any]:
    """Compact state and output contract; does not disclose host-computed choices."""
    normalized = validate_task(task)
    return {
        "instruction": "Select one legal next action from current job state. Do not claim a job ran or generated an artifact.",
        "task": normalized,
        "action_schema": ACTION_SCHEMA,
        "rules": [
            "dispatch only a pending job after dependencies complete and required human approval is present",
            "retry only a failed job below retry cap without an existing retry child",
            "wait when every job is blocked, already active, awaiting review, or complete",
        ],
    }


def _parse_action(raw: str) -> dict[str, Any]:
    action = _strict_object(raw)
    if set(action) != {"operation", "job_id"}:
        raise DispatchError("action fields must be exactly operation and job_id")
    operation = action["operation"]
    if not isinstance(operation, str) or operation not in {"dispatch", "retry", "wait"}:
        raise DispatchError("operation must be dispatch, retry, or wait")
    if operation == "wait":
        if action["job_id"] is not None:
            raise DispatchError("wait requires job_id=null")
    elif not isinstance(action["job_id"], str) or not _ID.fullmatch(action["job_id"]):
        raise DispatchError("dispatch/retry requires a valid job_id")
    return action


def evaluate(task: Mapping[str, Any], raw: str) -> dict[str, Any]:
    """Validate an action against the independent oracle, then apply a data-only transition."""
    normalized = validate_task(task)
    before = copy.deepcopy(normalized)
    choices = valid_choices(normalized)
    try:
        action = _parse_action(raw)
        if action not in choices:
            raise DispatchError("action is not among host-derived legal choices")
        after = copy.deepcopy(normalized)
        if action["operation"] == "dispatch":
            next(job for job in after["jobs"] if job["job_id"] == action["job_id"])["status"] = "running"
        elif action["operation"] == "retry":
            failed = next(job for job in after["jobs"] if job["job_id"] == action["job_id"])
            jobs_by_id = {job["job_id"]: job for job in after["jobs"]}
            retry_id = _derived_retry_id(failed, jobs_by_id)
            if retry_id is None:
                raise DispatchError("no valid unused retry ID is available")
            retry = copy.deepcopy(failed)
            retry.update({"job_id": retry_id, "status": "pending", "attempt": failed["attempt"] + 1,
                          "retry_of": failed["job_id"], "human_approved": False, "artifact_receipt": None})
            after["jobs"].append(retry)
        after = validate_task(after)
        return {
            "task_id": normalized["task_id"], "valid": True, "status": "accepted",
            "action": action, "valid_choices": choices, "before": before, "after": after,
            "state_preserved": _preservation_check(before, after, action),
            "generation_performed": False,
        }
    except DispatchError as exc:
        return {
            "task_id": normalized["task_id"], "valid": False, "status": "rejected",
            "reason": str(exc), "valid_choices": choices, "before": before, "after": before,
            "state_preserved": True, "generation_performed": False,
        }


def _preservation_check(before, after, action) -> bool:
    old = {job["job_id"]: job for job in before["jobs"]}
    new = {job["job_id"]: job for job in after["jobs"]}
    preserved_receipts = [job for job in before["jobs"] if job["status"] == "completed"]
    if any(new.get(job["job_id"]) != job for job in preserved_receipts):
        return False
    if action["operation"] == "dispatch":
        return all(new[jid] == job for jid, job in old.items() if jid != action["job_id"])
    if action["operation"] == "retry":
        return all(new[jid] == job for jid, job in old.items())
    return before == after


def _offline_action(task: Mapping[str, Any]) -> dict[str, str | None]:
    """Pick one legal action for the reproducible CPU evidence; not model behavior."""
    return valid_choices(task)[0]


def offline_evidence() -> dict[str, Any]:
    rows = []
    for task in TASKS:
        action = _offline_action(task)
        result = evaluate(task, json.dumps(action))
        rows.append({"task_id": task["task_id"], "valid_choice_count": len(result["valid_choices"]),
                     "valid_choices": result["valid_choices"], "scripted_action": action,
                     "result": result["status"], "state_preserved": result["state_preserved"]})
    return {
        "kind": "scripted_offline_fixture",
        "scope": "production dispatch policy and state-transition validation only",
        "frozen_scene_count": len(TASKS),
        "provider_calls": 0,
        "generation_performed": False,
        "artistic_quality_evaluated": False,
        "valid_action_ordering_is_not_scored": True,
        "scenes": rows,
    }



def rejection_feedback(task: Mapping[str, Any], raw: str) -> dict[str, Any] | None:
    """Host-owned correction facts for one proposal, never an enumerated answer list."""
    clean = validate_task(task)
    result = evaluate(clean, raw)
    if result['valid']:
        return None
    try:
        action = _parse_action(raw)
    except DispatchError:
        return {'code': 'invalid_action_schema', 'message': 'Return one action matching action_schema.'}
    jobs = {j['job_id']: j for j in clean['jobs']}
    job = jobs.get(action['job_id'])
    if action['operation'] == 'retry' and job is not None and job['attempt'] >= clean['max_attempts']:
        return {'code': 'attempt_cap_reached', 'job_id': job['job_id'],
                'attempt': job['attempt'], 'max_attempts': clean['max_attempts'],
                'rule': 'Retry requires attempt < max_attempts. Reconsider the current ledger.'}
    return {'code': 'illegal_action', 'message': 'Proposal violates current ledger rules. Reconsider dependencies, approval, status and retry lineage.'}

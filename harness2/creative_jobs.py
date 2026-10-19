"""Pure-data fixture for bounded creative-production job tracking.

This module validates plans and receipts only. It does not generate or judge art.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


BRIEF = MappingProxyType({
    "revision": "brief-r1",
    "requirements": MappingProxyType({"coat_color": "blue", "logo": "none", "pose": "fixed"}),
    "variation_axis": "silhouette",
    "variation_count": 3,
})
KNOWN_CAPABILITIES = frozenset({"synthetic_silhouette_v1"})
_JOB_ID = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
_PLAN_FIELDS = {"parent_revision", "capability", "budget", "jobs"}
_JOB_FIELDS = {"job_id", "variation_id", "depends_on", "status", "parent_revision", "attempt"}
_RECEIPT_FIELDS = {"artifact_id", "job_id", "parent_revision"}
MAX_ATTEMPTS = 3


class PlanError(ValueError):
    """A plan or state transition violates the host-owned contract."""


def _finite_budget(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PlanError("budget must be a finite non-negative number")
    try:
        numeric = float(value)
    except (OverflowError, ValueError):
        raise PlanError("budget must be a finite non-negative number") from None
    if not math.isfinite(numeric) or numeric < 0:
        raise PlanError("budget must be a finite non-negative number")
    return numeric


@dataclass(frozen=True)
class Job:
    job_id: str
    variation_id: str
    depends_on: tuple[str, ...]
    parent_revision: str
    status: str = "pending"
    attempt: int = 1
    parent_job_id: str | None = None
    artifact_receipt: Mapping[str, str] | None = None


@dataclass
class JobBoard:
    """In-memory ledger; budget is recorded metadata, not charged or enforced."""

    budget: float
    capability: str
    parent_revision: str = BRIEF["revision"]
    jobs: dict[str, Job] = field(default_factory=dict)
    _completed_artifacts: dict[str, Mapping[str, str]] = field(default_factory=dict)

    @classmethod
    def from_plan(cls, value: Mapping[str, Any]) -> "JobBoard":
        if not isinstance(value, Mapping) or set(value) != _PLAN_FIELDS:
            raise PlanError(f"plan fields must be exactly {sorted(_PLAN_FIELDS)}")
        revision = value["parent_revision"]
        if revision != BRIEF["revision"]:
            raise PlanError("plan parent_revision does not match the immutable brief")
        capability = value["capability"]
        if not isinstance(capability, str):
            raise PlanError("unknown production capability")
        if capability not in KNOWN_CAPABILITIES:
            raise PlanError("unknown production capability")
        budget = _finite_budget(value["budget"])
        raw_jobs = value["jobs"]
        if not isinstance(raw_jobs, list) or len(raw_jobs) != BRIEF["variation_count"]:
            raise PlanError("plan must contain exactly three silhouette jobs")

        jobs: dict[str, Job] = {}
        variation_ids: set[str] = set()
        for item in raw_jobs:
            if not isinstance(item, Mapping) or set(item) != _JOB_FIELDS:
                raise PlanError(f"job fields must be exactly {sorted(_JOB_FIELDS)}")
            job_id, variation_id = item["job_id"], item["variation_id"]
            if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id) or job_id in jobs:
                raise PlanError("job_id must be valid and unique")
            if not isinstance(variation_id, str) or not variation_id.strip() or variation_id in variation_ids:
                raise PlanError("variation_id must be non-empty and distinct")
            variation_ids.add(variation_id)
            deps = item["depends_on"]
            if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
                raise PlanError("depends_on must be a list of job IDs")
            if len(deps) != len(set(deps)) or job_id in deps:
                raise PlanError("dependencies must be unique and cannot include the job itself")
            attempt = item["attempt"]
            if (item["status"] != "pending" or item["parent_revision"] != revision
                    or isinstance(attempt, bool) or not isinstance(attempt, int) or attempt != 1):
                raise PlanError("new jobs must be pending, attempt 1, on the plan parent revision")
            jobs[job_id] = Job(job_id, variation_id, tuple(deps), revision, attempt=1)
        for job in jobs.values():
            if any(dep not in jobs for dep in job.depends_on):
                raise PlanError(f"job {job.job_id} has an unknown dependency")
        _assert_acyclic(jobs)
        return cls(budget=budget, capability=capability, jobs=jobs)

    def transition(self, job_id: str, status: str, receipt: Mapping[str, str] | None = None) -> None:
        job = self._get(job_id)
        allowed = {"pending": {"running"}, "running": {"completed", "failed"}}
        if status not in allowed.get(job.status, set()):
            raise PlanError(f"invalid transition {job.status}->{status}")
        if status == "running" and any(not self._dependency_completed(dep) for dep in job.depends_on):
            raise PlanError("job cannot run until all dependencies are completed")
        if status == "completed":
            if not isinstance(receipt, Mapping) or set(receipt) != _RECEIPT_FIELDS:
                raise PlanError(f"completed jobs require a receipt with exactly {sorted(_RECEIPT_FIELDS)}")
            if (not all(isinstance(receipt[k], str) and receipt[k].strip() for k in _RECEIPT_FIELDS)
                    or receipt["job_id"] != job_id or receipt["parent_revision"] != job.parent_revision):
                raise PlanError("artifact receipt must identify this job and its parent revision")
            immutable_receipt = MappingProxyType(dict(receipt))
            self._completed_artifacts[job_id] = immutable_receipt
            self.jobs[job_id] = Job(**{**job.__dict__, "status": status, "artifact_receipt": immutable_receipt})
        else:
            if receipt is not None:
                raise PlanError("receipts are accepted only when completing a job")
            self.jobs[job_id] = Job(**{**job.__dict__, "status": status})

    def retry_failed(self, job_id: str, retry_job_id: str) -> str:
        failed = self._get(job_id)
        if failed.status != "failed":
            raise PlanError("only failed jobs may be retried")
        if any(j.parent_job_id == job_id for j in self.jobs.values()):
            raise PlanError("this failed attempt already has a retry child")
        root_id = self._root_job_id(job_id)
        attempt_count = sum(1 for jid in self.jobs if self._root_job_id(jid) == root_id)
        if attempt_count >= MAX_ATTEMPTS:
            raise PlanError(f"retry limit reached ({MAX_ATTEMPTS} attempts per original job)")
        if not isinstance(retry_job_id, str) or not _JOB_ID.fullmatch(retry_job_id) or retry_job_id in self.jobs:
            raise PlanError("retry job_id must be valid and new")
        retry = Job(retry_job_id, failed.variation_id, failed.depends_on,
                    failed.parent_revision, attempt=failed.attempt + 1, parent_job_id=job_id)
        self.jobs[retry_job_id] = retry
        return retry_job_id

    def _root_job_id(self, job_id: str) -> str:
        job = self._get(job_id)
        while job.parent_job_id is not None:
            job = self._get(job.parent_job_id)
        return job.job_id

    def _dependency_completed(self, job_id: str) -> bool:
        root_id = self._root_job_id(job_id)
        return any(
            job.status == "completed" and self._root_job_id(candidate_id) == root_id
            for candidate_id, job in self.jobs.items()
        )

    def _get(self, job_id: str) -> Job:
        try:
            return self.jobs[job_id]
        except KeyError as exc:
            raise PlanError(f"unknown job {job_id!r}") from exc

    def snapshot(self) -> dict[str, Any]:
        return {
            "brief_revision": self.parent_revision,
            "capability": self.capability,
            "budget": self.budget,
            "jobs": [
                {"job_id": j.job_id, "variation_id": j.variation_id,
                 "depends_on": list(j.depends_on), "parent_revision": j.parent_revision,
                 "status": j.status, "attempt": j.attempt, "parent_job_id": j.parent_job_id,
                 "artifact_receipt": dict(j.artifact_receipt) if j.artifact_receipt else None}
                for j in self.jobs.values()
            ],
            "completed_artifacts": {k: dict(v) for k, v in self._completed_artifacts.items()},
        }


def _assert_acyclic(jobs: Mapping[str, Job]) -> None:
    seen: set[str] = set()
    active: set[str] = set()

    def visit(job_id: str) -> None:
        if job_id in active:
            raise PlanError("job dependencies contain a cycle")
        if job_id in seen:
            return
        active.add(job_id)
        for dep in jobs[job_id].depends_on:
            visit(dep)
        active.remove(job_id)
        seen.add(job_id)

    for job_id in jobs:
        visit(job_id)


def demo_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a three-variant plan and scripted retry receipt for CPU-only validation."""
    plan = {
        "parent_revision": BRIEF["revision"],
        "capability": "synthetic_silhouette_v1",
        "budget": 3.0,
        "jobs": [
            {"job_id": f"silhouette_{i}", "variation_id": f"silhouette-{i}",
             "depends_on": [], "status": "pending", "parent_revision": BRIEF["revision"], "attempt": 1}
            for i in range(1, 4)
        ],
    }
    expected = {"coat_color": "blue", "logo": "none", "pose": "fixed"}
    if BRIEF["requirements"] != expected:
        raise AssertionError("fixture brief drifted")
    retry_receipt = {"artifact_id": "artifact-retry-2", "job_id": "silhouette_2_retry",
                     "parent_revision": BRIEF["revision"]}
    board = JobBoard.from_plan(plan)
    board.transition("silhouette_1", "running")
    board.transition("silhouette_1", "completed", {
        "artifact_id": "artifact-1", "job_id": "silhouette_1", "parent_revision": BRIEF["revision"]})
    board.transition("silhouette_2", "running")
    board.transition("silhouette_2", "failed")
    board.retry_failed("silhouette_2", "silhouette_2_retry")
    board.transition("silhouette_2_retry", "running")
    board.transition("silhouette_2_retry", "completed", retry_receipt)
    return plan, board.snapshot()


def evidence_json() -> str:
    plan, state = demo_fixture()
    return json.dumps({
        "kind": "scripted_cpu_fixture",
        "scope": "creative job validation and state tracking only; no image generation or visual inspection",
        "brief_revision": BRIEF["revision"],
        "brief_requirements": dict(BRIEF["requirements"]),
        "variation_ids": [j["variation_id"] for j in plan["jobs"]],
        "plan_job_count": len(plan["jobs"]),
        "budget": plan["budget"],
        "final_states": {j["job_id"]: j["status"] for j in state["jobs"]},
        "job_lineage": {j["job_id"]: j["parent_job_id"] for j in state["jobs"]},
        "completed_artifacts": state["completed_artifacts"],
        "claims": {"generation_performed": False, "artistic_quality_evaluated": False,
                   "visual_brief_compliance_checked": False, "model_trial": False,
                   "budget_enforced": False, "budget_is_metadata_only": True},
    }, indent=2, sort_keys=True) + "\n"

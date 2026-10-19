"""Strict host-side contract for a three-item silhouette audition plan.

The validator checks structured intent only; it does not generate or inspect images.
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any, Mapping


BRIEF = MappingProxyType({
    "parent_revision": "brief-r1",
    "camera": "front",
    "pose": "fixed",
    "coat_color": "blue",
    "logo": "none",
    "variation_axis": "silhouette",
    "silhouettes": ("a_line", "cocoon", "straight"),
})
_JOB_ID = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
_PLAN_FIELDS = {
    "parent_revision", "camera", "pose", "coat_color", "logo", "variation_axis", "jobs"
}
_JOB_FIELDS = {"job_id", "silhouette"}

# Strict schema to give a model a compact, machine-readable output contract.
VARIANT_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(_PLAN_FIELDS),
    "properties": {
        "parent_revision": {"type": "string", "const": BRIEF["parent_revision"]},
        "camera": {"type": "string", "const": BRIEF["camera"]},
        "pose": {"type": "string", "const": BRIEF["pose"]},
        "coat_color": {"type": "string", "const": BRIEF["coat_color"]},
        "logo": {"type": "string", "const": BRIEF["logo"]},
        "variation_axis": {"type": "string", "const": BRIEF["variation_axis"]},
        "jobs": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": sorted(_JOB_FIELDS),
                "properties": {
                    "job_id": {"type": "string", "pattern": _JOB_ID.pattern},
                    "silhouette": {"type": "string", "enum": list(BRIEF["silhouettes"])},
                },
            },
        },
    },
}


class VariantPlanError(ValueError):
    """A structured plan violates the fixed-view silhouette contract."""


def model_brief() -> dict[str, Any]:
    """Return the host-owned immutable facts and exact required variation set."""
    return {
        "parent_revision": BRIEF["parent_revision"],
        "invariants": {
            "camera": BRIEF["camera"],
            "pose": BRIEF["pose"],
            "coat_color": BRIEF["coat_color"],
            "logo": BRIEF["logo"],
        },
        "variation_axis": BRIEF["variation_axis"],
        "required_silhouettes": list(BRIEF["silhouettes"]),
        "output_schema": VARIANT_PLAN_SCHEMA,
    }


def validate_variant_plan(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exactly three distinct silhouette designs with separate unique job IDs."""
    if not isinstance(value, Mapping) or set(value) != _PLAN_FIELDS:
        raise VariantPlanError(f"plan fields must be exactly {sorted(_PLAN_FIELDS)}")
    for key in ("parent_revision", "camera", "pose", "coat_color", "logo", "variation_axis"):
        if value[key] != BRIEF[key]:
            raise VariantPlanError(f"{key} must remain fixed at {BRIEF[key]!r}")
    jobs = value["jobs"]
    if not isinstance(jobs, list) or len(jobs) != len(BRIEF["silhouettes"]):
        raise VariantPlanError("plan must contain exactly three silhouette jobs")

    ids: set[str] = set()
    silhouettes: list[str] = []
    clean_jobs: list[dict[str, str]] = []
    for job in jobs:
        if not isinstance(job, Mapping) or set(job) != _JOB_FIELDS:
            raise VariantPlanError(f"each job must contain exactly {sorted(_JOB_FIELDS)}")
        job_id, silhouette = job["job_id"], job["silhouette"]
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id) or job_id in ids:
            raise VariantPlanError("job_id values must be valid and unique")
        if not isinstance(silhouette, str) or silhouette not in BRIEF["silhouettes"]:
            raise VariantPlanError(f"silhouette must be one of {list(BRIEF['silhouettes'])}")
        ids.add(job_id)
        silhouettes.append(silhouette)
        clean_jobs.append({"job_id": job_id, "silhouette": silhouette})
    if set(silhouettes) != set(BRIEF["silhouettes"]) or len(set(silhouettes)) != 3:
        raise VariantPlanError("jobs must cover a_line, cocoon, and straight exactly once")
    return {
        "parent_revision": BRIEF["parent_revision"],
        "camera": BRIEF["camera"],
        "pose": BRIEF["pose"],
        "coat_color": BRIEF["coat_color"],
        "logo": BRIEF["logo"],
        "variation_axis": BRIEF["variation_axis"],
        "jobs": clean_jobs,
    }

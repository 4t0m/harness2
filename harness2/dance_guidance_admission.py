"""Pure admission gate for the frozen four-candidate step-guidance trial.

This replays host verdicts for one supplied task. It does not call providers,
read or write files, or estimate guidance quality or generalization.
"""

from __future__ import annotations

import hashlib
import json

from . import dance_step_h2
from .dance_step_task import validate_task
from .production_h2 import validate_guidance


PRIORITY = ("c1", "dom1", "inv1", "base1")
_LABELS = frozenset(PRIORITY)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_task_wrapper(task: object) -> tuple[dict, dict]:
    if type(task) is not dict or set(task) != {"task", "request"}:
        raise ValueError("task wrapper requires exactly task and request")
    facts = validate_task(task["task"])
    request = task["request"]
    if (type(request) is not str or not 1 <= len(request) <= 3000
            or any(ord(char) < 32 and char not in "\n\t" for char in request)):
        raise ValueError("request must be bounded plain text")
    return facts, {"task": facts, "request": request}


def _validate_candidate(candidate: object, task: dict, facts: dict,
                        label: str) -> tuple[str, str, bool, str]:
    if type(candidate) is not dict or set(candidate) != {"label", "guidance", "receipt"}:
        raise ValueError(f"candidate {label} requires exactly label, guidance, receipt")
    if candidate["label"] != label:
        raise ValueError(f"candidate order/index mismatch for {label}")
    try:
        guidance = validate_guidance(candidate["guidance"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"candidate {label} has invalid guidance: {exc}") from exc
    guidance_hash = _digest(guidance)
    receipt = candidate["receipt"]
    if type(receipt) is not dict:
        raise ValueError(f"candidate {label} receipt must be an object")
    required = {"task_id", "run_id", "mode", "guidance_sha256", "request_sha256",
                "attempts", "finish_reason", "content", "verdict"}
    if not required.issubset(receipt):
        raise ValueError(f"candidate {label} receipt is missing required provenance")
    if receipt["task_id"] != facts["id"]:
        raise ValueError(f"candidate {label} receipt is bound to a different task")
    run_id = receipt["run_id"]
    if type(run_id) is not str or not run_id.endswith("/" + label):
        raise ValueError(f"candidate {label} run_id does not end in /{label}")
    if receipt["mode"] != "model_solver":
        raise ValueError(f"candidate {label} receipt mode is not model_solver")
    if receipt["attempts"] != 1 or type(receipt["attempts"]) is not int:
        raise ValueError(f"candidate {label} receipt must record exactly one attempt")
    if receipt["finish_reason"] != "stop":
        raise ValueError(f"candidate {label} solver did not finish with stop")
    if receipt["guidance_sha256"] != guidance_hash:
        raise ValueError(f"candidate {label} guidance hash mismatch")
    request_hash = _digest(
        guidance + "\n" + dance_step_h2.PUBLIC_CONTRACT + "\n"
        + json.dumps(task, sort_keys=True)
    )
    if receipt["request_sha256"] != request_hash:
        raise ValueError(f"candidate {label} request hash mismatch")
    content = receipt["content"]
    if type(content) is not str:
        raise ValueError(f"candidate {label} receipt content must be text")

    actual = dance_step_h2.verdict(content, task)
    saved = receipt["verdict"]
    if (type(saved) is not dict or type(saved.get("valid")) is not bool
            or type(saved.get("reason")) is not str):
        raise ValueError(f"candidate {label} saved verdict is malformed")
    if saved["valid"] != actual["valid"] or saved["reason"] != actual["reason"]:
        raise ValueError(f"candidate {label} saved verdict disagrees with host replay")
    return guidance, guidance_hash, actual["valid"], actual["reason"]


def choose_admitted(candidates: list[dict], task: dict) -> dict:
    """Return the highest-priority independently valid guidance candidate.

    The only supported candidate labels are ``base1``, ``inv1``, ``dom1`` and
    ``c1``. Every receipt is provenance-checked and its raw plan is replayed
    against the supplied task before it can be admitted.
    """
    _facts, normalized_task = _check_task_wrapper(task)
    if type(candidates) is not list or len(candidates) != len(PRIORITY):
        raise ValueError("exactly four guidance candidates are required")
    indexed = {}
    for candidate in candidates:
        if type(candidate) is not dict or "label" not in candidate:
            raise ValueError("candidate label is required")
        label = candidate["label"]
        if type(label) is not str or label not in _LABELS:
            raise ValueError(f"unknown candidate label: {label!r}")
        if label in indexed:
            raise ValueError(f"duplicate candidate label: {label}")
        indexed[label] = candidate
    if set(indexed) != _LABELS:
        missing = sorted(_LABELS - set(indexed))
        raise ValueError(f"missing candidate labels: {', '.join(missing)}")

    audits = []
    selected = None
    for rank, label in enumerate(PRIORITY):
        guidance, guidance_hash, valid, reason = _validate_candidate(
            indexed[label], normalized_task, normalized_task["task"], label)
        audits.append({"label": label, "priority": rank, "guidance_sha256": guidance_hash,
                       "valid": valid, "reason": reason})
        if selected is None and valid:
            selected = {"label": label, "guidance": guidance,
                        "guidance_sha256": guidance_hash}
    return {"selected": selected, "audited_candidates": audits}

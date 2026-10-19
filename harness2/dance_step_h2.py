"""Harness2 prompt adaptation for host-checked, structured stepping tasks."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Mapping, Sequence

from .actor_improver import _incomplete_content, _reported_cost
from .actor_provider import ProviderError, ProviderIncomplete, chat_completion
from .core import tree
from .core.spec import BenchPrompts, BenchSpec, ChannelSpec
from .dance_step_task import compile_task, validate_task, verify_task
from .production_h2 import ProductionAdapter, Provider, validate_guidance
from .substrate.opencode import OpencodeSubstrate

BASE_GUIDANCE = (
    "Read the approved task and request carefully. Check every stated constraint before choosing moves.\n"
    "Choose four chronological move and variation pairs that satisfy the task.\n"
    "Return only the required JSON object.\n"
)
# Exactly the fixed system contract used by the structured-task baseline trial.
PUBLIC_CONTRACT = (
    "Return only a JSON object with one field named moves: an array of exactly four pairs, in chronological order. "
    "Each pair contains two strings. The first string must be step_left or step_right. The second string must be "
    "soft or clear. Choose one identifier per string, never alternatives or coordinates. Every move is a two-beat "
    "side step at 120 BPM. Each step moves the planted stance 0.20 m in its named direction. Variation changes "
    "arm/body accent, not travel distance. No other fields. The approved task uses integer millimetres in world x. "
    "Each step_left changes x by -200 mm and step_right by +200 mm. Start at start_x_mm and finish at target_x_mm. "
    "Keep the root within the inclusive root_bounds_mm throughout. required_moves and required_variations map "
    "zero-based slot strings to required identifiers. Empty maps leave those choices free. All task fields are "
    "authoritative. Do not emit coordinates; output the four move/variation pairs only."
)
# ProductionImprover accepts at most 500 bytes of immutable editor framing.
EDITOR_PUBLIC_RULE = (
    "Solver output is exactly JSON moves with four chronological [direction, variation] pairs: direction "
    "step_left or step_right, variation soft or clear. Host-approved task fields set start_x_mm, target_x_mm, "
    "root_bounds_mm, required_moves, and required_variations. Each step changes x by 200 mm. Do not give "
    "the editor feasible plans or host answers."
)
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
_SAFE_RUN_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")


def _safe_run_id(run_id: str) -> bool:
    return (type(run_id) is str and len(run_id) <= 360 and
            1 <= len(run_id.split("/")) <= 3 and
            all(_SAFE_RUN_PART.fullmatch(part) and part != ".."
                for part in run_id.split("/")))


def verdict(raw: str, taskwrapper: dict) -> dict:
    """Accept any plan satisfying the public structured task, with no oracle plan."""
    try:
        compiled = compile_task(raw, taskwrapper["task"])
        verify_task(compiled, taskwrapper["task"])
    except (ValueError, TypeError, KeyError) as exc:
        return {"valid": False, "reason": str(exc)}
    return {"valid": True, "reason": "step task constraints satisfied",
            "compiled": compiled}


class StepAdapter(ProductionAdapter):
    """One bounded solver call per H2 execution; editor sees development tasks only."""

    def __init__(self, root: Path, tasks: Mapping[str, dict], train_ids: Sequence[str], *,
                 provider: Provider = chat_completion, base_url: str, model: str,
                 api_key: str = "", max_solver_calls: int = 12,
                 request_timeout: float = 20.0, max_output_tokens: int = 128):
        if type(max_solver_calls) is not int or not 1 <= max_solver_calls <= 100:
            raise ValueError("max_solver_calls must be 1..100")
        if (type(request_timeout) not in (int, float) or not 0 < request_timeout <= 20
                or type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 128):
            raise ValueError("invalid solver per-call budget")
        self.root = Path(root)
        self.provider, self.base_url, self.model, self.api_key = provider, base_url, model, api_key
        self.max_solver_calls = max_solver_calls
        self.request_timeout, self.max_output_tokens = request_timeout, max_output_tokens
        self.solver_calls = 0
        self._call_lock = threading.Lock()
        self.task_data = {}
        for task_id, original in tasks.items():
            if type(task_id) is not str or _SAFE_ID.fullmatch(task_id) is None:
                raise ValueError("invalid task id")
            if type(original) is not dict or set(original) != {"task", "request"}:
                raise ValueError("task wrapper requires exactly task and request")
            facts = validate_task(original["task"])
            if facts["id"] != task_id:
                raise ValueError("task mapping key differs from task id")
            request = original["request"]
            if (type(request) is not str or not 1 <= len(request) <= 3000
                    or any(ord(char) < 32 and char not in "\n\t" for char in request)):
                raise ValueError("bounded request required")
            self.task_data[task_id] = {"task": facts, "request": request}
        self.train_ids = tuple(train_ids)
        if len(set(self.train_ids)) != len(self.train_ids) or any(
                task_id not in self.task_data for task_id in self.train_ids):
            raise ValueError("train_ids must be unique task mapping keys")
        self.substrate = OpencodeSubstrate()
        channel = ChannelSpec("opencode", "local/injected")
        self.spec = BenchSpec(
            name="dance_step_h2", runs_root=self.root / "runs", install_mode="workspace_config",
            prompts=BenchPrompts(work="choose four side steps satisfying the approved task",
                                 domain_word="structured stepping"),
            channels={"proposer": channel, "selector": channel},
            leak_globs=("oracle.json", "holdout.json", "evaluation.json"),
        )
        base = {name: "" for name in self.substrate.surface().always_on}
        base["systemprompt.md"] = validate_guidance(BASE_GUIDANCE)
        tree.write_tree(self.substrate.surface(), base, self.base_harness(), stubs=False)
        for task_id in self.train_ids:
            source = self.task_files(task_id)
            source.mkdir(parents=True, exist_ok=True)
            (source / "brief.json").write_text(json.dumps(self.task_data[task_id], indent=2) + "\n")

    def domain_of(self, task_id):
        return "structured-stepping"

    def task_prompt(self, task_id):
        if task_id not in self.train_ids:
            raise ValueError("editor context is restricted to development tasks")
        return "Development approved task and request (source data):\n" + json.dumps(
            self.task_data[task_id], indent=2) + "\n"

    def execute(self, task_id, harness_dir, run_id, *, timeout=None):
        del timeout
        if task_id not in self.task_data:
            raise ValueError("unknown task")
        if not _safe_run_id(run_id):
            raise ValueError("invalid run id")
        path = (Path(harness_dir) if harness_dir else self.base_harness()) / "systemprompt.md"
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("guidance symlink refused")
        guidance = validate_guidance(path.read_text(encoding="utf-8"))
        run_dir = self.root / "executions" / run_id
        if run_dir.exists():
            raise FileExistsError("execution receipt already exists")
        run_dir.mkdir(parents=True)
        task = self.task_data[task_id]
        system = guidance + "\n" + PUBLIC_CONTRACT
        user = json.dumps(task, sort_keys=True)
        receipt = {"task_id": task_id, "run_id": run_id, "mode": "model_solver",
                   "model_requested": self.model,
                   "guidance_sha256": hashlib.sha256(guidance.encode()).hexdigest(),
                   "request_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest(),
                   "request_timeout_seconds": self.request_timeout,
                   "max_output_tokens": self.max_output_tokens, "attempts": 0}
        try:
            with self._call_lock:
                if self.solver_calls >= self.max_solver_calls:
                    raise RuntimeError("solver call budget exhausted")
                self.solver_calls += 1
                receipt["attempts"] = 1
            response = self.provider(base_url=self.base_url, model=self.model, api_key=self.api_key,
                                     system=system, user=user, timeout=self.request_timeout,
                                     max_output_tokens=self.max_output_tokens, include_raw=True)
            receipt.update(content=response.content[:8192], finish_reason=response.finish_reason,
                           usage=response.usage, latency_seconds=response.latency_seconds,
                           model_served=response.model, cost_usd=_reported_cost(response.raw_response))
            if len(response.content.encode("utf-8")) > 8192:
                receipt["error"] = "solver response exceeded 8192-byte limit"
            if response.finish_reason != "stop":
                receipt["error"] = "solver finish_reason was not stop"
            elif "error" not in receipt:
                scored = verdict(response.content, task)
                compiled = scored.pop("compiled", None)
                receipt["verdict"] = scored
                (run_dir / "proposal.json").write_text(response.content + "\n")
                (run_dir / "verdict.json").write_text(json.dumps(scored, indent=2) + "\n")
                if compiled is not None:
                    receipt["task_receipt"] = compiled["receipt"]
                    receipt["placement"] = compiled["placement"]
                    (run_dir / "compiled.json").write_text(json.dumps(compiled, indent=2) + "\n")
        except ProviderIncomplete as exc:
            receipt.update(error="provider incomplete", finish_reason=exc.finish_reason,
                           usage=exc.usage, latency_seconds=exc.latency_seconds,
                           model_served=exc.model, content=_incomplete_content(exc),
                           cost_usd=_reported_cost(exc.raw_response))
        except (ProviderError, RuntimeError, TimeoutError) as exc:
            receipt["error"] = str(exc)
        except Exception as exc:
            receipt["error"] = f"unexpected provider failure: {type(exc).__name__}"
        (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        status = receipt.get("verdict", {}).get("reason", receipt.get("error", "no verdict"))
        (run_dir / "trajectory.md").write_text(
            "[ACTION] Solver proposed a four-step plan\n"
            + "[OBSERVATION] " + str(receipt.get("content", ""))[:2048] + "\n"
            + "[HOST] " + str(status) + "\n")
        return run_dir

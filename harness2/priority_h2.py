"""Host-scored creative priority choices through the real Harness2 recursion.

Tasks and their expected choices are separate inputs. Only development briefs and
options enter the editable context; no job is dispatched by this adapter.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Mapping, Sequence

from .actor_improver import _incomplete_content, _reported_cost
from .actor_provider import ProviderError, ProviderIncomplete, chat_completion
from .core import tree
from .core.spec import BenchPrompts, BenchSpec, ChannelSpec
from .production_h2 import ProductionAdapter, Provider, validate_guidance

BASE_GUIDANCE = (
    "Choose the one supplied option that best satisfies every requirement in the user's brief.\n"
    "Consider constraints and requested next steps together.\n"
    "Return only a strict JSON object with choice_id set to an option_N identifier.\n"
)
_CHOICE = re.compile(r"option_(0|[1-9][0-9]*)\Z")
_FENCE = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n```", re.DOTALL)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _choice(content: str, count: int) -> str:
    if not isinstance(content, str) or len(content.encode("utf-8")) > 4096:
        raise ValueError("response must be bounded text")
    try:
        value = json.loads(content, object_pairs_hook=_unique_pairs)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("response is not strict JSON") from exc
    if not isinstance(value, dict) or set(value) != {"choice_id"}:
        raise ValueError("exact choice_id required")
    choice_id = value["choice_id"]
    match = _CHOICE.fullmatch(choice_id) if isinstance(choice_id, str) else None
    if match is None or int(match.group(1)) >= count:
        raise ValueError("unknown choice_id")
    return choice_id


def _normalization(content: str) -> tuple[str, bool]:
    stripped = content.strip()
    if not stripped.startswith("```") and not stripped.endswith("```"):
        return content, False
    match = _FENCE.fullmatch(stripped)
    if match is None:
        raise ValueError("only one full-response json fence may be normalized")
    return match.group(1), True


def _verdict(content: str, count: int, expected: int) -> dict:
    try:
        choice_id = _choice(content, count)
    except ValueError as exc:
        return {"accepted_format": False, "semantic_correct": False,
                "valid": False, "reason": str(exc)}
    correct = choice_id == f"option_{expected}"
    return {"accepted_format": True, "semantic_correct": correct,
            "valid": correct, "choice_id": choice_id,
            "reason": "correct choice" if correct else "choice does not satisfy brief"}


class PriorityAdapter(ProductionAdapter):
    """Bounded model solver with private host-side semantic acceptance."""

    def __init__(self, root: Path, tasks: Mapping[str, dict],
                 expected_indices: Mapping[str, int], train_ids: Sequence[str], *,
                 provider: Provider = chat_completion, base_url: str, model: str,
                 api_key: str | None = None, max_solver_calls: int = 20,
                 request_timeout: float = 20.0, max_output_tokens: int = 128,
                 repair_single_json_fence: bool = False):
        if not 1 <= max_solver_calls <= 100:
            raise ValueError("max_solver_calls must be 1..100")
        if not 0 < request_timeout <= 20 or not 1 <= max_output_tokens <= 128:
            raise ValueError("invalid solver per-call budget")
        if not isinstance(repair_single_json_fence, bool):
            raise ValueError("repair_single_json_fence must be boolean")
        self.root = Path(root)
        self.provider, self.base_url, self.model, self.api_key = provider, base_url, model, api_key
        self.max_solver_calls = max_solver_calls
        self.request_timeout, self.max_output_tokens = request_timeout, max_output_tokens
        self.repair_single_json_fence = repair_single_json_fence
        self.solver_calls = 0
        import threading
        self._call_lock = threading.Lock()
        self.task_data = {}
        for task_id, original in tasks.items():
            task = copy.deepcopy(original)
            if not isinstance(task_id, str) or not task_id or "/" in task_id or ".." in task_id:
                raise ValueError("invalid task id")
            if not isinstance(task, dict) or set(task) != {"task_id", "brief", "options"}:
                raise ValueError("task must contain only task_id, brief, options")
            if task["task_id"] != task_id:
                raise ValueError("task mapping key differs from task_id")
            if not isinstance(task["brief"], str) or not 1 <= len(task["brief"]) <= 2000:
                raise ValueError("bounded creative brief required")
            options = task["options"]
            if not isinstance(options, list) or not 2 <= len(options) <= 20 or any(
                not isinstance(option, str) or not 1 <= len(option) <= 500 for option in options
            ):
                raise ValueError("bounded option list required")
            self.task_data[task_id] = task
        if set(expected_indices) != set(self.task_data):
            raise ValueError("expected indices must cover exactly the task mapping")
        self.expected_indices = {}
        for task_id, index in expected_indices.items():
            if type(index) is not int or not 0 <= index < len(self.task_data[task_id]["options"]):
                raise ValueError("expected index outside option list")
            self.expected_indices[task_id] = index
        self.train_ids = tuple(train_ids)
        if len(set(self.train_ids)) != len(self.train_ids) or any(t not in self.task_data for t in self.train_ids):
            raise ValueError("train_ids must be unique task mapping keys")
        from .substrate.opencode import OpencodeSubstrate
        self.substrate = OpencodeSubstrate()
        channel = ChannelSpec("opencode", "local/injected")
        self.spec = BenchSpec(
            name="priority_h2", runs_root=self.root / "runs", install_mode="workspace_config",
            prompts=BenchPrompts(work="choose one option matching the creative brief",
                                 domain_word="creative priority"),
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
        return "creative-priority"

    def task_prompt(self, task_id):
        if task_id not in self.train_ids:
            raise ValueError("editor context is restricted to development tasks")
        return "Development task brief (source data):\n" + json.dumps(self.task_data[task_id], indent=2) + "\n"

    def execute(self, task_id, harness_dir, run_id, *, timeout=None):
        del timeout
        if task_id not in self.task_data:
            raise ValueError("unknown task")
        path = (Path(harness_dir) if harness_dir else self.base_harness()) / "systemprompt.md"
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("guidance symlink refused")
        guidance = validate_guidance(path.read_text(encoding="utf-8"))
        run_dir = self.root / "executions" / run_id
        if run_dir.exists():
            raise FileExistsError("execution receipt already exists")
        run_dir.mkdir(parents=True)
        task = self.task_data[task_id]
        user = json.dumps({"brief": task["brief"], "legal_options": [
            {"choice_id": f"option_{i}", "description": description}
            for i, description in enumerate(task["options"])
        ], "instruction": 'Choose one option. Return only {"choice_id":"option_N"}.'}, sort_keys=True)
        system = guidance + "\nReturn strict JSON only; no Markdown."
        receipt = {"task_id": task_id, "run_id": run_id, "mode": "model_solver",
                   "model_requested": self.model, "guidance_sha256": hashlib.sha256(guidance.encode()).hexdigest(),
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
            receipt.update(content=response.content[:4096], finish_reason=response.finish_reason,
                           usage=response.usage, latency_seconds=response.latency_seconds,
                           model_served=response.model, cost_usd=_reported_cost(response.raw_response))
            if len(response.content.encode("utf-8")) > 4096:
                receipt["content_bytes"] = len(response.content.encode("utf-8"))
                receipt["error"] = "solver response exceeded 4096-byte limit"
            if response.finish_reason != "stop":
                receipt["error"] = "solver finish_reason was not stop"
            elif "error" not in receipt:
                strict = _verdict(response.content, len(task["options"]), self.expected_indices[task_id])
                receipt["strict_verdict"] = strict
                verdict = strict
                if self.repair_single_json_fence:
                    try:
                        normalized, repaired = _normalization(response.content)
                        if repaired:
                            verdict = _verdict(normalized, len(task["options"]), self.expected_indices[task_id])
                            receipt["repaired_verdict"] = verdict
                            receipt["format_repaired"] = True
                    except ValueError as exc:
                        receipt["format_repair_error"] = str(exc)
                receipt["verdict"] = verdict
                (run_dir / "proposal.json").write_text(response.content + "\n")
                (run_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
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
            "[ACTION] Solver chose a creative priority\n"
            + "[OBSERVATION] " + str(receipt.get("content", ""))[:2048] + "\n"
            + "[HOST] " + str(status) + "\n")
        return run_dir

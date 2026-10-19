"""Host-scored compact staging choices through the real Harness2 recursion."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Mapping, Sequence

from .actor_improver import _incomplete_content, _reported_cost
from .actor_provider import ProviderError, ProviderIncomplete, chat_completion
from .actor_staging import compile_staging
from .actor_staging_compact import bind_scene, compile_compact
from .core import tree
from .core.spec import BenchPrompts, BenchSpec, ChannelSpec
from .production_h2 import ProductionAdapter, Provider, validate_guidance
from .substrate.opencode import OpencodeSubstrate

BASE_GUIDANCE = (
    "Read the scene and request carefully. Choose the actor on the requested screen-left side.\n"
    "Choose each actor, gesture, and variation in the requested chronological order.\n"
    "Return only the requested JSON object.\n"
)
PUBLIC_CONTRACT = (
    'Return strict JSON with exactly {"left":"actorID","cues":[["actorID","gesture","variation"],'
    '["actorID","gesture","variation"],["actorID","gesture","variation"]]}. '
    "Use exact scene actor IDs. The other actor is screen-right. The cues are slots 0, 1, 2 in order. "
    "Gesture must be wave, nod, or neutral. Variation must be soft or clear. "
    "The host binds revision, anchor, coordinates, and two-second timing; actors stay planted. "
    "No other fields, prose, or Markdown."
)
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
_SAFE_RUN_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")


def _safe_run_id(run_id: str) -> bool:
    # Harness2 uses namespace/task/label; standalone executions use one segment.
    return (type(run_id) is str and len(run_id) <= 360 and
            1 <= len(run_id.split("/")) <= 3 and
            all(_SAFE_RUN_SEGMENT.fullmatch(part) and part != ".."
                for part in run_id.split("/")))


def _canonical_expected(plan: dict, scene: dict) -> dict:
    """Verify host oracle is itself the canonical compiler output for this scene."""
    if not isinstance(plan, dict):
        raise ValueError("expected plan must be a canonical staging plan")
    try:
        positions = {actor["id"]: actor["x_m"] for actor in plan["actors"]}
        ids = scene["actor_ids"]
        left, right = sorted(ids, key=lambda actor_id: positions[actor_id])
        intent = {
            "scene_revision": scene["revision"],
            "placements": [
                {"actor_id": left, "anchor_id": scene["anchor"]["id"], "side": "left"},
                {"actor_id": right, "anchor_id": scene["anchor"]["id"], "side": "right"},
            ],
            "cues": [{key: cue[key] for key in ("slot", "actor_id", "gesture", "variation")}
                     for cue in plan["cues"]],
        }
        canonical = compile_staging(json.dumps(intent), scene)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise ValueError("expected plan must be a canonical staging plan") from exc
    if plan != canonical:
        raise ValueError("expected plan differs from canonical staging output")
    return copy.deepcopy(canonical)


def verdict(raw: str, task: dict, expected: dict, *, snapshot=None) -> dict:
    """Score strict compilation separately from private semantic correctness."""
    try:
        plan = compile_compact(raw, snapshot if snapshot is not None else bind_scene(task["scene"]),
                               task["scene"])
    except (ValueError, TypeError) as exc:
        return {"accepted_format": False, "semantic_correct": False, "valid": False,
                "reason": str(exc)}
    correct = plan == expected
    return {"accepted_format": True, "semantic_correct": correct, "valid": correct,
            "reason": "correct staging plan" if correct else "plan does not match the request",
            "plan": plan}


class StagingAdapter(ProductionAdapter):
    """One bounded solver attempt per execution, with host-only expected plans."""

    def __init__(self, root: Path, tasks: Mapping[str, dict], expected: Mapping[str, dict],
                 train_ids: Sequence[str], *, provider: Provider = chat_completion,
                 base_url: str, model: str, api_key: str | None = None,
                 max_solver_calls: int = 20, request_timeout: float = 20.0,
                 max_output_tokens: int = 128):
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
        self.snapshots = {}
        for task_id, original in tasks.items():
            if type(task_id) is not str or _SAFE_ID.fullmatch(task_id) is None:
                raise ValueError("invalid task id")
            task = copy.deepcopy(original)
            if not isinstance(task, dict) or set(task) != {"task_id", "scene", "request"}:
                raise ValueError("task requires exactly task_id, scene, and request")
            if task["task_id"] != task_id:
                raise ValueError("task mapping key differs from task_id")
            if (type(task["request"]) is not str or not 1 <= len(task["request"]) <= 3000
                    or any(ord(char) < 32 and char not in "\n\t" for char in task["request"])):
                raise ValueError("bounded request required")
            self.snapshots[task_id] = bind_scene(task["scene"])
            self.task_data[task_id] = task
        if set(expected) != set(self.task_data):
            raise ValueError("expected plans must cover exactly the task mapping")
        self.expected = {task_id: _canonical_expected(copy.deepcopy(plan), self.task_data[task_id]["scene"])
                         for task_id, plan in expected.items()}
        self.train_ids = tuple(train_ids)
        if len(set(self.train_ids)) != len(self.train_ids) or any(
                task_id not in self.task_data for task_id in self.train_ids):
            raise ValueError("train_ids must be unique task mapping keys")
        self.substrate = OpencodeSubstrate()
        channel = ChannelSpec("opencode", "local/injected")
        self.spec = BenchSpec(
            name="actor_staging_h2", runs_root=self.root / "runs", install_mode="workspace_config",
            prompts=BenchPrompts(work="choose compact two-actor staging intent",
                                 domain_word="actor staging"),
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
        return "actor-staging"

    def task_prompt(self, task_id):
        if task_id not in self.train_ids:
            raise ValueError("editor context is restricted to development tasks")
        return "Development scene and request (source data):\n" + json.dumps(
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
        user = json.dumps({"scene": task["scene"], "request": task["request"]}, sort_keys=True)
        system = guidance + "\n" + PUBLIC_CONTRACT
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
                scored = verdict(response.content, task, self.expected[task_id],
                                 snapshot=self.snapshots[task_id])
                receipt["verdict"] = scored
                (run_dir / "proposal.json").write_text(response.content + "\n")
                (run_dir / "verdict.json").write_text(json.dumps(scored, indent=2) + "\n")
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
            "[ACTION] Solver proposed compact staging\n"
            + "[OBSERVATION] " + str(receipt.get("content", ""))[:2048] + "\n"
            + "[HOST] " + str(status) + "\n")
        return run_dir

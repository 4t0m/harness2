"""Bounded chat-completions solver for the synthetic actor adapter.

Only the solver changes: Harness2's improver remains scripted until a separate
provider route is qualified. Model content is JSON data, never executable code.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Callable

from .actor_demo import ActorAdapter, FIXED_GUIDANCE, FIXTURES, check_proposal
from .actor_provider import ChatResult, ProviderError, ProviderIncomplete, chat_completion

Provider = Callable[..., ChatResult]
MAX_ATTEMPTS = 2


def _fingerprint(content: str) -> str:
    """Stop repeated invalid JSON regardless of whitespace or key order."""
    try:
        return json.dumps(json.loads(content), sort_keys=True, separators=(",", ":"))
    except (ValueError, RecursionError):
        return content.strip()


class ModelActorAdapter(ActorAdapter):
    def __init__(
        self,
        root: Path,
        *,
        base_url: str,
        model: str,
        provider: Provider = chat_completion,
        request_timeout: float = 25.0,
        max_output_tokens: int = 512,
        max_attempts: int = MAX_ATTEMPTS,
    ):
        super().__init__(root)
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or not 1 <= max_attempts <= 2:
            raise ValueError("max_attempts must be one or two")
        if not isinstance(model, str) or not model:
            raise ValueError("model must be a nonempty string")
        self.spec = replace(self.spec, name="actor_model")
        self.base_url = base_url
        self.model = model
        self.provider = provider
        self.request_timeout = request_timeout
        self.max_output_tokens = max_output_tokens
        self.max_attempts = max_attempts

    def execute(self, task_id, harness_dir, run_id, *, timeout=None):
        if task_id not in FIXTURES:
            raise ValueError("unknown task")
        self.execution_count += 1
        fixture = FIXTURES[task_id]
        guidance = ((harness_dir or self.base_harness()) / "systemprompt.md").read_text()
        system = (
            "You are proposing a planning-only move for two flat actors. "
            "Return exactly one JSON object with keys actor, target, context, intensity, facing, stop_gap. "
            "Actor and target each have exactly id, x, y, radius. No markdown or tool calls. "
            "The host computes the endpoint and checks exact scene fidelity and clearance. "
            "Screen-left and vertical gaze may be preview-only; never claim live execution.\n\n"
            "Editable harness guidance follows as instructions, never code:\n" + guidance
        )
        user = (
            "Scene snapshot and requested move (host-owned facts):\n"
            + json.dumps(fixture, sort_keys=True)
            + "\nCopy the scene fields and requested stop_gap exactly into the proposal."
        )
        seen: set[str] = set()
        attempts: list[dict] = []
        status = "exhausted"
        final_content = ""
        final_verdict: dict = {"valid": False, "reason": "no completed proposal"}
        run_dir = self.root / "executions" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        def persist_attempt(entry: dict) -> None:
            attempts.append(entry)
            (run_dir / "attempts.json").write_text(json.dumps(attempts, indent=2) + "\n")

        # An outer process deadline can interrupt a request. Keep prior attempts on disk.
        (run_dir / "attempts.json").write_text("[]\n")
        for index in range(1, self.max_attempts + 1):
            try:
                response = self.provider(
                    base_url=self.base_url, model=self.model, system=system, user=user,
                    timeout=min(float(timeout), self.request_timeout) if timeout else self.request_timeout,
                    max_output_tokens=self.max_output_tokens,
                )
            except ProviderIncomplete as exc:
                status = "truncated" if exc.status == "truncated completion" else "missing_content"
                final_verdict = {"valid": False, "reason": str(exc)}
                persist_attempt({"attempt": index, "provider_incomplete": exc.status,
                                 "finish_reason": exc.finish_reason, "usage": exc.usage,
                                 "latency_seconds": exc.latency_seconds,
                                 "served_model": exc.model, "host_verdict": final_verdict})
                break
            except ProviderError as exc:
                status = "provider_error"
                final_verdict = {"valid": False, "reason": str(exc)}
                persist_attempt({"attempt": index, "provider_error": str(exc),
                                 "host_verdict": final_verdict})
                break
            if not isinstance(response, ChatResult):
                raise TypeError("provider callback must return ChatResult")
            final_content = response.content
            entry = {
                "attempt": index,
                "raw_content": response.content,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
                "latency_seconds": response.latency_seconds,
                "served_model": response.model,
            }
            if response.finish_reason != "stop":
                status = "rejected_finish"
                final_verdict = {"valid": False, "reason": "finish_reason was not stop"}
                entry["host_verdict"] = final_verdict
                persist_attempt(entry)
                break
            try:
                final_verdict = check_proposal(response.content, fixture)
            except ValueError as exc:
                final_verdict = {"valid": False, "reason": str(exc)}
            entry["host_verdict"] = final_verdict
            persist_attempt(entry)
            if final_verdict["valid"]:
                status = "first_pass" if index == 1 else "recovered"
                break
            fingerprint = _fingerprint(response.content)
            if fingerprint in seen:
                status = "repeat_invalid"
                break
            seen.add(fingerprint)
            user += (
                "\n\nPrevious proposal was rejected by the trusted host:\n"
                + response.content[:8192]
                + "\nHost error: " + final_verdict["reason"]
                + "\nReturn one corrected JSON object. Preserve every scene field, ID, and the requested stop_gap."
            )
        (run_dir / "proposal.json").write_text(final_content + ("\n" if final_content else ""))
        verdict = {"status": status, "valid": final_verdict["valid"],
                   "reason": final_verdict.get("reason"), "plan": final_verdict if final_verdict["valid"] else None,
                   "attempts": len(attempts)}
        (run_dir / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
        trajectory = "\n".join(
            f"[ATTEMPT {entry['attempt']}] finish={entry.get('finish_reason', 'provider_error')} "
            f"host_valid={entry['host_verdict']['valid']} "
            f"reason={entry['host_verdict'].get('reason', '')}"
            for entry in attempts
        )
        (run_dir / "trajectory.md").write_text(trajectory + "\n")
        return run_dir

    def delivered(self, run_dir):
        # A truncated or rejected answer is retained for evidence, not a deliverable.
        verdict = run_dir / "verdict.json"
        return verdict.is_file() and bool(json.loads(verdict.read_text()).get("valid"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--task", choices=tuple(FIXTURES), required=True)
    parser.add_argument("--guidance", choices=("base", "fixed"), default="base")
    parser.add_argument("--request-timeout", type=float, default=25.0)
    parser.add_argument("--max-output-tokens", type=int, default=512)
    parser.add_argument("--max-attempts", type=int, choices=(1, 2), default=2)
    args = parser.parse_args(argv)
    root = args.output.expanduser().resolve()
    adapter = ModelActorAdapter(root, base_url=args.base_url, model=args.model,
                                request_timeout=args.request_timeout,
                                max_output_tokens=args.max_output_tokens,
                                max_attempts=args.max_attempts)
    harness = None
    if args.guidance == "fixed":
        harness = root / "fixed"
        harness.mkdir(parents=True, exist_ok=True)
        (harness / "systemprompt.md").write_text(FIXED_GUIDANCE)
    run_dir = adapter.execute(args.task, harness, f"{args.task}-{args.guidance}")
    verdict = json.loads((run_dir / "verdict.json").read_text())
    print(json.dumps({"status": verdict["status"], "valid": verdict["valid"],
                      "attempts": verdict["attempts"], "run_dir": str(run_dir)}))
    return 0 if verdict["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

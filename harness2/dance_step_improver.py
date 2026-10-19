"""Bounded candidate evidence for the structured-step Harness2 editor.

The upstream compose context already stages candidate diffs and rollouts. This
proposer adds those development-only files to ProductionImprover's HTTP request
without changing the shared collector or its historical behavior.
"""

from __future__ import annotations

from contextvars import ContextVar
import hashlib
import json
from pathlib import Path

from .actor_provider import chat_completion
from .core.proposer import ProposerError
from .dance_step_h2 import EDITOR_PUBLIC_RULE
from .production_h2 import ProductionImprover, Provider

_LABELS = ("dom1", "inv1")
_FILES = ("harness.diff", "rollout.md")
_MAX_FILE_BYTES = 6000
_MAX_POOL_BYTES = 8000
_MAX_USER_BYTES = 30000


def _pool_context(context: Path) -> tuple[str, list[dict]]:
    """Read only two known staged development candidates, rejecting path tricks."""
    context = Path(context)
    if context.is_symlink() or not context.is_dir():
        raise ValueError("editor context unavailable")
    pool = context / "pool"
    if pool.is_symlink() or (pool.exists() and
            (not pool.is_dir() or not pool.resolve().is_relative_to(context.resolve()))):
        raise ValueError("unsafe candidate pool")
    if not pool.exists():
        return "", []
    parts, files, total = [], [], 0
    for label in _LABELS:
        directory = pool / label
        if directory.is_symlink() or (directory.exists() and
                (not directory.is_dir() or not directory.resolve().is_relative_to(pool.resolve()))):
            raise ValueError("unsafe candidate directory")
        if not directory.exists():
            continue
        for filename in _FILES:
            path = directory / filename
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
                raise ValueError("candidate evidence file missing or unsafe")
            data = path.read_bytes()
            if len(data) > _MAX_FILE_BYTES or total + len(data) > _MAX_POOL_BYTES:
                raise ValueError("candidate evidence exceeds byte cap")
            try:
                body = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("candidate evidence must be UTF-8") from exc
            name = f"pool/{label}/{filename}"
            parts.append(f"## {name}\n{body}")
            files.append({"name": name, "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest()})
            total += len(data)
    if bool(files) and len(files) != len(_LABELS) * len(_FILES):
        raise ValueError("incomplete candidate pool")
    return "\n\n".join(parts), files


class StepImprover(ProductionImprover):
    """ProductionImprover plus a verified, bounded development candidate pool."""

    def __init__(self, spec, *, provider: Provider = chat_completion, base_url: str,
                 model: str, audit_dir: Path, api_key: str | None = None,
                 max_editor_calls: int = 3, request_timeout: float = 20.0,
                 max_output_tokens: int = 512,
                 guidance_domain: str = "four-step constrained motion planning",
                 public_rule: str = EDITOR_PUBLIC_RULE):
        self._underlying_provider = provider
        self._active = ContextVar(f"step_candidate_pool_{id(self)}", default=None)
        super().__init__(spec, provider=self._send_with_pool, base_url=base_url,
                         model=model, audit_dir=audit_dir, api_key=api_key,
                         max_editor_calls=max_editor_calls,
                         request_timeout=request_timeout,
                         max_output_tokens=max_output_tokens,
                         guidance_domain=guidance_domain, public_rule=public_rule)

    def _send_with_pool(self, **kwargs):
        active = self._active.get()
        if active is not None:
            user = kwargs["user"]
            if active["text"]:
                user += "\n\n## Development candidate pool evidence\n" + active["text"]
            if len(user.encode("utf-8")) > _MAX_USER_BYTES:
                raise ValueError("editor request exceeds byte cap")
            kwargs["user"] = user
            active["user_sha256"] = hashlib.sha256(user.encode("utf-8")).hexdigest()
        return self._underlying_provider(**kwargs)

    def call(self, mission, context_dir, label, **kwargs):
        if label.startswith(("select.", "experience.")):
            return super().call(mission, context_dir, label, **kwargs)
        scope = hashlib.sha256(str(Path(context_dir).absolute()).encode()).hexdigest()[:12]
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
        audit = self.audit_dir / f"{scope}-{safe_label}.json"
        if audit.exists():
            raise ProposerError("editor receipt already exists")
        pool_text, pool_files = _pool_context(Path(context_dir))
        active = {"text": pool_text, "files": pool_files, "user_sha256": None}
        token = self._active.set(active)
        try:
            return super().call(mission, context_dir, label, **kwargs)
        finally:
            self._active.reset(token)
            if audit.is_file():
                record = json.loads(audit.read_text(encoding="utf-8"))
                record["pool_included_files"] = pool_files
                record["included_files"] = record.get("included_files", []) + [
                    item["name"] for item in pool_files]
                record["editor_user_sha256"] = active["user_sha256"]
                audit.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

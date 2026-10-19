"""Bounded patch-first routing for approved phrase edits.

The callback owns prompts and transport. This router only checks host structure;
semantic acceptance belongs to an external oracle after a valid edit is returned.
"""

from __future__ import annotations

from collections.abc import Callable

from .dance_phrase_edit import (
    EditSnapshot, _check_current, apply_patch, validate_edit,
    validate_full_replacement,
)

MAX_ROUTER_REPLY_BYTES = 4096


class ProviderReplyError(RuntimeError):
    """The callback did not return one bounded complete text reply."""


def _reply(provider: Callable, mode: str, previous_raw: str | None,
           rejection_reason: str | None) -> str:
    # Deliberately outside compiler-exception handlers: transport and incomplete
    # replies never become a reason to try a second model format.
    raw = provider(mode, previous_raw, rejection_reason)
    if type(raw) is not str or not raw:
        raise ProviderReplyError("provider reply was incomplete")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise ProviderReplyError("provider reply was not UTF-8 text") from exc
    if size > MAX_ROUTER_REPLY_BYTES:
        raise ProviderReplyError("provider reply exceeded router bound")
    return raw


def route_edit(snapshot: EditSnapshot, current_source_raw: str,
               current_revision: str, current_slots: list[int] | tuple[int, ...],
               provider: Callable[[str, str | None, str | None], str]) -> dict:
    """Try one patch, then one full rewrite only after structural rejection.

    Returns ``{accepted, edit, attempts}``; no motion is committed or executed.
    Each attempt records the exact bounded reply and compiler verdict.
    """
    if not callable(provider):
        raise ValueError("provider callback required")
    # Capture caller-owned scope before any callback; strings are immutable.
    scope = tuple(current_slots) if type(current_slots) in (list, tuple) else current_slots
    source = current_source_raw
    revision = current_revision
    _check_current(snapshot, source, revision, scope)
    attempts = []

    raw_patch = _reply(provider, "patch", None, None)
    try:
        edit = apply_patch(raw_patch, snapshot, source, revision, scope)
    except ValueError as exc:
        reason = str(exc)
        attempts.append({"mode": "patch", "raw": raw_patch, "accepted": False,
                         "reason": reason})
    else:
        validate_edit(edit, snapshot, source, revision, scope)
        attempts.append({"mode": "patch", "raw": raw_patch, "accepted": True,
                         "reason": "structurally accepted"})
        return {"accepted": True, "edit": edit, "attempts": attempts}

    raw_full = _reply(provider, "full", raw_patch, reason)
    try:
        edit = validate_full_replacement(raw_full, snapshot, source, revision, scope)
    except ValueError as exc:
        attempts.append({"mode": "full", "raw": raw_full, "accepted": False,
                         "reason": str(exc)})
        return {"accepted": False, "edit": None, "attempts": attempts}
    validate_edit(edit, snapshot, source, revision, scope)
    attempts.append({"mode": "full", "raw": raw_full, "accepted": True,
                     "reason": "structurally accepted"})
    return {"accepted": True, "edit": edit, "attempts": attempts}

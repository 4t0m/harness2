"""Narrow subprocess bridge to Hermes's trusted flat-avatar helper.

Only an operator configures the Python executable and Hermes tools directory.
The model-facing inputs are the fixed action enum and a short hold duration.
Worker output has separate delivery, readback, cleanup and pixel-verification fields.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


ACTIONS = frozenset({"look_right", "neutral"})
MAX_STDOUT_BYTES = 65_536
MAX_STDERR_BYTES = 8_192


class AvatarBridgeError(Exception):
    """A bridge failure without subprocess output or environment details."""


def _validate_action(action: str, hold_seconds: int) -> None:
    if type(action) is not str or action not in ACTIONS:
        raise ValueError("unsupported avatar action")
    if type(hold_seconds) is not int or not 1 <= hold_seconds <= 3:
        raise ValueError("hold_seconds must be an integer from 1 to 3")


def _operator_paths(python_executable: str | Path, tools_dir: str | Path) -> tuple[str, str]:
    python = Path(python_executable)
    tools = Path(tools_dir)
    if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError("operator Python executable is unavailable")
    if (not tools.is_absolute() or not tools.is_dir()
            or not (tools / "avatar_safe_mcp.py").is_file()
            or not (tools / "anime_avatar_mcp.py").is_file()):
        raise ValueError("operator Hermes tools directory is unavailable")
    return str(python), str(tools)


def _parse_worker_output(stdout: str) -> dict[str, Any]:
    if len(stdout.encode("utf-8")) > MAX_STDOUT_BYTES:
        raise AvatarBridgeError("avatar worker output too large")
    try:
        lines = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    except (ValueError, RecursionError):
        raise AvatarBridgeError("malformed avatar worker output") from None
    if (len(lines) != 2 or not all(isinstance(item, dict) for item in lines)
            or lines[0].get("phase") != "applied" or lines[1].get("phase") != "finished"):
        raise AvatarBridgeError("malformed avatar worker output")
    applied, finished = lines
    return {
        "status": "finished" if finished.get("error_type") is None else "worker_error",
        "action": applied.get("action"),
        "hold_seconds": applied.get("hold_seconds"),
        "delivery_confirmed": applied.get("delivery_confirmed") is True,
        "readback_ok": finished.get("readback_ok") is True,
        "cleanup_confirmed": finished.get("cleanup_confirmed") is True,
        "control_receipt": applied.get("control_receipt"),
        "readback_receipt": finished.get("readback_receipt"),
        "cleanup_receipt": finished.get("cleanup_receipt"),
        "error_type": finished.get("error_type"),
        "pixels_verified": False,
        "visual_check": "not_assessed",
    }


def run_avatar(
    action: str,
    hold_seconds: int,
    *,
    python_executable: str | Path,
    tools_dir: str | Path,
    wall_timeout_seconds: int = 30,
    cleanup_grace_seconds: int = 12,
) -> dict[str, Any]:
    """Run one trusted avatar action, then wait for readback and cleanup.

    On timeout, send SIGTERM so the trusted helper can run its cleanup hook.
    The combined wall bound is ``wall_timeout_seconds + cleanup_grace_seconds``.
    """
    _validate_action(action, hold_seconds)
    python, tools = _operator_paths(python_executable, tools_dir)
    if (type(wall_timeout_seconds) is not int or not 1 <= wall_timeout_seconds <= 90
            or type(cleanup_grace_seconds) is not int or not 1 <= cleanup_grace_seconds <= 15):
        raise ValueError("invalid avatar wall timeout")
    command = [python, "-I", "-B", str(Path(__file__).resolve()), "--worker", action,
               str(hold_seconds)]
    env = {"PATH": os.defpath, "HERMES_AVATAR_TOOLS": tools, "PYTHONIOENCODING": "utf-8"}
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=env)
    except OSError:
        raise AvatarBridgeError("avatar worker could not start") from None
    try:
        stdout, stderr = process.communicate(timeout=wall_timeout_seconds)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.communicate(timeout=cleanup_grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        raise AvatarBridgeError("avatar worker timed out; cleanup unverified") from None
    if process.returncode != 0:
        raise AvatarBridgeError("avatar worker failed; cleanup unverified")
    if len(stderr.encode("utf-8")) > MAX_STDERR_BYTES:
        raise AvatarBridgeError("avatar worker error output too large")
    result = _parse_worker_output(stdout)
    if result["action"] != action or result["hold_seconds"] != hold_seconds:
        raise AvatarBridgeError("avatar worker receipt mismatch")
    return result


def _receipt_subset(value: object, fields: tuple[str, ...]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {key: value[key] for key in fields if key in value}


def _worker_once(safe: Any, action: str, hold_seconds: int,
                 *, sleep: Callable[[int], None], emit: Callable[[dict], None]) -> None:
    """Worker lifecycle, factored so offline tests can inject a fake helper."""
    control = None
    readback = None
    cleanup = None
    error_type = None
    try:
        control = safe.anime_avatar_control(action, hold_seconds)
        control_receipt = _receipt_subset(control, (
            "ok", "action", "http_status", "receipt_matches", "hold_seconds",
            "state_readback_status", "full_receipt_file",
        ))
        delivery = bool(isinstance(control, dict) and control.get("ok") is True
                        and control.get("receipt_matches") is True)
        emit({"phase": "applied", "action": action, "hold_seconds": hold_seconds,
              "delivery_confirmed": delivery, "control_receipt": control_receipt,
              "pixels_verified": False})
        if delivery:
            sleep(hold_seconds)
        readback = safe.anime_avatar_readback()
    except Exception as exc:
        error_type = type(exc).__name__
        if control is None:
            emit({"phase": "applied", "action": action, "hold_seconds": hold_seconds,
                  "delivery_confirmed": False, "control_receipt": None,
                  "pixels_verified": False})
    finally:
        try:
            cleanup = safe.cleanup("bridge_worker_exit")
        except Exception as exc:
            error_type = error_type or type(exc).__name__
        readback_receipt = _receipt_subset(readback, (
            "ok", "relay_http_status", "state_readback_http_status", "full_receipt_file",
        ))
        cleanup_receipt = _receipt_subset(cleanup, (
            "attempted", "http_status", "receipt_matches", "error", "receipt_file",
        ))
        emit({"phase": "finished", "readback_ok": isinstance(readback, dict)
              and readback.get("ok") is True,
              "cleanup_confirmed": isinstance(cleanup, dict)
              and cleanup.get("attempted") is True and cleanup.get("http_status") == 204
              and cleanup.get("receipt_matches") is True and cleanup.get("error") is None,
              "readback_receipt": readback_receipt, "cleanup_receipt": cleanup_receipt,
              "error_type": error_type, "pixels_verified": False})


def _main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] != "--worker":
        return 2
    action = sys.argv[2]
    try:
        hold_seconds = int(sys.argv[3])
        _validate_action(action, hold_seconds)
        tools = os.environ.get("HERMES_AVATAR_TOOLS", "")
        if not tools or not Path(tools).is_absolute():
            raise ValueError("operator tools directory missing")
        sys.path.insert(0, tools)
        import avatar_safe_mcp as safe

        safe.install_shutdown_handlers()
    except (ValueError, ImportError, OSError):
        return 2

    def emit(receipt: dict) -> None:
        print(json.dumps(receipt, separators=(",", ":")), flush=True)

    _worker_once(safe, action, hold_seconds, sleep=time.sleep, emit=emit)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

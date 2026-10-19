"""Finite loopback HTTP viewer for host-controlled motif playback.

The browser supplies prose only. The local model proposes compact intent; the
frozen compiler and runtime own motion, admission, timing, and interruption.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time

from .bounded_json_http import request_json
from .dance_motif_runtime import MotifRuntime
from experiments.dance_motif_probe import SCHEMAS, SYSTEMS

MODELS = ("gemma4:e2b", "hermes-lab-qwen3-8b:latest")
MAX_CALLS = 6
MAX_SAMPLES = 4000
MAX_BODY_BYTES = 4096
MAX_BRIEF_CHARS = 500
DEFAULT_HTML = Path(__file__).resolve().parents[1] / "experiments" / "motif_viewer.html"
SOURCE_FILES = (
    "harness2/motif_viewer.py", "harness2/dance_motif_runtime.py",
    "harness2/dance_motif_score.py", "harness2/dance_phrases.py",
    "harness2/dance_motion.py", "harness2/bounded_json_http.py",
    "experiments/dance_motif_probe.py",
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unique_pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _nonfinite(_value):
    raise ValueError("nonfinite JSON number")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_provider(body: dict) -> dict:
    return request_json("http://127.0.0.1:11434/api/chat", body, timeout=20)


class MotifViewer:
    """A single finite loopback session. Constructing it does not start serving."""

    def __init__(self, model: str, output: str | Path, *, lifetime: int = 300,
                 provider=None, html_path: str | Path = DEFAULT_HTML,
                 clock=time.monotonic) -> None:
        if model not in MODELS:
            raise ValueError("unsupported local model")
        if type(lifetime) is not int or not 1 <= lifetime <= 600:
            raise ValueError("lifetime must be 1 to 600 seconds")
        output = Path(output)
        if not output.is_absolute() or not output.parent.is_dir() or output.exists():
            raise ValueError("output must be a new absolute path with an existing parent")
        html_path = Path(html_path)
        if not html_path.is_file() or html_path.is_symlink():
            raise ValueError("viewer HTML file is unavailable")
        html = html_path.read_bytes()
        if not html or len(html) > 1048576:
            raise ValueError("viewer HTML exceeds bound")
        if provider is not None and not callable(provider):
            raise ValueError("provider must be callable")
        self.model = model
        self.output = output
        self._html = html
        self._provider = provider or _default_provider
        self._clock = clock
        self._origin_time = clock()
        self._deadline_time = self._origin_time + lifetime
        self._lock = threading.RLock()
        self._runtime = MotifRuntime()
        self._busy = False
        self._worker: threading.Thread | None = None
        self._closing = False
        self._timer: threading.Timer | None = None
        self._report = {
            "scope": "Finite loopback motif viewer. Local intent proposals and host motion; "
                     "no persistent service, avatar rig, or aesthetic validation.",
            "model": model, "started_at_utc": _utc(), "lifetime_seconds": lifetime,
            "max_calls": MAX_CALLS, "max_samples_logged": MAX_SAMPLES,
            "provider_timeout_seconds": 20, "provider_output_tokens": 128,
            "provider_context_tokens": 4096, "sources": {}, "events": [],
            "calls": [], "served_samples_total": 0, "samples": [],
            "termination_reason": None, "ended_at_utc": None,
        }
        root = Path(__file__).resolve().parents[1]
        self._report["sources"] = {
            item: _sha((root / item).read_bytes()) for item in SOURCE_FILES
        }
        self._report["sources"]["experiments/motif_viewer.html"] = _sha(html)

        viewer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def _respond(self, code: int, value: dict, *, html_page: bool = False):
                data = viewer._html if html_page else json.dumps(
                    value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8" if html_page
                                 else "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)

            def _allowed_host(self) -> bool:
                return self.headers.get("Host") == viewer.url.removeprefix("http://")

            def do_GET(self):
                if not self._allowed_host():
                    self._respond(403, {"error": "invalid_host"})
                    return
                if self.path == "/":
                    self._respond(200, {}, html_page=True)
                elif self.path == "/state":
                    self._respond(200, viewer.state())
                else:
                    self._respond(404, {"error": "not_found"})

            def do_POST(self):
                if not self._allowed_host() or self.headers.get("Origin") != viewer.url:
                    self._respond(403, {"error": "invalid_origin"})
                    return
                if self.headers.get("Content-Type") != "application/json":
                    self._respond(415, {"error": "json_required"})
                    return
                length = self.headers.get("Content-Length")
                if length is None or not length.isascii() or not length.isdecimal():
                    self._respond(400, {"error": "invalid_length"})
                    return
                size = int(length)
                if size > MAX_BODY_BYTES:
                    self._respond(413, {"error": "body_too_large"})
                    return
                try:
                    payload = json.loads(self.rfile.read(size).decode("utf-8"),
                                         object_pairs_hook=_unique_pairs,
                                         parse_constant=_nonfinite)
                except (UnicodeError, ValueError, RecursionError):
                    self._respond(400, {"error": "invalid_json"})
                    return
                if type(payload) is not dict:
                    self._respond(400, {"error": "object_required"})
                    return
                if self.path == "/direct":
                    if (set(payload) != {"brief"} or type(payload["brief"]) is not str
                            or not payload["brief"].strip()
                            or len(payload["brief"]) > MAX_BRIEF_CHARS):
                        self._respond(400, {"error": "invalid_brief"})
                        return
                    code, value = viewer.direct(payload["brief"])
                elif self.path == "/stop" and payload == {}:
                    code, value = viewer.stop()
                elif self.path == "/shutdown" and payload == {}:
                    code, value = viewer.shutdown()
                elif self.path in ("/stop", "/shutdown"):
                    code, value = 400, {"error": "empty_object_required"}
                else:
                    code, value = 404, {"error": "not_found"}
                self._respond(code, value)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._httpd.server_address[1]}"
        self._report["url"] = self.url
        # O_EXCL prevents an old receipt from being replaced by a new session.
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        with self._lock:
            self._save()

    def _now(self) -> int:
        return max(0, int((self._clock() - self._origin_time) * 1000))

    def _save(self) -> None:
        """Caller holds lock; replace receipt atomically after meaningful events."""
        fd, name = tempfile.mkstemp(prefix=self.output.name + ".", dir=self.output.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._report, handle, indent=2, allow_nan=False)
                handle.write("\n")
            os.replace(name, self.output)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _event(self, kind: str, at_ms: int, **fields) -> None:
        if len(self._report["events"]) < 1000:
            self._report["events"].append({"kind": kind, "at_ms": at_ms, **fields})
        else:
            self._report["events_dropped"] = self._report.get("events_dropped", 0) + 1

    def _sample(self, at_ms: int, *, log: bool) -> dict:
        sample = self._runtime.sample(at_ms)
        if log:
            self._report["served_samples_total"] += 1
            if len(self._report["samples"]) < MAX_SAMPLES:
                self._report["samples"].append({
                    "at_ms": at_ms, "status": sample["status"],
                    "source_frame_index": sample["source_frame_index"],
                    "score_sha256": sample["score_sha256"],
                    "frame_sha256": _sha(json.dumps(sample["frame"], sort_keys=True,
                                                   separators=(",", ":")).encode("utf-8")),
                })
        return sample

    def state(self) -> dict:
        with self._lock:
            at = self._now()
            sample = self._sample(at, log=True)
            snap = self._runtime.snapshot()
            if (self._report["served_samples_total"] <= MAX_SAMPLES and
                    self._report["served_samples_total"] % 20 == 0):
                self._save()
            # A failed worker has no outstanding computation even if the
            # runtime retains its supersedable request until the next action.
            return {"sample": sample, "pending": snap["pending"] if self._busy else None,
                    "queued_switch_ms": snap["queued_switch_ms"],
                    "events": list(self._report["events"]),
                    "calls_started": len(self._report["calls"]),
                    "worker_busy": self._busy, "model": self.model,
                    "remaining_seconds": max(0, self._deadline_time - self._clock())}

    def direct(self, brief: str) -> tuple[int, dict]:
        with self._lock:
            if self._closing:
                return 410, {"error": "session_closed"}
            if self._busy:
                return 409, {"error": "provider_busy"}
            if len(self._report["calls"]) >= MAX_CALLS:
                return 429, {"error": "call_cap_reached"}
            at = self._now()
            request = self._runtime.request(at, 5000)
            row = {"request_id": request["request_id"], "request_at_ms": at,
                   "brief": brief, "system": SYSTEMS["compact"],
                   "provider_started_ms": None, "provider_finished_ms": None,
                   "raw_response": None, "content": None, "finish_reason": None,
                   "delivery": None}
            self._report["calls"].append(row)
            self._event("request", at, request_id=request["request_id"])
            self._busy = True
            self._save()
            worker = threading.Thread(target=self._infer, args=(row,), daemon=True)
            self._worker = worker
            worker.start()
            return 202, {"request_id": request["request_id"]}

    def _infer(self, row: dict) -> None:
        body = {"model": self.model,
                "messages": [{"role": "system", "content": row["system"]},
                             {"role": "user", "content": row["brief"]}],
                "stream": False, "think": False, "format": SCHEMAS["compact"],
                "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 128},
                "keep_alive": "2m"}
        try:
            with self._lock:
                row["provider_started_ms"] = self._now()
                self._save()
            raw = self._provider(body)
            with self._lock:
                row["raw_response"] = raw
                row["provider_finished_ms"] = self._now()
                if type(raw) is not dict:
                    raise ValueError("provider JSON object required")
                message = raw.get("message")
                row["content"] = message.get("content") if type(message) is dict else None
                row["finish_reason"] = raw.get("done_reason")
                self._save()
            if row["finish_reason"] != "stop":
                raise ValueError("incomplete model response")
            prepared = self._runtime.prepare(row["content"])
            with self._lock:
                at = self._now()
                row["prepared_at_ms"] = at
                result = self._runtime.deliver_prepared(row["request_id"], prepared, at)
                row["delivery"] = result
                row["delivered_at_ms"] = at
                self._event("delivery", at, request_id=row["request_id"],
                            status=result["status"],
                            switch_at_ms=result.get("switch_at_ms"))
                self._save()
        except Exception as exc:
            with self._lock:
                at = self._now()
                row["error_type"] = type(exc).__name__
                row["error"] = str(exc)[:200]
                self._event("inference_error", at, request_id=row["request_id"],
                            error_type=type(exc).__name__)
                self._save()
        finally:
            with self._lock:
                self._busy = False
                self._save()

    def stop(self) -> tuple[int, dict]:
        with self._lock:
            if self._closing:
                return 410, {"error": "session_closed"}
            at = self._now()
            sample = self._runtime.interrupt(at)
            self._event("stop", at, revision=sample["revision"])
            self._save()
            return 200, {"sample": sample}

    def _close(self, reason: str) -> dict:
        with self._lock:
            if not self._closing:
                self._closing = True
                at = self._now()
                self._runtime.interrupt(at)
                self._event("shutdown", at, reason=reason)
                self._report["termination_reason"] = reason
                self._save()
                threading.Thread(target=self._httpd.shutdown, daemon=True).start()
            return {"termination_reason": self._report["termination_reason"]}

    def shutdown(self) -> tuple[int, dict]:
        return 200, self._close("user_shutdown")

    def serve(self) -> None:
        self._timer = threading.Timer(self._deadline_time - self._clock(),
                                      lambda: self._close("lifetime"))
        self._timer.daemon = True
        self._timer.start()
        try:
            self._httpd.serve_forever(poll_interval=0.1)
        finally:
            self._timer.cancel()
            self._httpd.server_close()
            worker = self._worker
            if worker is not None:
                worker.join(timeout=22)
            with self._lock:
                if not self._closing:
                    self._closing = True
                    at = self._now()
                    self._runtime.interrupt(at)
                    self._event("shutdown", at, reason="server_exit")
                    self._report["termination_reason"] = "server_exit"
                self._report["worker_drained"] = worker is None or not worker.is_alive()
                self._report["ended_at_utc"] = _utc()
                self._save()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Finite local motif viewer")
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--output", required=True)
    parser.add_argument("--lifetime", type=int, default=300)
    args = parser.parse_args(argv)
    viewer = MotifViewer(args.model, args.output, lifetime=args.lifetime)
    print(json.dumps({"url": viewer.url, "model": viewer.model,
                      "output": str(viewer.output)}), flush=True)
    try:
        viewer.serve()
    except KeyboardInterrupt:
        viewer._close("keyboard_interrupt")


if __name__ == "__main__":
    main()

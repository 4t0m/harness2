"""Narrow, authenticated ingress for a bounded Qwen motif trial.

This is a gate for one local vLLM process, not a general OpenAI proxy. Ending
this process does not stop or delete the rented pod and does not end billing.
"""

from __future__ import annotations

import argparse
import hmac
import http.client
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ALIAS = "qwen"
MODEL = "nvidia/Qwen3.6-35B-A3B-NVFP4"
REVISION = "6c7f09d4036e97393f82e9f9ecd1a5c35ca5ee92"
IMAGE = "vllm/vllm-openai@sha256:a77ed1c057e0458dbed205dea0ecaacd0ca2405721be6e58182bf9ee42c359f6"
MAX_BODY = 16 * 1024
MAX_UPSTREAM = 1024 * 1024
MAX_CALLS = 24
MAX_TOKENS = 128
UPSTREAM_TIMEOUT = 20


class GateError(ValueError):
    """A client request violates the trial contract."""


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateError("duplicate JSON key")
        result[key] = value
    return result


def _bad_constant(_: str) -> None:
    raise GateError("nonfinite JSON value")


def strict_json(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_BODY:
        raise GateError("request body too large")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                           parse_constant=_bad_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise GateError("JSON object required")
    return value


def _validate_chat(body: dict[str, Any]) -> None:
    allowed = {"model", "messages", "stream", "temperature", "max_tokens",
               "response_format", "chat_template_kwargs"}
    if set(body) - allowed:
        raise GateError("unsupported chat field")
    if body.get("model") != ALIAS:
        raise GateError("wrong model")
    tokens = body.get("max_tokens")
    if type(tokens) is not int or not 1 <= tokens <= MAX_TOKENS:
        raise GateError("max_tokens out of bounds")
    if body.get("stream", False) is not False:
        raise GateError("streaming unsupported")
    messages = body.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 4:
        raise GateError("messages out of bounds")
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or message["role"] not in {"system", "user", "assistant"}
                or not isinstance(message["content"], str)):
            raise GateError("unsupported message")
    if "temperature" in body:
        temp = body["temperature"]
        if type(temp) not in (int, float) or not 0 <= temp <= 1:
            raise GateError("temperature out of bounds")
    if "chat_template_kwargs" in body and body["chat_template_kwargs"] != {"enable_thinking": False}:
        raise GateError("thinking must be disabled")
    if "response_format" in body:
        fmt = body["response_format"]
        if not isinstance(fmt, dict) or fmt.get("type") != "json_schema":
            raise GateError("unsupported response format")


def vllm_command() -> list[str]:
    """Launch inside the separately pinned vLLM container image."""
    return [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL, "--revision", REVISION,
        "--host", "127.0.0.1", "--port", "8000",
        "--served-model-name", ALIAS,
        "--tensor-parallel-size", "1",
        "--quantization", "modelopt_fp4", "--kv-cache-dtype", "fp8",
        "--block-size", "128", "--moe-backend", "marlin",
        "--attention-backend", "flashinfer", "--attention-config",
        '{"use_trtllm_attention":true}', "--gpu-memory-utilization", "0.85",
        "--max-model-len", "4096", "--max-num-seqs", "1",
        "--max-num-batched-tokens", "4096", "--language-model-only",
        "--default-chat-template-kwargs", '{"enable_thinking":false}',
        "--no-enable-log-requests",
    ]


def _gpu_facts() -> dict[str, str | None]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        if result.returncode != 0:
            return {"name": None, "driver": None}
        first = result.stdout.splitlines()[0].split(",", 1)
        if len(first) != 2:
            return {"name": None, "driver": None}
        name, driver = (part.strip() for part in first)
        if not re.fullmatch(r"[\w .()+/-]{1,100}", name) or not re.fullmatch(r"\d+(?:\.\d+){1,3}", driver):
            return {"name": None, "driver": None}
        return {"name": name, "driver": driver}
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return {"name": None, "driver": None}


def _upstream(port: int, method: str, path: str, payload: bytes | None,
              internal_token: str | None, timeout: int = UPSTREAM_TIMEOUT) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if internal_token:
        headers["Authorization"] = "Bearer " + internal_token
    try:
        conn.request(method, path, payload, headers)
        response = conn.getresponse()
        raw = response.read(MAX_UPSTREAM + 1)
        if len(raw) > MAX_UPSTREAM:
            raise GateError("upstream response too large")
        # http.client never follows redirects; reject rather than relaying Location.
        if not 200 <= response.status < 300:
            raise GateError("upstream status " + str(response.status))
        return response.status, raw
    finally:
        conn.close()


class PodGate:
    def __init__(self, token: str, *, bind_host: str = "0.0.0.0", port: int = 8080,
                 upstream_port: int = 8000, internal_token: str | None = None,
                 child: subprocess.Popen[bytes] | None = None) -> None:
        if not isinstance(token, str) or len(token) < 43 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
            raise ValueError("gate token must be a strong URL-safe secret")
        if bind_host not in {"0.0.0.0", "127.0.0.1"}:
            raise ValueError("unsupported bind host")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("invalid gate port")
        if type(upstream_port) is not int or not 1 <= upstream_port <= 65535:
            raise ValueError("invalid upstream port")
        self._token = token
        self._internal_token = internal_token
        self._upstream_port = upstream_port
        self._child = child
        self._generation_lock = threading.Lock()
        self._count_lock = threading.Lock()
        self.calls_started = 0
        self.gpu = _gpu_facts()
        self.started_at = time.monotonic()
        self.ready = False
        self.readiness_diagnostic = "not_checked"
        gate = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(20)

            def log_message(self, *_: Any) -> None:
                pass  # Never log paths, headers, or bodies.

            def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
                # Base handler uses this for unknown HTTP verbs after headers parse.
                authorized = self._authorized()
                self._reply(404 if authorized else 401, {"error": "unsupported route" if authorized else "unauthorized"})

            def _authorized(self) -> bool:
                candidate = getattr(self, "headers", {}).get("Authorization", "")
                if candidate.startswith("Bearer "):
                    candidate = candidate[7:]
                else:
                    candidate = ""
                if len(candidate) > 256:
                    candidate = ""
                return hmac.compare_digest(candidate.encode(), gate._token.encode())

            def _reply(self, status: int, value: dict[str, Any] | bytes) -> None:
                raw = value if isinstance(value, bytes) else json.dumps(value, separators=(",", ":"), allow_nan=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(raw)
                self.close_connection = True

            def _dispatch(self, method: str) -> None:
                if not self._authorized():
                    self._reply(401, {"error": "unauthorized"})
                    return
                if self.path not in {"/health", "/v1/models", "/v1/chat/completions", "/trial-status"}:
                    self._reply(404, {"error": "unsupported route"})
                    return
                if method == "GET" and self.path == "/trial-status":
                    self._reply(200, gate.status())
                    return
                if method == "GET" and self.path in {"/health", "/v1/models"}:
                    try:
                        status, raw = _upstream(gate._upstream_port, "GET", self.path, None,
                                                gate._internal_token, timeout=3)
                        gate.ready = True
                        gate.readiness_diagnostic = "ready"
                        self._reply(status, raw)
                    except (OSError, TimeoutError, GateError, http.client.HTTPException):
                        gate.ready = False
                        gate.readiness_diagnostic = "upstream_unavailable"
                        self._reply(503, {"error": "upstream unavailable"})
                    return
                if method != "POST" or self.path != "/v1/chat/completions":
                    self._reply(405, {"error": "method unsupported"})
                    return
                try:
                    if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                        raise GateError("application/json required")
                    if self.headers.get("Transfer-Encoding"):
                        raise GateError("transfer encoding unsupported")
                    content_length = self.headers.get("Content-Length")
                    if content_length is None or not content_length.isdecimal():
                        raise GateError("Content-Length required")
                    length = int(content_length)
                    if length > MAX_BODY:
                        self._reply(413, {"error": "request body too large"})
                        return
                    body = strict_json(self.rfile.read(length))
                    _validate_chat(body)
                except GateError as exc:
                    self._reply(400, {"error": str(exc)})
                    return
                if not gate._generation_lock.acquire(blocking=False):
                    self._reply(429, {"error": "generation busy"})
                    return
                try:
                    with gate._count_lock:
                        if gate.calls_started >= MAX_CALLS:
                            self._reply(429, {"error": "call limit reached"})
                            return
                        gate.calls_started += 1
                    payload = json.dumps(body, separators=(",", ":"), allow_nan=False).encode()
                    try:
                        status, raw = _upstream(gate._upstream_port, "POST", self.path, payload,
                                                gate._internal_token)
                        self._reply(status, raw)
                    except (OSError, TimeoutError, GateError, http.client.HTTPException):
                        self._reply(502, {"error": "upstream failed"})
                finally:
                    gate._generation_lock.release()

            def do_GET(self) -> None:
                self._dispatch("GET")

            def do_POST(self) -> None:
                self._dispatch("POST")

            def do_PUT(self) -> None:
                self._dispatch("PUT")

            do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = do_PUT

        self.server = ThreadingHTTPServer((bind_host, port), Handler)
        self.server.daemon_threads = True

    @property
    def address(self) -> tuple[str, int]:
        return self.server.server_address[:2]

    def status(self) -> dict[str, Any]:
        exit_code = None if self._child is None else self._child.poll()
        if exit_code is None:
            self.check_ready()
        else:
            self.ready = False
            self.readiness_diagnostic = "child_exited"
        with self._count_lock:
            calls = self.calls_started
        return {
            "model": ALIAS, "checkpoint": MODEL, "revision": REVISION,
            "gpu": self.gpu, "vllm_ready": self.ready and exit_code is None,
            "readiness_diagnostic": self.readiness_diagnostic,
            "child_exit_code": exit_code, "calls_started": calls,
            "calls_remaining": MAX_CALLS - calls,
            "billing_cleanup_required": True,
        }

    def check_ready(self) -> bool:
        try:
            _upstream(self._upstream_port, "GET", "/health", None,
                      self._internal_token, timeout=2)
            _, raw = _upstream(self._upstream_port, "GET", "/v1/models", None,
                               self._internal_token, timeout=2)
            models = json.loads(raw)
            if not isinstance(models, dict) or not any(
                isinstance(item, dict) and item.get("id") == ALIAS
                for item in models.get("data", [])
            ):
                raise GateError("model alias unavailable")
            self.ready = True
            self.readiness_diagnostic = "ready"
        except (OSError, TimeoutError, GateError, http.client.HTTPException,
                json.JSONDecodeError, TypeError):
            self.ready = False
            self.readiness_diagnostic = "upstream_unavailable"
        return self.ready

    def serve_forever(self) -> None:
        self.server.serve_forever(poll_interval=0.2)

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--bind-host", choices=["0.0.0.0", "127.0.0.1"], default="0.0.0.0")
    parser.add_argument("--token-env", default="MOTIF_GATE_TOKEN")
    parser.add_argument("--startup-timeout", type=int, default=300)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.token_env):
        parser.error("invalid token environment variable name")
    if not 1 <= args.startup_timeout <= 600:
        parser.error("startup timeout must be 1..600 seconds")
    token = os.environ.get(args.token_env, "")
    if len(token) < 43 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        parser.error("a strong ephemeral gate token is required")
    internal_token = secrets.token_urlsafe(32)
    child_env = {key: value for key, value in os.environ.items()
                 if key != args.token_env and not any(part in key.upper() for part in ("TOKEN", "KEY", "SECRET"))}
    child_env["VLLM_API_KEY"] = internal_token
    child_env["HF_HOME"] = "/tmp/motif-hf-cache"
    child_env["VLLM_HAS_FLASHINFER_CUBIN"] = "1"
    log = tempfile.NamedTemporaryFile(prefix="motif-vllm-", suffix=".log", delete=False)
    os.chmod(log.name, 0o600)
    child = None
    gate = None
    log_thread = None
    try:
        child = subprocess.Popen(vllm_command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=child_env, shell=False)
        def management_log() -> None:
            # Use the existing authenticated RunPod management log surface.
            # No HTTP log route; both ephemeral tokens are removed from output.
            skipping = False
            for raw in iter(lambda: child.stdout.readline(8192), b""):
                if skipping or not raw.endswith(b"\n"):
                    skipping = not raw.endswith(b"\n")
                    continue
                text = raw.decode("utf-8", errors="replace")
                text = text.replace(token, "[redacted]").replace(internal_token, "[redacted]")
                log.write(text.encode("utf-8"))
                log.flush()
                print(json.dumps({"vllm_log": text.rstrip()}), flush=True)
        log_thread = threading.Thread(target=management_log, daemon=True)
        log_thread.start()
        gate = PodGate(token, bind_host=args.bind_host, port=args.port,
                       internal_token=internal_token, child=child)
        print(json.dumps({"gate_host": args.bind_host, "gate_port": gate.address[1],
                          "ready": False, "billing_cleanup_required": True}), flush=True)
        def readiness_watch() -> None:
            deadline = time.monotonic() + args.startup_timeout
            while time.monotonic() < deadline and child.poll() is None:
                if gate.check_ready():
                    return
                time.sleep(1)
            gate.readiness_diagnostic = "child_exited" if child.poll() is not None else "startup_timeout"
        threading.Thread(target=readiness_watch, daemon=True).start()
        gate.serve_forever()
    finally:
        if gate is not None:
            gate.server.server_close()
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        if log_thread is not None:
            log_thread.join(timeout=2)
        log.close()
        Path(log.name).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

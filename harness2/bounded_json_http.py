"""Thread-safe, deadline-bounded JSON POSTs for local and HTTPS model APIs."""

from __future__ import annotations

import ipaddress
import json
import re
import subprocess
import sys
from urllib.parse import urlsplit


_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_CHILD = r'''
import json, os, sys
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None

def emit(value):
    sys.stdout.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False))

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result

def reject_constant(_value):
    raise ValueError("nonfinite JSON number")

try:
    config = json.loads(sys.stdin.read())
    payload = json.dumps(config["body"], separators=(",", ":"), allow_nan=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json",
               "User-Agent": "Harness2-Bounded-JSON/1.0"}
    if config["bearer_env"] is not None:
        secret = os.environ.get(config["bearer_env"])
        if not secret or "\r" in secret or "\n" in secret:
            raise ValueError("bearer credential unavailable")
        headers["Authorization"] = "Bearer " + secret
    request = Request(config["url"], data=payload, headers=headers, method="POST")
    opener = build_opener(ProxyHandler({}), NoRedirect)
    with opener.open(request, timeout=config["timeout"]) as response:
        raw = response.read(config["max_bytes"] + 1)
        if len(raw) > config["max_bytes"]:
            raise OverflowError("response too large")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                           parse_constant=reject_constant)
        if not isinstance(value, dict):
            raise TypeError("JSON object required")
        emit({"ok": True, "value": value})
except HTTPError as exc:
    emit({"ok": False, "error": "http_status", "status": exc.code})
except Exception as exc:
    # Never emit exception messages: urllib may include URLs, headers or bodies.
    emit({"ok": False, "error": type(exc).__name__})
'''


def _valid_url(url: str) -> bool:
    if not isinstance(url, str) or not url or len(url) > 2048 or "?" in url or "#" in url or any(
            ord(char) < 33 or ord(char) == 127 for char in url):
        return False
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.port == 0):
            return False
        if parsed.scheme == "http":
            host = parsed.hostname
            if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
                return False
    except (ValueError, TypeError):
        return False
    return True


def request_json(url, body, *, timeout=45, bearer_env=None, max_bytes=1048576) -> dict:
    """POST JSON in a killable child process; return one bounded JSON object.

    Errors intentionally reveal only a category or HTTP status. In particular,
    request bodies, endpoint URLs, credentials and response text stay private.
    """
    if not _valid_url(url):
        raise ValueError("invalid HTTP endpoint")
    if (type(timeout) not in (int, float) or not 0 < timeout <= 60
            or type(max_bytes) is not int or not 1 <= max_bytes <= 1048576):
        raise ValueError("invalid HTTP request bound")
    if bearer_env is not None and (
            type(bearer_env) is not str or _ENV_NAME.fullmatch(bearer_env) is None):
        raise ValueError("bearer_env must be an environment variable name")
    try:
        config = json.dumps({"url": url, "body": body, "timeout": timeout,
                             "bearer_env": bearer_env, "max_bytes": max_bytes},
                            allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("request body must be finite JSON") from exc
    if len(config.encode("utf-8")) > 1048576:
        raise ValueError("request body exceeds bound")
    try:
        completed = subprocess.run([sys.executable, "-c", _CHILD], input=config,
                                   text=True, capture_output=True, timeout=timeout,
                                   check=False)
    except subprocess.TimeoutExpired:
        raise TimeoutError("HTTP request deadline exceeded") from None
    if completed.returncode != 0 or len(completed.stdout) > 6 * max_bytes + 4096:
        raise RuntimeError("HTTP subprocess failed")
    try:
        message = json.loads(completed.stdout)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise RuntimeError("HTTP subprocess returned invalid status") from None
    if not isinstance(message, dict) or type(message.get("ok")) is not bool:
        raise RuntimeError("HTTP subprocess returned invalid status")
    if not message["ok"]:
        if message.get("error") == "http_status" and type(message.get("status")) is int:
            raise RuntimeError(f"HTTP status {message['status']}")
        category = message.get("error")
        if type(category) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", category):
            category = "unknown"
        raise RuntimeError(f"HTTP request failed: {category}")
    if not isinstance(message.get("value"), dict):
        raise RuntimeError("HTTP subprocess returned invalid JSON object")
    return message["value"]

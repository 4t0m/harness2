"""One bounded OpenAI-compatible chat-completions request for actor experiments.

This module does not execute model output or record prompts, responses, or keys.
Endpoint compatibility must be verified separately against a real provider.
"""

from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib import error, parse, request


MAX_RESPONSE_BYTES = 1_048_576
Transport = Callable[[request.Request, float, int], bytes]


class ProviderError(Exception):
    """A safe, credential-free provider error."""


class ProviderIncomplete(ProviderError):
    """A valid response with truncated or absent answer content.

    Raw data is exposed only when the caller requested ``include_raw``.
    """

    def __init__(self, status: str, finish_reason: str, model: str,
                 usage: dict[str, int] | None, latency_seconds: float,
                 raw_response: dict[str, Any] | None):
        super().__init__(f"provider {status}")
        self.status = status
        self.finish_reason = finish_reason
        self.model = model
        self.usage = usage
        self.latency_seconds = latency_seconds
        self.raw_response = raw_response


@dataclass(frozen=True)
class ChatResult:
    content: str
    finish_reason: str
    usage: dict[str, int] | None
    latency_seconds: float
    model: str
    raw_response: dict[str, Any] | None = None


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError("provider redirect refused")


def _default_transport(req: request.Request, timeout: float, max_bytes: int) -> bytes:
    opener = request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as response:
            if response.status != 200:
                raise ProviderError(f"provider HTTP status {response.status}")
            data = response.read(max_bytes + 1)
    except error.HTTPError as exc:
        # Never include response bodies or URLs: either could echo a credential.
        raise ProviderError(f"provider HTTP status {exc.code}") from None
    except (error.URLError, TimeoutError, socket.timeout) as exc:
        if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)) or isinstance(
            exc, (TimeoutError, socket.timeout)
        ):
            raise ProviderError("provider timeout") from None
        raise ProviderError("provider connection failed") from None
    return data


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _bad_constant(_value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _parse_response(data: bytes, *, include_raw: bool, latency: float) -> ChatResult:
    if len(data) > MAX_RESPONSE_BYTES:
        raise ProviderError("provider response too large")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs,
                           parse_constant=_bad_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise ProviderError("malformed provider response") from None
    if not isinstance(value, dict):
        raise ProviderError("malformed provider response")
    if "error" in value:
        raise ProviderError("provider error response")
    choices = value.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ProviderError("malformed provider response")
    choice = choices[0]
    message = choice.get("message")
    finish_reason = choice.get("finish_reason")
    model = value.get("model")
    if (not isinstance(message, dict) or not isinstance(finish_reason, str)
            or not finish_reason or not isinstance(model, str) or not model):
        raise ProviderError("malformed provider response")
    usage = value.get("usage")
    if usage is not None:
        if not isinstance(usage, dict) or any(
            not isinstance(usage.get(k), int) or isinstance(usage[k], bool) or usage[k] < 0
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        ):
            raise ProviderError("malformed provider response")
        usage = {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise ProviderError("malformed provider response")
    if finish_reason == "length" or not content:
        status = "truncated completion" if finish_reason == "length" else "missing content"
        raise ProviderIncomplete(status, finish_reason, model, usage, latency,
                                 value if include_raw else None)
    return ChatResult(content, finish_reason, usage, latency, model, value if include_raw else None)


def chat_completion(
    *,
    base_url: str,
    model: str,
    system: str,
    user: str,
    api_key: str | None = None,
    timeout: float = 30.0,
    max_output_tokens: int = 512,
    include_raw: bool = False,
    transport: Transport | None = None,
) -> ChatResult:
    """Call a chat-completions endpoint exactly once; no retries or redirects.

    ``base_url`` includes any API prefix, for example ``https://host/v1``.
    ``api_key`` defaults to HARNESS2_ACTOR_API_KEY. Loopback HTTP can omit a key.
    A custom transport receives (Request, timeout, max_response_bytes).
    ``timeout`` is a socket operation timeout, not a total wall-clock deadline.
    A surrounding executor must enforce an overall run deadline.
    """
    parsed = parse.urlsplit(base_url)
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("invalid base URL") from None
    del port
    loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or
            (parsed.scheme == "http" and not loopback)):
        raise ValueError("base URL must be HTTPS or loopback HTTP without credentials or query")
    if (not isinstance(model, str) or not model or not isinstance(system, str)
            or not isinstance(user, str)):
        raise ValueError("invalid model or messages")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 300:
        raise ValueError("timeout must be between 0 and 300 seconds")
    if (isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int)
            or not 1 <= max_output_tokens <= 16384):
        raise ValueError("max_output_tokens must be between 1 and 16384")
    key = api_key if api_key is not None else os.environ.get("HARNESS2_ACTOR_API_KEY")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_output_tokens,
    }
    url = base_url.rstrip("/") + "/chat/completions"
    req = request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    started = time.monotonic()
    try:
        response = (transport or _default_transport)(req, float(timeout), MAX_RESPONSE_BYTES)
    except ProviderError:
        raise
    except (TimeoutError, socket.timeout):
        raise ProviderError("provider timeout") from None
    except Exception:
        # Injectable transports are not allowed to leak a secret in exception text.
        raise ProviderError("provider request failed") from None
    if not isinstance(response, bytes):
        raise ProviderError("malformed provider response")
    return _parse_response(response, include_raw=include_raw, latency=time.monotonic() - started)

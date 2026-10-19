"""Operator-configured OpenAI-compatible transport for compact motif intent.

The browser never supplies the endpoint, model alias, or authentication name.
The response retains the complete upstream object without Ollama timing claims.
"""

from __future__ import annotations

import copy
import json
import os
import re
from urllib.parse import urlsplit

from .bounded_json_http import request_json
from .dance_motif_score import MAX_INPUT_BYTES
from experiments.dance_motif_probe import SCHEMAS, SYSTEMS

MAX_CONTEXT_BYTES = 10000
MAX_RESPONSE_BYTES = 1048576
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+\-]{0,199}\Z")


def _endpoint(url: str) -> str:
    if (type(url) is not str or len(url) > 2048 or not url or
            any(ord(c) < 33 or ord(c) == 127 for c in url) or
            "\\" in url or "?" in url or "#" in url or "%" in url):
        raise ValueError("invalid chat endpoint")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid chat endpoint") from exc
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.query or parsed.fragment or port == 0 or
            not parsed.path.endswith("/v1/chat/completions") or
            "//" in parsed.path):
        raise ValueError("invalid chat endpoint")
    if parsed.scheme == "http" and parsed.hostname != "127.0.0.1":
        raise ValueError("HTTP chat endpoint must use literal 127.0.0.1")
    return url


def _usage(raw: object) -> dict:
    if type(raw) is not dict:
        raise ValueError("provider usage object required")
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = raw.get(field)
        if type(value) is not int or value < 0:
            raise ValueError("provider usage must contain nonnegative token counts")
    return copy.deepcopy(raw)


class OpenAICompatibleMotifProvider:
    """Translate the frozen local compact request into one bounded chat call."""

    provider_kind = "openai_compatible"

    def __init__(self, endpoint: str, model: str, auth_env_name: str, *,
                 checkpoint_name: str | None = None, transport=request_json) -> None:
        self.endpoint = _endpoint(endpoint)
        if type(model) is not str or _MODEL_NAME.fullmatch(model) is None:
            raise ValueError("invalid served model alias")
        if (type(auth_env_name) is not str or
                _ENV_NAME.fullmatch(auth_env_name) is None):
            raise ValueError("invalid auth environment variable name")
        secret = os.environ.get(auth_env_name)
        if not secret or "\r" in secret or "\n" in secret:
            raise ValueError("auth environment variable unavailable")
        if (checkpoint_name is not None and
                (type(checkpoint_name) is not str or
                 not 1 <= len(checkpoint_name) <= 200 or
                 any(ord(c) < 33 or ord(c) == 127 for c in checkpoint_name))):
            raise ValueError("invalid checkpoint name")
        if not callable(transport):
            raise ValueError("transport must be callable")
        self.model = model
        self.checkpoint_name = checkpoint_name or model
        self.auth_env_name = auth_env_name
        self._transport = transport

    @property
    def metadata(self) -> dict:
        return {"provider_kind": self.provider_kind,
                "checkpoint_name": self.checkpoint_name,
                "served_model": self.model}

    def __call__(self, local_request: dict) -> dict:
        if type(local_request) is not dict or local_request.get("model") != self.model:
            raise ValueError("local request model mismatch")
        messages = local_request.get("messages")
        if (type(messages) is not list or len(messages) != 2 or
                messages[0] != {"role": "system", "content": SYSTEMS["compact"]} or
                type(messages[1]) is not dict or set(messages[1]) != {"role", "content"} or
                messages[1]["role"] != "user" or
                type(messages[1]["content"]) is not str):
            raise ValueError("invalid compact conversation")
        if sum(len(m["content"].encode("utf-8")) for m in messages) > MAX_CONTEXT_BYTES:
            raise ValueError("conversation exceeds text cap")
        payload = {
            "model": self.model, "messages": copy.deepcopy(messages),
            "stream": False, "temperature": 0, "max_tokens": 128,
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "motif_intent", "strict": True,
                "schema": copy.deepcopy(SCHEMAS["compact"])}}}
        try:
            raw = self._transport(self.endpoint, payload, timeout=20,
                                  bearer_env=self.auth_env_name,
                                  max_bytes=MAX_RESPONSE_BYTES)
        except TimeoutError:
            raise TimeoutError("remote provider deadline exceeded") from None
        except Exception as exc:
            # Transport exceptions may embed URLs, headers, or response bodies.
            raise RuntimeError(f"remote transport failed: {type(exc).__name__}") from None
        if type(raw) is not dict:
            raise ValueError("provider response object required")
        try:
            response_bytes = json.dumps(raw, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("provider response must be finite JSON") from exc
        if len(response_bytes) > MAX_RESPONSE_BYTES:
            raise ValueError("provider response exceeds byte cap")
        if raw.get("model") != self.model:
            raise ValueError("provider served-model mismatch")
        choices = raw.get("choices")
        if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
            raise ValueError("provider requires one valid choice")
        choice = choices[0]
        if choice.get("index") != 0 or choice.get("finish_reason") != "stop":
            raise ValueError("provider choice incomplete or misindexed")
        message = choice.get("message")
        if (type(message) is not dict or message.get("role") != "assistant" or
                type(message.get("content")) is not str or
                not message["content"].strip() or
                len(message["content"].encode("utf-8")) > MAX_INPUT_BYTES):
            raise ValueError("provider choice content invalid")
        usage = _usage(raw.get("usage"))
        return {"provider_kind": self.provider_kind, "model": self.model,
                "message": {"role": "assistant", "content": message["content"]},
                "done_reason": "stop", "usage": usage,
                "upstream_request": payload,
                "upstream_response": copy.deepcopy(raw)}

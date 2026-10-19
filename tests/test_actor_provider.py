"""Offline contract checks for the bounded chat-completions transport."""

import json
import unittest
from unittest.mock import patch

from harness2.actor_provider import (
    MAX_RESPONSE_BYTES, ProviderError, ProviderIncomplete, _NoRedirect, chat_completion,
)


def response(**changes):
    value = {
        "model": "served-model",
        "choices": [{"message": {"role": "assistant", "content": "{\"action\":\"wait\"}"},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
    }
    value.update(changes)
    return json.dumps(value).encode()


class ActorProviderTest(unittest.TestCase):
    def test_one_request_and_selected_response_fields(self):
        calls = []

        def transport(req, timeout, max_bytes):
            calls.append((req, timeout, max_bytes))
            return response()

        with patch.dict("os.environ", {"HARNESS2_ACTOR_API_KEY": "env-secret"}):
            result = chat_completion(
                base_url="https://provider.example/v1", model="requested-model", system="rule",
                user="scene", timeout=2, max_output_tokens=23, transport=transport,
            )
        self.assertEqual(len(calls), 1)
        req, timeout, max_bytes = calls[0]
        self.assertEqual(req.full_url, "https://provider.example/v1/chat/completions")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer env-secret")
        self.assertEqual(timeout, 2)
        self.assertEqual(max_bytes, MAX_RESPONSE_BYTES)
        self.assertEqual(json.loads(req.data), {
            "model": "requested-model", "messages": [
                {"role": "system", "content": "rule"}, {"role": "user", "content": "scene"}],
            "max_tokens": 23,
        })
        self.assertEqual(result.content, '{"action":"wait"}')
        self.assertEqual(result.model, "served-model")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.usage["total_tokens"], 17)
        self.assertGreaterEqual(result.latency_seconds, 0)
        self.assertIsNone(result.raw_response)

    def test_raw_response_is_opt_in_and_caller_key_wins(self):
        def transport(req, _timeout, _max_bytes):
            self.assertEqual(req.get_header("Authorization"), "Bearer caller-secret")
            return response()

        with patch.dict("os.environ", {"HARNESS2_ACTOR_API_KEY": "env-secret"}):
            result = chat_completion(
                base_url="http://127.0.0.1:8000/v1", model="m", system="s", user="u",
                api_key="caller-secret", include_raw=True, transport=transport,
            )
        self.assertEqual(result.raw_response["model"], "served-model")

    def test_rejects_malformed_and_oversized_responses(self):
        bad = [
            b"not json", b'{"model":"m","model":"m","choices":[]}',
            response(choices=[]), response(choices=[{"message": {"content": ["fragment"]},
                                                    "finish_reason": "stop"}]),
            response(choices=[{"message": {"content": "ok"}, "finish_reason": None}]),
            response(usage={"prompt_tokens": True, "completion_tokens": 1, "total_tokens": 1}),
            b'{"model":"m","choices":[{"message":{"content":"ok"},'
            b'"finish_reason":"stop"}],"usage":NaN}',
            (b"[" * 700) + b"0" + (b"]" * 700),
            b"x" * (MAX_RESPONSE_BYTES + 1),
        ]
        for body in bad:
            with self.subTest(body=body[:40]), self.assertRaises(ProviderError):
                chat_completion(base_url="https://provider.example/v1", model="m", system="s",
                                user="u", transport=lambda *_: body)

    def test_timeout_and_errors_do_not_echo_credentials(self):
        def fail(*_):
            raise RuntimeError("caller-secret was exposed")

        for transport, expected in ((lambda *_: (_ for _ in ()).throw(TimeoutError()), "timeout"),
                                    (fail, "request failed")):
            with self.subTest(expected=expected), self.assertRaises(ProviderError) as caught:
                chat_completion(base_url="https://provider.example/v1", model="m", system="s",
                                user="u", api_key="caller-secret", transport=transport)
            self.assertIn(expected, str(caught.exception))
            self.assertNotIn("caller-secret", str(caught.exception))

    def test_reasoning_only_length_is_incomplete_with_opt_in_raw(self):
        body = response(choices=[{"message": {"role": "assistant", "content": None,
                                                "reasoning": "private reasoning"},
                                  "finish_reason": "length"}],
                        usage={"prompt_tokens": 110, "completion_tokens": 512,
                               "total_tokens": 622})
        with self.assertRaises(ProviderIncomplete) as caught:
            chat_completion(base_url="https://provider.example/v1", model="m", system="s",
                            user="u", include_raw=True, transport=lambda *_: body)
        exc = caught.exception
        self.assertEqual(exc.status, "truncated completion")
        self.assertEqual(exc.finish_reason, "length")
        self.assertEqual(exc.model, "served-model")
        self.assertEqual(exc.usage["completion_tokens"], 512)
        self.assertEqual(exc.raw_response["choices"][0]["message"]["content"], None)
        self.assertNotIn("private reasoning", str(exc))

    def test_partial_length_and_missing_content_are_not_success(self):
        for content, finish, status in (("partial JSON", "length", "truncated completion"),
                                        (None, "stop", "missing content"),
                                        ("", "stop", "missing content")):
            body = response(choices=[{"message": {"role": "assistant", "content": content},
                                      "finish_reason": finish}])
            with self.subTest(content=content, finish=finish), self.assertRaises(
                ProviderIncomplete
            ) as caught:
                chat_completion(base_url="https://provider.example/v1", model="m", system="s",
                                user="u", transport=lambda *_: body)
            self.assertEqual(caught.exception.status, status)
            self.assertIsNone(caught.exception.raw_response)

    def test_provider_error_envelope_is_distinct_and_redacted(self):
        body = b'{"error":{"message":"caller-secret refused"}}'
        with self.assertRaises(ProviderError) as caught:
            chat_completion(base_url="https://provider.example/v1", model="m", system="s",
                            user="u", api_key="caller-secret", transport=lambda *_: body)
        self.assertNotIsInstance(caught.exception, ProviderIncomplete)
        self.assertEqual(str(caught.exception), "provider error response")

    def test_url_and_limits_reject_unsafe_requests_before_transport(self):
        bad_urls = ["http://provider.example/v1", "https://user:pass@provider.example/v1",
                    "https://provider.example/v1?key=secret", "file:///tmp/socket"]
        for url in bad_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                chat_completion(base_url=url, model="m", system="s", user="u",
                                transport=lambda *_: self.fail("transport called"))
        with self.assertRaises(ValueError):
            chat_completion(base_url="https://provider.example/v1", model="m", system="s",
                            user="u", max_output_tokens=0, transport=lambda *_: b"")
        with self.assertRaises(ValueError):
            chat_completion(base_url="https://provider.example/v1", model="m", system="s",
                            user="u", timeout=True, transport=lambda *_: b"")

    def test_redirect_is_refused_before_following_target(self):
        with self.assertRaisesRegex(ProviderError, "redirect refused"):
            _NoRedirect().redirect_request(None, None, 307, "Temporary Redirect", {},
                                           "https://other.example/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()

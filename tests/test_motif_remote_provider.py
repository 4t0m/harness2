"""Offline remote-provider conversion and receipt-boundary tests."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.dance_motif_probe import SCHEMAS, SYSTEMS
from harness2.motif_remote_provider import OpenAICompatibleMotifProvider
from harness2.motif_viewer import MotifViewer


MODEL = "checkpoint/served-alias"
ENV = "MOTIF_REMOTE_TEST_TOKEN"
ENDPOINT = "https://example.invalid/v1/chat/completions"
CONTENT = '{"motif":"sway","accents":["soft","clear","soft","clear"]}'


def response(**changes):
    value = {"id": "chatcmpl-test", "model": MODEL, "object": "chat.completion",
             "choices": [{"index": 0, "message": {"role": "assistant", "content": CONTENT},
                          "finish_reason": "stop"}],
             "usage": {"prompt_tokens": 210, "completion_tokens": 23,
                       "total_tokens": 233}}
    value.update(changes)
    return value


def local_request(brief="Please sway"):
    return {"model": MODEL, "messages": [
        {"role": "system", "content": SYSTEMS["compact"]},
        {"role": "user", "content": brief}]}


class RemoteProviderTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {ENV: "sensitive-test-token"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_exact_schema_request_and_full_response_retention(self):
        calls = []

        def transport(url, body, **kwargs):
            calls.append((url, copy.deepcopy(body), kwargs))
            return response()

        provider = OpenAICompatibleMotifProvider(
            ENDPOINT, MODEL, ENV, checkpoint_name="weights-2026-10", transport=transport)
        normalized = provider(local_request())
        self.assertEqual(len(calls), 1)
        url, body, kwargs = calls[0]
        self.assertEqual(url, ENDPOINT)
        self.assertEqual(kwargs, {"timeout": 20, "bearer_env": ENV,
                                  "max_bytes": 1048576})
        self.assertEqual(body, {
            "model": MODEL, "messages": local_request()["messages"],
            "stream": False, "temperature": 0, "max_tokens": 128,
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "motif_intent", "strict": True, "schema": SCHEMAS["compact"]}}})
        self.assertEqual(normalized["provider_kind"], "openai_compatible")
        self.assertEqual(normalized["message"]["content"], CONTENT)
        self.assertEqual(normalized["done_reason"], "stop")
        self.assertEqual(normalized["usage"], response()["usage"])
        self.assertEqual(normalized["upstream_response"], response())
        self.assertEqual(normalized["upstream_request"], body)
        self.assertEqual(provider.metadata, {"provider_kind": "openai_compatible",
                                             "checkpoint_name": "weights-2026-10",
                                             "served_model": MODEL})
        self.assertNotIn("sensitive-test-token", json.dumps(normalized))
        self.assertNotIn("sensitive-test-token", json.dumps(provider.metadata))

    def test_rejects_nonoperator_endpoints_and_missing_auth_without_transport(self):
        invalid = (
            "http://localhost:8000/v1/chat/completions",
            "http://127.0.0.2:8000/v1/chat/completions",
            "http://example.invalid/v1/chat/completions",
            "https://user:pass@example.invalid/v1/chat/completions",
            "https://example.invalid/v1/chat/completions?token=x",
            "https://example.invalid/v1/chat/completions#frag",
            "https://example.invalid/other",
            "https://example.invalid:bad/v1/chat/completions",
        )
        for endpoint in invalid:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                OpenAICompatibleMotifProvider(endpoint, MODEL, ENV,
                                              transport=lambda *_a, **_k: response())
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "auth environment variable unavailable"):
                OpenAICompatibleMotifProvider(ENDPOINT, MODEL, ENV,
                                              transport=lambda *_a, **_k: response())
        with self.assertRaises(ValueError):
            OpenAICompatibleMotifProvider(ENDPOINT, MODEL, "BAD-ENV",
                                          transport=lambda *_a, **_k: response())
        self.assertEqual(OpenAICompatibleMotifProvider(
            "http://127.0.0.1:8000/v1/chat/completions", MODEL, ENV,
            transport=lambda *_a, **_k: response()).model, MODEL)

    def test_rejects_wrong_model_choice_completion_and_usage(self):
        variants = [
            response(model="different-model"),
            response(choices=[]),
            response(choices=response()["choices"] * 2),
            response(choices=[{"index": 1, "message": {"role": "assistant",
                                                   "content": CONTENT},
                               "finish_reason": "stop"}]),
            response(choices=[{"index": 0, "message": {"role": "assistant",
                                                   "content": CONTENT},
                               "finish_reason": "length"}]),
            response(choices=[{"index": 0, "message": {"role": "user",
                                                   "content": CONTENT},
                               "finish_reason": "stop"}]),
            response(usage={"prompt_tokens": True, "completion_tokens": 2,
                            "total_tokens": 3}),
            response(usage={"prompt_tokens": 1, "completion_tokens": -2,
                            "total_tokens": 3}),
            response(usage={"prompt_tokens": 1, "completion_tokens": 2}),
        ]
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                OpenAICompatibleMotifProvider(
                    ENDPOINT, MODEL, ENV, transport=lambda *_a, **_k: raw)(local_request())

    def test_timeout_and_error_are_redacted_and_context_is_capped(self):
        def timed_out(*_args, **_kwargs):
            raise TimeoutError("sensitive-test-token https://secret.invalid")

        provider = OpenAICompatibleMotifProvider(ENDPOINT, MODEL, ENV,
                                                  transport=timed_out)
        with self.assertRaisesRegex(TimeoutError, "remote provider deadline exceeded") as caught:
            provider(local_request())
        self.assertNotIn("sensitive-test-token", str(caught.exception))

        def failed(*_args, **_kwargs):
            raise RuntimeError("sensitive-test-token https://secret.invalid")

        provider = OpenAICompatibleMotifProvider(ENDPOINT, MODEL, ENV, transport=failed)
        with self.assertRaisesRegex(RuntimeError, "remote transport failed: RuntimeError") as caught:
            provider(local_request())
        self.assertNotIn("secret.invalid", str(caught.exception))
        with self.assertRaisesRegex(ValueError, "text cap"):
            provider(local_request("x" * 10000))
        with self.assertRaisesRegex(ValueError, "model mismatch"):
            provider({**local_request(), "model": "other"})

    def test_viewer_accepts_remote_identity_and_records_fake_upstream(self):
        class FakeHTTPServer:
            def __init__(self, _address, _handler):
                self.server_address = ("127.0.0.1", 42424)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            html = root / "viewer.html"
            html.write_text("<html>remote test</html>")
            output = root / "receipt.json"
            requests = []

            def fake_transport(_url, body, **_kwargs):
                requests.append(body)
                return response()

            provider = OpenAICompatibleMotifProvider(
                ENDPOINT, MODEL, ENV, checkpoint_name="weights-2026-10",
                transport=fake_transport)
            with patch("harness2.motif_viewer.ThreadingHTTPServer", FakeHTTPServer):
                viewer = MotifViewer(MODEL, output, provider=provider,
                                     provider_metadata=provider.metadata,
                                     extra_source_files=("harness2/motif_remote_provider.py",
                                                         "harness2/motif_remote_viewer.py"),
                                     html_path=html)
            receipt = json.loads(output.read_text())
            self.assertEqual(viewer.url, "http://127.0.0.1:42424")
            self.assertEqual(receipt["provider"]["provider_kind"], "openai_compatible")
            self.assertEqual(receipt["provider"]["checkpoint_name"], "weights-2026-10")
            self.assertIn("harness2/motif_remote_provider.py", receipt["sources"])
            self.assertIn("harness2/motif_remote_viewer.py", receipt["sources"])
            state = viewer.state()
            self.assertEqual(state["provider_kind"], "openai_compatible")
            self.assertEqual(state["checkpoint_name"], "weights-2026-10")
            self.assertEqual(state["model"], MODEL)
            status, accepted = viewer.direct("Please sway")
            self.assertEqual(status, 202)
            viewer._worker.join(3)
            self.assertFalse(viewer._worker.is_alive())
            self.assertEqual(viewer.state()["sample"]["status"], "playing")
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt["calls"][0]["request_id"], accepted["request_id"])
            self.assertEqual(receipt["calls"][0]["delivery"]["status"], "applied")
            self.assertEqual(receipt["calls"][0]["raw_response"]["upstream_response"],
                             response())
            self.assertEqual(receipt["calls"][0]["raw_response"]["usage"],
                             response()["usage"])
            self.assertEqual(requests[0]["model"], MODEL)
            public_receipt = output.read_text()
            for private in (ENDPOINT, ENV, "sensitive-test-token"):
                self.assertNotIn(private, public_receipt)
                self.assertNotIn(private, json.dumps(viewer.state()))


if __name__ == "__main__":
    unittest.main()

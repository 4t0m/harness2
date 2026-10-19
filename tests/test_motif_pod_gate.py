"""Offline loopback checks for the bounded rental gate."""

from __future__ import annotations

import http.client
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from experiments.motif_pod_gate import (
    ALIAS, IMAGE, MAX_CALLS, MAX_UPSTREAM, PodGate, strict_json, vllm_command,
)


TOKEN = "x" * 43


class FakeUpstream(BaseHTTPRequestHandler):
    response_mode = "normal"
    entered = threading.Event()
    release = threading.Event()
    paths: list[str] = []

    def log_message(self, *_):
        pass

    def do_GET(self):
        type(self).paths.append(self.path)
        if self.path == "/health":
            self._respond(200, b"{}")
        elif self.path == "/v1/models":
            self._respond(200, b'{"data":[{"id":"qwen"}]}')
        else:
            self._respond(404, b"{}")

    def do_POST(self):
        type(self).paths.append(self.path)
        self.rfile.read(int(self.headers["Content-Length"]))
        if self.response_mode == "blocked":
            type(self).entered.set()
            type(self).release.wait(3)
        if self.response_mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "/invocations")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.response_mode == "oversize":
            self._respond(200, b"z" * (MAX_UPSTREAM + 1))
        else:
            self._respond(200, b'{"choices":[{"message":{"content":"{}"}}]}')

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def call(gate, method, path, body=None, token=TOKEN):
    conn = http.client.HTTPConnection("127.0.0.1", gate.address[1], timeout=5)
    headers = {} if token is None else {"Authorization": "Bearer " + token}
    if body is not None:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body, headers)
    response = conn.getresponse()
    result = response.status, json.loads(response.read())
    conn.close()
    return result


def chat_body(**changes):
    body = {"model": ALIAS, "messages": [{"role": "user", "content": "motif"}],
            "max_tokens": 128, "stream": False}
    body.update(changes)
    return json.dumps(body).encode()


class PodGateTests(unittest.TestCase):
    def setUp(self):
        FakeUpstream.response_mode = "normal"
        FakeUpstream.paths = []
        FakeUpstream.entered.clear()
        FakeUpstream.release.clear()
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)
        self.upthread = threading.Thread(target=self.upstream.serve_forever, daemon=True)
        self.upthread.start()
        self.gate = PodGate(TOKEN, bind_host="127.0.0.1", port=0,
                            upstream_port=self.upstream.server_address[1])
        self.thread = threading.Thread(target=self.gate.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        FakeUpstream.release.set()
        self.gate.close()
        self.upstream.shutdown()
        self.upstream.server_close()
        self.thread.join(2)
        self.upthread.join(2)

    def test_auth_precedes_every_route_and_no_invocations(self):
        for method, path in [("GET", "/health"), ("GET", "/v1/models"),
                             ("GET", "/trial-status"), ("POST", "/v1/chat/completions"),
                             ("POST", "/invocations"), ("PUT", "/health")]:
            self.assertEqual(call(self.gate, method, path,
                                  b"{}" if method == "POST" else None, token=None)[0], 401)
        self.assertEqual(call(self.gate, "POST", "/invocations", b"{}")[0], 404)
        self.assertEqual(call(self.gate, "GET", "/health")[0], 200)
        self.assertEqual(call(self.gate, "GET", "/v1/models")[0], 200)
        self.assertEqual(FakeUpstream.paths, ["/health", "/v1/models"])

    def test_strict_json_and_model_limits(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b"[]", b"{", b"{}x"]:
            with self.assertRaises(ValueError):
                strict_json(raw)
        for body in [chat_body(model="other"), chat_body(max_tokens=129),
                     chat_body(max_tokens=True), chat_body(stream=True),
                     chat_body(tool_choice="auto"), b'{"model":"qwen","model":"qwen"}']:
            self.assertEqual(call(self.gate, "POST", "/v1/chat/completions", body)[0], 400)
        self.assertEqual(call(self.gate, "POST", "/v1/chat/completions", b"x" * 16385)[0], 413)
        self.assertEqual(self.gate.calls_started, 0)
        self.assertFalse(FakeUpstream.paths)

    def test_serial_and_total_call_cap(self):
        FakeUpstream.response_mode = "blocked"
        first = []
        worker = threading.Thread(target=lambda: first.append(call(self.gate, "POST", "/v1/chat/completions", chat_body())))
        worker.start()
        self.assertTrue(FakeUpstream.entered.wait(2))
        self.assertEqual(call(self.gate, "POST", "/v1/chat/completions", chat_body())[0], 429)
        FakeUpstream.release.set()
        worker.join(3)
        self.assertEqual(first[0][0], 200)
        FakeUpstream.response_mode = "normal"
        for _ in range(MAX_CALLS - 1):
            self.assertEqual(call(self.gate, "POST", "/v1/chat/completions", chat_body())[0], 200)
        self.assertEqual(call(self.gate, "POST", "/v1/chat/completions", chat_body())[0], 429)
        self.assertEqual(self.gate.calls_started, MAX_CALLS)
        self.assertEqual(FakeUpstream.paths.count("/v1/chat/completions"), MAX_CALLS)

    def test_upstream_redirect_and_oversize_do_not_escape(self):
        FakeUpstream.response_mode = "redirect"
        self.assertEqual(call(self.gate, "POST", "/v1/chat/completions", chat_body())[0], 502)
        FakeUpstream.response_mode = "oversize"
        self.assertEqual(call(self.gate, "POST", "/v1/chat/completions", chat_body())[0], 502)
        self.assertEqual(FakeUpstream.paths, ["/v1/chat/completions"] * 2)

    def test_status_redaction_and_pinned_launch(self):
        status = call(self.gate, "GET", "/trial-status")[1]
        text = json.dumps(status)
        self.assertIs(status["vllm_ready"], True)
        self.assertEqual(status["readiness_diagnostic"], "ready")
        self.assertIsNone(status["child_exit_code"])
        self.assertEqual(status["calls_remaining"], MAX_CALLS)
        self.assertIs(status["billing_cleanup_required"], True)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("8000", text)
        command = vllm_command()
        self.assertEqual(command[1:3], ["-m", "vllm.entrypoints.openai.api_server"])
        self.assertEqual(command[command.index("--host") + 1], "127.0.0.1")
        self.assertEqual(command[command.index("--port") + 1], "8000")
        self.assertIn("--no-enable-log-requests", command)
        self.assertEqual(command[command.index("--served-model-name") + 1], ALIAS)
        self.assertTrue(IMAGE.endswith("a77ed1c057e0458dbed205dea0ecaacd0ca2405721be6e58182bf9ee42c359f6"))
        self.assertFalse(any(TOKEN in arg for arg in command))


if __name__ == "__main__":
    unittest.main()

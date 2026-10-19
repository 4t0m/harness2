"""Offline transport checks for deadline-bounded JSON POSTs."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
import unittest

from harness2.bounded_json_http import request_json


class Handler(BaseHTTPRequestHandler):
    redirected = 0

    def log_message(self, *_args):
        pass

    def do_POST(self):
        if self.path == "/delay":
            time.sleep(0.5)
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/target")
            self.end_headers()
            return
        if self.path == "/target":
            type(self).redirected += 1
        if self.path == "/status":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"secret response body must remain hidden")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path == "/large":
            payload = b"{" + b" " * 1000 + b"}"
        elif self.path == "/malformed":
            payload = b"secret malformed body"
        elif self.path == "/array":
            payload = b"[]"
        elif self.path == "/duplicate":
            payload = b'{"a":1,"a":2}'
        elif self.path == "/nonfinite":
            payload = b'{"a":NaN}'
        else:
            payload = json.dumps({"received": json.loads(body),
                                  "authorized": self.headers.get("Authorization") ==
                                  "Bearer test-secret-value"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except BrokenPipeError:
            pass


class BoundedJsonHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.root = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_worker_thread_success_and_child_only_bearer_lookup(self):
        previous = os.environ.get("H2_TEST_BEARER")
        os.environ["H2_TEST_BEARER"] = "test-secret-value"
        result = []

        def call():
            result.append(request_json(self.root + "/ok", {"prompt": "hello"},
                                       bearer_env="H2_TEST_BEARER", timeout=2))

        try:
            worker = threading.Thread(target=call)
            worker.start()
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(result, [{"received": {"prompt": "hello"}, "authorized": True}])
        finally:
            if previous is None:
                os.environ.pop("H2_TEST_BEARER", None)
            else:
                os.environ["H2_TEST_BEARER"] = previous

    def test_total_deadline_kills_delayed_child(self):
        began = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, "deadline"):
            request_json(self.root + "/delay", {"a": 1}, timeout=0.1)
        self.assertLess(time.monotonic() - began, 0.4)

    def test_size_malformed_object_and_redirect_boundaries(self):
        with self.assertRaisesRegex(RuntimeError, "OverflowError"):
            request_json(self.root + "/large", {}, max_bytes=100)
        for endpoint in ("malformed", "array", "duplicate", "nonfinite"):
            with self.subTest(endpoint=endpoint), self.assertRaises(RuntimeError) as caught:
                request_json(self.root + "/" + endpoint, {})
            self.assertNotIn("secret", str(caught.exception))
        Handler.redirected = 0
        with self.assertRaisesRegex(RuntimeError, "HTTP status 302"):
            request_json(self.root + "/redirect", {})
        self.assertEqual(Handler.redirected, 0)

    def test_http_errors_redact_response_body_and_request_values(self):
        with self.assertRaises(RuntimeError) as caught:
            request_json(self.root + "/status", {"secret": "request-secret"})
        self.assertEqual(str(caught.exception), "HTTP status 401")
        self.assertNotIn(self.root, str(caught.exception))
        self.assertNotIn("request-secret", str(caught.exception))

    def test_endpoint_and_bounds_refuse_unsafe_inputs(self):
        for url in ("http://example.com/a", "http://localhost.evil/a",
                    "http://127.0.0.1/a?key=secret", "http://user:pass@localhost/a",
                    "https://example.com/a#fragment", "file:///tmp/a"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                request_json(url, {})
        for kwargs in ({"timeout": 61}, {"timeout": 0}, {"max_bytes": 1048577},
                       {"bearer_env": "BAD=NAME"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                request_json(self.root + "/ok", {}, **kwargs)
        with self.assertRaises(ValueError):
            request_json(self.root + "/ok", {"x": float("nan")})


if __name__ == "__main__":
    unittest.main()

"""Offline HTTP boundary tests for the finite loopback motif viewer."""

import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from harness2.motif_viewer import MAX_CALLS, MotifViewer


GOOD = '{"motif":"sway","accents":["soft","clear","soft","clear"]}'


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.html = self.root / "viewer.html"
        self.html.write_text("<html>test viewer</html>")
        self.output = self.root / "receipt.json"
        self.threads = []

    def start_viewer(self, provider, *, lifetime=30, clock=time.monotonic):
        viewer = MotifViewer("gemma4:e2b", self.output, provider=provider,
                             html_path=self.html, lifetime=lifetime, clock=clock)
        thread = threading.Thread(target=viewer.serve, daemon=True)
        thread.start()
        self.threads.append(thread)
        self.addCleanup(self.finish, viewer, thread)
        return viewer

    def finish(self, viewer, thread):
        if thread.is_alive():
            try:
                self.post(viewer, "/shutdown", {})
            except Exception:
                pass
            thread.join(3)

    def get(self, viewer, path):
        with urlopen(viewer.url + path, timeout=3) as response:
            return response.status, dict(response.headers), response.read()

    def post(self, viewer, path, data, *, origin=True, content_type="application/json"):
        payload = data if isinstance(data, bytes) else json.dumps(data).encode()
        headers = {"Content-Type": content_type}
        if origin:
            headers["Origin"] = viewer.url
        request = Request(viewer.url + path, data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def wait_until(self, predicate):
        end = time.monotonic() + 5
        while time.monotonic() < end:
            if predicate():
                return
            time.sleep(.02)
        self.fail("timed out waiting for viewer worker")

    def test_loopback_state_html_and_request_validation(self):
        viewer = self.start_viewer(lambda _body: {"message": {"content": GOOD},
                                                     "done_reason": "stop"})
        self.assertTrue(viewer.url.startswith("http://127.0.0.1:"))
        status, headers, body = self.get(viewer, "/")
        self.assertEqual((status, body), (200, self.html.read_bytes()))
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        state = json.loads(self.get(viewer, "/state")[2])
        self.assertEqual(state["sample"]["status"], "idle")
        self.assertEqual(state["model"], "gemma4:e2b")
        self.assertEqual((state["calls_started"], state["worker_busy"]), (0, False))
        self.assertEqual(self.post(viewer, "/direct", {"brief": "sway"}, origin=False)[0], 403)
        self.assertEqual(self.post(viewer, "/direct", {"brief": "sway"},
                                   content_type="text/plain")[0], 415)
        self.assertEqual(self.post(viewer, "/direct", b'{"brief":"a","brief":"b"}')[0],
                         400)
        self.assertEqual(self.post(viewer, "/direct", {"brief": "x" * 501})[0], 400)
        self.assertEqual(self.post(viewer, "/direct", b" " * 4097)[0], 413)
        self.assertEqual(self.post(viewer, "/stop", {"extra": 1})[0], 400)
        self.assertEqual(json.loads(self.get(viewer, "/state")[2])["calls_started"], 0)
        receipt = json.loads(self.output.read_text())
        self.assertEqual(receipt["sources"]["experiments/motif_viewer.html"],
                         __import__("hashlib").sha256(self.html.read_bytes()).hexdigest())

    def test_busy_stop_during_inference_and_stale_reply(self):
        entered = threading.Event()
        release = threading.Event()
        captured = []

        def provider(body):
            captured.append(body)
            entered.set()
            if not release.wait(3):
                raise TimeoutError("fake provider release timeout")
            return {"message": {"content": GOOD}, "done_reason": "stop",
                    "prompt_eval_count": 12, "eval_count": 10}

        viewer = self.start_viewer(provider)
        code, accepted = self.post(viewer, "/direct", {"brief": "Please sway."})
        self.assertEqual(code, 202)
        self.assertTrue(entered.wait(2))
        self.assertEqual(self.post(viewer, "/direct", {"brief": "pulse"}),
                         (409, {"error": "provider_busy"}))
        pending = json.loads(self.get(viewer, "/state")[2])
        self.assertEqual(pending["pending"]["request_id"], accepted["request_id"])
        self.assertTrue(pending["worker_busy"])
        code, stopped = self.post(viewer, "/stop", {})
        self.assertEqual(code, 200)
        self.assertEqual(stopped["sample"]["status"], "frozen")
        release.set()
        self.wait_until(lambda: not json.loads(self.get(viewer, "/state")[2])["worker_busy"])
        after = json.loads(self.get(viewer, "/state")[2])
        self.assertEqual(after["sample"]["frame"], stopped["sample"]["frame"])
        receipt = json.loads(self.output.read_text())
        self.assertEqual(len(receipt["calls"]), 1)
        self.assertEqual(receipt["calls"][0]["delivery"]["status"], "rejected_stale")
        self.assertEqual(receipt["calls"][0]["raw_response"]["message"]["content"], GOOD)
        self.assertEqual(captured[0]["model"], "gemma4:e2b")
        self.assertEqual(captured[0]["options"],
                         {"temperature": 0, "num_ctx": 4096, "num_predict": 128})
        self.assertFalse(captured[0]["think"])

    def test_call_cap_and_durable_shutdown(self):
        viewer = self.start_viewer(lambda _body: {"message": {"content": GOOD},
                                                     "done_reason": "stop"})
        for number in range(MAX_CALLS):
            code, accepted = self.post(viewer, "/direct", {"brief": "sway"})
            self.assertEqual(code, 202)
            self.assertTrue(accepted["request_id"])
            self.wait_until(lambda: not json.loads(self.get(viewer, "/state")[2])["worker_busy"])
        self.assertEqual(self.post(viewer, "/direct", {"brief": "one more"})[0], 429)
        self.assertEqual(self.post(viewer, "/shutdown", {}),
                         (200, {"termination_reason": "user_shutdown"}))
        self.threads[-1].join(3)
        self.assertFalse(self.threads[-1].is_alive())
        receipt = json.loads(self.output.read_text())
        self.assertEqual(len(receipt["calls"]), MAX_CALLS)
        self.assertEqual(receipt["termination_reason"], "user_shutdown")
        self.assertTrue(receipt["worker_drained"])
        self.assertIsNotNone(receipt["ended_at_utc"])
        self.assertLessEqual(len(receipt["samples"]), 4000)

    def test_incomplete_reply_is_recorded_without_false_preparing_state(self):
        viewer = self.start_viewer(lambda _body: {"message": {"content": GOOD},
                                                     "done_reason": "length"})
        self.assertEqual(self.post(viewer, "/direct", {"brief": "sway"})[0], 202)
        self.wait_until(lambda: not json.loads(self.get(viewer, "/state")[2])["worker_busy"])
        state = json.loads(self.get(viewer, "/state")[2])
        self.assertIsNone(state["pending"])
        self.assertEqual(state["sample"]["status"], "idle")
        self.assertTrue(any(e["kind"] == "inference_error" for e in state["events"]))
        receipt = json.loads(self.output.read_text())
        self.assertEqual(receipt["calls"][0]["error"], "incomplete model response")
        self.assertIsNone(receipt["calls"][0]["delivery"])

    def test_explicit_recovery_http_contract_and_fresh_restart(self):
        clock = [0.0]
        viewer = self.start_viewer(lambda _body: {"message": {"content": GOOD},
                                  "done_reason": "stop"}, clock=lambda: clock[0])
        rest = viewer.state()["sample"]["frame"]["joints"]
        self.assertEqual(self.post(viewer, "/recover", {})[0], 409)
        self.assertEqual(self.post(viewer, "/recover", {}, origin=False)[0], 403)
        self.assertEqual(self.post(viewer, "/recover", {"extra": 1})[0], 400)
        self.assertEqual(self.post(viewer, "/direct", {"brief": "sway"})[0], 202)
        self.wait_until(lambda: not viewer.state()["worker_busy"])
        clock[0] = 1.35
        stopped = self.post(viewer, "/stop", {})[1]["sample"]
        code, recovered = self.post(viewer, "/recover", {})
        self.assertEqual(code, 200)
        self.assertEqual(recovered["sample"]["status"], "recovering")
        self.assertEqual(recovered["sample"]["frame"]["joints"], stopped["frame"]["joints"])
        self.assertEqual(self.post(viewer, "/direct", {"brief": "pulse"}),
                         (409, {"error": "recovery_in_progress"}))
        self.assertEqual(viewer.state()["calls_started"], 1)
        clock[0] = 2.05
        partial = self.post(viewer, "/stop", {})[1]["sample"]
        self.assertEqual(partial["status"], "frozen")
        code, again = self.post(viewer, "/recover", {})
        self.assertEqual(code, 200)
        self.assertEqual(again["sample"]["frame"]["joints"], partial["frame"]["joints"])
        clock[0] = 4.1
        end = viewer.state()["sample"]
        self.assertEqual(end["status"], "frozen")
        self.assertEqual(end["frame"]["joints"], rest)
        self.assertEqual(self.post(viewer, "/direct", {"brief": "pulse"})[0], 202)
        self.wait_until(lambda: not viewer.state()["worker_busy"])
        self.assertEqual(viewer.state()["sample"]["status"], "playing")
        receipt = json.loads(self.output.read_text())
        self.assertEqual(sum(e["kind"] == "recover" for e in receipt["events"]), 2)
        self.assertEqual(len(receipt["calls"]), 2)

    def test_constructor_refuses_reuse_bad_bounds_and_missing_html(self):
        with self.assertRaises(ValueError):
            MotifViewer("wrong-model", self.output, html_path=self.html, provider=lambda _: {})
        with self.assertRaises(ValueError):
            MotifViewer("gemma4:e2b", "relative.json", html_path=self.html,
                        provider=lambda _: {})
        with self.assertRaises(ValueError):
            MotifViewer("gemma4:e2b", self.output, lifetime=601,
                        html_path=self.html, provider=lambda _: {})
        with self.assertRaises(ValueError):
            MotifViewer("gemma4:e2b", self.output, html_path=self.root / "missing.html",
                        provider=lambda _: {})
        viewer = self.start_viewer(lambda _body: {})
        with self.assertRaises(ValueError):
            MotifViewer("gemma4:e2b", self.output, html_path=self.html, provider=lambda _: {})
        self.assertTrue(viewer.output.exists())


if __name__ == "__main__":
    unittest.main()

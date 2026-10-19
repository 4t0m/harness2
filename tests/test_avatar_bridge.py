"""Offline checks for the narrow avatar subprocess bridge."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness2.avatar_bridge import AvatarBridgeError, _worker_once, run_avatar


def worker_output(action="look_right", hold=2):
    applied = {"phase": "applied", "action": action, "hold_seconds": hold,
               "delivery_confirmed": True, "control_receipt": {"ok": True},
               "pixels_verified": False}
    finished = {"phase": "finished", "readback_ok": True, "cleanup_confirmed": True,
                "readback_receipt": {"ok": True},
                "cleanup_receipt": {"attempted": True, "receipt_matches": True},
                "error_type": None, "pixels_verified": False}
    return json.dumps(applied) + "\n" + json.dumps(finished) + "\n"


class FakeProcess:
    def __init__(self, stdout=None, returncode=0, timeout=False):
        self.stdout = stdout or worker_output()
        self.returncode = returncode
        self.timeout = timeout
        self.terminated = False
        self.killed = False

    def communicate(self, timeout=None):
        if self.timeout and not self.terminated:
            raise subprocess.TimeoutExpired("avatar worker", timeout)
        return self.stdout, ""

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class AvatarBridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tools = Path(self.temp.name)
        (self.tools / "avatar_safe_mcp.py").touch()
        (self.tools / "anime_avatar_mcp.py").touch()

    def call(self, action="look_right", hold=2):
        return run_avatar(action, hold, python_executable=sys.executable, tools_dir=self.tools)

    def test_invokes_only_fixed_worker_with_minimal_environment(self):
        fake = FakeProcess()
        with patch("harness2.avatar_bridge.subprocess.Popen", return_value=fake) as popen:
            result = self.call()
        command = popen.call_args.args[0]
        self.assertEqual(command[:3], [sys.executable, "-I", "-B"])
        self.assertEqual(command[-3:], ["--worker", "look_right", "2"])
        self.assertEqual(popen.call_args.kwargs["env"]["HERMES_AVATAR_TOOLS"], str(self.tools))
        self.assertNotIn("OPENROUTER_API_KEY", popen.call_args.kwargs["env"])
        self.assertEqual(result["status"], "finished")
        self.assertTrue(result["delivery_confirmed"])
        self.assertTrue(result["readback_ok"])
        self.assertTrue(result["cleanup_confirmed"])
        self.assertFalse(result["pixels_verified"])
        self.assertEqual(result["visual_check"], "not_assessed")

    def test_rejects_unsupported_actions_and_holds_before_subprocess(self):
        with patch("harness2.avatar_bridge.subprocess.Popen") as popen:
            for action in ("wink_left", "look_left", "look_right; echo unsafe", ""):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    self.call(action=action)
            for hold in (0, 4, True, 1.5):
                with self.subTest(hold=hold), self.assertRaises(ValueError):
                    self.call(hold=hold)
            popen.assert_not_called()

    def test_timeout_requests_orderly_termination_without_claiming_cleanup(self):
        fake = FakeProcess(timeout=True)
        with patch("harness2.avatar_bridge.subprocess.Popen", return_value=fake):
            with self.assertRaisesRegex(AvatarBridgeError, "cleanup unverified"):
                self.call()
        self.assertTrue(fake.terminated)
        self.assertFalse(fake.killed)

    def test_worker_emits_delivery_before_hold_then_readback_and_cleanup(self):
        events = []

        class Safe:
            def anime_avatar_control(self, action, hold):
                events.append("control")
                return {"ok": True, "action": action, "receipt_matches": True,
                        "http_status": 204, "hold_seconds": hold}

            def anime_avatar_readback(self):
                events.append("readback")
                return {"ok": True, "relay_http_status": 200}

            def cleanup(self, reason):
                events.append("cleanup")
                return {"attempted": True, "http_status": 204, "receipt_matches": True}

        def emit(receipt):
            events.append(receipt["phase"])

        def sleep(seconds):
            self.assertEqual(seconds, 2)
            events.append("hold")

        _worker_once(Safe(), "look_right", 2, sleep=sleep, emit=emit)
        self.assertEqual(events, ["control", "applied", "hold", "readback", "cleanup",
                                  "finished"])

    def test_worker_cleans_up_after_readback_error(self):
        receipts = []

        class Safe:
            def anime_avatar_control(self, *_):
                return {"ok": True, "receipt_matches": True}

            def anime_avatar_readback(self):
                raise RuntimeError("private details")

            def cleanup(self, _reason):
                return {"attempted": True, "http_status": 204, "receipt_matches": True}

        _worker_once(Safe(), "neutral", 1, sleep=lambda _: None, emit=receipts.append)
        self.assertEqual(receipts[-1]["error_type"], "RuntimeError")
        self.assertTrue(receipts[-1]["cleanup_confirmed"])
        self.assertNotIn("private details", json.dumps(receipts))


if __name__ == "__main__":
    unittest.main()

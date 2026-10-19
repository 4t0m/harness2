"""Playback admission, boundary continuity, and stop semantics."""

import dataclasses
import json
import threading
import unittest
from unittest.mock import patch

from harness2.dance_motif_runtime import MotifRuntime
from harness2.dance_motif_recovery import recover_frames


def intent(motif="sway", accents=None):
    return json.dumps({"motif": motif, "accents": accents or ["soft"] * 4})


class MotifRuntimeTests(unittest.TestCase):
    def test_initial_admission_detached_sampling_and_finish_rest(self):
        runtime = MotifRuntime()
        idle = runtime.sample(0)
        self.assertEqual(idle["status"], "idle")
        self.assertIs(idle["at_rest"], True)
        request = runtime.request(0, 5000)
        prepared = runtime.prepare(intent())
        self.assertEqual(runtime.snapshot()["status"], "idle")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            prepared._digest = "tampered"
        self.assertEqual(runtime.deliver_prepared(request["request_id"], prepared, 0)["status"],
                         "applied")
        self.assertEqual(runtime.sample(49)["source_frame_index"], 0)
        frame = runtime.sample(50)
        self.assertEqual(frame["source_frame_index"], 1)
        self.assertIs(frame["at_rest"], False)
        frame["frame"]["joints"]["left_wrist"][0] = 999
        self.assertNotEqual(runtime.sample(50)["frame"]["joints"]["left_wrist"][0], 999)
        stopped = runtime.sample(16000)
        self.assertEqual(stopped["status"], "holding_end")
        self.assertEqual(stopped["source_frame_index"], 320)
        self.assertEqual(stopped["frame"]["joints"], idle["frame"]["joints"])
        self.assertEqual(runtime.sample(22000)["frame"], stopped["frame"])

    def test_queued_replacement_at_exact_shared_rest_boundary(self):
        runtime = MotifRuntime()
        first = runtime.prepare(intent("sway"))
        second = runtime.prepare(intent("pulse", ["clear"] * 4))
        r1 = runtime.request(0, 1000)
        runtime.deliver_prepared(r1["request_id"], first, 100)
        r2 = runtime.request(600, 1000)
        queued = runtime.deliver_prepared(r2["request_id"], second, 700)
        self.assertEqual((queued["status"], queued["switch_at_ms"]), ("queued", 4100))
        self.assertEqual(runtime.sample(4099)["score_sha256"], first._digest)
        previous_end = runtime.sample(4100)["frame"]
        self.assertEqual(previous_end["joints"], json.loads(first._frames[80])["joints"])
        self.assertEqual(previous_end["contacts"], json.loads(first._frames[80])["contacts"])
        self.assertEqual(runtime.sample(4100)["score_sha256"], second._digest)
        self.assertEqual(runtime.sample(4150)["frame"], json.loads(second._frames[1]))
        self.assertEqual(runtime.snapshot()["epoch_ms"], 4100)

    def test_supersession_duplicate_and_invalid_reply(self):
        runtime = MotifRuntime()
        good = runtime.prepare(intent())
        old = runtime.request(0, 1000)
        latest = runtime.request(10, 1000)
        self.assertEqual(runtime.deliver_prepared(old["request_id"], good, 20)["status"],
                         "rejected_stale")
        self.assertEqual(runtime.deliver(latest["request_id"], '{"motif":', 30)["status"],
                         "rejected_invalid")
        self.assertEqual(runtime.snapshot()["status"], "idle")
        fresh = runtime.request(40, 1000)
        self.assertEqual(runtime.deliver_prepared(fresh["request_id"], good, 50)["status"],
                         "applied")
        self.assertEqual(runtime.deliver_prepared(fresh["request_id"], good, 60)["status"],
                         "rejected_stale")
        bad = runtime.request(70, 1000)
        self.assertEqual(runtime.deliver(bad["request_id"],
                         '{"motif":"sway","motif":"pulse","accents":["soft","soft","soft","soft"]}',
                         80)["status"], "rejected_invalid")
        self.assertEqual(runtime.snapshot()["status"], "playing")

    def test_deadline_and_monotonic_clock_boundaries(self):
        runtime = MotifRuntime()
        prepared = runtime.prepare(intent())
        for budget in (0, 5001, True, 1.0):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                runtime.request(0, budget)
        request = runtime.request(100, 1)
        self.assertEqual(runtime.deliver_prepared(request["request_id"], prepared, 101)["status"],
                         "applied")
        late = runtime.request(200, 5)
        self.assertEqual(runtime.deliver_prepared(late["request_id"], prepared, 206)["status"],
                         "rejected_deadline")
        with self.assertRaises(ValueError):
            runtime.sample(205)
        for invalid in (-1, True, 3.2):
            with self.subTest(now=invalid), self.assertRaises(ValueError):
                runtime.sample(invalid)
        self.assertIsNone(runtime.snapshot()["pending"])

    def test_stop_freezes_exact_pose_revokes_work_and_blocks_midpose_restart(self):
        runtime = MotifRuntime()
        prepared = runtime.prepare(intent())
        runtime.deliver_prepared(runtime.request(0, 5000)["request_id"], prepared, 0)
        pending = runtime.request(2000, 5000)
        stopped = runtime.interrupt(2350)
        self.assertEqual(stopped["status"], "frozen")
        self.assertEqual(stopped["frame"], json.loads(prepared._frames[47]))
        self.assertEqual(runtime.sample(10000)["frame"], stopped["frame"])
        self.assertEqual(runtime.deliver_prepared(pending["request_id"], prepared, 10000)["status"],
                         "rejected_stale")
        new = runtime.request(10010, 5000)
        self.assertEqual(runtime.deliver_prepared(new["request_id"], prepared, 10020)["status"],
                         "rejected_unsupported_restart")
        snap = runtime.snapshot()
        snap["frame"]["joints"]["pelvis"][0] = 999
        self.assertEqual(runtime.sample(12000)["frame"], stopped["frame"])

    def test_rest_stop_can_restart_and_pending_queue_is_cleared(self):
        runtime = MotifRuntime()
        a = runtime.prepare(intent("sway"))
        b = runtime.prepare(intent("pulse"))
        runtime.deliver_prepared(runtime.request(0, 1000)["request_id"], a, 0)
        replace = runtime.request(500, 1000)
        self.assertEqual(runtime.deliver_prepared(replace["request_id"], b, 600)["status"],
                         "queued")
        self.assertEqual(runtime.snapshot()["queued_switch_ms"], 4000)
        stopped = runtime.interrupt(4000)
        self.assertEqual(stopped["status"], "frozen")
        self.assertIsNone(runtime.snapshot()["queued_switch_ms"])
        restart = runtime.request(4100, 1000)
        self.assertEqual(runtime.deliver_prepared(restart["request_id"], a, 4200)["status"],
                         "applied")
        self.assertEqual(runtime.sample(4250)["source_frame_index"], 1)

    def test_preparation_does_not_hold_sampler_lock(self):
        runtime = MotifRuntime()
        entered = threading.Event()
        release = threading.Event()
        error = []
        original = __import__("harness2.dance_motif_runtime", fromlist=["compile_intent"]).compile_intent

        def slow(raw):
            entered.set()
            if not release.wait(2):
                raise RuntimeError("test release timeout")
            return original(raw)

        def worker():
            try:
                runtime.prepare(intent())
            except Exception as exc:
                error.append(exc)

        with patch("harness2.dance_motif_runtime.compile_intent", side_effect=slow):
            thread = threading.Thread(target=worker)
            thread.start()
            self.assertTrue(entered.wait(2))
            try:
                self.assertEqual(runtime.sample(0)["status"], "idle")
                self.assertEqual(runtime.interrupt(0)["status"], "frozen")
            finally:
                release.set()
                thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(error, [])

    def test_explicit_recovery_exact_endpoints_and_fresh_restart(self):
        runtime = MotifRuntime()
        prepared = runtime.prepare(intent("pulse", ["clear"] * 4))
        runtime.deliver_prepared(runtime.request(0, 5000)["request_id"], prepared, 0)
        stopped = runtime.interrupt(2350)
        expected = recover_frames(stopped["frame"])
        self.assertIs(stopped["at_rest"], False)
        started = runtime.recover_to_rest(2400)
        self.assertEqual(started["status"], "recovering")
        self.assertIs(started["at_rest"], False)
        self.assertEqual(started["frame"]["joints"], stopped["frame"]["joints"])
        self.assertEqual(started["frame"]["contacts"], stopped["frame"]["contacts"])
        self.assertIsNone(started["score_sha256"])
        self.assertIsNone(started["epoch_ms"])
        self.assertIsNone(started["source_frame_index"])
        self.assertEqual(started["recovery_epoch_ms"], 2400)
        self.assertEqual(started["recovery_frame_index"], 0)
        self.assertEqual(runtime.sample(3400)["frame"], expected[20])
        self.assertEqual(runtime.sample(4399)["frame"], expected[39])
        complete = runtime.sample(4400)
        self.assertEqual(complete["status"], "frozen")
        self.assertIs(complete["at_rest"], True)
        self.assertEqual(complete["frame"], expected[40])
        self.assertEqual(runtime.sample(9000)["frame"], expected[40])
        self.assertEqual(runtime.snapshot()["recovery_sha256"], started["recovery_sha256"])
        fresh = runtime.request(9010, 5000)
        self.assertEqual(runtime.deliver_prepared(fresh["request_id"], prepared, 9020)["status"],
                         "applied")
        self.assertEqual(runtime.sample(9070)["source_frame_index"], 1)
        self.assertIsNone(runtime.snapshot()["recovery_sha256"])

    def test_recovery_revokes_pending_and_rejects_requests_until_complete(self):
        runtime = MotifRuntime()
        prepared = runtime.prepare(intent())
        runtime.deliver_prepared(runtime.request(0, 5000)["request_id"], prepared, 0)
        pending = runtime.request(1000, 5000)
        runtime.interrupt(1200)
        recovering = runtime.recover_to_rest(1300)
        self.assertIsNone(runtime.snapshot()["pending"])
        self.assertIsNone(runtime.snapshot()["queued_switch_ms"])
        self.assertEqual(runtime.deliver_prepared(pending["request_id"], prepared, 1400)["status"],
                         "rejected_stale")
        with self.assertRaises(ValueError):
            runtime.request(1500, 5000)
        self.assertEqual(runtime.sample(1500)["status"], "recovering")
        self.assertEqual(runtime.sample(3300)["status"], "frozen")
        self.assertGreater(runtime.snapshot()["revision"], recovering["revision"] - 1)

    def test_interrupt_recovery_freezes_sample_and_can_recover_again(self):
        runtime = MotifRuntime()
        prepared = runtime.prepare(intent("sway", ["clear"] * 4))
        runtime.deliver_prepared(runtime.request(0, 5000)["request_id"], prepared, 0)
        runtime.interrupt(650)
        runtime.recover_to_rest(700)
        current = runtime.sample(1550)
        self.assertEqual(current["recovery_frame_index"], 17)
        stopped = runtime.interrupt(1550)
        self.assertEqual(stopped["status"], "frozen")
        self.assertEqual(stopped["frame"], current["frame"])
        stopped["frame"]["joints"]["left_wrist"][0] = 999
        self.assertNotEqual(runtime.snapshot()["frame"]["joints"]["left_wrist"][0], 999)
        again = runtime.recover_to_rest(1700)
        self.assertEqual(again["status"], "recovering")
        self.assertEqual(again["frame"]["joints"], current["frame"]["joints"])
        self.assertEqual(again["frame"]["contacts"], current["frame"]["contacts"])
        self.assertEqual(again["frame"]["time"], 0.0)
        self.assertEqual(runtime.sample(3700)["status"], "frozen")
        self.assertEqual(runtime.sample(3700)["frame"]["joints"],
                         json.loads(prepared._frames[0])["joints"])

    def test_recovery_requires_stop_and_clock_is_monotonic(self):
        runtime = MotifRuntime()
        with self.assertRaises(ValueError):
            runtime.recover_to_rest(0)
        runtime.interrupt(100)
        with self.assertRaises(ValueError):
            runtime.recover_to_rest(99)
        self.assertEqual(runtime.recover_to_rest(100)["status"], "recovering")


if __name__ == "__main__":
    unittest.main()

"""Rigid planted recovery checks; no runtime, renderer, or model calls."""

from __future__ import annotations

import copy
import json
import math
import unittest

from harness2 import dance_motion
from harness2.dance_motif_recovery import (
    RECOVERY_FPS, RECOVERY_INTERVALS, RECOVERY_MS, recover_frames,
    verify_recovery,
)
from harness2.dance_motif_score import compile_intent
from harness2.dance_phrases import _pose


def score(motif, variation):
    return compile_intent(json.dumps({"motif": motif,
                                      "accents": [variation] * 4}))["sequence"]["frames"]


class RecoveryTests(unittest.TestCase):
    def test_all_motion_families_extremes_and_endpoints(self):
        seen = set()
        for motif in ("sway", "pulse"):
            for variation in ("soft", "clear"):
                source = score(motif, variation)
                # Section rise, interior motifs, settle, and shared rest.
                for index in (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 55, 65, 75, 80):
                    frame = source[index]
                    before = copy.deepcopy(frame)
                    recovery = recover_frames(frame)
                    report = verify_recovery(recovery, frame)
                    self.assertEqual(frame, before)
                    self.assertEqual(len(recovery), RECOVERY_INTERVALS + 1)
                    self.assertEqual(recovery[0]["joints"], frame["joints"])
                    self.assertEqual(recovery[0]["contacts"], frame["contacts"])
                    self.assertEqual(recovery[-1]["joints"], _pose("rest"))
                    self.assertEqual(recovery[-1]["time"], RECOVERY_MS / 1000)
                    self.assertLess(report["max_segment_error_m"], 1e-6)
                    seen.add(index // 20)
        self.assertEqual(seen, {0, 1, 2, 3, 4})

    def test_planted_links_finite_and_quintic_end_slope(self):
        frozen = score("pulse", "clear")[30]
        frames = recover_frames(frozen)
        self.assertEqual(RECOVERY_FPS, 20)
        for i, frame in enumerate(frames):
            self.assertAlmostEqual(frame["time"], i / RECOVERY_FPS)
            self.assertEqual(frame["contacts"], {"left": True, "right": True})
            joints = frame["joints"]
            for side in ("left", "right"):
                self.assertEqual(joints[f"{side}_ankle"], frames[0]["joints"][f"{side}_ankle"])
                self.assertEqual(joints[f"{side}_foot"], frames[0]["joints"][f"{side}_foot"])
            for a, b, target, _ in dance_motion._SEGMENTS:
                self.assertLess(abs(math.dist(joints[a], joints[b]) - target), 1e-6)
            self.assertTrue(all(math.isfinite(v) for point in joints.values() for v in point))
        # Ease starts and ends almost still, while traversing appreciably mid-way.
        def delta(a, b):
            return max(math.dist(a["joints"][name], b["joints"][name])
                       for name in a["joints"])
        self.assertLess(delta(frames[0], frames[1]), delta(frames[19], frames[20]))
        self.assertLess(delta(frames[-2], frames[-1]), delta(frames[19], frames[20]))

    def test_malformed_and_unsupported_sources_rejected(self):
        source = score("sway", "clear")[30]
        cases = []
        changed = copy.deepcopy(source)
        changed["contacts"]["left"] = 1
        cases.append(changed)
        changed = copy.deepcopy(source)
        changed["joints"]["left_ankle"][0] += 0.01
        cases.append(changed)
        changed = copy.deepcopy(source)
        changed["joints"]["right_wrist"][1] = 0.01
        cases.append(changed)
        changed = copy.deepcopy(source)
        changed["joints"]["pelvis"][0] = float("nan")
        cases.append(changed)
        changed = copy.deepcopy(source)
        changed["joints"]["left_elbow"] = [True, 0, 0]
        cases.append(changed)
        changed = copy.deepcopy(source)
        changed["extra"] = "unsupported"
        cases.append(changed)
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    recover_frames(case)

    def test_verifier_detects_path_and_link_corruption(self):
        source = score("sway", "clear")[30]
        frames = recover_frames(source)
        changed = copy.deepcopy(frames)
        changed[12]["joints"]["left_wrist"][0] += 0.01
        with self.assertRaises(ValueError):
            verify_recovery(changed, source)
        changed = copy.deepcopy(frames)
        changed[12]["joints"]["pelvis"][0] += 0.01
        with self.assertRaises(ValueError):
            verify_recovery(changed, source)
        changed = copy.deepcopy(frames)
        changed[12]["time"] = True
        with self.assertRaises(ValueError):
            verify_recovery(changed, source)

    def test_interrupted_recovery_can_recover_again_without_mutation(self):
        original = score("pulse", "clear")[30]
        first = recover_frames(original)
        frozen = copy.deepcopy(first[17])
        second = recover_frames(frozen)
        self.assertEqual(first[17], frozen)
        self.assertEqual(second[0]["joints"], frozen["joints"])
        self.assertEqual(second[-1]["joints"], _pose("rest"))
        self.assertEqual(verify_recovery(second, frozen)["frame_count"], 41)


if __name__ == "__main__":
    unittest.main()

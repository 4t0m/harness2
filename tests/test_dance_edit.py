"""Invariant checks for a host-owned, arm-only middle-span motion edit."""

import copy
import math
import unittest

from harness2 import dance_motion
from harness2.dance_edit import edit_arms, parse_intent, preservation_checks


class DanceEditTests(unittest.TestCase):
    def setUp(self):
        self.source = dance_motion.generate("restrained")
        self.snapshot = copy.deepcopy(self.source)

    def test_clear_and_soft_preserve_full_motion_contract(self):
        soft = edit_arms(self.source, '{"operation":"accent_arms","strength":"soft"}')
        clear = edit_arms(self.source, '{"operation":"accent_arms","strength":"clear"}')
        self.assertEqual(self.source, self.snapshot)
        self.assertIsNot(soft["sequence"], self.source)
        for item in (soft, clear):
            result, receipt = item["sequence"], item["receipt"]
            self.assertTrue(dance_motion.validate(result)["valid"])
            self.assertTrue(receipt["validation"]["valid"])
            self.assertTrue(receipt["source_unchanged"])
            self.assertTrue(all(receipt[key] for key in (
                "protected_frames_preserved", "non_arm_joints_preserved", "contacts_preserved",
                "timestamps_preserved", "metadata_preserved")))
            self.assertEqual(receipt["edit_window_beats"], [2, 6])
            self.assertTrue(receipt["changed_frames"])
            self.assertTrue(all(20 < index < 60 for index in receipt["changed_frames"]))
            self.assertNotEqual(receipt["source_sha256"], receipt["result_sha256"])
            for index, (before, after) in enumerate(zip(self.source["frames"], result["frames"])):
                self.assertEqual(before["time"], after["time"])
                self.assertEqual(before["contacts"], after["contacts"])
                if index <= 20 or index >= 60:
                    self.assertEqual(before, after)
                for name in before["joints"]:
                    if name not in {"left_elbow", "left_wrist", "right_elbow", "right_wrist"}:
                        self.assertEqual(before["joints"][name], after["joints"][name])
        midpoint = 40
        origin = self.source["frames"][midpoint]["joints"]["left_wrist"]
        soft_delta = math.dist(origin, soft["sequence"]["frames"][midpoint]["joints"]["left_wrist"])
        clear_delta = math.dist(origin, clear["sequence"]["frames"][midpoint]["joints"]["left_wrist"])
        self.assertGreater(clear_delta, soft_delta)
        self.assertGreater(soft_delta, 0.01)

    def test_independent_preservation_check_detects_corruption(self):
        edited = edit_arms(self.source, '{"operation":"accent_arms","strength":"soft"}')["sequence"]
        edited["frames"][40]["joints"]["spine"][0] += 0.001
        self.assertFalse(preservation_checks(self.source, edited)["non_arm_joints_preserved"])
        with self.assertRaisesRegex(ValueError, "wrong skeletal segment length"):
            dance_motion.validate(edited)
        protected = edit_arms(self.source, '{"operation":"accent_arms","strength":"soft"}')["sequence"]
        protected["frames"][20]["joints"]["left_wrist"][0] += 0.001
        self.assertFalse(preservation_checks(self.source, protected)["protected_frames_preserved"])

    def test_strict_intent_and_fixed_window_rejections(self):
        for raw in ('accent_arms', '```json\n{"operation":"accent_arms","strength":"soft"}\n```',
                    '{"operation":"accent_arms","strength":"soft","extra":1}',
                    '{"operation":"accent_arms","strength":"soft","strength":"clear"}',
                    '{"operation":"dance","strength":"soft"}',
                    '{"operation":"accent_arms","strength":"hard"}',
                    '{"operation":"accent_arms","strength":[]}',
                    '{"operation":"accent_arms","strength":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_intent(raw)
        self.assertEqual(parse_intent('{"operation":"accent_arms","strength":"clear"}'), "clear")
        with self.assertRaisesRegex(ValueError, "fixed"):
            edit_arms(self.source, '{"operation":"accent_arms","strength":"soft"}', 1, 6)
        with self.assertRaisesRegex(ValueError, "fixed"):
            edit_arms(self.source, '{"operation":"accent_arms","strength":"soft"}', 2, 7)
        self.assertEqual(self.source, self.snapshot)

    def test_invalid_source_refused_without_mutation(self):
        bad = copy.deepcopy(self.source)
        bad["frames"][40]["joints"]["left_knee"][0] += 0.02
        before = copy.deepcopy(bad)
        with self.assertRaisesRegex(ValueError, "wrong skeletal segment length"):
            edit_arms(bad, '{"operation":"accent_arms","strength":"clear"}')
        self.assertEqual(bad, before)

    def test_timing_metadata_cannot_move_protected_span(self):
        altered = copy.deepcopy(self.source)
        altered["bpm"] = 240
        # The upstream motion validator still accepts this metadata, so the
        # edit entry check must independently prevent an early-span edit.
        self.assertTrue(dance_motion.validate(altered)["valid"])
        before = copy.deepcopy(altered)
        with self.assertRaisesRegex(ValueError, "authoritative eight-beat prototype"):
            edit_arms(altered, '{"operation":"accent_arms","strength":"clear"}')
        self.assertEqual(altered, before)
        for field, wrong in (("bpm", 240), ("fps", 40), ("beats", 16),
                             ("duration_seconds", 8.0), ("bpm", True),
                             ("fps", True), ("beats", True),
                             ("duration_seconds", True), ("bpm", 120.0),
                             ("duration_seconds", 4)):
            with self.subTest(field=field, wrong=wrong):
                bad = copy.deepcopy(self.source)
                bad[field] = wrong
                with self.assertRaisesRegex(ValueError, "authoritative eight-beat prototype"):
                    edit_arms(bad, '{"operation":"accent_arms","strength":"soft"}')
        for field in ("bpm", "fps", "beats", "duration_seconds"):
            with self.subTest(missing=field):
                bad = copy.deepcopy(self.source)
                del bad[field]
                with self.assertRaisesRegex(ValueError, "authoritative eight-beat prototype"):
                    edit_arms(bad, '{"operation":"accent_arms","strength":"soft"}')

    def test_valid_prototype_keeps_prior_receipt_hashes(self):
        receipt = edit_arms(self.source, '{"operation":"accent_arms","strength":"clear"}')["receipt"]
        self.assertEqual(receipt["source_sha256"],
                         "b499ab93bc684b12c91b2f75cf57c51c7a8bfc8c3cf113c47abac344b3da130a")
        self.assertEqual(receipt["result_sha256"],
                         "2b17d4f9b9b476940ec9fbd35b589cd0b5b4e2947761bbb443b92865f8ce3174")


if __name__ == "__main__":
    unittest.main()

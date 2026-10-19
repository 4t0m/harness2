import copy
import unittest
from harness2.dance_score import REVISION, compile_score, offline_evidence


class DanceScoreTests(unittest.TestCase):
    def setUp(self):
        self.score = {"atlas_revision": REVISION, "moves": ["settle", "sway", "accent", "resolve"]}

    def test_timeline_and_no_motion_claims(self):
        before = copy.deepcopy(self.score)
        result = compile_score(self.score)
        self.assertEqual(self.score, before)
        self.assertEqual(result["duration_seconds"], 4)
        self.assertEqual([(c["start_seconds"], c["end_seconds"]) for c in result["cues"]],
                         [(0, 1), (1, 2), (2, 3), (3, 4)])
        self.assertFalse(result["physical_validity_verified"])
        self.assertFalse(result["motion_generated"])
        self.assertFalse(result["taste_evaluated"])

    def test_adversarial_contracts(self):
        rows = offline_evidence()["results"]
        self.assertEqual([r["accepted"] for r in rows], [True, False, False, False, False, False])

    def test_malformed_and_stale(self):
        for value in [None, [], {}, {**self.score, "atlas_revision": "old"},
                      {**self.score, "moves": [[]]}, {**self.score, "moves": "settle"},
                      {**self.score, "extra": 1}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                compile_score(value)
        for bpm in [True, float("nan"), float("inf"), "120", 0]:
            with self.subTest(bpm=bpm), self.assertRaises(ValueError):
                compile_score(self.score, bpm)

"""Fixed pose atlas to deterministic H3 scene-skeleton manifest."""

import json
import unittest

from harness2.scene_score import (
    EXPECTED, FRAME_RATE, SCENE, SLOTS, compile_score, evaluate_score,
    model_brief, parse_score, run_offline_evidence,
)


def correct():
    return {"scene_revision": SCENE["revision"],
            "beats": [{**beat, "duration_frames": 6} for beat in EXPECTED]}


class SceneScoreTests(unittest.TestCase):
    def test_brief_contains_scene_and_request_without_oracle(self):
        brief = model_brief()
        self.assertIn(SCENE["revision"], brief)
        self.assertIn("gentle three-beat exchange", brief)
        self.assertNotIn("EXPECTED", brief)
        self.assertNotIn('"pose": "listen"', brief)

    def test_compiles_three_deterministic_shot_cues(self):
        score = parse_score(json.dumps(correct()))
        manifest = compile_score(score)
        self.assertEqual(manifest["kind"], "h3_scene_skeleton")
        self.assertFalse(manifest["rendered"])
        self.assertFalse(manifest["runtime_executed"])
        self.assertEqual(manifest["frame_rate"], FRAME_RATE)
        self.assertIn("compressed", manifest["timing_scope"])
        cues = manifest["shot_cues"]
        self.assertEqual(len(cues), 3)
        self.assertEqual([(c["beat_id"], c["actor_id"], c["target_id"])
                          for c in cues],
                         [("beat-1", "aya", "ren"), ("beat-2", "aya", "mira"),
                          ("beat-3", "ren", "aya")])
        self.assertEqual([(c["start_frame"], c["end_frame_exclusive"]) for c in cues],
                         [(0, 6), (6, 12), (12, 18)])
        for cue in cues:
            self.assertAlmostEqual(cue["staging_suggestion"]["edge_gap_at_anchor"], 0.08)
            self.assertIn("no path", cue["staging_suggestion"]["checks"])
        self.assertEqual(cues[0]["scene_actor_position"], {"x": 0.2, "y": 0.5})
        self.assertEqual(manifest, compile_score(score))

    def test_wrong_target_stale_and_conflicting_timeline(self):
        wrong = correct()
        wrong["beats"][1]["target_id"] = "ren"
        verdict = evaluate_score(json.dumps(wrong))
        self.assertTrue(verdict["compiled"])
        self.assertFalse(verdict["semantic_correct"])
        stale = correct()
        stale["scene_revision"] = "prior"
        verdict = evaluate_score(json.dumps(stale))
        self.assertTrue(verdict["schema_valid"])
        self.assertFalse(verdict["compiled"])
        self.assertIn("stale", verdict["reason"])
        conflict = correct()
        conflict["beats"][0]["duration_frames"] = 8
        verdict = evaluate_score(json.dumps(conflict))
        self.assertTrue(verdict["schema_valid"])
        self.assertFalse(verdict["compiled"])
        self.assertIn("conflicting", verdict["reason"])

    def test_strict_enums_beats_and_bounds(self):
        bad = correct()
        bad["beats"][0]["pose"] = "dance"
        self.assertIn("unknown pose", evaluate_score(json.dumps(bad))["reason"])
        bad = correct()
        bad["beats"][0]["target_id"] = "ghost"
        self.assertIn("unknown", evaluate_score(json.dumps(bad))["reason"])
        bad = correct()
        bad["beats"][0]["duration_frames"] = 9
        self.assertIn("out of bounds", evaluate_score(json.dumps(bad))["reason"])
        bad = correct()
        bad["beats"][0]["duration_frames"] = True
        self.assertFalse(evaluate_score(json.dumps(bad))["schema_valid"])
        bad = correct()
        bad["beats"][1]["beat_id"] = "beat-1"
        self.assertIn("duplicate", evaluate_score(json.dumps(bad))["reason"])
        bad = correct()
        bad["beats"][0]["start_frame"] = 100
        self.assertIn("fields", evaluate_score(json.dumps(bad))["reason"])
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            parse_score('{"scene_revision":"x","scene_revision":"y","beats":[]}')

    def test_offline_receipt_covers_distinct_failures(self):
        report = run_offline_evidence()
        self.assertEqual(len(report["cases"]), 5)
        by_name = {case["name"]: case["verdict"] for case in report["cases"]}
        self.assertTrue(by_name["correct"]["accepted"])
        self.assertTrue(by_name["wrong_target"]["compiled"])
        self.assertFalse(by_name["wrong_target"]["accepted"])
        for name in ("stale_revision", "conflicting_timeline"):
            self.assertTrue(by_name[name]["schema_valid"])
            self.assertFalse(by_name[name]["compiled"])
        self.assertFalse(by_name["unknown_pose"]["schema_valid"])


if __name__ == "__main__":
    unittest.main()

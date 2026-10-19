"""Host-owned actor intent selection and geometry checks."""

import json
import unittest

from harness2.actor_intent import (
    TASKS, compile_intent, evaluate_intent, model_brief, parse_intent, run_offline_evidence,
)


def correct(task_id):
    task = TASKS[task_id]
    return {"scene_revision": task["scene"]["revision"], **task["expected"]}


class ActorIntentTests(unittest.TestCase):
    def test_brief_has_scene_and_task_but_no_answer(self):
        for task_id, task in TASKS.items():
            brief = model_brief(task_id)
            self.assertIn(task["request"], brief)
            self.assertIn(task["scene"]["revision"], brief)
            self.assertNotIn("expected", brief)
            self.assertNotIn('"target_id": "ren"', brief)

    def test_strict_action_fields_and_json(self):
        with self.assertRaisesRegex(ValueError, "fields do not match"):
            parse_intent(json.dumps({**correct("look-left-nearest"), "stop_gap": 0.12}))
        wrong = correct("approach-left")
        del wrong["stop_gap"]
        with self.assertRaisesRegex(ValueError, "fields do not match"):
            parse_intent(json.dumps(wrong))
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            parse_intent('{"action":"look_at","action":"approach"}')
        with self.assertRaisesRegex(ValueError, "nonfinite JSON number"):
            parse_intent(json.dumps({**correct("approach-left"), "stop_gap": float("nan")}))
        with self.assertRaisesRegex(ValueError, "unsupported action"):
            parse_intent(json.dumps({**correct("look-left-nearest"), "action": "dance"}))

    def test_semantics_are_separate_from_runtime_support(self):
        left = evaluate_intent("look-left-nearest", json.dumps(correct("look-left-nearest")))
        self.assertTrue(left["accepted"])
        self.assertEqual((left["runtime_status"], left["plan"]["adapter_control"]),
                         ("unsupported", None))
        self.assertEqual((left["plan"]["screen_gaze"], left["plan"]["actor_local_gaze"]),
                         ("screen_left", "actor_right"))
        right = evaluate_intent("look-right-mirror", json.dumps(correct("look-right-mirror")))
        self.assertTrue(right["accepted"])
        self.assertEqual((right["runtime_status"], right["plan"]["adapter_control"]),
                         ("supported", "look_right"))
        self.assertEqual(right["plan"]["actor_local_gaze"], "actor_right")
        vertical = evaluate_intent("look-vertical", json.dumps(correct("look-vertical")))
        self.assertTrue(vertical["accepted"])
        self.assertEqual((vertical["plan"]["vertical_gaze"], vertical["plan"]["adapter_control"]),
                         ("screen_down", None))

    def test_wrong_target_and_stale_revision(self):
        wrong = correct("look-left-nearest")
        wrong["target_id"] = "mira"
        verdict = evaluate_intent("look-left-nearest", json.dumps(wrong))
        self.assertTrue(verdict["schema_valid"])
        self.assertTrue(verdict["compiled"])
        self.assertFalse(verdict["semantic_correct"])
        stale = correct("look-left-nearest")
        stale["scene_revision"] = "old"
        verdict = evaluate_intent("look-left-nearest", json.dumps(stale))
        self.assertTrue(verdict["schema_valid"])
        self.assertFalse(verdict["compiled"])
        self.assertIn("stale", verdict["reason"])
        unknown = correct("look-left-nearest")
        unknown["target_id"] = "absent"
        verdict = evaluate_intent("look-left-nearest", json.dumps(unknown))
        self.assertFalse(verdict["compiled"])

    def test_approach_clearance_and_mirror(self):
        for task_id in ("approach-left", "approach-right-mirror"):
            verdict = evaluate_intent(task_id, json.dumps(correct(task_id)))
            self.assertTrue(verdict["accepted"])
            self.assertEqual(verdict["runtime_status"], "preview_only")
            self.assertIsNone(verdict["plan"]["adapter_control"])
            self.assertAlmostEqual(verdict["plan"]["geometry"]["edge_gap_final"], 0.12)
            self.assertTrue(verdict["plan"]["geometry"]["replan_if_target_moves"])
        left = compile_intent(correct("approach-left"), TASKS["approach-left"]["scene"])
        right = compile_intent(correct("approach-right-mirror"), TASKS["approach-right-mirror"]["scene"])
        self.assertLess(left["geometry"]["final_position"]["x"], 0.82)
        self.assertGreater(right["geometry"]["final_position"]["x"], 0.18)
        too_big = correct("approach-left")
        too_big["stop_gap"] = 0.5
        verdict = evaluate_intent("approach-left", json.dumps(too_big))
        self.assertFalse(verdict["compiled"])

    def test_offline_matrix(self):
        report = run_offline_evidence()
        self.assertEqual(len(report["cases"]), 2 * len(TASKS) + 1)
        for case in report["cases"]:
            if case["kind"] == "scripted_correct":
                self.assertTrue(case["verdict"]["accepted"])
            else:
                self.assertFalse(case["verdict"]["accepted"])


if __name__ == "__main__":
    unittest.main()

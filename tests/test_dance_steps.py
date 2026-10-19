"""Physical and structural checks for the planted side-step prototype."""

import copy
import json
import math
import unittest

from harness2 import dance_motion
from harness2.dance_steps import (
    PLAN_SCHEMA, PUBLIC_CONTRACT, compile_steps, parse_steps,
    validate_steps, verify_compilation,
)


def plan(*pairs):
    return json.dumps({"moves": [list(pair) for pair in pairs]})


RIGHT = plan(*(("step_right", "soft"),) * 4)
LEFT = plan(*(("step_left", "soft"),) * 4)


class DanceStepsTests(unittest.TestCase):
    def test_full_body_step_geometry_contacts_and_foot_lift(self):
        result = compile_steps(RIGHT)
        sequence = result["sequence"]
        report = verify_compilation(result)
        self.assertEqual(len(sequence["frames"]), 81)
        self.assertEqual((sequence["bpm"], sequence["fps"], sequence["beats"],
                          sequence["duration_seconds"]), (120, 20, 8, 4.0))
        self.assertEqual(len(sequence["frames"][0]["joints"]), 18)
        self.assertEqual(len(sequence["segment_lengths_m"]), 19)
        self.assertTrue(dance_motion.validate(sequence)["valid"])
        self.assertLess(report["max_segment_error_m"], 1e-6)
        self.assertGreater(report["max_moving_ankle_lift_m"], 0.06)
        self.assertEqual([row["end_root_x_m"] for row in sequence["move_plan"]],
                         [0.2, 0.4, 0.6000000000000001, 0.8])
        for move_index in range(4):
            start = move_index * 20
            frames = sequence["frames"]
            for local in (0, 10, 20):
                self.assertEqual(frames[start + local]["contacts"],
                                 {"left": True, "right": True})
            self.assertEqual(frames[start + 5]["contacts"],
                             {"left": True, "right": False})
            self.assertEqual(frames[start + 15]["contacts"],
                             {"left": False, "right": True})
            self.assertGreater(frames[start + 5]["joints"]["right_ankle"][2], 0.13)
            self.assertGreater(frames[start + 15]["joints"]["left_ankle"][2], 0.13)
            if move_index:
                self.assertEqual(frames[start]["joints"]["pelvis"][0],
                                 sequence["move_plan"][move_index]["start_root_x_m"])
        self.assertEqual(len(report["clips"]), 4)
        self.assertTrue(all(len(clip["source_clip_sha256"]) == 64 for clip in report["clips"]))
        self.assertIn("no balance", report["scope"])

    def test_mirror_displacement_bounds_and_variation_preserves_foot_path(self):
        right = compile_steps(RIGHT)["sequence"]
        left = compile_steps(LEFT)["sequence"]
        self.assertAlmostEqual(right["move_plan"][-1]["end_root_x_m"], 0.8)
        self.assertAlmostEqual(left["move_plan"][-1]["end_root_x_m"], -0.8)
        for rf, lf in zip(right["frames"], left["frames"]):
            self.assertAlmostEqual(rf["joints"]["pelvis"][0],
                                   -lf["joints"]["pelvis"][0])
            self.assertLessEqual(abs(rf["joints"]["pelvis"][0]), 0.8 + 1e-9)
            self.assertLessEqual(abs(lf["joints"]["pelvis"][0]), 0.8 + 1e-9)
        soft = compile_steps(plan(("step_right", "soft"), ("step_left", "soft"),
                                  ("step_right", "soft"), ("step_left", "soft")))["sequence"]
        clear = compile_steps(plan(("step_right", "clear"), ("step_left", "soft"),
                                   ("step_right", "soft"), ("step_left", "soft")))["sequence"]
        for a, b in zip(soft["frames"], clear["frames"]):
            for side in ("left", "right"):
                self.assertEqual(a["joints"][f"{side}_ankle"], b["joints"][f"{side}_ankle"])
                self.assertEqual(a["contacts"][side], b["contacts"][side])
        self.assertEqual(soft["frames"][20], clear["frames"][20])
        self.assertEqual(soft["frames"][21:], clear["frames"][21:])
        self.assertNotEqual(soft["frames"][5]["joints"]["left_wrist"],
                            clear["frames"][5]["joints"]["left_wrist"])
        self.assertNotEqual(soft["frames"][5]["joints"]["pelvis"][2],
                            clear["frames"][5]["joints"]["pelvis"][2])

    def test_corrupt_contact_slide_segment_timeline_nonfinite_and_receipt(self):
        baseline = compile_steps(RIGHT)
        corruptions = []
        contact = copy.deepcopy(baseline)
        contact["sequence"]["frames"][5]["contacts"]["right"] = True
        corruptions.append(contact)
        bool_contact = copy.deepcopy(baseline)
        bool_contact["sequence"]["frames"][5]["contacts"]["left"] = 1
        corruptions.append(bool_contact)
        slide = copy.deepcopy(baseline)
        slide["sequence"]["frames"][12]["joints"]["right_ankle"][0] += 0.01
        slide["sequence"]["frames"][12]["joints"]["right_foot"][0] += 0.01
        corruptions.append(slide)
        segment = copy.deepcopy(baseline)
        segment["sequence"]["frames"][7]["joints"]["left_elbow"][2] += 0.02
        corruptions.append(segment)
        timeline = copy.deepcopy(baseline)
        timeline["sequence"]["frames"][7]["time"] = 99.0
        corruptions.append(timeline)
        metadata = copy.deepcopy(baseline)
        metadata["sequence"]["fps"] = True
        corruptions.append(metadata)
        nonfinite = copy.deepcopy(baseline)
        nonfinite["sequence"]["frames"][7]["joints"]["head"][2] = math.nan
        corruptions.append(nonfinite)
        provenance = copy.deepcopy(baseline)
        provenance["receipt"]["sequence_sha256"] = "0" * 64
        corruptions.append(provenance)
        for index, corrupted in enumerate(corruptions):
            with self.subTest(index=index), self.assertRaises(ValueError):
                verify_compilation(corrupted)
        with self.assertRaisesRegex(ValueError, "planted foot sliding"):
            validate_steps(slide["sequence"])

    def test_strict_schema_and_plan_bounds(self):
        bad = [
            "not json", "```json\n" + RIGHT + "\n```",
            '{"moves":[],"moves":[]}',
            json.dumps({"moves": json.loads(RIGHT)["moves"], "revision": "model"}),
            json.dumps({"moves": json.loads(RIGHT)["moves"][:3]}),
            json.dumps({"moves": json.loads(RIGHT)["moves"] + [["step_left", "soft"]]}),
            json.dumps({"moves": [["walk", "soft"]] + json.loads(RIGHT)["moves"][1:]}),
            json.dumps({"moves": [["step_right", "wild"]] + json.loads(RIGHT)["moves"][1:]}),
            json.dumps({"moves": [["step_right", True]] + json.loads(RIGHT)["moves"][1:]}),
            json.dumps({"moves": [{"id": "step_right", "variation": "soft"}] + json.loads(RIGHT)["moves"][1:]}),
            RIGHT.replace('"soft"', 'NaN', 1),
            " " * 2049,
        ]
        for raw in bad:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                parse_steps(raw)
        self.assertEqual(set(PLAN_SCHEMA["required"]), {"moves"})
        self.assertFalse(PLAN_SCHEMA["additionalProperties"])
        self.assertIn("0.20 m", PUBLIC_CONTRACT)


if __name__ == "__main__":
    unittest.main()

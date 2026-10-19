"""Host task checks over the frozen procedural stepping compiler."""

import copy
import json
import unittest

from harness2.dance_step_task import (
    compile_task, feasible_plans, validate_task, verify_task,
)


def task(**changes):
    value = {"id": "lane-a", "start_x_mm": 0, "target_x_mm": 0,
             "root_bounds_mm": [-400, 400], "required_moves": {},
             "required_variations": {}}
    value.update(changes)
    return value


def plan(*pairs):
    return json.dumps({"moves": [list(pair) for pair in pairs]})


ALTERNATE = plan(("step_right", "soft"), ("step_left", "clear"),
                 ("step_right", "soft"), ("step_left", "clear"))


class DanceStepTaskTests(unittest.TestCase):
    def test_nonzero_origin_and_reverification(self):
        facts = task(start_x_mm=1250, target_x_mm=1250,
                     root_bounds_mm=[1050, 1450],
                     required_moves={"0": "step_right"},
                     required_variations={"1": "clear"})
        source = copy.deepcopy(facts)
        result = compile_task(ALTERNATE, facts)
        self.assertEqual(facts, source)
        self.assertEqual(result["placement"],
                         {"world_start_x_mm": 1250, "world_final_x_mm": 1250})
        self.assertEqual(result["receipt"]["checks"]["sample_count"], 81)
        self.assertEqual(result["receipt"]["checks"]["world_root_max_x_mm"], 1450)
        self.assertEqual(verify_task(result, facts), result["receipt"]["checks"])
        detached = validate_task(facts)
        detached["root_bounds_mm"][0] = -9999
        detached["required_moves"]["0"] = "step_left"
        self.assertEqual(facts, source)

    def test_feasibility_enumerates_multiple_plans_and_impossible_tasks(self):
        plans = feasible_plans(task())
        self.assertEqual(len(plans), 96)  # Six direction orders, 16 accents each.
        self.assertIn(json.loads(ALTERNATE)["moves"], plans)
        self.assertEqual(len(feasible_plans(task(required_moves={"0": "step_right"},
                                             required_variations={"1": "clear"}))), 24)
        self.assertEqual(feasible_plans(task(target_x_mm=200)), [])
        self.assertEqual(feasible_plans(task(target_x_mm=0,
                                             root_bounds_mm=[0, 0])), [])

    def test_final_target_lane_and_slot_requirements_are_distinct(self):
        with self.assertRaisesRegex(ValueError, "final root"):
            compile_task(ALTERNATE, task(target_x_mm=400))
        excursion = plan(("step_right", "soft"), ("step_right", "soft"),
                         ("step_left", "soft"), ("step_left", "soft"))
        with self.assertRaisesRegex(ValueError, "root leaves lane at frame"):
            compile_task(excursion, task(root_bounds_mm=[-200, 200]))
        with self.assertRaisesRegex(ValueError, "move slot 0"):
            compile_task(ALTERNATE, task(required_moves={"0": "step_left"}))
        with self.assertRaisesRegex(ValueError, "variation slot 1"):
            compile_task(ALTERNATE, task(required_variations={"1": "soft"}))

    def test_snapshot_receipt_and_motion_tampering_rejected(self):
        facts = task()
        result = compile_task(ALTERNATE, facts)
        changed_task = copy.deepcopy(facts)
        changed_task["id"] = "other"
        with self.assertRaisesRegex(ValueError, "receipt mismatch"):
            verify_task(result, changed_task)
        changed_placement = copy.deepcopy(result)
        changed_placement["placement"]["world_final_x_mm"] = 200
        with self.assertRaisesRegex(ValueError, "placement or receipt mismatch"):
            verify_task(changed_placement, facts)
        changed_motion = copy.deepcopy(result)
        changed_motion["local"]["sequence"]["frames"][5]["joints"]["pelvis"][0] += 0.01
        with self.assertRaises(ValueError):
            verify_task(changed_motion, facts)
        changed_receipt = copy.deepcopy(result)
        changed_receipt["receipt"]["checks"]["lane_valid"] = False
        with self.assertRaisesRegex(ValueError, "placement or receipt mismatch"):
            verify_task(changed_receipt, facts)

    def test_invalid_tasks_and_strict_model_json(self):
        bad_tasks = [
            {**task(), "extra": 1},
            task(id=""), task(id="x" * 81), task(start_x_mm=True),
            task(target_x_mm=10001), task(root_bounds_mm=(-400, 400)),
            task(root_bounds_mm=[400, -400]),
            task(root_bounds_mm=[100, 400]), task(root_bounds_mm=[False, 400]),
            task(required_moves={0: "step_left"}),
            task(required_moves={"4": "step_left"}),
            task(required_moves={"1": "walk"}),
            task(required_variations={"1": True}),
        ]
        for candidate in bad_tasks:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_task(candidate)
        for raw in ('{"moves":[],"moves":[]}',
                    '{"moves":[["step_left","soft"]],"extra":1}',
                    plan(("walk", "soft"), ("step_left", "soft"),
                         ("step_right", "soft"), ("step_left", "soft"))):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                compile_task(raw, task())


if __name__ == "__main__":
    unittest.main()

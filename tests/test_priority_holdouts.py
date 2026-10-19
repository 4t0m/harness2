"""Structural checks for the heldout priority cases; no answer-quality tests."""

import unittest

from experiments.priority_holdouts import EXPECTED_INDICES, TASKS


class PriorityHoldoutsStructureTests(unittest.TestCase):
    def test_task_shapes_and_ids(self):
        self.assertEqual(len(TASKS), 6)
        task_ids = [task["task_id"] for task in TASKS]
        self.assertEqual(len(task_ids), len(set(task_ids)))
        for task in TASKS:
            self.assertEqual(set(task), {"task_id", "brief", "options"})
            self.assertIsInstance(task["task_id"], str)
            self.assertTrue(task["task_id"].strip())
            self.assertIsInstance(task["brief"], str)
            self.assertTrue(task["brief"].strip())
            self.assertIsInstance(task["options"], list)
            self.assertEqual(len(task["options"]), 4)
            self.assertTrue(all(isinstance(option, str) and option.strip() for option in task["options"]))

    def test_expected_indices_are_separate_and_in_range(self):
        task_ids = {task["task_id"] for task in TASKS}
        self.assertEqual(set(EXPECTED_INDICES), task_ids)
        for task_id, index in EXPECTED_INDICES.items():
            self.assertIsInstance(index, int)
            self.assertGreaterEqual(index, 0)
            self.assertLess(index, 4)


if __name__ == "__main__":
    unittest.main()

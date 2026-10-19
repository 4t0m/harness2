"""Structural checks only for heldout avatar-scope cases."""

import unittest

from experiments.avatar_scope_holdouts import ACTION_CATALOG, EXPECTED_INDICES, TASKS


class AvatarScopeHoldoutsStructureTests(unittest.TestCase):
    def test_task_shapes_and_unique_ids(self):
        self.assertEqual(len(TASKS), 8)
        task_ids = [task["task_id"] for task in TASKS]
        self.assertEqual(len(task_ids), len(set(task_ids)))
        for task in TASKS:
            self.assertEqual(set(task), {"task_id", "brief", "options"})
            self.assertIsInstance(task["task_id"], str)
            self.assertTrue(task["task_id"].strip())
            self.assertIsInstance(task["brief"], str)
            self.assertTrue(task["brief"].strip())
            self.assertIsInstance(task["options"], list)
            self.assertEqual(task["options"], ACTION_CATALOG)

    def test_expected_choices_are_separate_and_in_range(self):
        task_ids = {task["task_id"] for task in TASKS}
        self.assertEqual(set(EXPECTED_INDICES), task_ids)
        for index in EXPECTED_INDICES.values():
            self.assertIsInstance(index, int)
            self.assertGreaterEqual(index, 0)
            self.assertLess(index, len(ACTION_CATALOG))


if __name__ == "__main__":
    unittest.main()

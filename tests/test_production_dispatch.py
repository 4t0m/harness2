"""Offline tests for production-job dispatch choices and trusted state transitions."""

import copy
import json
import unittest

from harness2.production_dispatch import (
    TASKS,
    DispatchError,
    evaluate,
    model_brief,
    valid_choices,
    validate_task,
)


def scene(task_id):
    return next(task for task in TASKS if task["task_id"] == task_id)


def action(operation, job_id):
    return json.dumps({"operation": operation, "job_id": job_id})


class ProductionDispatchTest(unittest.TestCase):
    def test_eight_frozen_scenes_cover_expected_policy_cases(self):
        self.assertEqual(len(TASKS), 8)
        self.assertEqual(len({task["task_id"] for task in TASKS}), 8)
        self.assertEqual({choice["operation"] for choice in valid_choices(scene("mix-order-01"))},
                         {"retry", "dispatch"})
        self.assertEqual(valid_choices(scene("blocked-02")), [{"operation": "wait", "job_id": None}])
        self.assertEqual(valid_choices(scene("approval-03")), [{"operation": "wait", "job_id": None}])
        self.assertEqual(valid_choices(scene("retry-lineage-04")), [{"operation": "wait", "job_id": None}])
        self.assertEqual(valid_choices(scene("dependency-unlocked-05")),
                         [{"operation": "dispatch", "job_id": "child_eta"}])
        self.assertEqual(len(valid_choices(scene("two-runnable-06"))), 2)
        self.assertEqual(valid_choices(scene("nothing-left-07")), [{"operation": "wait", "job_id": None}])
        self.assertEqual(valid_choices(scene("human-approved-08")),
                         [{"operation": "dispatch", "job_id": "approved_nu"}])

    def test_model_brief_does_not_leak_oracle_choices(self):
        brief = model_brief(scene("mix-order-01"))
        self.assertIn("task", brief)
        self.assertIn("action_schema", brief)
        self.assertNotIn("valid_choices", brief)
        self.assertEqual(brief["action_schema"]["properties"]["operation"]["enum"],
                         ["dispatch", "retry", "wait"])

    def test_accepts_any_oracle_legal_action_not_a_hardcoded_order(self):
        task = scene("mix-order-01")
        choices = valid_choices(task)
        selected = choices[-1]
        result = evaluate(task, json.dumps(selected))
        self.assertTrue(result["valid"])
        self.assertEqual(result["action"], selected)
        self.assertTrue(result["state_preserved"])
        self.assertEqual(task["jobs"][0]["status"], "pending")  # evaluator did not mutate input

    def test_completed_dependency_unlocks_pending_dispatch(self):
        result = evaluate(scene("dependency-unlocked-05"), action("dispatch", "child_eta"))
        self.assertTrue(result["valid"])
        statuses = {job["job_id"]: job["status"] for job in result["after"]["jobs"]}
        self.assertEqual(statuses, {"child_eta": "running", "parent_eta": "completed"})
        self.assertEqual(result["after"]["jobs"][1]["artifact_receipt"]["artifact_id"], "asset-eta")

    def test_failed_dependency_and_missing_human_approval_block_dispatch(self):
        for task_id, job_id in (("blocked-02", "waiting_child"), ("approval-03", "needs_human")):
            with self.subTest(task=task_id):
                result = evaluate(scene(task_id), action("dispatch", job_id))
                self.assertFalse(result["valid"])
                self.assertEqual(result["status"], "rejected")
                self.assertTrue(result["state_preserved"])

    def test_retry_cap_and_existing_retry_child_prevent_duplicate_retry(self):
        result = evaluate(scene("retry-lineage-04"), action("retry", "orig_epsilon"))
        self.assertFalse(result["valid"])
        self.assertEqual(result["valid_choices"], [{"operation": "wait", "job_id": None}])

    def test_retry_creates_child_and_preserves_original_and_completed_receipts(self):
        task = scene("mix-order-01")
        result = evaluate(task, action("retry", "retry_beta"))
        self.assertTrue(result["valid"])
        self.assertTrue(result["state_preserved"])
        rows = {job["job_id"]: job for job in result["after"]["jobs"]}
        self.assertEqual(rows["retry_beta"]["status"], "failed")
        self.assertEqual(rows["retry_beta_retry_2"]["retry_of"], "retry_beta")
        self.assertEqual(rows["retry_beta_retry_2"]["status"], "pending")
        self.assertEqual(rows["done_z"]["artifact_receipt"]["artifact_id"], "asset-z")
        self.assertEqual(validate_task(result["after"]), result["after"])

    def test_wait_is_valid_noop_only_when_nothing_can_run_or_retry(self):
        result = evaluate(scene("blocked-02"), action("wait", None))
        self.assertTrue(result["valid"])
        self.assertEqual(result["before"], result["after"])
        self.assertFalse(evaluate(scene("mix-order-01"), action("wait", None))["valid"])

    def test_rejects_malformed_or_non_exact_actions(self):
        for raw in ("not json", '{"operation":"wait","job_id":null,"note":"x"}',
                    '{"operation":"dispatch","job_id":"later_alpha","operation":"wait"}',
                    '{"operation":"wait","job_id":"not-null"}'):
            with self.subTest(raw=raw):
                result = evaluate(scene("blocked-02"), raw)
                self.assertFalse(result["valid"])
                self.assertTrue(result["state_preserved"])

    def test_unhashable_operation_values_are_structured_rejections(self):
        for raw in ('{"operation":[],"job_id":null}',
                    '{"operation":{},"job_id":null}'):
            with self.subTest(raw=raw):
                result = evaluate(scene("blocked-02"), raw)
                self.assertFalse(result["valid"])
                self.assertEqual(result["status"], "rejected")
                self.assertTrue(result["state_preserved"])

    def test_long_failed_id_derives_valid_retry_id_and_post_state(self):
        task = copy.deepcopy(scene("mix-order-01"))
        failed = task["jobs"][1]
        long_id = "a" + "b" * 39
        failed["job_id"] = long_id
        result = evaluate(task, action("retry", long_id))
        self.assertTrue(result["valid"])
        retry = result["after"]["jobs"][-1]
        self.assertLessEqual(len(retry["job_id"]), 40)
        self.assertEqual(retry["retry_of"], long_id)
        self.assertEqual(validate_task(result["after"]), result["after"])

    def test_retry_id_collision_is_not_advertised_as_legal(self):
        task = copy.deepcopy(scene("mix-order-01"))
        task["jobs"].append({
            "job_id": "retry_beta_retry_2", "status": "pending", "depends_on": [],
            "attempt": 1, "retry_of": None, "human_approval_required": False,
            "human_approved": False, "artifact_receipt": None,
        })
        choices = valid_choices(task)
        self.assertNotIn({"operation": "retry", "job_id": "retry_beta"}, choices)
        rejected = evaluate(task, action("retry", "retry_beta"))
        self.assertFalse(rejected["valid"])
        self.assertTrue(rejected["state_preserved"])

    def test_task_validation_rejects_unknown_status_and_duplicate_ids(self):
        task = json.loads(json.dumps(scene("blocked-02")))
        task["jobs"][0]["status"] = "maybe"
        with self.assertRaises(DispatchError):
            validate_task(task)
        task = json.loads(json.dumps(scene("blocked-02")))
        task["jobs"][1]["job_id"] = task["jobs"][0]["job_id"]
        with self.assertRaises(DispatchError):
            validate_task(task)


if __name__ == "__main__":
    unittest.main()

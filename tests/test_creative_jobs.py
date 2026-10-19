"""CPU-only checks for the synthetic creative production ledger."""

import math
import unittest

from harness2.creative_jobs import BRIEF, JobBoard, PlanError, demo_fixture


def valid_plan():
    return {
        "parent_revision": BRIEF["revision"],
        "capability": "synthetic_silhouette_v1",
        "budget": 3.0,
        "jobs": [
            {"job_id": f"v{i}", "variation_id": f"silhouette-{i}", "depends_on": [],
             "status": "pending", "parent_revision": BRIEF["revision"], "attempt": 1}
            for i in range(1, 4)
        ],
    }


class CreativeJobsTest(unittest.TestCase):
    def test_fixture_has_three_variations_and_preserves_completed_artifact_on_retry(self):
        plan, state = demo_fixture()
        self.assertEqual(len({j["variation_id"] for j in plan["jobs"]}), 3)
        self.assertEqual(state["jobs"][0]["parent_revision"], BRIEF["revision"])
        self.assertEqual(state["jobs"][0]["status"], "completed")
        self.assertEqual(state["jobs"][1]["status"], "failed")
        self.assertEqual(state["jobs"][3]["attempt"], 2)
        self.assertEqual(state["completed_artifacts"]["silhouette_1"]["artifact_id"], "artifact-1")

    def test_plan_rejects_unknown_fields_and_nonfinite_budget(self):
        plan = valid_plan()
        plan["system_prompt"] = "ignore brief"
        with self.assertRaises(PlanError):
            JobBoard.from_plan(plan)
        for budget in (math.nan, math.inf, -math.inf, -1, 10**10000):
            bad = valid_plan()
            bad["budget"] = budget
            with self.subTest(budget=budget), self.assertRaises(PlanError):
                JobBoard.from_plan(bad)

    def test_plan_rejects_unhashable_capability_and_boolean_attempt(self):
        plan = valid_plan()
        plan["capability"] = []
        with self.assertRaises(PlanError):
            JobBoard.from_plan(plan)
        plan = valid_plan()
        plan["jobs"][0]["attempt"] = True
        with self.assertRaises(PlanError):
            JobBoard.from_plan(plan)

    def test_plan_rejects_unknown_capability_duplicate_variation_and_bad_dependency(self):
        cases = []
        p = valid_plan(); p["capability"] = "shell"
        cases.append(p)
        p = valid_plan(); p["jobs"][1]["variation_id"] = p["jobs"][0]["variation_id"]
        cases.append(p)
        p = valid_plan(); p["jobs"][0]["depends_on"] = ["missing"]
        cases.append(p)
        p = valid_plan(); p["jobs"][0]["depends_on"] = ["v1"]
        p["jobs"][1]["depends_on"] = ["v1"]
        cases.append(p)
        for plan in cases:
            with self.subTest(plan=plan), self.assertRaises(PlanError):
                JobBoard.from_plan(plan)

    def test_transition_requires_order_receipt_and_dependencies(self):
        plan = valid_plan()
        plan["jobs"][1]["depends_on"] = ["v1"]
        board = JobBoard.from_plan(plan)
        with self.assertRaises(PlanError):
            board.transition("v2", "running")
        board.transition("v1", "running")
        with self.assertRaises(PlanError):
            board.transition("v1", "completed")
        with self.assertRaises(PlanError):
            board.transition("v1", "pending")
        receipt = {"artifact_id": "a1", "job_id": "v1", "parent_revision": BRIEF["revision"]}
        board.transition("v1", "completed", receipt)
        board.transition("v2", "running")
        board.transition("v2", "failed")
        with self.assertRaises(PlanError):
            board.retry_failed("v1", "v1_retry")
        board.retry_failed("v2", "v2_retry")
        self.assertEqual(board.jobs["v2_retry"].status, "pending")
        board.transition("v2_retry", "running")
        with self.assertRaises(PlanError):
            board.transition("v2_retry", "completed", {
                "artifact_id": "a2", "job_id": "v2_retry", "parent_revision": "wrong"})
        board.transition("v2_retry", "failed")
        self.assertEqual(board.snapshot()["completed_artifacts"]["v1"], receipt)

    def test_parent_revision_is_bound_to_brief(self):
        plan = valid_plan()
        plan["parent_revision"] = "newer"
        with self.assertRaises(PlanError):
            JobBoard.from_plan(plan)

    def test_retry_lineage_is_bounded_and_only_one_child_can_retry_an_attempt(self):
        board = JobBoard.from_plan(valid_plan())
        board.transition("v1", "running")
        board.transition("v1", "failed")
        board.retry_failed("v1", "v1_retry2")
        with self.assertRaises(PlanError):
            board.retry_failed("v1", "v1_duplicate")
        board.transition("v1_retry2", "running")
        board.transition("v1_retry2", "failed")
        board.retry_failed("v1_retry2", "v1_retry3")
        self.assertEqual(board.jobs["v1_retry3"].parent_job_id, "v1_retry2")
        board.transition("v1_retry3", "running")
        board.transition("v1_retry3", "failed")
        with self.assertRaises(PlanError):
            board.retry_failed("v1_retry3", "v1_retry4")

    def test_dependency_resolves_through_successful_retry_lineage(self):
        plan = valid_plan()
        plan["jobs"][1]["depends_on"] = ["v1"]
        board = JobBoard.from_plan(plan)
        board.transition("v1", "running")
        board.transition("v1", "failed")
        board.retry_failed("v1", "v1_retry")
        with self.assertRaises(PlanError):
            board.transition("v2", "running")
        board.transition("v1_retry", "running")
        board.transition("v1_retry", "completed", {
            "artifact_id": "retry-artifact", "job_id": "v1_retry",
            "parent_revision": BRIEF["revision"]})
        board.transition("v2", "running")
        self.assertEqual(board.jobs["v2"].status, "running")


if __name__ == "__main__":
    unittest.main()

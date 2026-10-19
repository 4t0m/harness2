"""Offline checks for the frozen four-candidate guidance admission gate."""

import copy
import hashlib
import json
import unittest

from harness2.dance_guidance_admission import PRIORITY, choose_admitted
from harness2.dance_step_h2 import PUBLIC_CONTRACT, verdict


TASK = {
    "task": {
        "id": "admission_case",
        "start_x_mm": 0,
        "target_x_mm": 0,
        "root_bounds_mm": [-400, 400],
        "required_moves": {},
        "required_variations": {},
    },
    "request": "Return to the origin inside the approved lane.",
}

VALID_PLAN = json.dumps({"moves": [
    ["step_left", "soft"], ["step_right", "clear"],
    ["step_left", "clear"], ["step_right", "soft"],
]})
INVALID_PLAN = json.dumps({"moves": [
    ["step_right", "soft"], ["step_right", "clear"],
    ["step_right", "clear"], ["step_right", "soft"],
]})
GUIDANCE = {
    "base1": "Read every approved task field and choose a four-step plan that satisfies them.\n",
    "inv1": "Track the root position after each step and honor every required slot.\n",
    "dom1": "Check the endpoint and lane bounds before returning the four pairs.\n",
    "c1": "Use the structured task as authority and verify all constraints before responding.\n",
}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _candidate(label, content=VALID_PLAN):
    guidance = GUIDANCE[label]
    host = verdict(content, TASK)
    receipt = {
        "task_id": TASK["task"]["id"],
        "run_id": f"eval/session/{label}",
        "mode": "model_solver",
        "guidance_sha256": _sha(guidance),
        "request_sha256": _sha(guidance + "\n" + PUBLIC_CONTRACT + "\n"
                                 + json.dumps(TASK, sort_keys=True)),
        "attempts": 1,
        "finish_reason": "stop",
        "content": content,
        "verdict": {"valid": host["valid"], "reason": host["reason"]},
    }
    return {"label": label, "guidance": guidance, "receipt": receipt}


def _all(content_by_label=None):
    content_by_label = content_by_label or {}
    return [_candidate(label, content_by_label.get(label, VALID_PLAN))
            for label in reversed(PRIORITY)]


class DanceGuidanceAdmissionTests(unittest.TestCase):
    def test_selects_highest_priority_candidate_with_replayed_valid_plan(self):
        candidates = _all({"c1": INVALID_PLAN, "dom1": VALID_PLAN,
                           "inv1": VALID_PLAN, "base1": INVALID_PLAN})
        result = choose_admitted(candidates, TASK)
        self.assertEqual(result["selected"]["label"], "dom1")
        self.assertEqual(result["selected"]["guidance"], GUIDANCE["dom1"])
        self.assertEqual(result["selected"]["guidance_sha256"], _sha(GUIDANCE["dom1"]))
        self.assertEqual([row["label"] for row in result["audited_candidates"]], list(PRIORITY))
        self.assertFalse(result["audited_candidates"][0]["valid"])
        self.assertTrue(result["audited_candidates"][1]["valid"])

    def test_composed_candidate_failure_falls_back_in_fixed_priority(self):
        result = choose_admitted(_all({"c1": INVALID_PLAN, "dom1": INVALID_PLAN,
                                       "inv1": VALID_PLAN}), TASK)
        self.assertEqual(result["selected"]["label"], "inv1")

    def test_c1_wins_when_independently_valid(self):
        result = choose_admitted(_all(), TASK)
        self.assertEqual(result["selected"]["label"], "c1")

    def test_all_semantically_invalid_candidates_return_none(self):
        result = choose_admitted(_all({label: INVALID_PLAN for label in PRIORITY}), TASK)
        self.assertIsNone(result["selected"])
        self.assertEqual(len(result["audited_candidates"]), 4)
        self.assertTrue(all(not row["valid"] for row in result["audited_candidates"]))

    def test_receipt_for_different_task_is_provenance_error(self):
        candidates = _all()
        candidates[0]["receipt"]["task_id"] = "other_task"
        with self.assertRaisesRegex(ValueError, "different task"):
            choose_admitted(candidates, TASK)

    def test_request_hash_mismatch_is_provenance_error(self):
        candidates = _all()
        candidates[0]["receipt"]["request_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "request hash mismatch"):
            choose_admitted(candidates, TASK)

    def test_guidance_hash_mismatch_is_provenance_error(self):
        candidates = _all()
        candidates[0]["receipt"]["guidance_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "guidance hash mismatch"):
            choose_admitted(candidates, TASK)

    def test_saved_true_verdict_cannot_admit_invalid_raw_plan(self):
        forged = _candidate("c1", INVALID_PLAN)
        forged["receipt"]["verdict"] = {"valid": True, "reason": "step task constraints satisfied"}
        candidates = [_candidate(label) for label in PRIORITY if label != "c1"] + [forged]
        with self.assertRaisesRegex(ValueError, "saved verdict disagrees"):
            choose_admitted(candidates, TASK)

    def test_duplicate_or_extra_candidate_labels_are_rejected(self):
        candidates = _all()
        candidates[-1] = copy.deepcopy(candidates[0])
        with self.assertRaisesRegex(ValueError, "duplicate candidate label"):
            choose_admitted(candidates, TASK)
        candidates = _all()
        candidates[0]["label"] = "extra"
        with self.assertRaisesRegex(ValueError, "unknown candidate label"):
            choose_admitted(candidates, TASK)

    def test_false_saved_verdict_for_valid_plan_is_rejected(self):
        candidates = _all()
        candidates[0]["receipt"]["verdict"] = {"valid": False, "reason": "forged rejection"}
        with self.assertRaisesRegex(ValueError, "saved verdict disagrees"):
            choose_admitted(candidates, TASK)


if __name__ == "__main__":
    unittest.main()

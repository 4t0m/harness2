"""Offline tests for model-selected retry intent and trusted host application."""

import json
import unittest

from harness2.actor_provider import ChatResult
from experiments.creative_retry_probe import (
    model_request,
    replay_saved_live_receipt,
    run_probe,
    synthetic_board,
)


def reply(content):
    return ChatResult(content=content, finish_reason="stop", usage={
        "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
    }, latency_seconds=0.01, model="fake-model")


class CreativeRetryProbeTest(unittest.TestCase):
    def test_retry_target_is_inferred_from_visible_state_not_separately_prompted(self):
        board = synthetic_board()
        _system, user = model_request(board)
        self.assertIn('"status": "failed"', user)
        self.assertNotIn("expected_failed_job", user)
        self.assertNotIn('"slot_2"', user.split("Current production state:", 1)[0])

    def test_rejects_completed_target_without_mutating_state(self):
        board = synthetic_board()
        before = board.snapshot()
        evidence = run_probe(
            lambda **_: reply(json.dumps({"operation": "retry_failed", "job_id": "slot_1",
                                          "new_job_id": "slot_1_retry"})),
            base_url="https://provider.invalid/v1", model="fake-model", board=board,
        )
        self.assertEqual(evidence["result"], "rejected")
        self.assertIn("host-selected failed job", evidence["validation_error"])
        self.assertEqual(board.snapshot(), before)

    def test_rejects_existing_job_id_collision_without_mutating_state(self):
        board = synthetic_board()
        before = board.snapshot()
        evidence = run_probe(
            lambda **_: reply(json.dumps({"operation": "retry_failed", "job_id": "slot_2",
                                          "new_job_id": "slot_3"})),
            base_url="https://provider.invalid/v1", model="fake-model", board=board,
        )
        self.assertEqual(evidence["result"], "rejected")
        self.assertIn("must not collide", evidence["validation_error"])
        self.assertEqual(board.snapshot(), before)

    def test_valid_retry_applies_only_to_failed_job_and_preserves_completed_receipt(self):
        board = synthetic_board()
        before = board.snapshot()
        evidence = run_probe(
            lambda **_: reply(json.dumps({"operation": "retry_failed", "job_id": "slot_2",
                                          "new_job_id": "slot_2_retry"})),
            base_url="https://provider.invalid/v1", model="fake-model", board=board,
        )
        self.assertEqual(evidence["result"], "retry_queued")
        self.assertTrue(evidence["applied"]["preserved_completed_receipts"])
        self.assertTrue(evidence["applied"]["unaffected_jobs_preserved"])
        self.assertEqual(board.jobs["slot_1"].artifact_receipt["artifact_id"], "artifact-slot-1")
        self.assertEqual(board.jobs["slot_2"].status, "failed")
        self.assertEqual(board.jobs["slot_3"].status, "pending")
        self.assertEqual(board.jobs["slot_2_retry"].parent_job_id, "slot_2")
        self.assertEqual(board.jobs["slot_2_retry"].attempt, 2)

    def test_strict_intent_rejects_unknown_field(self):
        evidence = run_probe(
            lambda **_: reply(json.dumps({"operation": "retry_failed", "job_id": "slot_2",
                                          "new_job_id": "slot_2_retry", "status": "pending"})),
            base_url="https://provider.invalid/v1", model="fake-model",
        )
        self.assertEqual(evidence["result"], "rejected")
        self.assertIn("exactly operation", evidence["validation_error"])

    def test_exact_json_fence_is_optional_repair_and_still_uses_strict_validation(self):
        content = '```json\n{"operation":"retry_failed","job_id":"slot_2","new_job_id":"slot_2_retry"}\n```'
        board = synthetic_board()
        evidence = run_probe(
            lambda **_: reply(content), base_url="https://provider.invalid/v1",
            model="fake-model", board=board,
        )
        self.assertEqual(evidence["result"], "rejected")
        board = synthetic_board()
        evidence = run_probe(
            lambda **_: reply(content), base_url="https://provider.invalid/v1",
            model="fake-model", board=board, repair_single_json_fence=True,
        )
        self.assertEqual(evidence["result"], "retry_queued")
        self.assertTrue(evidence["fence_repair_applied"])
        self.assertEqual(board.jobs["slot_2_retry"].status, "pending")

    def test_exact_repair_rejects_malformed_multiple_and_surrounding_text(self):
        body = '{"operation":"retry_failed","job_id":"slot_2","new_job_id":"slot_2_retry"}'
        invalid = [
            "```json\n{bad json}\n```",
            f"```json\n{body}\n```\n```json\n{body}\n```",
            f"Here is the plan:\n```json\n{body}\n```",
            f"```json\n{body}\n```\nDone.",
            f"```\n{body}\n```",
        ]
        for content in invalid:
            with self.subTest(content=content):
                evidence = run_probe(
                    lambda **_: reply(content), base_url="https://provider.invalid/v1",
                    model="fake-model", repair_single_json_fence=True,
                )
                self.assertEqual(evidence["result"], "rejected")

    def test_fenced_wrong_target_still_fails_host_target_validation(self):
        content = '```json\n{"operation":"retry_failed","job_id":"slot_1","new_job_id":"slot_1_retry"}\n```'
        board = synthetic_board()
        before = board.snapshot()
        evidence = run_probe(
            lambda **_: reply(content), base_url="https://provider.invalid/v1",
            model="fake-model", board=board, repair_single_json_fence=True,
        )
        self.assertEqual(evidence["result"], "rejected")
        self.assertIn("host-selected failed job", evidence["validation_error"])
        self.assertEqual(board.snapshot(), before)

    def test_offline_saved_receipt_replay_is_labeled_and_preserves_original(self):
        content = '```json\n{"operation":"retry_failed","job_id":"slot_2","new_job_id":"slot_2_retry_1"}\n```'
        replay = replay_saved_live_receipt({
            "result": "rejected", "validation_error": "response must be one strict JSON object",
            "model_served": "google/gemma-4-26b-a4b-it", "raw_content": content,
        })
        self.assertEqual(replay["kind"], "deterministic_repair_replay")
        self.assertTrue(replay["fence_repair_applied"])
        self.assertEqual(replay["original_raw_content"], content)
        self.assertFalse(replay["model_retry_performed"])
        self.assertEqual(replay["result"], "retry_queued")


if __name__ == "__main__":
    unittest.main()

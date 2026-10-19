"""Offline integration checks for model-backed production Harness2 wiring."""

import json
from pathlib import Path
import tempfile
import unittest

from harness2.actor_provider import ChatResult
from harness2.core.schedule import run_domain
from harness2.production_dispatch import _job, _task
from harness2.production_h2 import (
    BASE_GUIDANCE, ProductionAdapter, ProductionImprover, parse_editor_response,
)


def _result(content):
    return ChatResult(content=content, finish_reason="stop", usage={"prompt_tokens": 1,
                      "completion_tokens": 1, "total_tokens": 2}, latency_seconds=0.01,
                      model="fake", raw_response={"usage": {"cost": 0.001}})


class ProductionH2Tests(unittest.TestCase):
    def test_editor_response_is_single_bounded_text_field(self):
        with self.assertRaises(ValueError):
            parse_editor_response('{"systemprompt":"a","systemprompt":"b"}')
        with self.assertRaises(ValueError):
            parse_editor_response(json.dumps({"systemprompt": BASE_GUIDANCE, "other": "x"}))
        with self.assertRaises(ValueError):
            parse_editor_response(json.dumps({"systemprompt": "```python\nprint(1)\n```\n"}))

    def test_exact_fence_and_final_newline_are_format_only(self):
        raw = json.dumps({"systemprompt": BASE_GUIDANCE.rstrip("\n")})
        self.assertEqual(parse_editor_response("```json\n" + raw + "\n```"), BASE_GUIDANCE)
        with self.assertRaises(ValueError):
            parse_editor_response("Here is the answer: " + raw)
        with self.assertRaises(ValueError):
            parse_editor_response(json.dumps({"systemprompt": []}))

    def test_actual_run_domain_uses_model_solver_and_editor(self):
        dev = _task("dev_cap", [_job("failed_job", "failed", attempt=2)], max_attempts=2)
        holdout = _task("private_holdout", [_job("other_job", "pending")])
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            if "Improve generic production dispatch guidance" in kwargs["system"]:
                self.assertIn("dev_cap", kwargs["user"])
                self.assertNotIn("private_holdout", kwargs["user"])
                return _result(json.dumps({"systemprompt": BASE_GUIDANCE +
                                           "Check attempt < max_attempts before retrying.\n"}))
            self.assertNotIn("private_holdout", kwargs["user"])
            action = {"operation": "wait", "job_id": None} if "Check attempt <" in kwargs["system"] else {
                "operation": "retry", "job_id": "failed_job"}
            return _result(json.dumps(action))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = ProductionAdapter(root, {dev["task_id"]: dev, holdout["task_id"]: holdout},
                                        [dev["task_id"]], provider=provider,
                                        base_url="http://localhost:8080/v1", model="fake",
                                        max_solver_calls=8)
            editor = ProductionImprover(adapter.spec.channels["proposer"], provider=provider,
                                        base_url="http://localhost:8080/v1", model="fake",
                                        audit_dir=root / "editor", max_editor_calls=3)
            with self.assertRaises(ValueError):
                adapter.task_prompt(holdout["task_id"])
            result = run_domain("production-planning", adapter.tasks("train"), 1,
                                adapter=adapter, prop=editor, runs_root=adapter.spec.runs_root,
                                library_root=root / "library", modes=("seq",))
            self.assertEqual(result["done"], 1, result)
            self.assertEqual(adapter.solver_calls, 4)
            self.assertEqual(editor.editor_calls, 3)
            summary = json.loads((adapter.spec.runs_root / "production_h2-oc-agg1" /
                                  "dev_cap" / "summary.json").read_text())
            chosen = Path(summary["selections"]["seq"]["chosen_run_dir"])
            verdict = json.loads((chosen / "verdict.json").read_text())
            self.assertTrue(verdict["valid"])
            self.assertEqual(verdict["action"], {"operation": "wait", "job_id": None})
            base = Path(summary["base"][0]["run_dir"])
            self.assertFalse(json.loads((base / "verdict.json").read_text())["valid"])
            self.assertEqual(len(list((root / "editor").glob("*.json"))), 3)
            self.assertEqual(len(list((root / "executions").rglob("receipt.json"))), 4)
            self.assertTrue(all("private_holdout" not in json.dumps(call) for call in calls))

    def test_separate_solver_cap_preserves_refusal_receipt(self):
        dev = _task("dev_cap", [_job("failed_job", "failed", attempt=2)], max_attempts=2)
        with tempfile.TemporaryDirectory() as directory:
            adapter = ProductionAdapter(Path(directory), {dev["task_id"]: dev}, [dev["task_id"]],
                                        provider=lambda **kw: _result('{"operation":"wait","job_id":null}'),
                                        base_url="http://localhost:8080/v1", model="fake",
                                        max_solver_calls=1)
            first = adapter.execute("dev_cap", None, "first")
            second = adapter.execute("dev_cap", None, "second")
            self.assertTrue(adapter.delivered(first))
            self.assertFalse(adapter.delivered(second))
            self.assertEqual(json.loads((second / "receipt.json").read_text())["attempts"], 0)
            self.assertEqual(adapter.solver_calls, 1)


if __name__ == "__main__":
    unittest.main()

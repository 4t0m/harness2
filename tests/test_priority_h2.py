"""Offline semantic-choice integration checks for the creative priority adapter."""

import json
from pathlib import Path
import tempfile
import unittest

from harness2.actor_provider import ChatResult
from harness2.core.schedule import run_domain
from harness2.priority_h2 import BASE_GUIDANCE, PriorityAdapter
from harness2.production_h2 import ProductionImprover


def _result(content):
    return ChatResult(content=content, finish_reason="stop", usage={"prompt_tokens": 3,
                      "completion_tokens": 2, "total_tokens": 5}, latency_seconds=0.01,
                      model="fake", raw_response={"usage": {"cost": 0.001}})


def _task(task_id, brief="Preserve the approved shape and compare only expressions."):
    return {"task_id": task_id, "brief": brief, "options": [
        "Change camera and expression together.",
        "Compare expressions with the approved shape and camera fixed.",
        "Change the approved shape and keep expression fixed.",
    ]}


class PriorityH2Tests(unittest.TestCase):
    def test_actual_run_domain_uses_semantic_host_verdict_and_private_holdout(self):
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            if "Improve generic production dispatch guidance" in kwargs["system"]:
                self.assertIn("dev_priority", kwargs["user"])
                self.assertNotIn("private_holdout", kwargs["user"])
                return _result(json.dumps({"systemprompt": BASE_GUIDANCE +
                                           "Keep approved elements fixed while selecting the next step.\n"}))
            self.assertEqual(kwargs["timeout"], 20.0)
            self.assertEqual(kwargs["max_output_tokens"], 128)
            request = json.loads(kwargs["user"])
            self.assertEqual(len(request["legal_options"]), 3)
            self.assertIn("brief", request)
            self.assertNotIn("expected", kwargs["user"])
            self.assertNotIn("private_holdout", kwargs["user"])
            choice = "option_1" if "Keep approved elements" in kwargs["system"] else "option_0"
            return _result(json.dumps({"choice_id": choice}))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tasks = {"dev_priority": _task("dev_priority"),
                     "private_holdout": _task("private_holdout", "Holdout-only marker.")}
            adapter = PriorityAdapter(root, tasks, {"dev_priority": 1, "private_holdout": 2},
                                      ["dev_priority"], provider=provider,
                                      base_url="http://localhost:8080/v1", model="fake",
                                      max_solver_calls=8)
            editor = ProductionImprover(adapter.spec.channels["proposer"], provider=provider,
                                        base_url="http://localhost:8080/v1", model="fake",
                                        audit_dir=root / "editor", max_editor_calls=3)
            with self.assertRaises(ValueError):
                adapter.task_prompt("private_holdout")
            with self.assertRaises(ValueError):
                adapter.task_files("private_holdout")
            result = run_domain("creative-priority", adapter.tasks("train"), 1,
                                adapter=adapter, prop=editor, runs_root=adapter.spec.runs_root,
                                library_root=root / "library", modes=("seq",))
            self.assertEqual(result["done"], 1, result)
            self.assertEqual(adapter.solver_calls, 4)
            self.assertEqual(editor.editor_calls, 3)
            summary = json.loads((adapter.spec.runs_root / "priority_h2-oc-agg1" /
                                  "dev_priority" / "summary.json").read_text())
            chosen = Path(summary["selections"]["seq"]["chosen_run_dir"])
            chosen_verdict = json.loads((chosen / "verdict.json").read_text())
            self.assertTrue(chosen_verdict["valid"])
            self.assertTrue(chosen_verdict["semantic_correct"])
            self.assertEqual(chosen_verdict["choice_id"], "option_1")
            base = Path(summary["base"][0]["run_dir"])
            base_verdict = json.loads((base / "verdict.json").read_text())
            self.assertTrue(base_verdict["accepted_format"])
            self.assertFalse(base_verdict["valid"])
            self.assertEqual(base_verdict["choice_id"], "option_0")
            self.assertEqual(len(list((root / "editor").glob("*.json"))), 3)
            self.assertTrue(all("private_holdout" not in json.dumps(call) for call in calls))
            self.assertNotIn("expected", (root / "sources" / "dev_priority" / "brief.json").read_text())

    def test_strict_and_repaired_format_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = PriorityAdapter(Path(directory), {"dev": _task("dev")}, {"dev": 1}, ["dev"],
                                      provider=lambda **kw: _result('```json\n{"choice_id":"option_1"}\n```'),
                                      base_url="http://localhost:8080/v1", model="fake",
                                      repair_single_json_fence=True)
            run = adapter.execute("dev", None, "fenced")
            receipt = json.loads((run / "receipt.json").read_text())
            self.assertFalse(receipt["strict_verdict"]["accepted_format"])
            self.assertTrue(receipt["repaired_verdict"]["valid"])
            self.assertTrue(receipt["verdict"]["valid"])
            self.assertEqual((run / "proposal.json").read_text().strip(),
                             '```json\n{"choice_id":"option_1"}\n```')

    def test_malformed_choice_and_budget_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = PriorityAdapter(Path(directory), {"dev": _task("dev")}, {"dev": 1}, ["dev"],
                                      provider=lambda **kw: _result('{"choice_id":"option_1","choice_id":"option_0"}'),
                                      base_url="http://localhost:8080/v1", model="fake",
                                      max_solver_calls=1)
            first = adapter.execute("dev", None, "first")
            second = adapter.execute("dev", None, "second")
            verdict = json.loads((first / "verdict.json").read_text())
            self.assertFalse(verdict["accepted_format"])
            self.assertFalse(verdict["valid"])
            self.assertFalse(adapter.delivered(second))
            self.assertEqual(json.loads((second / "receipt.json").read_text())["attempts"], 0)
            self.assertEqual(adapter.solver_calls, 1)

    def test_host_input_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            task = _task("dev")
            kwargs = {"base_url": "http://localhost:8080/v1", "model": "fake"}
            with self.assertRaises(ValueError):
                PriorityAdapter(Path(directory), {"dev": task}, {"dev": 3}, ["dev"], **kwargs)
            with self.assertRaises(ValueError):
                PriorityAdapter(Path(directory), {"dev": task}, {}, ["dev"], **kwargs)
            with self.assertRaises(ValueError):
                PriorityAdapter(Path(directory), {"dev": dict(task, expected_index=1)},
                                {"dev": 1}, ["dev"], **kwargs)


if __name__ == "__main__":
    unittest.main()

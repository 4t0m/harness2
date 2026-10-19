"""Scripted Harness2 wiring for host-checked side-step tasks."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.dance_step_task_cases import CASES
from experiments.dance_step_task_probe import SYSTEM as TRIAL_SYSTEM
from harness2.actor_provider import ChatResult
from harness2.core.schedule import run_domain
from harness2.dance_step_h2 import (
    BASE_GUIDANCE, EDITOR_PUBLIC_RULE, PUBLIC_CONTRACT, StepAdapter, verdict,
)
from harness2.production_h2 import ProductionImprover


def _result(content, finish_reason="stop"):
    return ChatResult(content=content, finish_reason=finish_reason,
                      usage={"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
                      latency_seconds=0.01, model="fake",
                      raw_response={"usage": {"cost": 0.001}})


def _wrapper(case):
    return {"task": copy.deepcopy(case["task"]), "request": case["request"]}


GOOD = json.dumps({"moves": [["step_right", "soft"], ["step_left", "clear"],
                              ["step_right", "soft"], ["step_right", "clear"]]})
BAD = json.dumps({"moves": [["step_right", "soft"], ["step_right", "clear"],
                             ["step_right", "soft"], ["step_right", "clear"]]})


class StepH2Tests(unittest.TestCase):
    def test_run_domain_guidance_only_and_holdout_boundary(self):
        dev, heldout = CASES[0], CASES[1]
        tasks = {case["id"]: _wrapper(case) for case in (dev, heldout)}
        source_sha = hashlib.sha256(Path("harness2/dance_step_task.py").read_bytes()).hexdigest()
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            if "Improve generic structured stepping guidance" in kwargs["system"]:
                self.assertIn(dev["id"], kwargs["user"])
                self.assertNotIn(heldout["id"], kwargs["user"])
                return _result(json.dumps({"systemprompt": BASE_GUIDANCE +
                                           "Recheck final position, lane, and required slots.\n"}))
            self.assertIn(PUBLIC_CONTRACT, kwargs["system"])
            self.assertEqual(kwargs["timeout"], 20.0)
            self.assertEqual(kwargs["max_output_tokens"], 128)
            self.assertEqual(json.loads(kwargs["user"]), tasks[dev["id"]])
            return _result(GOOD if "Recheck final position" in kwargs["system"] else BAD)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = StepAdapter(root, tasks, [dev["id"]], provider=provider,
                                  base_url="http://localhost:8080/v1", model="fake",
                                  max_solver_calls=8)
            editor = ProductionImprover(adapter.spec.channels["proposer"], provider=provider,
                                        base_url="http://localhost:8080/v1", model="fake",
                                        audit_dir=root / "editor", max_editor_calls=3,
                                        guidance_domain="structured stepping",
                                        public_rule=EDITOR_PUBLIC_RULE)
            with self.assertRaises(ValueError):
                adapter.task_prompt(heldout["id"])
            with self.assertRaises(ValueError):
                adapter.task_files(heldout["id"])
            result = run_domain("structured-stepping", adapter.tasks("train"), 1,
                                adapter=adapter, prop=editor,
                                runs_root=adapter.spec.runs_root,
                                library_root=root / "library", modes=("seq",))
            self.assertEqual(result["done"], 1, result)
            self.assertEqual(adapter.solver_calls, 4)
            self.assertEqual(editor.editor_calls, 3)
            summary = json.loads((adapter.spec.runs_root / "dance_step_h2-oc-agg1" /
                                  dev["id"] / "summary.json").read_text())
            base = Path(summary["base"][0]["run_dir"])
            chosen = Path(summary["selections"]["seq"]["chosen_run_dir"])
            self.assertFalse(json.loads((base / "verdict.json").read_text())["valid"])
            self.assertTrue(json.loads((chosen / "verdict.json").read_text())["valid"])
            self.assertTrue((chosen / "compiled.json").is_file())
            self.assertEqual(len(list((root / "executions").rglob("receipt.json"))), 4)
            self.assertNotIn(heldout["id"], json.dumps(calls))
            self.assertFalse((root / "sources" / heldout["id"]).exists())
            self.assertEqual(hashlib.sha256(Path("harness2/dance_step_task.py").read_bytes()).hexdigest(),
                             source_sha)

    def test_public_contract_and_host_verdict(self):
        self.assertEqual(PUBLIC_CONTRACT, TRIAL_SYSTEM)
        self.assertLessEqual(len(EDITOR_PUBLIC_RULE.encode()), 500)
        case = CASES[0]
        accepted = verdict(GOOD, _wrapper(case))
        self.assertTrue(accepted["valid"])
        self.assertIn("compiled", accepted)
        wrong = verdict(BAD, _wrapper(case))
        self.assertFalse(wrong["valid"])
        self.assertIn("target", wrong["reason"])
        malformed = verdict('{"moves":[],"moves":[]}', _wrapper(case))
        self.assertFalse(malformed["valid"])
        self.assertNotIn("compiled", malformed)

    def test_incomplete_budget_immutability_and_path_scope(self):
        case = CASES[0]
        original = _wrapper(case)
        task = copy.deepcopy(original)
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            return _result(GOOD, finish_reason="length")

        with tempfile.TemporaryDirectory() as directory:
            adapter = StepAdapter(Path(directory), {case["id"]: task}, [case["id"]],
                                  provider=provider, base_url="http://localhost:8080/v1",
                                  model="fake", max_solver_calls=1)
            task["task"]["target_x_mm"] = 9999
            first = adapter.execute(case["id"], None, "first")
            second = adapter.execute(case["id"], None, "second")
            self.assertFalse(adapter.delivered(first))
            self.assertFalse(adapter.delivered(second))
            self.assertEqual(adapter.solver_calls, 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(json.loads((second / "receipt.json").read_text())["attempts"], 0)
            self.assertEqual(adapter.task_data[case["id"]], original)
            with self.assertRaises(ValueError):
                adapter.execute(case["id"], None, "../escape")
            with self.assertRaises(FileExistsError):
                adapter.execute(case["id"], None, "first")

    def test_rejects_malformed_tasks_and_extra_editor_surface(self):
        case = CASES[0]
        with tempfile.TemporaryDirectory() as directory:
            kwargs = {"base_url": "http://localhost:8080/v1", "model": "fake"}
            with self.assertRaises(ValueError):
                StepAdapter(Path(directory), {case["id"]: dict(_wrapper(case), expected=GOOD)},
                            [case["id"]], **kwargs)
            with self.assertRaises(ValueError):
                StepAdapter(Path(directory), {"../escape": _wrapper(case)},
                            ["../escape"], **kwargs)
            with self.assertRaises(ValueError):
                StepAdapter(Path(directory), {case["id"]: _wrapper(case)},
                            ["missing"], **kwargs)
            adapter = StepAdapter(Path(directory), {case["id"]: _wrapper(case)},
                                  [case["id"]], **kwargs)
            tree = {name: "" for name in adapter.substrate.surface().always_on}
            tree["systemprompt.md"] = BASE_GUIDANCE
            tree["dance_step_task.py"] = "tamper"
            with self.assertRaises(ValueError):
                adapter.validate_tree(tree)


if __name__ == "__main__":
    unittest.main()

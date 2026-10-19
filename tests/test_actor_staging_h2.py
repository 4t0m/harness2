"""Host-private compact staging through actual Harness2 recursion."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.actor_staging_cases import CASES
from harness2.actor_provider import ChatResult
from harness2.actor_staging import compile_staging
from harness2.actor_staging_h2 import BASE_GUIDANCE, PUBLIC_CONTRACT, StagingAdapter, verdict
from harness2.core.schedule import run_domain
from harness2.production_h2 import ProductionImprover


def _result(content, finish_reason="stop"):
    return ChatResult(content=content, finish_reason=finish_reason,
                      usage={"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
                      latency_seconds=0.01, model="fake",
                      raw_response={"usage": {"cost": 0.001}})


def _task(case):
    return {"task_id": case["id"], "scene": copy.deepcopy(case["scene"]),
            "request": case["request"]}


def _expected(case):
    return compile_staging(json.dumps({"scene_revision": case["scene"]["revision"],
                                       **case["expected"]}), case["scene"])


def _compact(case):
    left = next(item["actor_id"] for item in case["expected"]["placements"]
                if item["side"] == "left")
    return {"left": left, "cues": [
        [cue["actor_id"], cue["gesture"], cue["variation"]]
        for cue in sorted(case["expected"]["cues"], key=lambda item: item["slot"])]}


class StagingH2Tests(unittest.TestCase):
    def test_run_domain_editor_wiring_and_private_host_oracle(self):
        dev, holdout = CASES[1], CASES[2]
        tasks = {case["id"]: _task(case) for case in (dev, holdout)}
        expected = {case["id"]: _expected(case) for case in (dev, holdout)}
        wrong = _compact(dev)
        wrong["cues"][0][1] = "wave"
        correct = _compact(dev)
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            if "Improve generic actor staging guidance" in kwargs["system"]:
                self.assertIn(dev["id"], kwargs["user"])
                self.assertNotIn(holdout["id"], kwargs["user"])
                return _result(json.dumps({"systemprompt": BASE_GUIDANCE +
                                           "Check each chronological cue against the request.\n"}))
            self.assertIn(PUBLIC_CONTRACT, kwargs["system"])
            self.assertEqual(kwargs["timeout"], 20.0)
            self.assertEqual(kwargs["max_output_tokens"], 128)
            user = json.loads(kwargs["user"])
            self.assertEqual(set(user), {"scene", "request"})
            self.assertNotIn("expected", kwargs["user"])
            answer = correct if "Check each chronological cue" in kwargs["system"] else wrong
            return _result(json.dumps(answer))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = StagingAdapter(root, tasks, expected, [dev["id"]], provider=provider,
                                     base_url="http://localhost:8080/v1", model="fake",
                                     max_solver_calls=8)
            editor = ProductionImprover(adapter.spec.channels["proposer"], provider=provider,
                                        base_url="http://localhost:8080/v1", model="fake",
                                        audit_dir=root / "editor", max_editor_calls=3,
                                        guidance_domain="actor staging", public_rule=PUBLIC_CONTRACT)
            with self.assertRaises(ValueError):
                adapter.task_prompt(holdout["id"])
            with self.assertRaises(ValueError):
                adapter.task_files(holdout["id"])
            result = run_domain("actor-staging", adapter.tasks("train"), 1,
                                adapter=adapter, prop=editor, runs_root=adapter.spec.runs_root,
                                library_root=root / "library", modes=("seq",))
            self.assertEqual(result["done"], 1, result)
            self.assertEqual(adapter.solver_calls, 4)
            self.assertEqual(editor.editor_calls, 3)
            summary = json.loads((adapter.spec.runs_root / "actor_staging_h2-oc-agg1" /
                                  dev["id"] / "summary.json").read_text())
            chosen = Path(summary["selections"]["seq"]["chosen_run_dir"])
            selected = json.loads((chosen / "verdict.json").read_text())
            self.assertTrue(selected["valid"])
            self.assertTrue(selected["semantic_correct"])
            base = Path(summary["base"][0]["run_dir"])
            baseline = json.loads((base / "verdict.json").read_text())
            self.assertTrue(baseline["accepted_format"])
            self.assertFalse(baseline["valid"])
            self.assertFalse(baseline["semantic_correct"])
            self.assertNotIn(holdout["id"], json.dumps(calls))
            self.assertNotIn("expected", (root / "sources" / dev["id"] / "brief.json").read_text())
            self.assertFalse((root / "sources" / holdout["id"]).exists())

    def test_verdict_separates_compilation_from_semantic_match(self):
        case = CASES[0]
        task, expected = _task(case), _expected(case)
        good = _compact(case)
        self.assertTrue(verdict(json.dumps(good), task, expected)["valid"])
        wrong = copy.deepcopy(good)
        wrong["cues"][1][2] = "soft"
        scored = verdict(json.dumps(wrong), task, expected)
        self.assertTrue(scored["accepted_format"])
        self.assertFalse(scored["semantic_correct"])
        malformed = verdict('{"left":"x","left":"y","cues":[]}', task, expected)
        self.assertFalse(malformed["accepted_format"])
        self.assertFalse(malformed["valid"])

    def test_copies_inputs_caps_calls_and_refuses_incomplete(self):
        case = CASES[0]
        task, expected = _task(case), _expected(case)
        original_task, original_expected = copy.deepcopy(task), copy.deepcopy(expected)
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            return _result(json.dumps(_compact(case)), finish_reason="length")

        with tempfile.TemporaryDirectory() as directory:
            adapter = StagingAdapter(Path(directory), {case["id"]: task}, {case["id"]: expected},
                                     [case["id"]], provider=provider,
                                     base_url="http://localhost:8080/v1", model="fake",
                                     max_solver_calls=1)
            task["scene"]["anchor"]["x_m"] = 0.7
            expected["actors"][0]["x_m"] = 999
            first = adapter.execute(case["id"], None, "first")
            second = adapter.execute(case["id"], None, "second")
            self.assertFalse(adapter.delivered(first))
            self.assertFalse(adapter.delivered(second))
            self.assertEqual(adapter.solver_calls, 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(json.loads((second / "receipt.json").read_text())["attempts"], 0)
            self.assertEqual(adapter.task_data[case["id"]], original_task)
            self.assertEqual(adapter.expected[case["id"]], original_expected)
            with self.assertRaises(ValueError):
                adapter.execute(case["id"], None, "../escape")

    def test_rejects_noncanonical_oracle_and_illegal_task_scope(self):
        case = CASES[0]
        task, expected = _task(case), _expected(case)
        with tempfile.TemporaryDirectory() as directory:
            kwargs = {"base_url": "http://localhost:8080/v1", "model": "fake"}
            bad_plan = copy.deepcopy(expected)
            bad_plan["frame_count"] = 47
            with self.assertRaises(ValueError):
                StagingAdapter(Path(directory), {case["id"]: task}, {case["id"]: bad_plan},
                               [case["id"]], **kwargs)
            with self.assertRaises(ValueError):
                StagingAdapter(Path(directory), {case["id"]: dict(task, expected=expected)},
                               {case["id"]: expected}, [case["id"]], **kwargs)
            with self.assertRaises(ValueError):
                StagingAdapter(Path(directory), {"../bad": task}, {"../bad": expected},
                               ["../bad"], **kwargs)


if __name__ == "__main__":
    unittest.main()

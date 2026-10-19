"""Offline checks for the model solver and trusted actor oracle."""

import json
import tempfile
import unittest
from pathlib import Path

from harness2.actor_demo import ActorProposer, FIXTURES
from harness2.actor_model import ModelActorAdapter
from harness2.actor_provider import ChatResult, ProviderIncomplete
from harness2.core.schedule import run_domain


def result(content, finish="stop"):
    return ChatResult(content, finish, {"prompt_tokens": 10, "completion_tokens": 20,
                                        "total_tokens": 30}, 0.01, "mock-model")


class ActorModelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def adapter(self, provider, **kwargs):
        return ModelActorAdapter(self.root, base_url="http://127.0.0.1:8000/v1",
                                 model="mock", provider=provider, **kwargs)

    def verdict(self, run):
        return json.loads((run / "verdict.json").read_text())

    def test_first_pass_and_persisted_receipt(self):
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            return result(json.dumps(FIXTURES["left-mirror"]))

        adapter = self.adapter(provider)
        run = adapter.execute("left-mirror", None, "first")
        self.assertEqual(self.verdict(run)["status"], "first_pass")
        self.assertTrue(adapter.delivered(run))
        self.assertEqual(len(calls), 1)
        self.assertIn("coordinate_policy: round_to_tenth", calls[0]["system"])
        self.assertIn('"stop_gap": 0.12', calls[0]["user"])
        receipt = json.loads((run / "attempts.json").read_text())
        self.assertEqual(receipt[0]["finish_reason"], "stop")
        self.assertEqual(receipt[0]["usage"]["total_tokens"], 30)
        self.assertTrue(receipt[0]["host_verdict"]["valid"])

    def test_correction_recovery_and_exhaustion(self):
        bad = json.loads(json.dumps(FIXTURES["left-mirror"]))
        bad["actor"]["id"] = "unknown"
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                prior = json.loads((self.root / "executions/recovered/attempts.json").read_text())
                self.assertEqual(len(prior), 1)
                self.assertFalse(prior[0]["host_verdict"]["valid"])
            return result(json.dumps(bad if len(calls) == 1 else FIXTURES["left-mirror"]))

        adapter = self.adapter(provider)
        run = adapter.execute("left-mirror", None, "recovered")
        self.assertEqual(self.verdict(run)["status"], "recovered")
        self.assertEqual(self.verdict(run)["attempts"], 2)
        self.assertIn("Host error:", calls[1]["user"])
        self.assertIn("unknown", calls[1]["user"])
        receipts = json.loads((run / "attempts.json").read_text())
        self.assertFalse(receipts[0]["host_verdict"]["valid"])
        self.assertTrue(receipts[1]["host_verdict"]["valid"])

        adapter = self.adapter(lambda **_: result(json.dumps(bad)))
        run = adapter.execute("left-mirror", None, "repeat")
        self.assertEqual(self.verdict(run)["status"], "repeat_invalid")
        self.assertFalse(adapter.delivered(run))
        attempts = json.loads((run / "attempts.json").read_text())
        self.assertEqual(len(attempts), 2)
        self.assertTrue(all(not item["host_verdict"]["valid"] for item in attempts))

        alternate = json.loads(json.dumps(FIXTURES["left-mirror"]))
        alternate["stop_gap"] = 0.08
        sequence = iter([result(json.dumps(bad)), result(json.dumps(alternate))])
        adapter = self.adapter(lambda **_: next(sequence))
        run = adapter.execute("left-mirror", None, "exhausted")
        self.assertEqual(self.verdict(run)["status"], "exhausted")
        self.assertFalse(adapter.delivered(run))

    def test_truncation_and_schema_rejection(self):
        calls = []

        def truncated(**kwargs):
            calls.append(kwargs)
            return result(json.dumps(FIXTURES["left-mirror"]), "length")

        adapter = self.adapter(truncated)
        run = adapter.execute("left-mirror", None, "truncated")
        self.assertEqual(self.verdict(run)["status"], "rejected_finish")
        self.assertEqual(len(calls), 1)
        self.assertFalse(adapter.delivered(run))
        def incomplete(**_):
            raise ProviderIncomplete("truncated completion", "length", "mock-model",
                                     {"prompt_tokens": 10, "completion_tokens": 20,
                                      "total_tokens": 30}, 0.02, None)

        adapter = self.adapter(incomplete)
        run = adapter.execute("left-mirror", None, "provider-truncated")
        self.assertEqual(self.verdict(run)["status"], "truncated")
        receipt = json.loads((run / "attempts.json").read_text())[0]
        self.assertEqual(receipt["usage"]["total_tokens"], 30)
        self.assertEqual(receipt["finish_reason"], "length")
        adapter = self.adapter(lambda **_: result('{"actor":{},"actor":{}}'), max_attempts=1)
        run = adapter.execute("left-mirror", None, "schema")
        self.assertEqual(self.verdict(run)["status"], "exhausted")
        self.assertIn("duplicate JSON key", json.loads((run / "attempts.json").read_text())[0]
                      ["host_verdict"]["reason"])

    def test_real_run_domain_with_mock_solver(self):
        def provider(**kwargs):
            scene = json.loads(kwargs["user"].split("\n")[1])
            if "coordinate_policy: round_to_tenth" in kwargs["system"]:
                scene["stop_gap"] = 0.08
            return result(json.dumps(scene))

        adapter = self.adapter(provider, max_attempts=1)
        proposer = ActorProposer(adapter.spec.channels["proposer"])
        output = run_domain("actor-planning", adapter.tasks("train"), 1, adapter=adapter,
                            prop=proposer, runs_root=adapter.spec.runs_root,
                            library_root=self.root / "library", modes=("seq",))
        self.assertEqual((output["done"], output["failed"]), (2, 0))
        for task in adapter.tasks("train"):
            summary = json.loads((adapter.spec.runs_root / "actor_model-oc-agg1" / task /
                                  "summary.json").read_text())
            base = Path(summary["base"][0]["run_dir"])
            chosen = Path(summary["selections"]["seq"]["chosen_run_dir"])
            self.assertFalse(self.verdict(base)["valid"])
            self.assertTrue(self.verdict(chosen)["valid"])


if __name__ == "__main__":
    unittest.main()

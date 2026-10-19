"""Guidance-only model proposer and real Harness2 loop with a mock provider."""

import json
import tempfile
import unittest
from pathlib import Path

from harness2.actor_demo import ActorAdapter, BASE_GUIDANCE, FIXED_GUIDANCE
from harness2.actor_improver import ActorImprover, collect_context, validate_response
from harness2.actor_provider import ChatResult, ProviderIncomplete
from harness2.core.proposer import ProposerError
from harness2.core.schedule import run_domain


def response(prompt=FIXED_GUIDANCE, finish="stop"):
    return ChatResult(json.dumps({"systemprompt": prompt}), finish,
                      {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
                      0.01, "mock-model")


class ActorImproverTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.adapter = ActorAdapter(self.root)

    def context(self):
        context = self.root / "context"
        (context / "harness").mkdir(parents=True)
        (context / "task.md").write_text("Plan the current actor move.")
        (context / "harness/systemprompt.md").write_text(BASE_GUIDANCE)
        return context

    def improver(self, provider, max_provider_calls=3):
        return ActorImprover(self.adapter.spec.channels["proposer"],
                             base_url="http://127.0.0.1:8000/v1", model="mock-model",
                             audit_dir=self.root / "receipts", provider=provider,
                             max_provider_calls=max_provider_calls)

    def receipt(self, label):
        paths = list((self.root / "receipts").glob(f"*-{label}.json"))
        self.assertEqual(len(paths), 1)
        return json.loads(paths[0].read_text())

    def test_collects_only_whitelisted_bounded_context(self):
        context = self.context()
        (context / "source").mkdir()
        (context / "source/oracle.json").write_text("SECRET_ORACLE")
        (context / "heldout.json").write_text("SECRET_HELDOUT")
        (context / "rollouts").mkdir()
        (context / "rollouts/base1.md").write_text("Current rollout failed.")
        (context / "rollouts/huge.md").write_text("x" * 6001)
        (context / "rollouts/link.md").symlink_to(context / "source/oracle.json")
        (context / "decisions").mkdir()
        (context / "decisions/inv1.md").write_text("Keep exact scene values.")
        text, names = collect_context(context)
        self.assertEqual(names, ["task.md", "harness/systemprompt.md",
                                 "rollouts/base1.md", "decisions/inv1.md"])
        self.assertNotIn("SECRET_ORACLE", text)
        self.assertNotIn("SECRET_HELDOUT", text)
        self.assertNotIn("x" * 100, text)
        prompt = context / "harness/systemprompt.md"
        prompt.unlink()
        prompt.symlink_to(context / "source/oracle.json")
        with self.assertRaisesRegex(ValueError, "unavailable"):
            collect_context(context)

    def test_strict_json_and_preserves_prompt_on_invalid_response(self):
        context = self.context()
        for raw in ('{"systemprompt":"x","other":1}',
                    '{"systemprompt":"x","systemprompt":"y"}',
                    json.dumps({"systemprompt": FIXED_GUIDANCE + "import os\n"}),
                    json.dumps({"systemprompt": FIXED_GUIDANCE.replace(
                        "preserve_snapshot", "unknown")})):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                validate_response(raw)
            improver = self.improver(lambda **_: ChatResult(raw, "stop", None, 0.01, "mock"))
            with self.assertRaises(ProposerError):
                improver.call("ignored", context, "inv1.a1")
            self.assertEqual((context / "harness/systemprompt.md").read_text(), BASE_GUIDANCE)
            receipt = self.receipt("inv1_a1")
            self.assertTrue(receipt["provider_called"])
            self.assertIn("error", receipt)
            self.assertEqual(receipt["response_content"], raw)

    def test_budget_and_provider_incomplete_receipt(self):
        context = self.context()
        calls = []

        def provider(**kwargs):
            calls.append(kwargs)
            return response()

        improver = self.improver(provider, max_provider_calls=1)
        reply = improver.call("ignored", context, "inv1.a1")
        self.assertEqual(reply.workspace, context / "harness")
        self.assertEqual((context / "harness/systemprompt.md").read_text(), FIXED_GUIDANCE)
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]["timeout"], calls[0]["max_output_tokens"]), (20, 256))
        receipt = self.receipt("inv1_a1")
        self.assertEqual(receipt["usage"]["total_tokens"], 33)
        self.assertEqual(receipt["response_content"], response().content)
        self.assertIsNone(receipt["cost_usd"])
        with self.assertRaisesRegex(ProposerError, "budget exhausted"):
            improver.call("ignored", context, "dom1.a1")
        self.assertEqual(len(calls), 1)

        def incomplete(**_):
            raise ProviderIncomplete("truncated completion", "length", "mock", 
                                     {"prompt_tokens": 12, "completion_tokens": 20,
                                      "total_tokens": 32}, 0.02, None)

        improver = self.improver(incomplete)
        with self.assertRaises(ProposerError):
            improver.call("ignored", context, "c1.a1")
        receipt = self.receipt("c1_a1")
        self.assertEqual((receipt["finish_reason"], receipt["usage"]["total_tokens"]),
                         ("length", 32))

    def test_actual_run_domain_mock_improver_scripted_solver(self):
        prompts = []

        def provider(**kwargs):
            prompts.append(kwargs["user"])
            return response()

        improver = self.improver(provider)
        result = run_domain("actor-planning", ["left-mirror"], 1, adapter=self.adapter,
                            prop=improver, runs_root=self.adapter.spec.runs_root,
                            library_root=self.root / "library", modes=("seq",))
        self.assertEqual((result["done"], result["failed"]), (1, 0))
        self.assertEqual(improver.provider_calls, 3)
        summary = json.loads((self.adapter.spec.runs_root / "actor_demo-oc-agg1" /
                              "left-mirror/summary.json").read_text())
        base = Path(summary["base"][0]["run_dir"])
        chosen = Path(summary["selections"]["seq"]["chosen_run_dir"])
        self.assertFalse(json.loads((base / "verdict.json").read_text())["valid"])
        self.assertTrue(json.loads((chosen / "verdict.json").read_text())["valid"])
        self.assertEqual(summary["selections"]["seq"]["chosen_label"], "c1")
        self.assertTrue(all("source/scene.json" not in prompt and "oracle" not in prompt
                            and "heldout" not in prompt for prompt in prompts))
        receipt = self.receipt("experience_seq1")
        self.assertEqual(receipt["mode"], "scripted_experience")


if __name__ == "__main__":
    unittest.main()

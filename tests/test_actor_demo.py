"""Actor adapter contract and real Harness2 recursion smoke test."""

import json
import tempfile
import unittest
from pathlib import Path

from harness2.actor_demo import ActorAdapter, FIXTURES, check_proposal, run_actor_demo


class ActorDemoTests(unittest.TestCase):
    def test_strict_host_oracle_and_mirrored_clearance(self):
        for task in ("left-mirror", "right-mirror", "heldout-diagonal"):
            fixture = FIXTURES[task]
            result = check_proposal(json.dumps(fixture), fixture)
            self.assertTrue(result["valid"])
            self.assertAlmostEqual(result["edge_gap_final"], fixture["stop_gap"])
        left = check_proposal(json.dumps(FIXTURES["left-mirror"]), FIXTURES["left-mirror"])
        right = check_proposal(json.dumps(FIXTURES["right-mirror"]), FIXTURES["right-mirror"])
        self.assertEqual((left["gaze"], left["adapter_control"]), ("screen_left", None))
        self.assertEqual((right["gaze"], right["adapter_control"]), ("screen_right", "look_right"))
        bad = json.loads(json.dumps(FIXTURES["left-mirror"]))
        bad["actor"]["id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "actor: scene or requested action changed"):
            check_proposal(json.dumps(bad), FIXTURES["left-mirror"])
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            check_proposal('{"actor":{},"actor":{}}', FIXTURES["left-mirror"])
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            check_proposal(json.dumps(FIXTURES["left-mirror"]).replace("0.8", "NaN"), FIXTURES["left-mirror"])
        with self.assertRaisesRegex(ValueError, "finite number"):
            check_proposal(json.dumps(FIXTURES["left-mirror"]).replace("0.8", "9" * 350), FIXTURES["left-mirror"])
        with self.assertRaisesRegex(ValueError, "proposal fields differ"):
            check_proposal("[" * 1500 + "]" * 1500, FIXTURES["left-mirror"])

    def test_actual_run_domain_and_heldout_remains_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = run_actor_demo(root)
            self.assertEqual((evidence["harness2_run_domain"]["done"],
                              evidence["harness2_run_domain"]["failed"]), (2, 0))
            self.assertEqual(len(evidence["train"]), 2)
            for row in evidence["train"]:
                self.assertFalse(row["base"]["host_verdict"]["valid"])
                self.assertTrue(row["adapted"]["host_verdict"]["valid"])
            self.assertFalse(evidence["heldout"]["base"]["host_verdict"]["valid"])
            self.assertTrue(evidence["heldout"]["adapted"]["host_verdict"]["valid"])
            self.assertTrue((root / "actor-demo.json").is_file())
            adapter = ActorAdapter(root / "another")
            self.assertEqual(adapter.tasks("train"), ["left-mirror", "right-mirror"])
            self.assertEqual(adapter.tasks("heldout"), ["heldout-diagonal"])


if __name__ == "__main__":
    unittest.main()

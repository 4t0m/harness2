"""Bounded candidate-pool evidence in the step-specific H2 editor."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.dance_step_task_cases import CASES
from harness2.actor_provider import ChatResult
from harness2.core.proposer import ProposerError
from harness2.core.schedule import run_domain
from harness2.dance_step_h2 import BASE_GUIDANCE, PUBLIC_CONTRACT, StepAdapter
from harness2.dance_step_improver import StepImprover, _pool_context


def _result(content):
    return ChatResult(content=content, finish_reason="stop",
                      usage={"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
                      latency_seconds=0.01, model="fake", raw_response={"usage": {"cost": 0.001}})


BAD = json.dumps({"moves": [["step_right", "soft"], ["step_right", "clear"],
                             ["step_right", "soft"], ["step_right", "clear"]]})
GOOD = json.dumps({"moves": [["step_right", "soft"], ["step_right", "clear"],
                              ["step_left", "soft"], ["step_right", "clear"]]})


class StepImproverTests(unittest.TestCase):
    def test_scripted_h2_compose_receives_successful_pool_evidence(self):
        dev, heldout = CASES[0], CASES[1]
        wrapper = {"task": dev["task"], "request": dev["request"]}
        editor_users = []

        def provider(**kwargs):
            if "Improve generic four-step constrained motion planning guidance" in kwargs["system"]:
                user = kwargs["user"]
                editor_users.append(user)
                self.assertNotIn(heldout["id"], user)
                if "## Development candidate pool evidence" in user:
                    self.assertIn("## pool/inv1/harness.diff", user)
                    self.assertIn("## pool/dom1/harness.diff", user)
                    self.assertIn("## pool/inv1/rollout.md", user)
                    self.assertIn("## pool/dom1/rollout.md", user)
                    self.assertEqual(user.count("[HOST] step task constraints satisfied"), 2)
                    guidance = BASE_GUIDANCE + "Check endpoint, lane, and every required slot.\n"
                elif len(editor_users) == 1:
                    guidance = BASE_GUIDANCE + "Check cumulative displacement at every step.\n"
                else:
                    guidance = BASE_GUIDANCE + "Check directions and variations by slot.\n"
                return _result(json.dumps({"systemprompt": guidance}))
            return _result(GOOD if kwargs["system"] != BASE_GUIDANCE + "\n" + PUBLIC_CONTRACT
                           else BAD)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = StepAdapter(root, {dev["id"]: wrapper}, [dev["id"]],
                                  provider=provider, base_url="http://localhost:8080/v1",
                                  model="fake", max_solver_calls=4)
            editor = StepImprover(adapter.spec.channels["proposer"], provider=provider,
                                  base_url="http://localhost:8080/v1", model="fake",
                                  audit_dir=root / "editor", max_editor_calls=3,
                                  guidance_domain="four-step constrained motion planning",
                                  public_rule="Approved task constraints remain host-owned.")
            result = run_domain(adapter.domain_of(dev["id"]), adapter.tasks("train"), 1,
                                adapter=adapter, prop=editor,
                                runs_root=adapter.spec.runs_root,
                                library_root=root / "library", modes=("seq",))
            self.assertEqual(result["done"], 1, result)
            self.assertEqual(adapter.solver_calls, 4)
            self.assertEqual(editor.editor_calls, 3)
            self.assertEqual(len(editor_users), 3)
            self.assertNotIn("## Development candidate pool evidence", editor_users[0])
            self.assertNotIn("## Development candidate pool evidence", editor_users[1])
            self.assertIn("## Development candidate pool evidence", editor_users[2])
            audits = {r["label"]: r for p in (root / "editor").glob("*.json")
                      if (r := json.loads(p.read_text()))}
            self.assertEqual(audits["inv1.a1"]["pool_included_files"], [])
            self.assertEqual(audits["dom1.a1"]["pool_included_files"], [])
            compose = audits["c1.a1"]
            self.assertEqual(len(compose["pool_included_files"]), 4)
            self.assertEqual(compose["editor_user_sha256"],
                             hashlib.sha256(editor_users[2].encode()).hexdigest())
            context = root / "runs" / "dance_step_h2-oc-seq1" / dev["id"] / "context" / "c1"
            for item in compose["pool_included_files"]:
                self.assertEqual(hashlib.sha256((context / item["name"]).read_bytes()).hexdigest(),
                                 item["sha256"])
                self.assertIn(item["name"], compose["included_files"])
            audit_path = next(p for p in (root / "editor").glob("*.json")
                              if json.loads(p.read_text())["label"] == "c1.a1")
            before = audit_path.read_bytes()
            with self.assertRaisesRegex(ProposerError, "already exists"):
                editor.call("duplicate", context, "c1.a1")
            self.assertEqual(audit_path.read_bytes(), before)
            self.assertEqual(len(editor_users), 3)

    def test_rejects_unsafe_incomplete_and_oversized_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(_pool_context(root), ("", []))
            for label in ("inv1", "dom1"):
                folder = root / "pool" / label
                folder.mkdir(parents=True)
                for name in ("harness.diff", "rollout.md"):
                    (folder / name).write_text("candidate")
            text, files = _pool_context(root)
            self.assertEqual(len(files), 4)
            self.assertIn("pool/inv1/rollout.md", text)
            (root / "pool" / "inv1" / "rollout.md").unlink()
            with self.assertRaisesRegex(ValueError, "missing or unsafe"):
                _pool_context(root)
            (root / "pool" / "inv1" / "rollout.md").symlink_to(root / "pool" / "dom1" / "rollout.md")
            with self.assertRaisesRegex(ValueError, "missing or unsafe"):
                _pool_context(root)
            (root / "pool" / "inv1" / "rollout.md").unlink()
            (root / "pool" / "inv1" / "rollout.md").write_text("x" * 6001)
            with self.assertRaisesRegex(ValueError, "byte cap"):
                _pool_context(root)
            (root / "pool" / "inv1" / "rollout.md").write_text("candidate")
            (root / "pool" / "inv1").rename(root / "moved-inv1")
            (root / "pool" / "inv1").symlink_to(root / "missing-inv1")
            with self.assertRaisesRegex(ValueError, "unsafe candidate directory"):
                _pool_context(root)
            (root / "pool" / "inv1").unlink()
            (root / "pool").rename(root / "moved-pool")
            (root / "pool").symlink_to(root / "missing-pool")
            with self.assertRaisesRegex(ValueError, "unsafe candidate pool"):
                _pool_context(root)


if __name__ == "__main__":
    unittest.main()

"""Offline checks for the frozen avatar capability probe; no Ollama calls."""

import json
from pathlib import Path
import tempfile
import unittest

from experiments import avatar_capability_probe as probe


class AvatarCapabilityProbeTests(unittest.TestCase):
    def test_frozen_cases_and_answer_key_are_independent(self):
        self.assertEqual(len(probe.CASES), 8)
        self.assertEqual(set(case_id for case_id, _ in probe.CASES), set(probe.EXPECTED))
        self.assertEqual(probe.MAX_CALLS, 48)
        for model in probe.MODELS:
            for case in probe.CASES:
                body = probe.request_body(model, case)
                self.assertEqual(body["messages"], [
                    {"role": "system", "content": probe.SYSTEM},
                    {"role": "user", "content": case[1]},
                ])
                self.assertNotIn("expected", json.dumps(body))
                self.assertEqual(body["format"], probe.SCHEMA)
                self.assertEqual(body["options"], {"num_ctx": 4096, "num_predict": 96,
                                                   "temperature": 0})
                self.assertIs(body["think"], False)
        old = probe.EXPECTED["listen_plain"]
        before = probe.request_body(probe.MODELS[0], probe.CASES[0])
        try:
            probe.EXPECTED["listen_plain"] = "unsupported"
            self.assertEqual(before, probe.request_body(probe.MODELS[0], probe.CASES[0]))
        finally:
            probe.EXPECTED["listen_plain"] = old

    def test_strict_json_duplicate_unknown_and_semantic_mismatch(self):
        for raw in ('{"action":"listen","action":"nod"}',
                    '{"action":"dance"}', 'listen',
                    '```json\n{"action":"listen"}\n```',
                    '{"action":"listen","extra":1}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                probe.parse_action(raw)
        self.assertEqual(probe.parse_action('{"action":"listen"}'), "listen")
        bad = probe.verdict('{"action":"nod"}', "listen")
        self.assertTrue(bad["strict_json"])
        self.assertFalse(bad["semantic_correct"])
        self.assertFalse(bad["valid"])
        malformed = probe.verdict('{"action":"dance"}', "listen")
        self.assertFalse(malformed["strict_json"])

    def test_bounded_probe_records_first_and_one_correction(self):
        calls = []
        def fake_call(body):
            calls.append(body)
            self.assertLessEqual(len(calls), 48)
            self.assertEqual(len(body["messages"]), 2 if len(calls) % 2 else 4)
            if len(body["messages"]) == 4:
                self.assertEqual(body["messages"][2], {"role": "assistant", "content": '{"action": "dance"}'})
                self.assertNotIn("expected", body["messages"][3]["content"])
                action = probe.EXPECTED[probe.CASES[((len(calls) - 1) // 2) % 8][0]]
            else:
                action = "dance"  # Unknown action: format rejection, not bare-text recovery.
            return {"model": body["model"], "done_reason": "stop",
                    "message": {"content": json.dumps({"action": action})},
                    "total_duration": 100, "load_duration": 10,
                    "prompt_eval_count": 11, "prompt_eval_duration": 20,
                    "eval_count": 2, "eval_duration": 30}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fresh.json"
            report = probe.run_probe(output, call=fake_call, metadata=lambda: {m: {"name": m} for m in probe.MODELS})
            self.assertEqual(len(calls), 48)
            self.assertEqual(report["calls_made"], 48)
            self.assertEqual(len(report["rows"]), 24)
            self.assertEqual(report["unattempted"], [])
            self.assertTrue(all(not row["first"]["valid"] and row["repaired"]["valid"]
                                for row in report["rows"]))
            self.assertEqual(report["rows"][0]["first"]["prompt_eval_count"], 11)
            self.assertEqual(json.loads(output.read_text())["calls_made"], 48)
            with self.assertRaises(FileExistsError):
                probe.run_probe(output, call=fake_call, metadata=lambda: {})
            self.assertEqual(len(calls), 48)

    def test_transport_failure_stops_only_current_model(self):
        calls = []
        def fake_call(body):
            calls.append(body)
            if body["model"] == probe.MODELS[0]:
                raise TimeoutError("offline fake timeout")
            return {"model": body["model"], "done_reason": "stop",
                    "message": {"content": '{"action":"listen"}'}}
        with tempfile.TemporaryDirectory() as directory:
            report = probe.run_probe(Path(directory) / "fresh.json", call=fake_call,
                                     metadata=lambda: {m: {"name": m} for m in probe.MODELS})
        self.assertEqual(sum(body["model"] == probe.MODELS[0] for body in calls), 1)
        self.assertEqual(len([item for item in report["unattempted"]
                              if item["model"] == probe.MODELS[0]]), 7)
        self.assertTrue(any(body["model"] == probe.MODELS[1] for body in calls))


if __name__ == "__main__":
    unittest.main()

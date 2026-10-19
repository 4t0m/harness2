"""Patch-first routing never uses a semantic oracle or retries transport errors."""

import json
import unittest

from harness2.dance_edit_route import ProviderReplyError, route_edit
from harness2.dance_phrase_edit import bind_source, validate_edit


SOURCE = json.dumps({"moves": [["rise", "soft"], ["sway", "soft"],
                               ["pulse", "clear"], ["settle", "soft"]]})
PATCH = json.dumps({"slot": 1, "move": "sway", "variation": "clear"})
FULL = json.dumps({"moves": [["rise", "soft"], ["sway", "clear"],
                             ["pulse", "clear"], ["settle", "soft"]]})


class ScriptedProvider:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, mode, previous_raw, rejection_reason):
        self.calls.append((mode, previous_raw, rejection_reason))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class DanceEditRouteTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = bind_source(SOURCE, "approved-r3", [1])

    def route(self, provider, **overrides):
        return route_edit(self.snapshot, overrides.get("source", SOURCE),
                          overrides.get("revision", "approved-r3"),
                          overrides.get("slots", [1]), provider)

    def test_patch_success_returns_after_one_call(self):
        provider = ScriptedProvider([PATCH])
        result = self.route(provider)
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(provider.calls, [("patch", None, None)])
        self.assertEqual(result["edit"]["receipt"]["edited_slot"], 1)
        self.assertTrue(validate_edit(result["edit"], self.snapshot, SOURCE,
                                      "approved-r3", [1])["outside_frames_exact"])

    def test_noop_patch_then_full_success_with_prior_reply_and_reason(self):
        noop = json.dumps({"slot": 1, "move": "sway", "variation": "soft"})
        provider = ScriptedProvider([noop, FULL])
        result = self.route(provider)
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(provider.calls[0], ("patch", None, None))
        self.assertEqual(provider.calls[1][0:2], ("full", noop))
        self.assertIn("exactly one", provider.calls[1][2])
        self.assertFalse(result["attempts"][0]["accepted"])
        self.assertTrue(result["attempts"][1]["accepted"])

    def test_invalid_full_is_explicit_failure_without_candidate(self):
        provider = ScriptedProvider(['{"slot":1,"move":"walk","variation":"clear"}', SOURCE])
        result = self.route(provider)
        self.assertFalse(result["accepted"])
        self.assertIsNone(result["edit"])
        self.assertEqual([item["mode"] for item in result["attempts"]], ["patch", "full"])
        self.assertTrue(all(not item["accepted"] for item in result["attempts"]))
        self.assertEqual(len(provider.calls), 2)

    def test_stale_snapshot_rejected_before_any_call(self):
        changed = json.dumps({"moves": [["rise", "soft"], ["sway", "clear"],
                                     ["pulse", "clear"], ["settle", "soft"]]})
        for overrides in ({"source": changed}, {"revision": "approved-r4"},
                          {"slots": [1, 2]}):
            with self.subTest(overrides=overrides):
                provider = ScriptedProvider([PATCH])
                with self.assertRaisesRegex(ValueError, "stale"):
                    self.route(provider, **overrides)
                self.assertEqual(provider.calls, [])

    def test_transport_and_incomplete_reply_do_not_trigger_fallback(self):
        for first in (TimeoutError("network timeout"), None, "", "x" * 4097):
            with self.subTest(first=type(first).__name__):
                provider = ScriptedProvider([first, FULL])
                with self.assertRaises((TimeoutError, ProviderReplyError)):
                    self.route(provider)
                self.assertEqual(len(provider.calls), 1)
        provider = ScriptedProvider(["{}", RuntimeError("provider down")])
        with self.assertRaisesRegex(RuntimeError, "provider down"):
            self.route(provider)
        self.assertEqual(len(provider.calls), 2)

    def test_structurally_valid_but_semantically_wrong_patch_is_terminal(self):
        # The user's external target could be pulse-soft instead. The router has
        # no target and cannot claim semantic correctness or start a rewrite.
        provider = ScriptedProvider([PATCH, FULL])
        result = self.route(provider)
        actual_pair = result["edit"]["compiled"]["moves"][1]
        self.assertEqual((actual_pair["id"], actual_pair["variation"]),
                         ("sway", "clear"))
        self.assertNotEqual((actual_pair["id"], actual_pair["variation"]),
                            ("pulse", "soft"))
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(result["attempts"][0]["reason"], "structurally accepted")


if __name__ == "__main__":
    unittest.main()

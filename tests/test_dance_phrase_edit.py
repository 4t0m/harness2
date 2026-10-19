"""Selective dance edits preserve the approved motion outside one phrase."""

import copy
from dataclasses import FrozenInstanceError
import json
import unittest

from harness2.dance_phrase_edit import (
    FULL_SCHEMA, PATCH_SCHEMA, apply_patch, bind_source,
    validate_edit, validate_full_replacement,
)
from harness2.dance_phrases import compile_plan


SOURCE = json.dumps({"moves": [["rise", "soft"], ["sway", "soft"],
                               ["pulse", "clear"], ["settle", "soft"]]})
PATCH = json.dumps({"slot": 1, "move": "sway", "variation": "clear"})
FULL = json.dumps({"moves": [["rise", "soft"], ["sway", "clear"],
                             ["pulse", "clear"], ["settle", "soft"]]})


class DancePhraseEditTests(unittest.TestCase):
    def test_patch_and_full_rewrite_match_with_exact_protection(self):
        snapshot = bind_source(SOURCE, "approved-r3", [1])
        patched = apply_patch(PATCH, snapshot, SOURCE, "approved-r3", [1])
        full = validate_full_replacement(FULL, snapshot, SOURCE, "approved-r3", [1])
        self.assertEqual(patched, full)
        receipt = validate_edit(patched, snapshot, SOURCE, "approved-r3", [1])
        self.assertEqual(receipt["edited_slot"], 1)
        self.assertEqual(receipt["accepted_revision"], "approved-r3")
        self.assertEqual(receipt["protected_frame_count"], 62)
        self.assertTrue(all(receipt[key] for key in (
            "outside_frames_exact", "other_clips_exact", "seam_endpoints_exact",
            "source_unmutated")))
        source = compile_plan(SOURCE)
        self.assertEqual(snapshot.source_sequence_sha256,
                         source["receipt"]["sequence_sha256"])
        frames = patched["compiled"]["sequence"]["frames"]
        original = source["sequence"]["frames"]
        for index in list(range(0, 21)) + list(range(40, 81)):
            self.assertEqual(frames[index], original[index])
        self.assertTrue(any(frames[index] != original[index] for index in range(21, 40)))
        for index in (0, 2, 3):
            self.assertEqual(patched["compiled"]["clips"][index], source["clips"][index])
        with self.assertRaises(FrozenInstanceError):
            snapshot.revision = "changed"

    def test_source_revision_and_scope_staleness_even_without_revision_bump(self):
        snapshot = bind_source(SOURCE, "approved-r3", [1, 2])
        stale_source = json.dumps({"moves": [["rise", "soft"], ["sway", "clear"],
                                          ["pulse", "clear"], ["settle", "soft"]]})
        attempts = [
            (stale_source, "approved-r3", [1, 2]),
            (SOURCE, "approved-r4", [1, 2]),
            (SOURCE, "approved-r3", [1]),
            (SOURCE, "approved-r3", [0, 1, 2]),
        ]
        for current, revision, scope in attempts:
            with self.subTest(revision=revision, scope=scope, source=current), self.assertRaisesRegex(ValueError, "stale"):
                apply_patch(PATCH, snapshot, current, revision, scope)
            with self.assertRaisesRegex(ValueError, "stale"):
                validate_full_replacement(FULL, snapshot, current, revision, scope)
        # Formatting alone does not change the semantically bound plan.
        compact_source = json.dumps(json.loads(SOURCE), separators=(",", ":"))
        self.assertEqual(apply_patch(PATCH, snapshot, compact_source, "approved-r3", [2, 1])["receipt"]["edited_slot"], 1)

    def test_patch_shape_scope_noop_and_seam_rejections(self):
        snapshot = bind_source(SOURCE, "approved-r3", [1])
        bad_patches = [
            '{"slot":1,"slot":1,"move":"sway","variation":"clear"}',
            json.dumps({"slot": True, "move": "sway", "variation": "clear"}),
            json.dumps({"slot": 1.0, "move": "sway", "variation": "clear"}),
            json.dumps({"slot": 1, "move": "walk", "variation": "clear"}),
            json.dumps({"slot": 1, "move": "sway", "variation": "wild"}),
            json.dumps({"slot": 1, "move": "sway", "variation": "clear", "revision": "approved-r3"}),
            json.dumps({"slot": 1, "move": "sway"}),
            json.dumps({"slot": 0, "move": "rise", "variation": "clear"}),
            json.dumps({"slot": 1, "move": "sway", "variation": "soft"}),
            json.dumps({"slot": 1, "move": "settle", "variation": "clear"}),
            '{"slot":NaN,"move":"sway","variation":"clear"}',
            "```json\n" + PATCH + "\n```",
            " " * 1025,
        ]
        for raw in bad_patches:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                apply_patch(raw, snapshot, SOURCE, "approved-r3", [1])
        with self.assertRaises(ValueError):
            bind_source(SOURCE, "approved-r3", [True])
        with self.assertRaises(ValueError):
            bind_source(SOURCE, "approved-r3", [1, 1])

    def test_full_rewrite_requires_exactly_one_authorized_change(self):
        snapshot = bind_source(SOURCE, "approved-r3", [1, 2])
        multiple = json.dumps({"moves": [["rise", "soft"], ["sway", "clear"],
                                         ["pulse", "soft"], ["settle", "soft"]]})
        outside = json.dumps({"moves": [["rise", "clear"], ["sway", "soft"],
                                        ["pulse", "clear"], ["settle", "soft"]]})
        wrong_seam = json.dumps({"moves": [["rise", "soft"], ["settle", "soft"],
                                           ["pulse", "clear"], ["settle", "soft"]]})
        for raw in (SOURCE, multiple, outside, wrong_seam,
                    json.dumps({"moves": json.loads(FULL)["moves"], "revision": "fake"}),
                    '{"moves":[],"moves":[]}'):
            with self.subTest(raw=raw[:90]), self.assertRaises(ValueError):
                validate_full_replacement(raw, snapshot, SOURCE, "approved-r3", [1, 2])

    def test_outside_span_and_receipt_tamper_detected(self):
        snapshot = bind_source(SOURCE, "approved-r3", [1])
        accepted = apply_patch(PATCH, snapshot, SOURCE, "approved-r3", [1])
        variants = []
        outside = copy.deepcopy(accepted)
        outside["compiled"]["sequence"]["frames"][60]["joints"]["head"][0] += 0.01
        variants.append(outside)
        seam = copy.deepcopy(accepted)
        seam["compiled"]["sequence"]["frames"][20]["joints"]["left_wrist"][0] += 0.01
        variants.append(seam)
        clip = copy.deepcopy(accepted)
        clip["compiled"]["clips"][2]["frames"][5]["joints"]["left_wrist"][0] += 0.01
        variants.append(clip)
        receipt = copy.deepcopy(accepted)
        receipt["receipt"]["protected_frame_count"] = 61
        variants.append(receipt)
        for index, changed in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                validate_edit(changed, snapshot, SOURCE, "approved-r3", [1])
        self.assertEqual(set(PATCH_SCHEMA["required"]), {"slot", "move", "variation"})
        self.assertEqual(set(FULL_SCHEMA["required"]), {"moves"})


if __name__ == "__main__":
    unittest.main()

"""Strict phrase planning and physical source-clip assembly checks."""

import copy
import json
import math
import unittest

from harness2 import dance_motion
from harness2.dance_phrases import (
    CATALOG, PUBLIC_CONTRACT, compile_plan, parse_plan, validate_compilation,
)


def plan(*moves):
    return json.dumps({"moves": [list(move) for move in moves]})


GOOD = plan(("rise", "soft"), ("sway", "clear"),
            ("pulse", "soft"), ("settle", "clear"))


class DancePhraseTests(unittest.TestCase):
    def test_full_sequence_source_clips_and_real_seams(self):
        result = compile_plan(GOOD)
        report = validate_compilation(result)
        self.assertTrue(report["valid"])
        self.assertEqual((result["sequence"]["bpm"], result["sequence"]["fps"],
                          result["sequence"]["beats"], result["sequence"]["duration_seconds"]),
                         (120, 20, 8, 4.0))
        self.assertEqual(len(result["sequence"]["frames"]), 81)
        self.assertEqual([len(clip["frames"]) for clip in result["clips"]], [21] * 4)
        self.assertEqual(len(report["source_clip_validation"]), 4)
        self.assertLess(report["max_segment_error_m"], 1e-6)
        self.assertLess(report["max_seam_displacement_jump_m"], 0.05)
        self.assertEqual(result["sequence"]["frames"][0]["joints"],
                         result["sequence"]["frames"][-1]["joints"])
        for boundary in (20, 40, 60):
            prior_clip = result["clips"][boundary // 20 - 1]["frames"][-1]
            next_clip = result["clips"][boundary // 20]["frames"][0]
            frame = result["sequence"]["frames"][boundary]
            self.assertEqual(prior_clip["joints"], next_clip["joints"])
            self.assertEqual(frame["joints"], prior_clip["joints"])
            self.assertEqual(prior_clip["contacts"], next_clip["contacts"])
        self.assertTrue(dance_motion.validate(result["sequence"])["valid"])
        self.assertEqual(tuple(move["id"] for move in result["moves"]),
                         ("rise", "sway", "pulse", "settle"))
        self.assertEqual(tuple(item[0] for item in CATALOG),
                         ("rise", "sway", "pulse", "settle", "hold"))
        self.assertIn("No other fields", PUBLIC_CONTRACT)

    def test_distinct_moves_and_variation_is_local_to_its_phrase(self):
        soft = compile_plan(plan(("rise", "soft"), ("sway", "soft"),
                                 ("pulse", "soft"), ("settle", "soft")))
        changed = compile_plan(plan(("rise", "soft"), ("sway", "clear"),
                                    ("pulse", "soft"), ("settle", "soft")))
        a, b = soft["sequence"]["frames"], changed["sequence"]["frames"]
        for index in list(range(0, 21)) + list(range(40, 81)):
            self.assertEqual(a[index], b[index])
        self.assertEqual(a[20], b[20])
        self.assertEqual(a[40], b[40])
        self.assertTrue(any(a[index] != b[index] for index in range(21, 40)))
        for clip_index in (0, 2, 3):
            self.assertEqual(soft["clips"][clip_index], changed["clips"][clip_index])
        self.assertNotEqual(soft["clips"][1], changed["clips"][1])
        # Catalog entries have visibly distinct interior paths, not metadata-only names.
        rise = soft["clips"][0]["frames"][10]["joints"]
        sway = soft["clips"][1]["frames"][10]["joints"]
        pulse = soft["clips"][2]["frames"][10]["joints"]
        self.assertNotEqual(rise, sway)
        self.assertNotEqual(sway, pulse)
        self.assertNotEqual(rise, pulse)

    def test_all_legal_state_paths_compile_and_end_at_rest(self):
        legal = [
            plan(("hold", "soft"), ("rise", "clear"), ("settle", "soft"), ("hold", "clear")),
            plan(("rise", "clear"), ("pulse", "clear"), ("sway", "soft"), ("settle", "soft")),
            plan(("hold", "clear"), ("hold", "soft"), ("hold", "clear"), ("hold", "soft")),
        ]
        for raw in legal:
            with self.subTest(raw=raw):
                result = compile_plan(raw)
                self.assertTrue(validate_compilation(result)["valid"])
                self.assertEqual(result["moves"][0]["start_state"], "rest")
                self.assertEqual(result["moves"][-1]["end_state"], "rest")

    def test_strict_plan_rejects_wrong_order_unknown_and_extra_fields(self):
        bad = [
            "not json", "```json\n" + GOOD + "\n```",
            '{"moves":[],"moves":[]}',
            json.dumps({"moves": json.loads(GOOD)["moves"], "revision": "model-r1"}),
            json.dumps({"moves": json.loads(GOOD)["moves"][:3]}),
            plan(("sway", "soft"), ("rise", "soft"), ("settle", "soft"), ("hold", "soft")),
            plan(("rise", "soft"), ("sway", "soft"), ("pulse", "soft"), ("pulse", "soft")),
            plan(("rise", "soft"), ("settle", "soft"), ("sway", "soft"), ("hold", "soft")),
            plan(("rise", "soft"), ("walk", "soft"), ("pulse", "soft"), ("settle", "soft")),
            plan(("rise", "soft"), ("sway", "wild"), ("pulse", "soft"), ("settle", "soft")),
            json.dumps({"moves": [["rise", True], ["sway", "soft"],
                                  ["pulse", "soft"], ["settle", "soft"]]}),
            json.dumps({"moves": [{"id": "rise", "variation": "soft"},
                                  ["sway", "soft"], ["pulse", "soft"], ["settle", "soft"]]}),
            GOOD.replace('"soft"', 'NaN', 1),
            " " * 2049,
        ]
        for raw in bad:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                parse_plan(raw)

    def test_corrupt_source_boundary_foot_segment_or_receipt_rejected(self):
        result = compile_plan(GOOD)
        corruptions = []
        boundary = copy.deepcopy(result)
        boundary["clips"][1]["frames"][0]["joints"]["left_wrist"][0] += 0.02
        corruptions.append(boundary)
        foot = copy.deepcopy(result)
        foot["sequence"]["frames"][30]["joints"]["left_ankle"][0] += 0.01
        corruptions.append(foot)
        segment = copy.deepcopy(result)
        segment["clips"][2]["frames"][8]["joints"]["left_elbow"][2] += 0.02
        corruptions.append(segment)
        nonfinite = copy.deepcopy(result)
        nonfinite["sequence"]["frames"][5]["joints"]["head"][2] = math.nan
        corruptions.append(nonfinite)
        contact = copy.deepcopy(result)
        contact["sequence"]["frames"][5]["contacts"]["left"] = 1
        corruptions.append(contact)
        timing = copy.deepcopy(result)
        timing["sequence"]["beats"] = True
        corruptions.append(timing)
        hash_only = copy.deepcopy(result)
        hash_only["receipt"]["sequence_sha256"] = "0" * 64
        corruptions.append(hash_only)
        for index, corrupted in enumerate(corruptions):
            with self.subTest(corruption=index), self.assertRaises(ValueError):
                validate_compilation(corrupted)


if __name__ == "__main__":
    unittest.main()

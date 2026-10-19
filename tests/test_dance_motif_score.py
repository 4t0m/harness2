"""AABA score grammar and independent assembly checks."""

import copy
import itertools
import json
import math
import unittest

from harness2.dance_motif_score import compile_expanded, compile_intent, verify_score


def compact(motif="sway", accents=None):
    return json.dumps({"motif": motif, "accents": accents or ["soft"] * 4})


def expanded(motif="sway", accents=None):
    accents = accents or ["soft"] * 4
    other = "pulse" if motif == "sway" else "sway"
    moves = [[move, accent] for section_motif, accent in
             zip((motif, motif, other, motif), accents)
             for move in ("rise", section_motif, section_motif, "settle")]
    return json.dumps({"moves": moves})


class MotifScoreTests(unittest.TestCase):
    def test_all_32_compact_scores_equal_expanded_and_verify(self):
        for motif in ("sway", "pulse"):
            for accents_tuple in itertools.product(("soft", "clear"), repeat=4):
                accents = list(accents_tuple)
                with self.subTest(motif=motif, accents=accents):
                    a = compile_intent(compact(motif, accents))
                    b = compile_expanded(expanded(motif, accents))
                    self.assertEqual(a, b)
                    self.assertTrue(verify_score(a)["valid"])
                    self.assertEqual(len(a["sections"]), 4)
                    self.assertEqual(len(a["sequence"]["frames"]), 321)
                    self.assertEqual((a["sequence"]["fps"], a["sequence"]["beats"],
                                      a["sequence"]["duration_seconds"]), (20, 32, 16.0))
                    self.assertEqual(a["sequence"]["frames"][-1]["time"], 16.0)

    def test_seams_and_section_variations_change_only_their_span(self):
        base = compile_intent(compact("sway", ["soft"] * 4))
        changed = compile_intent(compact("sway", ["soft", "clear", "soft", "soft"]))
        a, b = base["sequence"]["frames"], changed["sequence"]["frames"]
        self.assertEqual(a[:81], b[:81])
        self.assertEqual(a[160:], b[160:])
        self.assertEqual(a[80], b[80])
        self.assertEqual(a[160], b[160])
        self.assertTrue(any(a[i] != b[i] for i in range(81, 160)))
        for seam in (80, 160, 240):
            left = base["sections"][seam // 80 - 1]["sequence"]["frames"][-1]
            right = base["sections"][seam // 80]["sequence"]["frames"][0]
            self.assertEqual(left["joints"], right["joints"])
            self.assertEqual(left["contacts"], right["contacts"])
            self.assertEqual(base["sequence"]["frames"][seam]["joints"], left["joints"])

    def test_strict_compact_and_expanded_grammar(self):
        for raw in (
            "not json", "```json\n" + compact() + "\n```",
            '{"motif":"sway","motif":"pulse","accents":["soft","soft","soft","soft"]}',
            compact("hold"), compact(accents=["soft"] * 3),
            json.dumps({"motif": "sway", "accents": ["soft", True, "soft", "clear"]}),
            json.dumps({"motif": "sway", "accents": ["soft"] * 4, "revision": 1}),
            compact().replace('"soft"', 'NaN', 1),
            " " * 4097,
        ):
            with self.subTest(raw=raw[:70]), self.assertRaises(ValueError):
                compile_intent(raw)
        valid = json.loads(expanded())
        corruptions = []
        wrong_b = copy.deepcopy(valid)
        wrong_b["moves"][9][0] = "sway"
        corruptions.append(wrong_b)
        mixed_accent = copy.deepcopy(valid)
        mixed_accent["moves"][6][1] = "clear"
        corruptions.append(mixed_accent)
        wrong_open = copy.deepcopy(valid)
        wrong_open["moves"][4][0] = "hold"
        corruptions.append(wrong_open)
        wrong_a = copy.deepcopy(valid)
        wrong_a["moves"][13][0] = "pulse"
        corruptions.append(wrong_a)
        bool_variation = copy.deepcopy(valid)
        bool_variation["moves"][0][1] = True
        corruptions.append(bool_variation)
        for candidate in corruptions:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                compile_expanded(json.dumps(candidate))
        with self.assertRaises(ValueError):
            compile_expanded('{"moves":[],"moves":[]}')
        with self.assertRaises(ValueError):
            compile_expanded(json.dumps({"moves": valid["moves"], "extra": 1}))

    def test_rejects_corrupted_section_seam_frame_metadata_and_receipt(self):
        source = compile_intent(compact())
        mutations = []
        section = copy.deepcopy(source)
        section["sections"][2]["sequence"]["frames"][10]["joints"]["left_elbow"][2] += 0.02
        mutations.append(section)
        seam = copy.deepcopy(source)
        seam["sections"][1]["sequence"]["frames"][0]["joints"]["left_wrist"][0] += 0.01
        mutations.append(seam)
        frame = copy.deepcopy(source)
        frame["sequence"]["frames"][120]["joints"]["pelvis"][0] += 0.01
        mutations.append(frame)
        nan = copy.deepcopy(source)
        nan["sequence"]["frames"][120]["joints"]["head"][2] = math.nan
        mutations.append(nan)
        metadata = copy.deepcopy(source)
        metadata["sequence"]["beats"] = True
        mutations.append(metadata)
        contact = copy.deepcopy(source)
        contact["sequence"]["frames"][100]["contacts"]["left"] = 1
        mutations.append(contact)
        intent = copy.deepcopy(source)
        intent["intent"]["motif"] = "pulse"
        mutations.append(intent)
        receipt = copy.deepcopy(source)
        receipt["receipt"]["sequence_sha256"] = "0" * 64
        mutations.append(receipt)
        for index, changed in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                verify_score(changed)


if __name__ == "__main__":
    unittest.main()

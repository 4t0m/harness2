"""Host-bound geometry and strict symbolic-intent checks for two-actor staging."""

import copy
import json
import math
import unittest

from harness2.actor_staging import compile_staging, parse_intent


def scene(x=0.0):
    return {"revision": "scene-r1", "anchor": {"id": "mark", "x_m": x},
            "actor_ids": ["aya", "ren"]}


def intent(left="aya", right="ren"):
    return {"scene_revision": "scene-r1", "placements": [
        {"actor_id": left, "anchor_id": "mark", "side": "left"},
        {"actor_id": right, "anchor_id": "mark", "side": "right"}],
        "cues": [
            {"slot": 0, "actor_id": "aya", "gesture": "wave", "variation": "soft"},
            {"slot": 1, "actor_id": "ren", "gesture": "nod", "variation": "clear"},
            {"slot": 2, "actor_id": "aya", "gesture": "neutral", "variation": "soft"}]}


class ActorStagingTests(unittest.TestCase):
    def test_valid_compilation_is_static_ordered_and_nonmutating(self):
        host = scene()
        proposal = intent()
        before_host, before_proposal = copy.deepcopy(host), copy.deepcopy(proposal)
        raw = json.dumps(proposal)
        result = compile_staging(raw, host)
        self.assertEqual(host, before_host)
        self.assertEqual(proposal, before_proposal)
        self.assertEqual(result["scene_revision"], "scene-r1")
        self.assertEqual(result["actors"], [
            {"id": "aya", "x_m": -0.85, "y_m": 0, "z_m": 0},
            {"id": "ren", "x_m": 0.85, "y_m": 0, "z_m": 0}])
        self.assertEqual(result["cues"], [
            {"slot": 0, "start_s": 0, "end_s": 2, "actor_id": "aya", "gesture": "wave", "variation": "soft"},
            {"slot": 1, "start_s": 2, "end_s": 4, "actor_id": "ren", "gesture": "nod", "variation": "clear"},
            {"slot": 2, "start_s": 4, "end_s": 6, "actor_id": "aya", "gesture": "neutral", "variation": "soft"}])
        self.assertEqual((result["fps"], result["frame_count"], result["duration_s"]), (8, 48, 6))
        self.assertIn("positions held", result["scope"])
        self.assertIn("no walking", result["scope"])
        json.dumps(result, allow_nan=False)

    def test_roles_mirror_and_anchor_offset_without_input_coordinates(self):
        host = scene(0.4)
        proposal = intent(left="ren", right="aya")
        result = compile_staging(json.dumps(proposal), host)
        self.assertEqual(result["actors"], [
            {"id": "aya", "x_m": 1.25, "y_m": 0, "z_m": 0},
            {"id": "ren", "x_m": 0.4 - 0.85, "y_m": 0, "z_m": 0}])
        self.assertAlmostEqual(abs(result["actors"][0]["x_m"] - result["actors"][1]["x_m"]), 1.7)
        self.assertTrue(all(abs(actor["x_m"]) <= 3 for actor in result["actors"]))

    def test_strict_json_and_field_shape_rejections(self):
        good = intent()
        bad_values = [
            "not JSON", "```json\n" + json.dumps(good) + "\n```",
            '{"scene_revision":"scene-r1","scene_revision":"scene-r1","placements":[],"cues":[]}',
            json.dumps(dict(good, duration_s=6)),
            json.dumps(dict(good, placements=good["placements"] + [good["placements"][0]])),
            json.dumps(dict(good, cues=good["cues"][:2])),
            json.dumps(dict(good, cues=[dict(good["cues"][0], start_s=0)] + good["cues"][1:])),
            json.dumps(dict(good, placements=[dict(good["placements"][0], x_m=-0.85), good["placements"][1]])),
            json.dumps(dict(good, cues=[dict(good["cues"][0], slot=True)] + good["cues"][1:])),
            json.dumps(good).replace('"slot": 0', '"slot": NaN', 1),
            " " * 8193,
        ]
        for raw in bad_values:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                parse_intent(raw)

    def test_host_semantics_reject_stale_unknown_duplicate_and_order_errors(self):
        cases = []
        stale = intent(); stale["scene_revision"] = "old"; cases.append(stale)
        wrong_actor = intent(); wrong_actor["placements"][0]["actor_id"] = "unknown"; cases.append(wrong_actor)
        duplicate_actor = intent(); duplicate_actor["placements"][1]["actor_id"] = "aya"; cases.append(duplicate_actor)
        same_side = intent(); same_side["placements"][1]["side"] = "left"; cases.append(same_side)
        wrong_anchor = intent(); wrong_anchor["placements"][0]["anchor_id"] = "other"; cases.append(wrong_anchor)
        wrong_cue_actor = intent(); wrong_cue_actor["cues"][1]["actor_id"] = "other"; cases.append(wrong_cue_actor)
        duplicate_slot = intent(); duplicate_slot["cues"][1]["slot"] = 0; cases.append(duplicate_slot)
        for proposal in cases:
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                compile_staging(json.dumps(proposal), scene())
        unordered = intent(); unordered["cues"].reverse()
        normalized = compile_staging(json.dumps(unordered), scene())
        self.assertEqual([cue["slot"] for cue in normalized["cues"]], [0, 1, 2])
        wrong_gesture = intent(); wrong_gesture["cues"][0]["gesture"] = "walk"
        with self.assertRaisesRegex(ValueError, "unsupported gesture"):
            compile_staging(json.dumps(wrong_gesture), scene())
        wrong_variation = intent(); wrong_variation["cues"][0]["variation"] = "wild"
        with self.assertRaisesRegex(ValueError, "unsupported variation"):
            compile_staging(json.dumps(wrong_variation), scene())

    def test_scene_validation_rejects_nonfinite_out_of_bounds_and_bad_ids(self):
        raw = json.dumps(intent())
        for x in (math.nan, math.inf, -1.01, 1.01, True, "0", 10 ** 1000):
            with self.subTest(x=x), self.assertRaises(ValueError):
                compile_staging(raw, scene(x))
        missing = scene(); del missing["anchor"]["x_m"]
        with self.assertRaises(ValueError):
            compile_staging(raw, missing)
        duplicate = scene(); duplicate["actor_ids"] = ["aya", "aya"]
        with self.assertRaises(ValueError):
            compile_staging(raw, duplicate)
        extra = scene(); extra["renderer"] = "run"
        with self.assertRaises(ValueError):
            compile_staging(raw, extra)


if __name__ == "__main__":
    unittest.main()

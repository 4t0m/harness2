"""Independent staging replies compile only as a complete canonical plan."""

import copy
import itertools
import json
import unittest

from experiments.actor_staging_cases import CASES
from experiments.actor_staging_extra_holdouts import EVAL_CASES
from harness2.actor_staging import compile_staging
from harness2.actor_staging_compact import bind_scene
from harness2.actor_staging_steps import (
    CUE_SCHEMA, PLACEMENT_SCHEMA, assemble_staging,
)


def pieces(case):
    expected = case["expected"]
    left = next(item["actor_id"] for item in expected["placements"]
                if item["side"] == "left")
    cues = sorted(expected["cues"], key=lambda cue: cue["slot"])
    return json.dumps({"left": left}), [json.dumps({
        "actor": cue["actor_id"], "gesture": cue["gesture"],
        "variation": cue["variation"]}) for cue in cues]


class ActorStagingStepsTests(unittest.TestCase):
    def test_all_twelve_frozen_cases_match_canonical_compiler(self):
        frozen = CASES + EVAL_CASES
        self.assertEqual(len(frozen), 12)
        for case in frozen:
            with self.subTest(case=case["id"]):
                scene = copy.deepcopy(case["scene"])
                before = copy.deepcopy(scene)
                placement, cues = pieces(case)
                expected = compile_staging(json.dumps({
                    "scene_revision": scene["revision"], **case["expected"]}), scene)
                actual = assemble_staging(placement, cues, bind_scene(scene), scene)
                self.assertEqual(actual, expected)
                self.assertEqual(scene, before)
                self.assertEqual(len(actual["cues"]), 3)
                self.assertEqual([cue["slot"] for cue in actual["cues"]], [0, 1, 2])

    def test_representative_choices_preserve_actor_gesture_and_variation(self):
        scene = copy.deepcopy(CASES[0]["scene"])
        snapshot = bind_scene(scene)
        first, second = scene["actor_ids"]
        for left in (first, second):
            for actor, gesture, variation in itertools.product(
                    (first, second), ("wave", "nod", "neutral"), ("soft", "clear")):
                with self.subTest(left=left, actor=actor, gesture=gesture, variation=variation):
                    cues = [
                        json.dumps({"actor": actor, "gesture": gesture, "variation": variation}),
                        json.dumps({"actor": left, "gesture": "neutral", "variation": "clear"}),
                        json.dumps({"actor": second, "gesture": "wave", "variation": "soft"}),
                    ]
                    actual = assemble_staging(json.dumps({"left": left}), cues, snapshot, scene)
                    self.assertEqual(actual["cues"][0]["actor_id"], actor)
                    self.assertEqual(actual["cues"][0]["gesture"], gesture)
                    self.assertEqual(actual["cues"][0]["variation"], variation)
                    actor_x = {item["id"]: item["x_m"] for item in actual["actors"]}
                    self.assertLess(actor_x[left], actor_x[second if left == first else first])

    def test_bad_piece_or_missing_reply_refuses_whole_plan(self):
        case = CASES[0]
        placement, cues = pieces(case)
        scene = copy.deepcopy(case["scene"])
        snapshot = bind_scene(scene)
        bad_placements = [
            '{"left":"actor_rowan_17","left":"actor_rowan_17"}',
            json.dumps({"left": "unknown"}),
            json.dumps({"left": True}),
            json.dumps({"left": scene["actor_ids"][0], "x_m": -0.85}),
            "```json\n" + placement + "\n```",
            " " * 1025,
            "[]",
            None,
        ]
        for bad in bad_placements:
            with self.subTest(placement=str(bad)[:50]), self.assertRaises(ValueError):
                assemble_staging(bad, cues, snapshot, scene)
        bad_cues = [
            '{"actor":"actor_rowan_17","actor":"actor_ivo_42","gesture":"wave","variation":"soft"}',
            json.dumps({"actor": "unknown", "gesture": "wave", "variation": "soft"}),
            json.dumps({"actor": scene["actor_ids"][0], "gesture": "walk", "variation": "soft"}),
            json.dumps({"actor": scene["actor_ids"][0], "gesture": "wave", "variation": "wild"}),
            json.dumps({"actor": scene["actor_ids"][0], "gesture": "wave", "variation": "soft", "slot": 0}),
            json.dumps({"actor": scene["actor_ids"][0], "gesture": "wave"}),
            '{"actor":"actor_rowan_17","gesture":NaN,"variation":"soft"}',
            "[]",
            " " * 1025,
            None,
        ]
        for bad in bad_cues:
            for index in range(3):
                with self.subTest(cue=str(bad)[:50], index=index), self.assertRaises(ValueError):
                    altered = list(cues)
                    altered[index] = bad
                    assemble_staging(placement, altered, snapshot, scene)
        for incomplete in ([], cues[:2], cues + cues[:1], tuple(cues), None):
            with self.subTest(incomplete=incomplete), self.assertRaises(ValueError):
                assemble_staging(placement, incomplete, snapshot, scene)

    def test_full_scene_binding_and_schema_contract(self):
        case = CASES[0]
        placement, cues = pieces(case)
        scene = copy.deepcopy(case["scene"])
        snapshot = bind_scene(scene)
        altered = copy.deepcopy(scene)
        altered["anchor"]["x_m"] = 0.5  # revision deliberately unchanged
        with self.assertRaisesRegex(ValueError, "stale scene facts"):
            assemble_staging(placement, cues, snapshot, altered)
        self.assertEqual(set(PLACEMENT_SCHEMA["required"]), {"left"})
        self.assertEqual(set(CUE_SCHEMA["required"]), {"actor", "gesture", "variation"})
        self.assertFalse(PLACEMENT_SCHEMA["additionalProperties"])
        self.assertFalse(CUE_SCHEMA["additionalProperties"])


if __name__ == "__main__":
    unittest.main()

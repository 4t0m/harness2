"""Compact staging preserves the full compiler's choices and host boundary."""

import copy
from dataclasses import FrozenInstanceError
import json
import unittest

from experiments.actor_staging_cases import CASES
from harness2.actor_staging import compile_staging
from harness2.actor_staging_compact import bind_scene, compile_compact


def compact_from_expected(expected):
    left = next(item["actor_id"] for item in expected["placements"]
                if item["side"] == "left")
    ordered = sorted(expected["cues"], key=lambda item: item["slot"])
    return {"left": left, "cues": [[item["actor_id"], item["gesture"],
                                      item["variation"]] for item in ordered]}


class CompactStagingTests(unittest.TestCase):
    def test_exact_canonical_equivalence_for_each_fixture(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                scene = copy.deepcopy(case["scene"])
                compact = compact_from_expected(case["expected"])
                before_scene = copy.deepcopy(scene)
                before_compact = copy.deepcopy(compact)
                full = {"scene_revision": scene["revision"], **case["expected"]}
                expected = compile_staging(json.dumps(full), scene)
                actual = compile_compact(json.dumps(compact), bind_scene(scene), scene)
                self.assertEqual(actual, expected)
                self.assertEqual(scene, before_scene)
                self.assertEqual(compact, before_compact)

    def test_both_roles_and_all_gesture_variations_remain_expressible(self):
        scene = copy.deepcopy(CASES[1]["scene"])
        actor_a, actor_b = scene["actor_ids"]
        for left in (actor_a, actor_b):
            right = actor_b if left == actor_a else actor_a
            for gesture in ("wave", "nod", "neutral"):
                for variation in ("soft", "clear"):
                    with self.subTest(left=left, gesture=gesture, variation=variation):
                        compact = {"left": left, "cues": [
                            [right, gesture, variation],
                            [left, "neutral", "clear"],
                            [right, "wave", "soft"],
                        ]}
                        plan = compile_compact(json.dumps(compact), bind_scene(scene), scene)
                        self.assertEqual(plan["cues"][0]["actor_id"], right)
                        self.assertEqual(plan["cues"][0]["gesture"], gesture)
                        self.assertEqual(plan["cues"][0]["variation"], variation)
                        self.assertEqual(plan["cues"][1]["slot"], 1)
                        self.assertEqual(plan["cues"][2]["slot"], 2)
                        by_id = {actor["id"]: actor["x_m"] for actor in plan["actors"]}
                        self.assertLess(by_id[left], by_id[right])

    def test_snapshot_is_immutable_and_rejects_changed_current_facts(self):
        original = copy.deepcopy(CASES[0]["scene"])
        mutable = copy.deepcopy(original)
        snapshot = bind_scene(mutable)
        with self.assertRaises(FrozenInstanceError):
            snapshot.anchor_x_m = 0.7
        self.assertIsInstance(snapshot.actor_ids, tuple)
        raw = json.dumps(compact_from_expected(CASES[0]["expected"]))
        baseline = compile_compact(raw, snapshot, copy.deepcopy(original))
        self.assertEqual(baseline["scene_revision"], original["revision"])

        changes = [
            lambda scene: scene["anchor"].update(x_m=0.4),
            lambda scene: scene["anchor"].update(id="new_anchor"),
            lambda scene: scene["actor_ids"].reverse(),
            lambda scene: scene.update(revision="new_revision"),
        ]
        for change in changes:
            current = copy.deepcopy(original)
            change(current)
            with self.subTest(current=current), self.assertRaisesRegex(ValueError, "stale"):
                compile_compact(raw, snapshot, current)
        mutable["anchor"]["x_m"] = -0.5
        mutable["actor_ids"][0] = "replaced"
        self.assertEqual(snapshot.anchor_x_m, original["anchor"]["x_m"])
        self.assertEqual(snapshot.actor_ids, tuple(original["actor_ids"]))
        self.assertEqual(compile_compact(raw, snapshot, original), baseline)

    def test_strict_compact_rejections(self):
        scene = copy.deepcopy(CASES[0]["scene"])
        snapshot = bind_scene(scene)
        good = compact_from_expected(CASES[0]["expected"])
        variants = [
            "garbage",
            "```json\n" + json.dumps(good) + "\n```",
            '{"left":"actor_rowan_17","left":"actor_rowan_17","cues":[]}',
            json.dumps(dict(good, scene_revision=scene["revision"])),
            json.dumps({"left": good["left"]}),
            json.dumps(dict(good, cues=good["cues"][:2])),
            json.dumps(dict(good, cues=good["cues"] + [good["cues"][0]])),
            json.dumps(dict(good, cues=[{"actor_id": good["left"]}] + good["cues"][1:])),
            json.dumps(dict(good, cues=[[good["left"], "wave"]] + good["cues"][1:])),
            json.dumps(dict(good, cues=[[good["left"], "wave", "soft", 0]] + good["cues"][1:])),
            json.dumps(dict(good, cues=[[good["left"], "walk", "soft"]] + good["cues"][1:])),
            json.dumps(dict(good, cues=[[good["left"], "wave", "wild"]] + good["cues"][1:])),
            json.dumps(dict(good, cues=[[True, "wave", "soft"]] + good["cues"][1:])),
            json.dumps(dict(good, cues=[["unknown", "wave", "soft"]] + good["cues"][1:])),
            json.dumps(dict(good, left="unknown")),
            json.dumps(dict(good, left=True)),
            json.dumps(good).replace('"left":', '"left": NaN, "spare":', 1),
            " " * 8193,
        ]
        for raw in variants:
            with self.subTest(raw=raw[:90]), self.assertRaises(ValueError):
                compile_compact(raw, snapshot, scene)

    def test_invalid_scene_and_snapshot_rejected(self):
        scene = copy.deepcopy(CASES[0]["scene"])
        raw = json.dumps(compact_from_expected(CASES[0]["expected"]))
        with self.assertRaises(ValueError):
            compile_compact(raw, None, scene)
        for bad_x in (True, "0", float("nan"), 1.1):
            bad = copy.deepcopy(scene)
            bad["anchor"]["x_m"] = bad_x
            with self.subTest(x=bad_x), self.assertRaises(ValueError):
                bind_scene(bad)
        bad = copy.deepcopy(scene)
        bad["anchor"]["x_m"] = 2
        with self.assertRaises(ValueError):
            compile_compact(raw, bind_scene(scene), bad)


if __name__ == "__main__":
    unittest.main()

"""Checks for render sampling boundaries and measured interpolation drift."""

import copy
import math
import unittest

from harness2 import dance_motion
from harness2.motion_reference import resample_for_render


class MotionReferenceTests(unittest.TestCase):
    def setUp(self):
        self.source = dance_motion.generate("restrained")
        self.before = copy.deepcopy(self.source)

    def test_24fps_render_samples_map_to_source_without_endpoint(self):
        result = resample_for_render(self.source)
        self.assertEqual(result["kind"], "render_only_linear_resample")
        self.assertEqual(result["source"], {"fps": 20, "frame_count": 81,
                                            "endpoint_inclusive": True, "duration_seconds": 4.0})
        self.assertEqual(result["render"], {"fps": 24, "frame_count": 96,
                                            "endpoint_inclusive": False, "duration_seconds": 4.0})
        self.assertEqual(len(result["frames"]), 96)
        self.assertEqual(result["frames"][0]["time"], 0.0)
        self.assertEqual(result["frames"][-1]["time"], 95 / 24)
        self.assertLess(result["frames"][-1]["time"], 4.0)
        self.assertEqual(result["frames"][-1]["source_mapping"],
                         {"left_index": 79, "right_index": 80, "alpha": 1 / 6})
        self.assertEqual(result["bone_edges"], self.source["bone_edges"])
        self.assertIsNot(result["bone_edges"], self.source["bone_edges"])
        self.assertEqual(self.source, self.before)
        self.assertNotIn("contacts", result["frames"][0])
        with self.assertRaisesRegex(ValueError, "invalid skeletal segment metadata"):
            dance_motion.validate(result)

    def test_exact_source_coincidences_and_linear_intermediate(self):
        result = resample_for_render(self.source)
        indices = result["measurements"]["source_coincidence_render_indices"]
        self.assertEqual(indices, list(range(0, 96, 6)))
        self.assertTrue(result["measurements"]["exact_source_coincidence_preserved"])
        for render_index in indices:
            sample = result["frames"][render_index]
            source_index = sample["source_mapping"]["left_index"]
            self.assertEqual(sample["source_mapping"]["alpha"], 0.0)
            self.assertEqual(sample["source_mapping"]["right_index"], source_index + 1)
            self.assertEqual(sample["joints"], self.source["frames"][source_index]["joints"])
        sample = result["frames"][1]
        self.assertEqual(sample["source_mapping"],
                         {"left_index": 0, "right_index": 1, "alpha": 5 / 6})
        name = "left_wrist"
        left = self.source["frames"][0]["joints"][name]
        right = self.source["frames"][1]["joints"][name]
        self.assertEqual(sample["joints"][name],
                         [left[axis] + (right[axis] - left[axis]) * 5 / 6 for axis in range(3)])

    def test_segment_drift_is_measured_not_claimed_valid(self):
        result = resample_for_render(self.source)
        reported = result["measurements"]["max_segment_length_deviation_from_source_m"]
        self.assertTrue(math.isfinite(reported))
        self.assertGreater(reported, 0.0)
        # Independently measure one interpolated frame: rigid source bones can
        # shrink during Cartesian interpolation, so the metric is substantive.
        frame = result["frames"][1]["joints"]
        deviations = [abs(math.dist(frame[start], frame[end]) - target)
                      for edge, target in self.source["segment_lengths_m"].items()
                      for start, end in [edge.split(":", 1)]]
        self.assertGreater(max(deviations), 0.0)
        self.assertGreaterEqual(reported, max(deviations))
        self.assertIn("no contact", result["scope"])

    def test_invalid_rate_timing_and_nonfinite_source_refused(self):
        for fps in (20, 30, True, 24.0, math.nan):
            with self.subTest(render_fps=fps), self.assertRaises(ValueError):
                resample_for_render(self.source, fps)
        for field, value in (("fps", 24), ("fps", True), ("bpm", 240),
                             ("beats", 7), ("duration_seconds", 3.0)):
            with self.subTest(field=field):
                bad = copy.deepcopy(self.source)
                bad[field] = value
                with self.assertRaises(ValueError):
                    resample_for_render(bad)
        bad = copy.deepcopy(self.source)
        bad["frames"][12]["joints"]["head"][0] = math.nan
        with self.assertRaises(ValueError):
            resample_for_render(bad)
        malformed = copy.deepcopy(self.source)
        malformed["frames"][0]["joints"]["extra"] = None
        with self.assertRaises(ValueError):
            resample_for_render(malformed)
        self.assertEqual(self.source, self.before)


if __name__ == "__main__":
    unittest.main()

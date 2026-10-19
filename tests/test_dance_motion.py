import math
import unittest

from harness2 import dance_motion


class DanceMotionTests(unittest.TestCase):
    def test_variants_are_valid_and_distinct(self):
        restrained = dance_motion.generate("restrained")
        broad = dance_motion.generate("broad")
        for sequence in (restrained, broad):
            report = dance_motion.validate(sequence)
            self.assertTrue(report["valid"])
            self.assertEqual(report["frame_count"], 81)
            self.assertEqual(report["duration_seconds"], 4.0)
            self.assertEqual(sequence["frames"][0]["time"], 0.0)
            self.assertEqual(sequence["frames"][-1]["time"], 4.0)
        self.assertNotEqual(
            restrained["frames"][5]["joints"]["left_wrist"],
            broad["frames"][5]["joints"]["left_wrist"],
        )
        self.assertEqual(restrained["coordinate_system"], "world x=lateral, y=forward, z=up; ground z=0")
        self.assertTrue(restrained["bone_edges"])

    def test_rejects_foot_sliding_during_contact(self):
        sequence = dance_motion.generate("restrained")
        # Frames 7 and 8 are both in the right-foot stance after its swing.
        self.assertTrue(sequence["frames"][7]["contacts"]["right"])
        sequence["frames"][8]["joints"]["right_ankle"][0] += 0.02
        with self.assertRaisesRegex(ValueError, "planted foot sliding"):
            dance_motion.validate(sequence)

    def test_rejects_nonfinite_position(self):
        sequence = dance_motion.generate("broad")
        sequence["frames"][12]["joints"]["head"][1] = math.nan
        with self.assertRaisesRegex(ValueError, "invalid position"):
            dance_motion.validate(sequence)

    def test_rejects_wrong_limb_length(self):
        sequence = dance_motion.generate("restrained")
        sequence["frames"][10]["joints"]["left_knee"][0] += 0.03
        with self.assertRaisesRegex(ValueError, "wrong skeletal segment length"):
            dance_motion.validate(sequence)

    def test_rejects_deformed_foot_marker_and_torso(self):
        foot_deformed = dance_motion.generate("broad")
        foot_deformed["frames"][12]["joints"]["left_foot"][2] += 0.02
        with self.assertRaisesRegex(ValueError, "wrong skeletal segment length: left_ankle to left_foot"):
            dance_motion.validate(foot_deformed)

        torso_deformed = dance_motion.generate("restrained")
        torso_deformed["frames"][20]["joints"]["spine"][2] += 0.02
        with self.assertRaisesRegex(ValueError, "wrong skeletal segment length: pelvis to spine"):
            dance_motion.validate(torso_deformed)

    def test_rigid_foot_and_torso_edges_remain_fixed(self):
        sequence = dance_motion.generate("broad")
        self.assertIn(["left_ankle", "left_foot"], sequence["bone_edges"])
        self.assertIn(["right_ankle", "right_foot"], sequence["bone_edges"])
        self.assertLess(dance_motion.validate(sequence)["max_skeletal_segment_error_m"], 1e-6)
        for frame in sequence["frames"]:
            joints = frame["joints"]
            for side in ("left", "right"):
                self.assertAlmostEqual(joints[f"{side}_foot"][2],
                                       joints[f"{side}_ankle"][2] - 0.025)
            self.assertAlmostEqual(joints["spine"][2] - joints["pelvis"][2], 0.36)
            self.assertAlmostEqual(joints["neck"][2] - joints["spine"][2], 0.25)

    def test_authored_contact_transitions_are_continuous_at_beat_boundaries(self):
        sequence = dance_motion.generate("broad")
        report = dance_motion.validate(sequence)
        self.assertLess(report["max_joint_delta_m"], 0.20)
        for boundary in range(1, 8):
            index = boundary * 10
            previous, current = sequence["frames"][index - 1], sequence["frames"][index]
            for side in ("left", "right"):
                if previous["contacts"][side] and current["contacts"][side]:
                    before = previous["joints"][f"{side}_ankle"]
                    after = current["joints"][f"{side}_ankle"]
                    self.assertLess(math.dist(before, after), 1e-5)
        for frame in sequence["frames"]:
            for side in ("left", "right"):
                self.assertGreater(frame["joints"][f"{side}_knee"][1],
                                   frame["joints"][f"{side}_hip"][1])


if __name__ == "__main__":
    unittest.main()

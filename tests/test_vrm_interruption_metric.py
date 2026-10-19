import math
import unittest
from experiments.vrm_interrupt_probe import rotation_distance


class RotationDistanceTests(unittest.TestCase):
    def test_quaternion_sign_does_not_count_as_motion(self):
        self.assertAlmostEqual(rotation_distance([0,0,0,1],[0,0,0,-1]),0)

    def test_known_angle_and_invalid_rotation(self):
        self.assertAlmostEqual(rotation_distance([0,0,math.sqrt(0.5),math.sqrt(0.5)],[0,0,0,1]),math.pi/2)
        with self.assertRaises(ValueError):rotation_distance([0,0,0,0],[0,0,0,1])

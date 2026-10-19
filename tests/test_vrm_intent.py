import unittest
from harness2.vrm_intent import compile_intent


class VRMIntentTests(unittest.TestCase):
    def test_relative_coordinates_host_owned(self):
        self.assertAlmostEqual(compile_intent('{"gesture":"wave_goodbye","side":"right"}',0.1,0.25)['x_position'],0.35)
        self.assertAlmostEqual(compile_intent('{"gesture":"salute","side":"left"}',0.1,0.25)['x_position'],-0.15)

    def test_invalid_and_unreachable(self):
        for raw in ['{"gesture":[],"side":"right"}', '{"gesture":"dance","side":"left"}',
                    '{"gesture":"salute","side":"left","x_position":0}']:
            with self.assertRaises(ValueError):compile_intent(raw,0,0.2)
        for anchor,offset in [(0.5,0.3),(float('nan'),0.2),(0,0),(True,0.2)]:
            with self.assertRaises(ValueError):compile_intent('{"gesture":"salute","side":"right"}',anchor,offset)

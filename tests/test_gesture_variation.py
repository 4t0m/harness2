import unittest
from harness2.gesture_variation import compile_variation,SOURCE_SHA256


class VariationTests(unittest.TestCase):
    def test_only_variation_is_model_controlled(self):
        for name,value in [('soft',2.35),('restrained',2.1)]:
            plan=compile_variation('{"variation":"'+name+'"}',SOURCE_SHA256)
            self.assertEqual(plan['peak_radians'],value)
            self.assertEqual(plan['editable_frames'],[13,35])
            self.assertEqual(plan['keyframe'],24)

    def test_forged_scope_and_stale_source_rejected(self):
        for raw in ['{"variation":"soft","keyframe":1}','{"variation":[]}',
                    '{"variation":"anything"}','{"variation":"soft","variation":"restrained"}']:
            with self.assertRaises(ValueError):compile_variation(raw,SOURCE_SHA256)
        with self.assertRaises(ValueError):compile_variation('{"variation":"soft"}','changed')

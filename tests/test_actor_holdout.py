import json
import unittest
from experiments.actor_holdout_probe import CASES, packet, assess

class HoldoutTests(unittest.TestCase):
    def test_oracle_matches_independent_distance_selection(self):
        for i, (_, _, side, _) in enumerate(CASES):
            scene, _, expected = packet(i)
            actor = next(a for a in scene['actors'] if a['id'] == expected['actor_id'])
            options = [a for a in scene['actors'] if (a['x'] > actor['x'] if side == 'right' else a['x'] < actor['x'])]
            nearest = min(options, key=lambda a: (a['x']-actor['x'])**2+(a['y']-actor['y'])**2)
            self.assertEqual(nearest['id'], expected['target_id'])
            self.assertTrue(assess(i,json.dumps({'scene_revision':scene['revision'],**expected}))['accepted'])
    def test_fixed_target_and_stale_revision_fail(self):
        for i in range(len(CASES)):
            scene, _, expected = packet(i)
            self.assertFalse(assess(i,json.dumps({'scene_revision':scene['revision'],**expected,'target_id':'ren'}))['accepted'])
            self.assertFalse(assess(i,json.dumps({'scene_revision':'old',**expected}))['accepted'])

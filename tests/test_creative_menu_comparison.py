import unittest
from experiments.creative_menu_comparison import CASES, build
from harness2.production_menu import resolve
import json


class ComparisonFixtureTests(unittest.TestCase):
    def test_rotation_preserves_semantic_target_and_changes_position(self):
        for case in CASES:
            positions=[]
            for rotation in range(3):
                task,labels,brief,packet,expected=build(case,rotation)
                index=next(i for i,a in enumerate(packet['actions']) if a['job_id']==expected)
                positions.append(index)
                result=resolve(task,labels,brief,packet['revision'],json.dumps({'choice_id':'option_'+str(index)}))
                self.assertTrue(result['valid'])
                self.assertEqual(result['action']['job_id'],expected)
                self.assertNotIn('expected',json.dumps(packet['prompt']))
            self.assertEqual(len(set(positions)),3)

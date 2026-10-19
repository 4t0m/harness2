import unittest
from experiments.summarize_creative_menu import summarize


class SummaryTests(unittest.TestCase):
    def test_missing_errors_and_unknown_cost_remain_visible(self):
        report={'models':['a'],'cases':[['case']], 'rotations':[0,1,2],
                'rows':[{'requested_model':'a','task_id':'case','strict_match':False,
                         'repaired_match':True,'latency_seconds':1,'cost':0.01},
                        {'requested_model':'a','task_id':'case','error':'timeout'}]}
        result=summarize(report)['models'][0]
        self.assertFalse(result['complete'])
        self.assertEqual(result['expected_observations'],3)
        self.assertEqual(result['repaired_matches'],1)
        self.assertEqual(result['errors'],1)
        self.assertEqual(result['unknown_cost_calls'],1)
        self.assertEqual(result['known_cost_usd'],0.01)

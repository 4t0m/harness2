import copy
import json
import unittest
from harness2.production_dispatch import TASKS, rejection_feedback


class ProductionFeedbackTests(unittest.TestCase):
    def test_cap_is_derived_from_current_state(self):
        task = copy.deepcopy(TASKS[1])
        task['max_attempts'] = 2
        task['jobs'][1]['attempt'] = 2
        task['jobs'][1]['job_id'] = 'renamed_parent'
        task['jobs'][0]['depends_on'] = ['renamed_parent']
        before = copy.deepcopy(task)
        feedback = rejection_feedback(task, json.dumps({'operation':'retry','job_id':'renamed_parent'}))
        self.assertEqual(feedback['code'], 'attempt_cap_reached')
        self.assertEqual(feedback['attempt'], 2)
        self.assertEqual(feedback['max_attempts'], 2)
        self.assertEqual(task, before)
        self.assertNotIn('valid_choices', feedback)

    def test_accepted_proposal_gets_no_correction(self):
        self.assertIsNone(rejection_feedback(TASKS[1], '{"operation":"wait","job_id":null}'))

    def test_schema_and_other_errors(self):
        self.assertEqual(rejection_feedback(TASKS[1], '[]')['code'], 'invalid_action_schema')
        self.assertEqual(rejection_feedback(TASKS[1], '{"operation":"dispatch","job_id":"waiting_child"}')['code'], 'illegal_action')

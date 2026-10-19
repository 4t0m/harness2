import unittest
from experiments.production_holdouts import fixtures
from harness2.production_dispatch import valid_choices, model_brief


class HoldoutContractTests(unittest.TestCase):
    def test_combinations_have_independent_legal_outcomes(self):
        expected = [('dispatch','scene_b'), ('retry','take_b'), ('wait',None), ('dispatch','clip_c')]
        for task, (operation, job_id) in zip(fixtures(), expected):
            self.assertEqual(valid_choices(task), [{'operation':operation,'job_id':job_id}])
            self.assertNotIn('valid_choices', model_brief(task))

    def test_fixtures_are_fresh_copies(self):
        original = fixtures()
        original[0]['jobs'].clear()
        self.assertEqual(len(fixtures()[0]['jobs']), 3)

import copy
import unittest
from harness2.production_dispatch import _job, _task
from harness2.production_menu import menu, resolve


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.task = _task('menu-case', [_job('locked','failed',attempt=2), _job('ready','pending')], max_attempts=2)
        self.descriptions={'locked':'Polish the dance render.', 'ready':'Prepare pose variations.'}
        self.brief='Explore poses.'
        self.packet=menu(self.task,self.descriptions,self.brief)

    def test_host_removes_illegal_and_revalidates_selection(self):
        self.assertEqual(len(self.packet['prompt']['legal_options']), 1)
        result=resolve(self.task,self.descriptions,self.brief,self.packet['revision'],'{"choice_id":"option_0"}')
        self.assertTrue(result['valid'])
        self.assertEqual(result['action']['job_id'],'ready')
        self.assertEqual(self.task['jobs'][1]['status'],'pending')

    def test_stale_state_and_brief_cannot_commit(self):
        changed=copy.deepcopy(self.task);changed['jobs'][1]['status']='running'
        for task,brief in [(changed,self.brief),(self.task,'New priority')]:
            result=resolve(task,self.descriptions,brief,self.packet['revision'],'{"choice_id":"option_0"}')
            self.assertFalse(result['valid'])
            self.assertIn('stale',result['reason'])

    def test_bad_or_forged_response(self):
        for raw in ['[]','{"choice_id":[]}','{"choice_id":"option_9"}',
                    '{"choice_id":"option_0","operation":"retry"}',
                    '{"choice_id":"option_0","choice_id":"option_0"}']:
            self.assertFalse(resolve(self.task,self.descriptions,self.brief,self.packet['revision'],raw)['valid'])

    def test_mutated_menu_cannot_change_host_action(self):
        self.packet['actions'][0]['job_id']='locked'
        result=resolve(self.task,self.descriptions,self.brief,self.packet['revision'],'{"choice_id":"option_0"}')
        self.assertEqual(result['action']['job_id'],'ready')

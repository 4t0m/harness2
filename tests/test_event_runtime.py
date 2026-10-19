import json
import unittest
from harness2.event_runtime import EventRuntime, replay

class EventTests(unittest.TestCase):
    def test_interruption_and_delayed_response_never_restart(self):
        rt=EventRuntime(); r=rt.request(now_ms=0)
        self.assertEqual(rt.deliver(r.request_id,'{"action":"nod"}',now_ms=10),'applied')
        rt.interrupt(now_ms=11)
        self.assertEqual(rt.deliver(r.request_id,'{"action":"nod"}',now_ms=12),'stale_or_duplicate')
        self.assertIsNone(rt.active)
        self.assertEqual([c['action'] for c in rt.commands],['nod','neutral'])

    def test_interrupt_before_first_response(self):
        rt=EventRuntime(); r=rt.request(now_ms=0); rt.interrupt(now_ms=1)
        self.assertEqual(rt.deliver(r.request_id,'{"action":"nod"}',now_ms=2),'stale_or_duplicate')
        self.assertEqual(rt.commands,[])

    def test_deadline_boundary(self):
        for arrival, expected in [(99,'applied'),(100,'expired'),(101,'expired')]:
            rt=EventRuntime(); r=rt.request(now_ms=0,budget_ms=100)
            self.assertEqual(rt.deliver(r.request_id,'{"action":"nod"}',now_ms=arrival),expected)

    def test_latest_event_supersedes_pending(self):
        rt=EventRuntime(); old=rt.request(now_ms=0); new=rt.request(now_ms=1)
        self.assertEqual(rt.deliver(old.request_id,'{"action":"nod"}',now_ms=2),'stale_or_duplicate')
        self.assertEqual(rt.deliver(new.request_id,'{"action":"listen"}',now_ms=3),'applied')

    def test_invalid_calls_cannot_extend_lease_or_repeat(self):
        for raw in ['{"action":"nod","hold_ms":999999}', '{"action":"nod","action":"listen"}',
                    '{"action":[]}', '```json\n{"action":"nod"}\n```']:
            rt=EventRuntime(); r=rt.request(now_ms=0)
            self.assertEqual(rt.deliver(r.request_id,raw,now_ms=1),'invalid')
            self.assertEqual(rt.deliver(r.request_id,'{"action":"nod"}',now_ms=2),'stale_or_duplicate')
            self.assertEqual(rt.commands,[])

    def test_lease_expires_once_and_snapshot_is_detached(self):
        rt=EventRuntime(); r=rt.request(now_ms=0,hold_ms=10)
        rt.deliver(r.request_id,'{"action":"listen"}',now_ms=1)
        rt.snapshot()['active']['expires_ms']=999999
        rt.advance(10); self.assertIsNotNone(rt.active)
        rt.advance(11); rt.advance(12)
        self.assertIsNone(rt.active); self.assertEqual(len(rt.commands),2)
        with self.assertRaises(ValueError): rt.advance(5)

    def test_end_to_end_replay(self):
        result=replay()
        self.assertEqual([c['action'] for c in result['commands']],['nod','neutral','listen','neutral'])
        self.assertEqual([v['status'] for v in result['verdicts']],
                         ['applied','stale_or_duplicate','expired','stale_or_duplicate','applied'])
        self.assertFalse(result['live_execution'])

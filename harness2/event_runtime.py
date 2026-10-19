"""CPU reference runtime for bounded asynchronous avatar decisions.

A model chooses an action only. The host owns revision, request identity,
deadline and duration. Commands are simulation receipts, not live execution.
"""
from dataclasses import dataclass, asdict
import json

ACTIONS = frozenset({'listen', 'nod', 'look_right', 'neutral'})

@dataclass(frozen=True)
class Request:
    request_id: int
    revision: int
    deadline_ms: int
    hold_ms: int

class EventRuntime:
    def __init__(self):
        self.now_ms = 0
        self.revision = 0
        self.next_id = 1
        self.pending = {}
        self.active = None
        self.commands = []
        self.verdicts = []

    def advance(self, now_ms):
        if type(now_ms) is not int or now_ms < self.now_ms:
            raise ValueError('clock must be a monotonic integer')
        self.now_ms = now_ms
        if self.active and now_ms >= self.active['expires_ms']:
            self._cancel('lease_expired')

    def _cancel(self, reason):
        if self.active is not None:
            self.commands.append({'at_ms': self.now_ms, 'action': 'neutral',
                                  'reason': reason, 'cancelled_request': self.active['request_id']})
            self.active = None

    def request(self, *, now_ms, budget_ms=500, hold_ms=1000):
        if type(budget_ms) is not int or not 1 <= budget_ms <= 5000:
            raise ValueError('invalid decision budget')
        if type(hold_ms) is not int or not 1 <= hold_ms <= 3000:
            raise ValueError('invalid action hold')
        self.advance(now_ms)
        # Latest event wins; older outstanding responses no longer have authority.
        self.revision += 1
        self.pending.clear()
        req = Request(self.next_id, self.revision, now_ms + budget_ms, hold_ms)
        self.next_id += 1
        self.pending[req.request_id] = req
        return req

    def interrupt(self, *, now_ms):
        self.advance(now_ms)
        self.revision += 1
        self.pending.clear()
        self._cancel('interrupted')

    def deliver(self, request_id, raw, *, now_ms):
        self.advance(now_ms)
        if type(request_id) is not int:
            raise ValueError('request ID must be an integer')
        req = self.pending.pop(request_id, None)
        status = 'stale_or_duplicate'
        if req is not None:
            if now_ms >= req.deadline_ms:
                status = 'expired'
            else:
                try:
                    def pairs(items):
                        obj = {}
                        for k, v in items:
                            if k in obj:
                                raise ValueError('duplicate field')
                            obj[k] = v
                        return obj
                    if not isinstance(raw, str) or len(raw) > 256:
                        raise ValueError('invalid response size')
                    value = json.loads(raw, object_pairs_hook=pairs)
                    if (not isinstance(value, dict) or set(value) != {'action'}
                        or not isinstance(value['action'], str) or value['action'] not in ACTIONS):
                        raise ValueError('invalid action')
                except (ValueError, RecursionError):
                    status = 'invalid'
                else:
                    self._cancel('replaced')
                    action = value['action']
                    self.commands.append({'at_ms': now_ms, 'action': action, 'request_id': request_id})
                    if action != 'neutral':
                        self.active = {'request_id': request_id, 'action': action,
                                       'expires_ms': now_ms + req.hold_ms}
                    status = 'applied'
        self.verdicts.append({'request_id': request_id, 'at_ms': now_ms, 'status': status})
        return status

    def snapshot(self):
        # Detached output: callers cannot mutate the authoritative runtime state.
        return json.loads(json.dumps({'now_ms':self.now_ms, 'revision':self.revision,
            'pending':[asdict(r) for r in self.pending.values()], 'active':self.active,
            'commands':self.commands, 'verdicts':self.verdicts, 'live_execution':False}))


def replay():
    rt = EventRuntime()
    first = rt.request(now_ms=0)
    rt.deliver(first.request_id, '{"action":"nod"}', now_ms=100)
    rt.interrupt(now_ms=140)
    rt.deliver(first.request_id, '{"action":"nod"}', now_ms=150)
    late = rt.request(now_ms=200, budget_ms=100)
    rt.deliver(late.request_id, '{"action":"look_right"}', now_ms=301)
    old = rt.request(now_ms=400)
    fresh = rt.request(now_ms=410)
    rt.deliver(old.request_id, '{"action":"nod"}', now_ms=420)
    rt.deliver(fresh.request_id, '{"action":"listen"}', now_ms=450)
    rt.advance(1450)
    return rt.snapshot()

if __name__ == '__main__':
    print(json.dumps(replay(), indent=2))

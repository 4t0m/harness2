"""Real local inference under host interruption; CPU avatar runtime only."""
import concurrent.futures
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
from harness2.event_runtime import EventRuntime

MODELS = ['hermes-lab-qwen3-8b:latest','hermes-lab-qwen30:latest']
SYSTEM = 'Choose the avatar action for the latest event. Allowed actions: listen, nod, look_right, neutral. Return only strict JSON with exactly action. Do not resume a superseded instruction.'


def infer(model, brief):
    start=time.monotonic()
    body={'model':model,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':brief}],
          'stream':False,'think':False,'options':{'num_ctx':2048,'num_predict':64,'temperature':0},'keep_alive':'2m'}
    req=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=25) as response:data=response.read(1048577)
    if len(data)>1048576:raise ValueError('oversized response')
    raw=json.loads(data)
    return {'content':raw.get('message',{}).get('content',''),'done_reason':raw.get('done_reason'),
            'wall_ms':round((time.monotonic()-start)*1000),
            **{k:raw.get(k) for k in ['load_duration','prompt_eval_count','eval_count','prompt_eval_duration','eval_duration']}}


def main():
    output=Path('evidence/local-event-v1.json')
    if output.exists():raise SystemExit('refusing overwrite')
    report={'scope':'real local inference with actual timed interruption; CPU reference runtime, no live avatar',
            'decision_budget_ms':5000,'interrupt_after_ms':100,'rows':[]}
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    for model in MODELS:
        row={'model':model,'calls':[]};report['rows'].append(row);save()
        rt=EventRuntime();start=time.monotonic()
        def now():return round((time.monotonic()-start)*1000)
        try:
            # Initial cold-load latency is measured separately, before the interaction begins.
            warm=infer(model,'The speaker is still explaining their request. Listen without agreeing yet.')
            row['warmup']=warm
            for phase,brief,expected in [
                ('listening','The speaker is still explaining their request. Listen without agreeing yet.','listen'),
                ('interrupted','The speaker finished and asked for a brief nod of acknowledgement.','nod'),
                ('fresh','The speaker interrupted: stop all gestures and return to neutral. The earlier request to nod is cancelled.','neutral')]:
                req=rt.request(now_ms=now(),budget_ms=5000,hold_ms=3000)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future=pool.submit(infer,model,brief)
                    if phase=='interrupted':
                        # Even if inference finishes sooner, delivery waits for this real host event.
                        time.sleep(.1)
                        rt.interrupt(now_ms=now())
                    result=future.result(timeout=28)
                arrival=now()
                status=rt.deliver(req.request_id,result['content'],now_ms=arrival)
                try:semantic=json.loads(result['content'])=={'action':expected}
                except (ValueError,TypeError):semantic=False
                row['calls'].append(dict(phase=phase,expected_action=expected,semantic_match=semantic,
                    arrival_ms=arrival,request_deadline_ms=req.deadline_ms,status=status,result=result))
                save()
            row['snapshot']=rt.snapshot()
            row['pass']=all(c['semantic_match'] and c['result']['done_reason']=='stop' for c in row['calls']) and [c['status'] for c in row['calls']]==['applied','stale_or_duplicate','applied'] and rt.active is None
            # Observed wall latency threshold comparison, not a separate live run at each deadline.
            row['latency_thresholds']={str(b):sum(c['result']['wall_ms']<b for c in row['calls']) for b in (250,500,1000,2000,5000)}
        except Exception as exc:row.update(error_type=type(exc).__name__,snapshot=rt.snapshot(),passed=False)
        save();print(json.dumps(row),flush=True)

if __name__=='__main__':main()

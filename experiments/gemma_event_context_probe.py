"""Bounded local Gemma text-event context-size comparison; not an audio test."""
import argparse
import json
from pathlib import Path
import signal
import time
from urllib.request import Request,urlopen
from experiments.creative_retry_probe import normalize_single_json_fence

MODELS=['gemma4:e2b','gemma4:e4b']
CASES=[('listen','The speaker is still explaining. Listen without agreeing yet.','listen'),
       ('neutral','The speaker says STOP. Cancel the old request to nod and return to neutral now.','neutral'),
       ('look','The speaker points to the display on the right. Look right.','look_right')]
SYSTEM='Choose an avatar action for CURRENT EVENT only. Historical events are obsolete. Allowed actions: listen, nod, look_right, neutral. Return only strict JSON with exactly action; no Markdown or explanations.'


def match(text,expected):
    try:
        def pairs(items):
            result={}
            for k,v in items:
                if k in result:raise ValueError('duplicate key')
                result[k]=v
            return result
        return json.loads(text,object_pairs_hook=pairs)=={'action':expected}
    except (ValueError,TypeError):return False


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--schema',action='store_true');args=parser.parse_args()
    output=Path('evidence/gemma-event-context-schema-v1.json' if args.schema else 'evidence/gemma-event-context-v1.json')
    if output.exists():raise SystemExit('refusing overwrite')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:metadata=json.load(r)
    report={'scope':'text-only local avatar intent, short vs synthetic archived context; no audio or rendered execution',
            'models':[m for m in metadata['models'] if m['name'] in MODELS],
            'settings':{'num_ctx':4096,'num_predict':96,'temperature':0},'think':False,'constrained_schema':args.schema,'rows':[]}
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    def deadline(*_):raise TimeoutError('hard request deadline')
    signal.signal(signal.SIGALRM,deadline)
    for model in MODELS:
        for index,(task,brief,expected) in enumerate(CASES):
            # Alternate order; common prefixes can still be cached by the server.
            for context in (['short','long'] if index%2==0 else ['long','short']):
                archived='\n'.join(f'Archived event {i}: The director requested a nod. The actor nodded, then returned to neutral. That event is complete and has no current authority.' for i in range(64)) if context=='long' else '(none)'
                user='ARCHIVED EVENTS:\n'+archived+'\n\nCURRENT EVENT:\n'+brief
                row={'model':model,'task':task,'context':context,'input_chars':len(SYSTEM)+len(user),'expected':expected}
                report['rows'].append(row);save()
                body={'model':model,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':user}],
                    'stream':False,'think':False,'options':report['settings'],'keep_alive':'2m'}
                if args.schema:
                    body['format']={'type':'object','properties':{'action':{'type':'string','enum':['listen','nod','look_right','neutral']}},'required':['action'],'additionalProperties':False}
                start=time.monotonic();signal.alarm(40)
                try:
                    req=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
                    with urlopen(req,timeout=35) as response:data=response.read(1048577)
                    if len(data)>1048576:raise ValueError('oversized response')
                    raw=json.loads(data);text=raw.get('message',{}).get('content','')
                    fixed,changed=normalize_single_json_fence(text)
                    row.update(content=text,strict_match=match(text,expected),repaired_match=match(fixed,expected),format_repaired=changed,
                               done_reason=raw.get('done_reason'),thinking_present=bool(raw.get('message',{}).get('thinking')))
                    for key in ['load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration']:row[key]=raw.get(key)
                except Exception as exc:row['error_type']=type(exc).__name__
                finally:signal.alarm(0);row['wall_seconds']=time.monotonic()-start;save()
                print(json.dumps({k:v for k,v in row.items() if k!='content'}),flush=True)
                if 'error_type' in row:return

if __name__=='__main__':main()

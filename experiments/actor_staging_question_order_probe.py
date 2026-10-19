"""Controlled cue-query field order diagnostic; observed cases, not holdouts."""
import hashlib,json,time
from pathlib import Path
from harness2.bounded_json_http import request_json
from harness2.actor_staging_steps import CUE_SCHEMA
from experiments.actor_staging_steps_probe import COMMON,CUE,MODELS
from experiments.dance_visual_probe import NATIVE_KEYS


def main():
    path=Path('evidence/actor-staging-question-order-v1.json')
    if path.exists():raise ValueError('refusing overwrite')
    source=Path('evidence/actor-staging-steps-v1.json');prior=json.loads(source.read_text())
    if not prior.get('complete'):raise ValueError('main comparison still running/incomplete')
    cases=prior['cases'][:2];report={'scope':'Prompt-field-order diagnostic on two observed cases and later cues; not new heldout or whole-plan success.',
      'prior_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'models':prior['models'],'max_calls':16,'calls':[]}
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for mi,model in enumerate(MODELS):
        for ci,case in enumerate(cases):
            for slot,ordinal in [(1,'second/middle'),(2,'third/final')]:
                question=f'Return only chronological slot {slot}, the {ordinal} cue. Apply any amendments affecting this cue.'
                early={'question':question,'request':case['request'],'scene':case['scene']}
                late={'request':case['request'],'scene':case['scene'],'question':question}
                # Keep nested scene order exactly as sort_keys used in the main probe.
                early=json.loads(json.dumps(early,sort_keys=True));late={k:early[k] for k in ['request','scene','question']}
                orders=['early','late'] if (mi+ci+slot)%2 else ['late','early']
                for order in orders:
                    user=json.dumps(early if order=='early' else late)
                    system=COMMON+'\n'+CUE;row={'model':model,'case_id':case['id'],'slot':slot,'order':order,'user':user,'system':system}
                    started=time.monotonic()
                    try:
                        raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user}],
                          'stream':False,'think':False,'format':CUE_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':64},'keep_alive':'2m'},timeout=20)
                        row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS})
                        value=json.loads(raw.get('message',{}).get('content',''));expected=case['expected']['cues'][slot]
                        row['correct']=raw.get('done_reason')=='stop' and value=={'actor':expected['actor_id'],'gesture':expected['gesture'],'variation':expected['variation']}
                    except Exception as exc:row.update(error_type=type(exc).__name__,correct=False)
                    row['wall_seconds']=time.monotonic()-started;report['calls'].append(row);save()
                    print(json.dumps({k:row[k] for k in ['model','case_id','slot','order','correct','wall_seconds']}),flush=True)
    report['complete']=True;save()

if __name__=='__main__':main()

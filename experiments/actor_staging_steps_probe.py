"""Matched one-shot versus four-question local staging comparison on reused cases."""
import hashlib
import json
from pathlib import Path
import time
from urllib.request import urlopen
from harness2.actor_staging import compile_staging
from harness2.actor_staging_compact import bind_scene,compile_compact
from harness2.actor_staging_steps import assemble_staging,PLACEMENT_SCHEMA,CUE_SCHEMA
from harness2.actor_staging_h2 import PUBLIC_CONTRACT
from harness2.bounded_json_http import request_json
from experiments.actor_staging_compact_probe import COMPACT_SCHEMA
from experiments.dance_visual_probe import NATIVE_KEYS

MODELS=['gemma4:e2b','hermes-lab-qwen3-8b:latest']
COMMON='Read the scene and request carefully. Apply the final amendments in the request. Resolve screen sides independently of chronological cue order. Use exact scene actor IDs. Return only the requested strict JSON.'
PLACE='Answer only the placement question: which actor is on screen-left? Return exactly {"left":"actorID"}. The other actor will be screen-right. Do not output any cues.'
CUE='Answer only the requested chronological cue. Return exactly {"actor":"actorID","gesture":"wave|nod|neutral","variation":"soft|clear"}, choosing one allowed gesture and variation. Do not output side assignments or other cues.'


def main():
    path=Path('evidence/actor-staging-steps-v1.json')
    if path.exists():raise ValueError('refusing overwrite')
    prior_path=Path('evidence/actor-staging-h2-v2.json');prior=json.loads(prior_path.read_text())
    cases=prior['frozen_evaluation']
    expected={c['id']:compile_staging(json.dumps({'scene_revision':c['scene']['revision'],**c['expected']}),c['scene']) for c in cases}
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    paths=['harness2/actor_staging_steps.py','harness2/actor_staging_compact.py','harness2/bounded_json_http.py','experiments/actor_staging_steps_probe.py']
    report={'scope':'Manual task-decomposition comparison, not learned adaptation. Twelve already-observed cases; no new holdout/generalization claim.',
        'prior_source_sha256':hashlib.sha256(prior_path.read_bytes()).hexdigest(),'cases':cases,
        'sources':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        'models':{m:{k:next(x for x in tags if x['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
        'common_guidance':COMMON,'max_calls':120,'calls':[],'results':[],
        'design':'Models sequential; condition order alternates by case and reverses by model. Four independent requests repeat full scene/request, without previous model answers or expected plans. No correction calls. Shared amendment/chronology guidance differs from prior H2 baseline; compare matched conditions here.',
        'api_cost_usd':None,'local_hardware_cost':'unmeasured'}
    calls=report['calls'];errors=0
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    def call(model,case,part,system,user,schema):
        nonlocal errors
        if len(calls)>=120 or errors>=2:raise RuntimeError('call/error budget exhausted')
        row={'model':model,'case_id':case['id'],'part':part,'system':system,'user':user,
             'input_text_characters':len(system)+len(user),'options':{'temperature':0,'num_ctx':4096,'num_predict':128 if part=='full' else 64}}
        start=time.monotonic()
        try:
            raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user}],
                'stream':False,'think':False,'format':schema,'options':row['options'],'keep_alive':'2m'},timeout=20)
            row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','')
            row['complete']=raw.get('done_reason')=='stop';errors=0
        except Exception as exc:row['error_type']=type(exc).__name__;row['complete']=False;errors+=1
        finally:
            row['wall_seconds']=time.monotonic()-start;calls.append(row);save()
        return len(calls)-1,row
    try:
        for mi,model in enumerate(MODELS):
            for ci,c in enumerate(cases):
                snapshot=bind_scene(c['scene']);public={'scene':c['scene'],'request':c['request']}
                order=['one_shot','four_questions'] if (mi+ci)%2==0 else ['four_questions','one_shot']
                for condition in order:
                    result={'model':model,'case_id':c['id'],'condition':condition,'call_indices':[]};report['results'].append(result)
                    start=time.monotonic()
                    if condition=='one_shot':
                        idx,row=call(model,c,'full',COMMON+'\n'+PUBLIC_CONTRACT,json.dumps(public,sort_keys=True),COMPACT_SCHEMA);result['call_indices'].append(idx)
                        try:
                            if not row['complete']:raise ValueError('incomplete response')
                            plan=compile_compact(row['content'],snapshot,c['scene']);result['compiled']=True;result['semantic_correct']=plan==expected[c['id']];result['plan']=plan
                        except (ValueError,TypeError) as exc:result.update(compiled=False,semantic_correct=False,reason=str(exc))
                    else:
                        idx,row=call(model,c,'placement',COMMON+'\n'+PLACE,json.dumps(public,sort_keys=True),PLACEMENT_SCHEMA);result['call_indices'].append(idx)
                        placement=row['content'] if row.get('complete') else '';cue_raws=[]
                        for slot,ordinal in enumerate(['first/opening','second/middle','third/final']):
                            prompt=dict(public,question=f'Return only chronological slot {slot}, the {ordinal} cue. Apply any amendments affecting this cue.')
                            idx,row=call(model,c,f'cue_{slot}',COMMON+'\n'+CUE,json.dumps(prompt,sort_keys=True),CUE_SCHEMA);result['call_indices'].append(idx)
                            cue_raws.append(row['content'] if row.get('complete') else '')
                        try:
                            plan=assemble_staging(placement,cue_raws,snapshot,c['scene']);result['compiled']=True;result['semantic_correct']=plan==expected[c['id']];result['plan']=plan
                        except (ValueError,TypeError) as exc:result.update(compiled=False,semantic_correct=False,reason=str(exc))
                    result['wall_seconds']=time.monotonic()-start;save()
                    print(json.dumps({k:result[k] for k in ['model','case_id','condition','compiled','semantic_correct','wall_seconds']}),flush=True)
        report['complete']=True
    except Exception as exc:report['error_type']=type(exc).__name__
    finally:save();print(json.dumps({'complete':report.get('complete',False),'calls':len(calls),'error':report.get('error_type')}),flush=True)

if __name__=='__main__':main()

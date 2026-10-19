"""Local scene planning, bounded correction and separately injected repair trial."""
import copy
import hashlib
import json
from pathlib import Path
import time
from urllib.request import urlopen
from harness2.actor_staging import compile_staging
from experiments.actor_staging_cases import CASES
from experiments.dance_visual_probe import _ollama_call, NATIVE_KEYS

MODELS=['gemma4:e2b','hermes-lab-qwen3-8b:latest']
SCHEMA={'type':'object','required':['scene_revision','placements','cues'],'additionalProperties':False,
 'properties':{'scene_revision':{'type':'string'},'placements':{'type':'array','minItems':2,'maxItems':2,
  'items':{'type':'object','required':['actor_id','anchor_id','side'],'additionalProperties':False,'properties':{
    'actor_id':{'type':'string'},'anchor_id':{'type':'string'},'side':{'type':'string','enum':['left','right']}}}},
 'cues':{'type':'array','minItems':3,'maxItems':3,'items':{'type':'object','required':['slot','actor_id','gesture','variation'],
 'additionalProperties':False,'properties':{'slot':{'type':'integer','enum':[0,1,2]},'actor_id':{'type':'string'},
 'gesture':{'type':'string','enum':['wave','nod','neutral']},'variation':{'type':'string','enum':['soft','clear']}}}}}}
SYSTEM='Plan a six-second two-actor scene. Return strict JSON only. Use exact scene identities and revision. Place one actor on each side of the anchor. Choose three numbered gesture cues matching the request; each lasts two seconds. Actors stay planted. Host code owns coordinates, timing and rendering. Each cue has slot, actor_id, gesture (wave/nod/neutral), variation (soft/clear). Each placement has actor_id, anchor_id, side (left/right). Root fields: scene_revision, placements, cues. No other fields.'


def verdict(raw,case):
    try:
        compiled=compile_staging(raw,case['scene'])
    except (ValueError,TypeError) as exc:return {'compiled':False,'semantic_correct':False,'reason':str(exc)}
    value=json.loads(raw)
    same=lambda a,b,key:sorted(a,key=lambda x:x[key])==sorted(b,key=lambda x:x[key])
    correct=same(value['placements'],case['expected']['placements'],'actor_id') and same(value['cues'],case['expected']['cues'],'slot')
    return {'compiled':True,'semantic_correct':correct,'reason':None if correct else 'The placements or cues do not match the user request. Re-read actor, side, order and variation.', 'plan':compiled}


def main():
    work=Path('/Users/adom/Development/hermes-testing/runs/harness2-actor-staging-v1')
    evidence=Path('evidence/actor-staging-v1.json')
    if work.exists() or evidence.exists():raise ValueError('refusing overwrite')
    work.mkdir()
    for case in CASES:compile_staging(json.dumps({'scene_revision':case['scene']['revision'],**case['expected']}),case['scene'])
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    metadata={m:{k:next(x for x in tags if x['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS}
    rows=[];report={'scope':'local multi-cue scene planning and bounded repair; no adaptation, walking or taste claim','models':metadata,
        'fixture_sha256':hashlib.sha256(Path('experiments/actor_staging_cases.py').read_bytes()).hexdigest(),
        'sources':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['harness2/actor_staging.py','experiments/actor_staging_probe.py']},
        'schema':SCHEMA,'cases':CASES,'calls':rows,'max_calls':18,'api_cost_usd':None,'local_hardware_cost':'unmeasured'}
    def save():evidence.write_text(json.dumps(report,indent=2)+'\n')
    save();failed_transport=0;demo=None
    def call(model,case,messages,kind):
        nonlocal failed_transport
        if len(rows)>=18:raise ValueError('call cap')
        body={'model':model,'messages':messages,'stream':False,'think':False,'format':SCHEMA,
            'options':{'temperature':0,'num_ctx':4096,'num_predict':384},'keep_alive':'2m'}
        row={'model':model,'case_id':case['id'],'kind':kind,'messages':messages,'input_text_characters':sum(len(m['content']) for m in messages),'options':body['options']}
        start=time.monotonic()
        try:
            raw=_ollama_call(body);row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS})
            content=raw.get('message',{}).get('content','');row['verdict']=verdict(content,case) if raw.get('done_reason')=='stop' else {'semantic_correct':False,'compiled':False,'reason':'incomplete native response'}
            failed_transport=0
        except Exception as exc:row.update(error_type=type(exc).__name__,verdict={'semantic_correct':False,'compiled':False,'reason':'transport failure'});failed_transport+=1
        finally:row['wall_seconds']=time.monotonic()-start;rows.append(row);save()
        return row
    for model in MODELS:
        accepted_first=None
        for case in CASES:
            messages=[{'role':'system','content':SYSTEM},{'role':'user','content':'Scene: '+json.dumps(case['scene'])+'\nRequest: '+case['request']}]
            row=call(model,case,messages,'first')
            if failed_transport>=2:return
            if not row['verdict']['semantic_correct'] and not row.get('error_type'):
                content=row['raw_response'].get('message',{}).get('content','')
                row=call(model,case,messages+[{'role':'assistant','content':content},{'role':'user','content':'Validation feedback: '+row['verdict']['reason']+' Return a corrected complete JSON plan.'}],'bounded_correction')
                if failed_transport>=2:return
            if row['verdict']['semantic_correct']:
                plan=row['verdict']['plan'];slug=model.replace(':','-').replace('/','-')+'--'+case['id']
                (work/(slug+'.json')).write_text(json.dumps(plan,indent=2)+'\n')
                if accepted_first is None:accepted_first=(case,messages,row)
                if demo is None:demo={'path':str(work/(slug+'.json')),'case':case['id'],'model':model,'call_index':len(rows)-1}
        if accepted_first:
            case,messages,accepted=accepted_first
            original=json.loads(accepted['raw_response']['message']['content'])
            broken=copy.deepcopy(original);broken['cues'][0]['actor_id']='missing_actor'
            try:compile_staging(json.dumps(broken),case['scene']);raise RuntimeError('injection not rejected')
            except ValueError as exc:feedback=str(exc)
            row=call(model,case,messages+[{'role':'assistant','content':json.dumps(broken)},{'role':'user','content':'A test deliberately corrupted one cue actor_id. Validator: '+feedback+'. Repair only that invalid actor_id. Preserve every other value and array order. Return the complete JSON.'}],'injected_invalid_actor_repair')
            try:repaired=json.loads(row['raw_response']['message']['content']);preserved=repaired==original
            except (KeyError,ValueError):preserved=False
            row['injected_repair']={'injected_not_natural_failure':True,'unchanged_other_values_and_expected_id':preserved,'broken_proposal':broken};save()
    report.update(complete=True,demo=demo);save();print(json.dumps({'demo':demo,'calls':[{k:r.get(k) for k in ['model','case_id','kind','wall_seconds','prompt_eval_count','eval_count']}|{'accepted':r['verdict']['semantic_correct'],'repair':r.get('injected_repair',{}).get('unchanged_other_values_and_expected_id')} for r in rows]},indent=2))

if __name__=='__main__':main()

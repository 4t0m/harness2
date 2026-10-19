"""Balanced local comparison of equivalent full and compact staging protocols.

Reuses observed cases: interface regression, not unseen generalization or H2 learning.
"""
import copy
import hashlib
import json
import itertools
from pathlib import Path
import time
from urllib.request import urlopen

from harness2.actor_staging import compile_staging
from harness2.actor_staging_compact import bind_scene, compile_compact
from experiments.actor_staging_cases import CASES
from experiments.actor_staging_probe import MODELS, SCHEMA as FULL_SCHEMA, SYSTEM as FULL_SYSTEM
from experiments.dance_visual_probe import _ollama_call, NATIVE_KEYS

COMPACT_SCHEMA = {
    'type':'object', 'required':['left','cues'], 'additionalProperties':False,
    'properties':{
        'left':{'type':'string'},
        'cues':{'type':'array','minItems':3,'maxItems':3,
                'items':{'type':'array','minItems':3,'maxItems':3,'items':{'type':'string'}}}}}
COMPACT_SYSTEM = (
    'Plan a six-second two-actor scene. Return strict JSON only: '
    '{"left":"actorID","cues":[["actorID","gesture","variation"],...three cues]}. '
    'Use exact scene actor IDs. left names the screen-left actor; the other is screen-right. '
    'The cues array is chronological: first, second, third (slots 0, 1, 2). '
    'Each cue is exactly [actorID,gesture,variation]. Gesture: wave/nod/neutral. '
    'Variation: soft/clear. Match the request. Host code binds scene revision, anchor, '
    'coordinates and two-second timing. Actors stay planted. No other fields.')


def expected_plan(case):
    return compile_staging(json.dumps({'scene_revision':case['scene']['revision'], **case['expected']}),case['scene'])


def check(raw, case, protocol, snapshot):
    try:
        plan = (compile_compact(raw,snapshot,case['scene']) if protocol=='compact'
                else compile_staging(raw,case['scene']))
    except (ValueError,TypeError) as exc:
        return {'compiled':False,'semantic_correct':False,'reason':str(exc)}
    correct = plan == expected_plan(case)
    return {'compiled':True,'semantic_correct':correct,'plan':plan,
            'reason':None if correct else 'Plan does not match the request. Re-read actor, side, cue order and variation.'}


def equivalence_check():
    checked=0
    for case in CASES:
        scene=case['scene']; snapshot=bind_scene(scene)
        choices=list(itertools.product(scene['actor_ids'],['wave','nod','neutral'],['soft','clear']))
        for left in scene['actor_ids']:
            right=next(a for a in scene['actor_ids'] if a!=left)
            for cues in itertools.product(choices,repeat=3):
                compact={'left':left,'cues':cues}
                full={'scene_revision':scene['revision'],
                      'placements':[{'actor_id':a,'anchor_id':scene['anchor']['id'],'side':side}
                                    for a,side in [(left,'left'),(right,'right')]],
                      'cues':[dict(slot=i,actor_id=c[0],gesture=c[1],variation=c[2]) for i,c in enumerate(cues)]}
                if compile_compact(json.dumps(compact),snapshot,scene)!=compile_staging(json.dumps(full),scene):
                    raise AssertionError('compact representation changed a canonical plan')
                checked+=1
    return {'canonical_equal_plans':checked,'scope':'All two-side assignments and all three-cue actor/gesture/variation combinations for four scene fixtures.'}


def main():
    path = Path('evidence/actor-staging-compact-v1.json')
    if path.exists():raise ValueError('refusing overwrite')
    for case in CASES:expected_plan(case)
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as response: tags=json.load(response)['models']
    paths=['harness2/actor_staging.py','harness2/actor_staging_compact.py',
           'experiments/actor_staging_compact_probe.py','experiments/actor_staging_probe.py',
           'experiments/actor_staging_cases.py']
    report={
        'scope':'Reused-fixture balanced full/compact local interface comparison; no learning, render or generalization claim.',
        'sources':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        'models':{m:{k:next(x for x in tags if x['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
        'schemas':{'full':FULL_SCHEMA,'compact':COMPACT_SCHEMA},'cases':CASES,
        'equivalence_check':equivalence_check(),
        'max_calls':32,'max_consecutive_transport_errors':2,'api_cost_usd':None,
        'local_hardware_cost':'unmeasured','calls':[],
        'design':'Models sequential, cases fixed, protocol order alternates within each model and reverses for next model; one sample per cell. Corrections immediate. Cold load and prefix cache confounding retained in timings.'}
    rows=report['calls']; errors=0
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    def call(model,case,protocol,messages,kind,snapshot):
        nonlocal errors
        if len(rows)>=32:raise ValueError('call cap')
        body={'model':model,'messages':messages,'stream':False,'think':False,
              'format':COMPACT_SCHEMA if protocol=='compact' else FULL_SCHEMA,
              'options':{'temperature':0,'num_ctx':4096,'num_predict':384},'keep_alive':'2m'}
        row={'model':model,'case_id':case['id'],'protocol':protocol,'kind':kind,
             'messages':copy.deepcopy(messages),'input_text_characters':sum(len(m['content']) for m in messages),
             'options':body['options']}
        start=time.monotonic()
        try:
            raw=_ollama_call(body);row['raw_response']=raw
            row.update({k:raw.get(k) for k in NATIVE_KEYS})
            content=raw.get('message',{}).get('content','')
            row['verdict']=(check(content,case,protocol,snapshot) if raw.get('done_reason')=='stop'
                            else {'compiled':False,'semantic_correct':False,'reason':'incomplete native response'})
            errors=0
        except Exception as exc:
            row.update(error_type=type(exc).__name__,verdict={'compiled':False,'semantic_correct':False,'reason':'transport failure'})
            errors+=1
        finally:
            row['wall_seconds']=time.monotonic()-start;rows.append(row);save()
        print(json.dumps({k:row.get(k) for k in ['model','case_id','protocol','kind','wall_seconds','prompt_eval_count','eval_count']}|{'accepted':row['verdict']['semantic_correct']}),flush=True)
        return row
    for mi,model in enumerate(MODELS):
        for ci,case in enumerate(CASES):
            snapshot=bind_scene(case['scene'])
            protocols=['full','compact'] if (mi+ci)%2==0 else ['compact','full']
            for protocol in protocols:
                messages=[{'role':'system','content':COMPACT_SYSTEM if protocol=='compact' else FULL_SYSTEM},
                          {'role':'user','content':'Scene: '+json.dumps(case['scene'])+'\nRequest: '+case['request']}]
                row=call(model,case,protocol,messages,'first',snapshot)
                if errors>=2:report['stop_reason']='consecutive transport failures';save();return
                if not row['verdict']['semantic_correct'] and not row.get('error_type'):
                    messages += [{'role':'assistant','content':row['raw_response'].get('message',{}).get('content','')},
                                 {'role':'user','content':'Validation feedback: '+row['verdict']['reason']+' Return a corrected complete JSON plan.'}]
                    call(model,case,protocol,messages,'bounded_correction',snapshot)
                    if errors>=2:report['stop_reason']='consecutive transport failures';save();return
    report['complete']=True;save()

if __name__=='__main__': main()

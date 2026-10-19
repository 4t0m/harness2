"""Bounded local phrase planning with one correction; fixtures frozen before calls."""
import hashlib,itertools,json,time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from experiments.dance_visual_probe import NATIVE_KEYS

MODELS=['gemma4:e2b','hermes-lab-qwen3-8b:latest']
NAMES=['rise','sway','pulse','settle','hold'];VARIATIONS=['soft','clear']
BOUNDARIES={'rise':('rest','open'),'sway':('open','open'),'pulse':('open','open'),'settle':('open','rest'),'hold':('rest','rest')}
SYSTEM='''Plan a short procedural dance from this exact catalog. Every move lasts two beats, at 120 BPM. Choose exactly four moves for eight beats. Start and finish at rest. Each move must start in the previous move's ending pose. Catalog: rise rest->open; sway open->open; pulse open->open; settle open->rest; hold rest->rest. Every move has soft and clear variations, which do not change its boundary pose. Follow the user's requested order and variations, including final amendments. Return only strict JSON {"moves":[["move_id","soft|clear"], ...]}. Use exact catalog identifiers and variation words. No extra fields, explanations, invented moves, coordinates or timings.'''
SCHEMA={'type':'object','properties':{'moves':{'type':'array','minItems':4,'maxItems':4,'items':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'string','enum':NAMES+VARIATIONS}}}},'required':['moves'],'additionalProperties':False}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def feasible_choices():
    for moves in itertools.product(list(itertools.product(NAMES,VARIATIONS)),repeat=4):
        state='rest'
        for name,variation in moves:
            entry,exit=BOUNDARIES[name]
            if entry!=state:break
            state=exit
        else:
            if state=='rest':yield [list(p) for p in moves]


def main():
    # APIs supplied by independent compiler/fixture authors; imported only once ready.
    from harness2.dance_phrases import compile_plan
    from experiments.dance_phrase_cases import CASES,INFEASIBLE_CASES,score_plan
    path=Path('evidence/dance-phrase-model-v1.json')
    if path.exists():raise ValueError('refusing overwrite')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as response:tags=json.load(response)['models']
    feasible=list(feasible_choices())
    counts={c['id']:sum(not score_plan(m,c) for m in feasible) for c in CASES}
    for c in CASES:
        if c.get('feasible',True)!=(counts[c['id']]>0):raise ValueError('fixture feasibility mismatch: '+c['id'])
    impossible_counts={c['id']:sum(not score_plan(m,c) for m in feasible) for c in INFEASIBLE_CASES}
    if any(impossible_counts.values()):raise ValueError('infeasible fixture has solution')
    source_paths=['harness2/dance_phrases.py','experiments/dance_phrase_cases.py','experiments/dance_phrase_probe.py','harness2/bounded_json_http.py']
    report={'scope':'Fixed planner and one bounded correction on independently authored new briefs. Not H2 learning, taste judgment, or production semantic verification.',
      'sources':{p:digest(p) for p in source_paths},'models':{m:{k:next(t for t in tags if t['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
      'cases':CASES,'infeasible_cases_offline_only':INFEASIBLE_CASES,'infeasible_solution_counts':impossible_counts,'feasible_plan_counts':counts,'catalog_structurally_valid_plans':len(feasible),'schema':SCHEMA,'system':SYSTEM,
      'max_calls':32,'max_seconds_per_call':20,'max_output_tokens':128,'provider_calls_paid':0,
      'repair_policy':'Compiler errors returned verbatim. For structurally valid semantic failure, generic reminder only. Experimental oracle triggers repair; arbitrary prose mismatch detection is not a deployed capability.',
      'calls':[],'results':[]}
    errors=0
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for mi,model in enumerate(MODELS):
            cases=[c for c in CASES if c.get('feasible',True)]
            if mi%2:cases=list(reversed(cases))
            for case in cases:
                messages=[{'role':'system','content':SYSTEM},{'role':'user','content':case['request']}]
                result={'model':model,'case_id':case['id'],'attempts':[]};report['results'].append(result)
                for attempt in range(2):
                    if len(report['calls'])>=32 or errors>=2:raise RuntimeError('call/error budget exhausted')
                    row={'model':model,'case_id':case['id'],'attempt':attempt,'messages':list(messages),'input_text_characters':sum(len(x['content']) for x in messages)}
                    started=time.monotonic()
                    try:
                        raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':messages,'stream':False,'think':False,'format':SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
                        row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','');errors=0
                        if raw.get('done_reason')!='stop':raise ValueError('incomplete response')
                        plan=compile_plan(row['content']);row['compiled']=True
                        # Host-only acceptance predicate. No expected constraints are sent to model.
                        choices=[[m['id'],m['variation']] for m in plan['moves']]
                        row['violations']=score_plan(choices,case);row['correct']=not row['violations'];row['moves']=choices
                        row['motion_receipt']=plan['receipt']
                    except Exception as exc:
                        if 'raw_response' not in row:errors+=1
                        row.update(error_type=type(exc).__name__,reason=str(exc),correct=False)
                    row['wall_seconds']=time.monotonic()-started;result['attempts'].append(len(report['calls']));report['calls'].append(row);save()
                    print(json.dumps({k:row.get(k) for k in ['model','case_id','attempt','compiled','correct','reason','wall_seconds']}),flush=True)
                    if row['correct']:break
                    if row.get('compiled'):feedback='The plan does not fully follow the brief. Re-read the original request, including order and final amendments, and return the corrected plan.'
                    else:feedback='The plan was rejected: '+row.get('reason','invalid response')+'. Return a corrected plan following the original request and catalog.'
                    messages += [{'role':'assistant','content':row.get('content','')},{'role':'user','content':feedback}]
                result['first_correct']=report['calls'][result['attempts'][0]]['correct'];result['final_correct']=report['calls'][result['attempts'][-1]]['correct'];save()
        report['complete']=True
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:save();print(json.dumps({'complete':report.get('complete'),'calls':len(report['calls'])}),flush=True)

if __name__=='__main__':main()

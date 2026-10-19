"""Bounded hosted phrase planning with one correction; fixtures frozen before calls."""
import hashlib,itertools,json,time,math
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from experiments.dance_visual_probe import NATIVE_KEYS

MODELS=['qwen/qwen3.6-35b-a3b','qwen/qwen3.6-27b','google/gemma-4-26b-a4b-it','google/gemma-4-31b-it']
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
    path=Path('evidence/dance-phrase-hosted-v1.json')
    if path.exists():raise ValueError('refusing overwrite')
    with urlopen('https://openrouter.ai/api/v1/models',timeout=15) as response:tags=json.load(response)['data']
    metadata={m:next(t for t in tags if t['id']==m) for m in MODELS}
    if any(float(t['pricing']['prompt'])>1e-6 or float(t['pricing']['completion'])>3e-6 for t in metadata.values()):raise ValueError('price listing exceeds cap')
    feasible=list(feasible_choices())
    counts={c['id']:sum(not score_plan(m,c) for m in feasible) for c in CASES}
    for c in CASES:
        if c.get('feasible',True)!=(counts[c['id']]>0):raise ValueError('fixture feasibility mismatch: '+c['id'])
    impossible_counts={c['id']:sum(not score_plan(m,c) for m in feasible) for c in INFEASIBLE_CASES}
    if any(impossible_counts.values()):raise ValueError('infeasible fixture has solution')
    source_paths=['harness2/dance_phrases.py','experiments/dance_phrase_cases.py','experiments/dance_phrase_hosted_probe.py','experiments/dance_phrase_probe.py','harness2/bounded_json_http.py']
    report={'scope':'Fixed planner and one bounded correction on independently authored new briefs. Not H2 learning, taste judgment, or production semantic verification.',
      'sources':{p:digest(p) for p in source_paths},'models':{m:{k:t.get(k) for k in ['id','name','pricing','architecture','supported_parameters']} for m,t in metadata.items()},
      'cases':CASES,'infeasible_cases_offline_only':INFEASIBLE_CASES,'infeasible_solution_counts':impossible_counts,'feasible_plan_counts':counts,'catalog_structurally_valid_plans':len(feasible),'schema':SCHEMA,'system':SYSTEM,
      'max_calls':64,'max_seconds_per_call':30,'max_output_tokens':128,'reported_cost_stop_usd':.25,'price_caps_per_million':{'prompt':1,'completion':3},'reported_cost_usd':0,'provider_calls_paid':0,
      'repair_policy':'Compiler errors returned verbatim. For structurally valid semantic failure, generic reminder only. Experimental oracle triggers repair; arbitrary prose mismatch detection is not a deployed capability.',
      'calls':[],'results':[]}
    errors=0;paid=0.0
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
                    if len(report['calls'])>=64 or errors>=2 or paid>=.25 or report.get('cost_unknown'):raise RuntimeError('call/error/cost budget exhausted')
                    if sum(len(x['content'].encode()) for x in messages)>4096:raise ValueError('context byte cap')
                    row={'model':model,'case_id':case['id'],'attempt':attempt,'messages':list(messages),'input_text_characters':sum(len(x['content']) for x in messages)}
                    started=time.monotonic()
                    try:
                        body={'model':model,'messages':messages,'temperature':0,'max_tokens':128,'reasoning':{'enabled':False},'provider':{'max_price':{'prompt':1,'completion':3}},'response_format':{'type':'json_schema','json_schema':{'name':'dance_plan','strict':True,'schema':SCHEMA}}}
                        report['provider_calls_paid']+=1
                        raw=request_json('https://openrouter.ai/api/v1/chat/completions',body,timeout=30,bearer_env='OPENROUTER_API_KEY')
                        row['raw_response']=raw;row['usage']=raw.get('usage',{});cost=row['usage'].get('cost');row['reported_cost_usd']=cost
                        if type(cost) not in (float,int) or not math.isfinite(cost) or cost<0:report['cost_unknown']=True
                        else:paid+=cost;report['reported_cost_usd']=paid
                        choice=raw.get('choices',[{}])[0];row['content']=choice.get('message',{}).get('content','');errors=0
                        if choice.get('finish_reason')!='stop':raise ValueError('incomplete response')
                        plan=compile_plan(row['content']);row['compiled']=True
                        # Host-only acceptance predicate. No expected constraints are sent to model.
                        choices=[[m['id'],m['variation']] for m in plan['moves']]
                        row['violations']=score_plan(choices,case);row['correct']=not row['violations'];row['moves']=choices
                        row['motion_receipt']=plan['receipt']
                    except Exception as exc:
                        if 'raw_response' not in row:
                            errors+=1;report['cost_unknown']=True
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

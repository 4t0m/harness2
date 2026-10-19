"""Fresh structured staging tasks with host feasibility and bounded repair."""
import json, hashlib, time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from experiments.dance_steps_contract_probe import EXPLICIT, ENUM_SCHEMA
from experiments.dance_steps_probe import MODELS
from experiments.dance_visual_probe import NATIVE_KEYS

SYSTEM=EXPLICIT+' The approved task uses integer millimetres in world x. Each step_left changes x by -200 mm and step_right by +200 mm. Start at start_x_mm and finish at target_x_mm. Keep the root within the inclusive root_bounds_mm throughout. required_moves and required_variations map zero-based slot strings to required identifiers. Empty maps leave those choices free. All task fields are authoritative. Do not emit coordinates; output the four move/variation pairs only.'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    from harness2.dance_step_task import feasible_plans,compile_task,verify_task
    from experiments.dance_step_task_cases import CASES
    output=Path('evidence/dance-step-task-model-v1.json')
    if output.exists():raise ValueError('refusing overwrite')
    preflight=[]
    for c in CASES:
        plans=feasible_plans(c['task'])
        if bool(plans)!=c['feasible']:raise ValueError('fixture feasibility mismatch: '+c['id'])
        preflight.append({'id':c['id'],'supported':bool(plans),'feasible_plan_count':len(plans),'provider_calls_if_unsupported':0})
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    paths=['harness2/dance_step_task.py','harness2/dance_steps.py','harness2/dance_motion.py','experiments/dance_step_task_cases.py','experiments/dance_step_task_probe.py','experiments/dance_steps_contract_probe.py','harness2/bounded_json_http.py']
    report={'scope':'New structured step tasks with explicit approved constraints. Any satisfying plan accepted. Model does not extract authoritative constraints from prose. Fixed first pass versus one host-feedback repair; not H2 learning or live avatar execution.',
      'sources':{p:digest(p) for p in paths},'cases':CASES,'preflight':preflight,'system':SYSTEM,'schema':ENUM_SCHEMA,
      'models':{m:{k:next(t for t in tags if t['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
      'max_calls':32,'max_seconds_per_call':20,'max_output_tokens':128,'paid_provider_calls':0,'repair_policy':'One attempt after compiler/task rejection; feedback reports violated public constraint only, never an enumerated solution. No call for preflight infeasible tasks.','calls':[],'results':[]}
    errors=0
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for mi,model in enumerate(MODELS):
            cases=[c for c in CASES if c['feasible']]
            if mi:cases=list(reversed(cases))
            for c in cases:
                messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'task':c['task'],'request':c['request']},sort_keys=True)}]
                result={'model':model,'case_id':c['id'],'call_indices':[]};report['results'].append(result)
                for attempt in range(2):
                    if len(report['calls'])>=32:raise RuntimeError('call cap')
                    row={'model':model,'case_id':c['id'],'attempt':attempt,'messages':list(messages),'input_text_characters':sum(len(m['content']) for m in messages)};start=time.monotonic()
                    try:
                        raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':messages,'stream':False,'think':False,'format':ENUM_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
                        row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','');errors=0
                        if raw.get('done_reason')!='stop':raise RuntimeError('incomplete response')
                        compiled=compile_task(row['content'],c['task']);verify_task(compiled,c['task']);row['accepted']=True;row['receipt']=compiled['receipt'];row['placement']=compiled['placement'];row['moves']=json.loads(row['content'])['moves']
                    except Exception as exc:
                        if 'raw_response' not in row:errors+=1
                        row.update(accepted=False,error_type=type(exc).__name__,reason=str(exc))
                    row['wall_seconds']=time.monotonic()-start;result['call_indices'].append(len(report['calls']));report['calls'].append(row);save()
                    print(json.dumps({k:row.get(k) for k in ['model','case_id','attempt','accepted','reason','wall_seconds']}),flush=True)
                    if row['accepted'] or errors or row.get('error_type')!='ValueError':break
                    messages += [{'role':'assistant','content':row['content']},{'role':'user','content':'Host rejected the plan: '+row['reason']+'. Re-read the approved task and return a corrected four-pair plan.'}]
                result['first_accepted']=report['calls'][result['call_indices'][0]]['accepted'];result['final_accepted']=report['calls'][result['call_indices'][-1]]['accepted'];save()
                if errors>=2:raise RuntimeError('transport error cap')
        report['complete']=True
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:save()

if __name__=='__main__':main()

"""Prompt/schema factorial diagnostic on the now-observed stepping briefs."""
import copy, hashlib, json, time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from harness2.dance_steps import compile_steps, PLAN_SCHEMA, PUBLIC_CONTRACT
from experiments.dance_steps_probe import CASES, MODELS
from experiments.dance_visual_probe import NATIVE_KEYS

SUFFIX=' World +x is right; -x is left. Each step moves the actor exactly 0.20 metres in its named direction. Start at x=0. Use exact move and variation identifiers.'
EXPLICIT='Return only a JSON object with one field named moves: an array of exactly four pairs, in chronological order. Each pair contains two strings. The first string must be step_left or step_right. The second string must be soft or clear. Choose one identifier per string, never alternatives or coordinates. Every move is a two-beat side step at 120 BPM. Each step moves the planted stance 0.20 m in its named direction. Variation changes arm/body accent, not travel distance. No other fields.'
ENUM_SCHEMA=copy.deepcopy(PLAN_SCHEMA)
ENUM_SCHEMA['properties']['moves']['items']['items']['enum']=['step_left','step_right','soft','clear']
CONDITIONS=[('explicit_free',EXPLICIT,PLAN_SCHEMA),('original_enum',PUBLIC_CONTRACT,ENUM_SCHEMA),('explicit_enum',EXPLICIT,ENUM_SCHEMA)]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    path=Path('evidence/dance-steps-contract-v1.json')
    if path.exists():raise ValueError('refusing overwrite')
    baseline=Path('evidence/dance-steps-model-v1.json');old=json.loads(baseline.read_text())
    if not old.get('complete'):raise ValueError('baseline incomplete')
    for p,h in old['sources'].items():
        if digest(p)!=h:raise ValueError('baseline source changed')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    for m in MODELS:
        if next(t for t in tags if t['name']==m)['digest']!=old['models'][m]['digest']:raise ValueError('model changed')
    paths=['harness2/dance_steps.py','harness2/dance_motion.py','experiments/dance_steps_probe.py',__file__]
    report={'scope':'Post-failure prompt/schema factorial diagnostic on observed briefs, not heldout improvement or Harness2 learning. Original/free cell reused from earlier run; remaining cells run later. No claim of isolated token-level causal mechanism.',
      'baseline_path':str(baseline),'baseline_sha256':digest(baseline),'sources':{str(p):digest(p) for p in paths},'models':old['models'],'cases':CASES,
      'conditions':{n:{'system':p+SUFFIX,'schema':s} for n,p,s in CONDITIONS},'schema_limit':'Union enum applies to both pair positions; compiler still enforces roles.',
      'max_calls':24,'max_seconds_per_call':20,'max_output_tokens':128,'paid_provider_calls':0,'calls':[]}
    errors=0
    def save():path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for mi,model in enumerate(MODELS):
            for ci,case in enumerate(CASES):
                order=CONDITIONS[ci%3:]+CONDITIONS[:ci%3]
                if mi:order=list(reversed(order))
                for condition,prompt,schema in order:
                    system=prompt+SUFFIX;row={'model':model,'case_id':case['id'],'condition':condition,'system':system,'user':case['request'],'input_text_characters':len(system)+len(case['request'])};start=time.monotonic()
                    try:
                        raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':case['request']}],'stream':False,'think':False,'format':schema,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
                        row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','');errors=0
                        if raw.get('done_reason')!='stop':raise ValueError('incomplete response')
                        compiled=compile_steps(row['content']);row['receipt']=compiled['receipt'];row['compiled']=True
                        choices=json.loads(row['content'])['moves'];row['moves']=choices;row['correct']=choices==case['expected_moves'];row['final_root_x']=compiled['sequence']['frames'][-1]['joints']['pelvis'][0]
                        row['requested_final_x_correct']=abs(row['final_root_x']-case['expected_final_x'])<1e-9
                    except Exception as exc:
                        if 'raw_response' not in row:errors+=1
                        row.update(correct=False,error_type=type(exc).__name__,reason=str(exc))
                    row['wall_seconds']=time.monotonic()-start;report['calls'].append(row);save();print(json.dumps({k:row.get(k) for k in ['model','case_id','condition','compiled','correct','reason','wall_seconds']}),flush=True)
                    if errors>=2:raise RuntimeError('transport error cap')
        report['complete']=True
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:save()

if __name__=='__main__':main()

"""Small local plan-to-stepping-motion trial; no style or physics claim."""
import hashlib,json,time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from experiments.dance_visual_probe import NATIVE_KEYS
MODELS=['gemma4:e2b','hermes-lab-qwen3-8b:latest']
CASES=[
 {'id':'alternating_soft','request':'Take four soft steps: left, right, left, right. Return to the starting position.','expected_moves':[['step_left','soft'],['step_right','soft'],['step_left','soft'],['step_right','soft']],'expected_final_x':0.0},
 {'id':'alternating_clear','request':'Take four clear steps: left, right, left, right. Return to the starting position.','expected_moves':[['step_left','clear'],['step_right','clear'],['step_left','clear'],['step_right','clear']],'expected_final_x':0.0},
 {'id':'two_left_then_two_right','request':'Step left twice, then right twice. Keep every step soft except the final right step, which is clear.','expected_moves':[['step_left','soft'],['step_left','soft'],['step_right','soft'],['step_right','clear']],'expected_final_x':0.0},
 {'id':'offset_finish','request':'Step right clearly, right softly, left softly, then right clearly. Finish 0.4 metres right of the start.','expected_moves':[['step_right','clear'],['step_right','soft'],['step_left','soft'],['step_right','clear']],'expected_final_x':0.4},
]


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    from harness2.dance_steps import compile_steps,validate_steps,PLAN_SCHEMA,PUBLIC_CONTRACT
    out=Path('evidence/dance-steps-model-v1.json')
    if out.exists():raise ValueError('refusing overwrite')
    for c in CASES:compile_steps(json.dumps({'moves':c['expected_moves']}))
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    paths=['harness2/dance_steps.py','harness2/dance_motion.py','experiments/dance_steps_probe.py']
    report={'scope':'Four simple new stepping briefs, one local attempt each; not heldout H2 adaptation, taste, or physics. Host computes relative positions and foot contacts.',
      'sources':{p:digest(p) for p in paths},'cases':CASES,'models':{m:{k:next(t for t in tags if t['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},'max_calls':8,'paid_provider_calls':0,'calls':[]}
    def save():out.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for model in MODELS:
        for case in CASES:
            system=PUBLIC_CONTRACT+' World +x is right; -x is left. Each step moves the actor exactly 0.20 metres in its named direction. Start at x=0. Use exact move and variation identifiers.'
            row={'model':model,'case_id':case['id'],'system':system,'user':case['request'],'input_text_characters':len(system)+len(case['request'])};start=time.monotonic()
            try:
                raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':case['request']}],'stream':False,'think':False,'format':PLAN_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
                row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','')
                if raw.get('done_reason')!='stop':raise ValueError('incomplete response')
                compiled=compile_steps(row['content']);row['validation']=validate_steps(compiled['sequence']);row['receipt']=compiled['receipt'];row['compiled']=True
                choices=json.loads(row['content'])['moves'];row['correct']=choices==case['expected_moves'];row['moves']=choices
                final_x=compiled['sequence']['frames'][-1]['joints']['pelvis'][0];row['final_root_x']=final_x;row['requested_final_x_correct']=abs(final_x-case['expected_final_x'])<1e-9
            except Exception as exc:row.update(correct=False,error_type=type(exc).__name__,reason=str(exc))
            row['wall_seconds']=time.monotonic()-start;report['calls'].append(row);save();print(json.dumps({k:row.get(k) for k in ['model','case_id','compiled','correct','requested_final_x_correct','reason','wall_seconds']}),flush=True)
    report['complete']=True;save()

if __name__=='__main__':main()

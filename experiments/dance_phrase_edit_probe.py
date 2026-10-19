"""Matched patch versus full-replacement local editing on frozen new briefs."""
import hashlib,json,time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from experiments.dance_visual_probe import NATIVE_KEYS

MODELS=['gemma4:e2b','hermes-lab-qwen3-8b:latest']
COMMON='''Edit the approved dance plan to follow the latest request. Change exactly one [move,variation] pair, only within permitted_slots. Keep every other pair exactly unchanged. Slots are zero-based: first=0, second=1, third=2, fourth=3. Each move lasts two beats; four moves start/end at rest. Catalog: rise rest->open; sway open->open; pulse open->open; settle open->rest; hold rest->rest. Variations are exactly soft or clear. Move boundaries must remain compatible. Apply final amendments to the request. Return only strict JSON, with no extra fields.'''
OUTPUT={'full':'Return the entire edited plan: {"moves":[["move_id","variation"], ...]} with exactly four pairs.',
        'patch':'Return only the one replacement: {"slot":0,"move":"move_id","variation":"soft|clear"}. Use the actual zero-based slot and exact values.'}


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    from harness2.dance_phrases import compile_plan
    from harness2.dance_phrase_edit import bind_source,apply_patch,validate_full_replacement,PATCH_SCHEMA,FULL_SCHEMA
    from experiments.dance_phrase_edit_cases import CASES
    out=Path('evidence/dance-phrase-edit-model-v1.json')
    if out.exists():raise ValueError('refusing overwrite')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    for case in CASES:
        a,b=case['source_moves'],case['expected_moves'];compile_plan(json.dumps({'moves':a}));compile_plan(json.dumps({'moves':b}))
        changed=[i for i in range(4) if a[i]!=b[i]]
        if len(changed)!=1 or changed[0] not in case['editable_slots']:raise ValueError('fixture scope mismatch')
    schemas={'full':FULL_SCHEMA,'patch':PATCH_SCHEMA}
    source_paths=['harness2/dance_phrases.py','harness2/dance_phrase_edit.py','experiments/dance_phrase_edit_cases.py','experiments/dance_phrase_edit_probe.py','harness2/bounded_json_http.py']
    report={'scope':'Matched protocol bundles: full replacement vs one-slot patch, each with at most one correction. Different schemas/instructions are part of the interface; not a pure wording causal test or H2 learning.',
      'cases':CASES,'sources':{p:digest(p) for p in source_paths},'schemas':schemas,
      'models':{m:{k:next(x for x in tags if x['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
      'design':'Models sequential; condition order alternates by case and reverses by model; same source/request/approved scope. Case oracle stays host-only. No mutation of source or executing motion during model calls.',
      'repair':'Compiler rejection supplied; accepted-but-wrong edit gets generic reminder. Experimental oracle triggers retries, not a production prose verifier.',
      'max_calls':64,'timeout_per_call_seconds':20,'max_output_tokens':128,'paid_provider_calls':0,'calls':[],'results':[]}
    errors=0
    def save():out.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for mi,model in enumerate(MODELS):
            for ci,case in enumerate(CASES):
                source=json.dumps({'moves':case['source_moves']});revision='approved-dance-v1';scope=case['editable_slots'];snapshot=bind_source(source,revision,scope)
                public={'source_plan':json.loads(source),'permitted_slots':scope,'request':case['request']}
                order=['full','patch'] if (mi+ci)%2==0 else ['patch','full']
                for condition in order:
                    messages=[{'role':'system','content':COMMON+'\n'+OUTPUT[condition]},{'role':'user','content':json.dumps(public,sort_keys=True)}]
                    result={'model':model,'case_id':case['id'],'condition':condition,'call_indices':[]};report['results'].append(result)
                    for attempt in range(2):
                        if len(report['calls'])>=64 or errors>=2:raise RuntimeError('call/error cap')
                        row={'model':model,'case_id':case['id'],'condition':condition,'attempt':attempt,'messages':list(messages),'input_text_characters':sum(len(m['content']) for m in messages)};start=time.monotonic()
                        try:
                            raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':messages,'stream':False,'think':False,'format':schemas[condition],'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
                            row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','');errors=0
                            if raw.get('done_reason')!='stop':raise ValueError('incomplete response')
                            fn=apply_patch if condition=='patch' else validate_full_replacement
                            edit=fn(row['content'],snapshot,source,revision,scope);row['accepted']=True;row['edit_receipt']=edit['receipt']
                            choices=[[m['id'],m['variation']] for m in edit['compiled']['moves']];row['moves']=choices;row['correct']=choices==case['expected_moves']
                        except Exception as exc:
                            if 'raw_response' not in row:errors+=1
                            row.update(correct=False,error_type=type(exc).__name__,reason=str(exc))
                        row['wall_seconds']=time.monotonic()-start;result['call_indices'].append(len(report['calls']));report['calls'].append(row);save()
                        print(json.dumps({k:row.get(k) for k in ['model','case_id','condition','attempt','accepted','correct','reason','wall_seconds']}),flush=True)
                        if row['correct']:break
                        feedback=('The edited plan does not fully follow the request. Reread the original request and approved plan, then return the correct edit.' if row.get('accepted') else 'The edit was rejected: '+row.get('reason','invalid response')+'. Return a corrected edit within the approved scope.')
                        messages += [{'role':'assistant','content':row.get('content','')},{'role':'user','content':feedback}]
                    result['first_correct']=report['calls'][result['call_indices'][0]]['correct'];result['final_correct']=report['calls'][result['call_indices'][-1]]['correct'];save()
        report['complete']=True
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:save();print(json.dumps({'complete':report.get('complete'),'calls':len(report['calls'])}),flush=True)

if __name__=='__main__':main()

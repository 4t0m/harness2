"""Frozen-policy evaluation on independently authored unseen edit briefs."""
import hashlib,json,time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from harness2.dance_phrase_edit import bind_source,apply_patch,validate_full_replacement,PATCH_SCHEMA,FULL_SCHEMA
from harness2.dance_edit_route import route_edit
from experiments.dance_phrase_edit_probe import COMMON,OUTPUT,MODELS
from experiments.dance_visual_probe import NATIVE_KEYS


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    from experiments.dance_edit_policy_holdouts import CASES
    from harness2.dance_phrases import compile_plan
    output=Path('evidence/dance-edit-policy-holdout-v1.json')
    if output.exists():raise ValueError('refusing overwrite')
    assert len(CASES)==12 and len({c['id'] for c in CASES})==12
    for c in CASES:
        for moves in [c['source_moves'],c['expected_moves']]:compile_plan(json.dumps({'moves':moves}))
        changed=[i for i in range(4) if c['source_moves'][i]!=c['expected_moves'][i]]
        if len(changed)!=1 or changed[0] not in c['editable_slots']:raise ValueError('fixture scope mismatch')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    paths=['harness2/dance_phrases.py','harness2/dance_phrase_edit.py','harness2/dance_edit_route.py','experiments/dance_phrase_edit_probe.py','experiments/dance_edit_policy_holdouts.py','experiments/dance_edit_policy_probe.py']
    report={'scope':'New within-shelf evaluation of previously fixed full/patch/fresh-fallback policies. No editor or H2 learning, no new motion capability. Twelve briefs independently authored before calls.',
      'sources':{p:digest(p) for p in paths},'cases':CASES,'models':{m:{k:next(t for t in tags if t['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
      'policies':['full','patch','fresh_route'],'design':'Policy order rotates by case; reversed for second model. Standalone policies have no correction. Route uses compiler rejection only; expected moves score results after return.',
      'max_calls':96,'max_call_seconds':20,'max_output_tokens':128,'paid_provider_calls':0,'calls':[],'results':[]}
    errors=0
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for mi,model in enumerate(MODELS):
            for ci,case in enumerate(CASES):
                raw_source=json.dumps({'moves':case['source_moves']});revision='approved-policy-eval-v1';scope=case['editable_slots'];snapshot=bind_source(raw_source,revision,scope)
                public={'source_plan':json.loads(raw_source),'permitted_slots':scope,'request':case['request']}
                order=report['policies'][ci%3:]+report['policies'][:ci%3]
                if mi:order=list(reversed(order))
                for policy in order:
                    result={'model':model,'case_id':case['id'],'policy':policy,'call_indices':[]};report['results'].append(result);start=time.monotonic()
                    def provider(mode,previous_raw=None,rejection_reason=None):
                        nonlocal errors
                        if len(report['calls'])>=96 or errors>=2:raise RuntimeError('call/error cap')
                        messages=[{'role':'system','content':COMMON+'\n'+OUTPUT[mode]},{'role':'user','content':json.dumps(public,sort_keys=True)}]
                        row={'model':model,'case_id':case['id'],'policy':policy,'mode':mode,'messages':messages,'input_text_characters':sum(len(m['content']) for m in messages),'previous_raw_audit':previous_raw,'rejection_reason_audit':rejection_reason};started=time.monotonic()
                        try:
                            raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':messages,'stream':False,'think':False,'format':PATCH_SCHEMA if mode=='patch' else FULL_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
                            row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','');errors=0
                            if raw.get('done_reason')!='stop':raise RuntimeError('incomplete provider response')
                            return row['content']
                        except Exception as exc:
                            if 'raw_response' not in row:errors+=1
                            row['error_type']=type(exc).__name__;raise
                        finally:row['wall_seconds']=time.monotonic()-started;result['call_indices'].append(len(report['calls']));report['calls'].append(row);save()
                    try:
                        if policy=='fresh_route':
                            routed=route_edit(snapshot,raw_source,revision,scope,provider);result['accepted']=routed['accepted'];result['attempts']=routed['attempts'];edit=routed['edit']
                        else:
                            raw=provider(policy);fn=apply_patch if policy=='patch' else validate_full_replacement
                            edit=fn(raw,snapshot,raw_source,revision,scope);result['accepted']=True
                        if result['accepted']:
                            choices=[[m['id'],m['variation']] for m in edit['compiled']['moves']];result.update(moves=choices,correct=choices==case['expected_moves'],edit_receipt=edit['receipt'])
                        else:result['correct']=False
                    except Exception as exc:result.update(accepted=False,correct=False,error_type=type(exc).__name__,reason=str(exc))
                    result['wall_seconds']=time.monotonic()-start;save()
                    print(json.dumps({k:result.get(k) for k in ['model','case_id','policy','accepted','correct','reason','wall_seconds']}),flush=True)
                    if errors>=2:raise RuntimeError('consecutive transport errors')
        report['complete']=True
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:save();print(json.dumps({'complete':report.get('complete'),'calls':len(report['calls'])}),flush=True)

if __name__=='__main__':main()

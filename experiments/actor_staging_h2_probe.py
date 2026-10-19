"""Actual Harness2 guidance refinement plus frozen compact-staging evaluation."""
import copy
import hashlib
import json
import math
from pathlib import Path
import argparse
import threading
import time
from urllib.request import urlopen

from harness2.actor_provider import ChatResult,_parse_response
from harness2.bounded_json_http import request_json
from harness2.actor_staging import compile_staging
from harness2.actor_staging_h2 import StagingAdapter,BASE_GUIDANCE,PUBLIC_CONTRACT,verdict
from harness2.core.schedule import run_domain
from harness2.production_h2 import ProductionImprover
from experiments.actor_staging_cases import CASES
from experiments.actor_staging_fresh_cases import EVAL_CASES as EVAL_PRIMARY
from experiments.actor_staging_extra_holdouts import EVAL_CASES as EVAL_EXTRA
from experiments.actor_staging_compact_probe import COMPACT_SCHEMA
from experiments.dance_visual_probe import NATIVE_KEYS

EDITOR='google/gemma-4-31b-it'
MODELS=['gemma4:e2b','hermes-lab-qwen3-8b:latest']

def canonical(case):
    return compile_staging(json.dumps({'scene_revision':case['scene']['revision'],**case['expected']}),case['scene'])

def task(case):return {'task_id':case['id'],'scene':copy.deepcopy(case['scene']),'request':case['request']}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',type=int,default=2);args=parser.parse_args()
    if not 2<=args.version<=99:raise ValueError('version must be 2..99')
    output=Path(f'evidence/actor-staging-h2-v{args.version}.json');root=Path(f'runs/actor-staging-h2-v{args.version}')
    if output.exists() or root.exists():raise ValueError('refusing overwrite')
    root.mkdir()
    evaluation=copy.deepcopy(EVAL_PRIMARY+EVAL_EXTRA)
    for c in evaluation:canonical(c)
    assert len({c['id'] for c in evaluation})==12
    dev=copy.deepcopy(next(c for c in CASES if c['id']=='gallery_roles_reversed'))
    with urlopen('https://openrouter.ai/api/v1/models',timeout=15) as r:listing=json.load(r)['data']
    metadata=next(x for x in listing if x['id']==EDITOR)
    if float(metadata['pricing']['prompt'])>1e-6 or float(metadata['pricing']['completion'])>3e-6:raise ValueError('editor listing exceeds price cap')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    sources=['harness2/actor_staging_h2.py','harness2/actor_staging_compact.py','harness2/production_h2.py','harness2/bounded_json_http.py',
             'experiments/actor_staging_h2_probe.py','experiments/actor_staging_fresh_cases.py','experiments/actor_staging_extra_holdouts.py']
    report={'scope':'Actual k=1 sequential Harness2 guidance refinement on one previously observed gallery case; 12 frozen within-family eval cases. No animation executed.',
      'sources':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
      'editor_metadata':{k:metadata.get(k) for k in ['id','pricing','architecture','supported_parameters']},
      'local_metadata':{m:{k:next(x for x in tags if x['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
      'frozen_evaluation':evaluation,'evaluation_sha256':hashlib.sha256(json.dumps(evaluation,sort_keys=True).encode()).hexdigest(),
      'development_case_id':dev['id'],'max_calls':80,'max_editor_calls':3,'reported_cost_stop_usd':.10,
      'editor_price_cap_per_million':{'prompt':1,'completion':3},'calls':[],'evaluation':[],
      'limitations':['New fixed prompt framing differs from earlier compact probe.','Single sample per condition/case, no service-rate or hardware forecast.','Expected plans are host-only; structural validity does not prove semantic correctness.','k=1 returns a single final candidate; experience remains scripted NO_ENTRY.']}
    rows=report['calls'];paid=0.;editor_calls=0;errors=0
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    provider_lock=threading.RLock()
    def provider(**kw):
        with provider_lock:return provider_serial(**kw)
    def provider_serial(**kw):
        nonlocal paid,editor_calls,errors
        if len(rows)>=80 or errors>=2:raise RuntimeError('call/error budget exhausted')
        local=kw['model'] in MODELS
        if not local and (editor_calls>=3 or paid>=.10 or report.get('cost_unknown')):raise RuntimeError('editor budget exhausted')
        if not local:
            # Entire case IDs and unique actor IDs are checked absent from all editor requests.
            text=kw['system']+'\n'+kw['user']
            for c in evaluation:
                if c['id'] in text or any(a in text for a in c['scene']['actor_ids']):raise RuntimeError('heldout leakage')
            if len(text.encode())>60000:raise RuntimeError('editor context cap')
            editor_calls+=1
        row={'phase':report.get('phase','development'),'model_requested':kw['model'],'system':kw['system'],'user':kw['user'],
             'input_text_characters':len(kw['system'])+len(kw['user']),'hard_timeout_seconds':min(45,kw.get('timeout',45))}
        rows.append(row);save();start=time.monotonic()
        try:
            if local:
                raw=request_json('http://127.0.0.1:11434/api/chat',{'model':kw['model'],'messages':[{'role':'system','content':kw['system']},{'role':'user','content':kw['user']}],
                     'stream':False,'think':False,'format':COMPACT_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=row['hard_timeout_seconds'])
                row.update({k:raw.get(k) for k in NATIVE_KEYS});row['raw_response']=raw
                result=ChatResult(raw.get('message',{}).get('content',''),raw.get('done_reason','unknown'),
                    {'prompt_tokens':raw.get('prompt_eval_count'),'completion_tokens':raw.get('eval_count')},time.monotonic()-start,raw.get('model',''),raw)
            else:
                body={'model':EDITOR,'messages':[{'role':'system','content':kw['system']},{'role':'user','content':kw['user']}],
                    'temperature':0,'max_tokens':1024,'reasoning':{'enabled':False},
                    'provider':{'max_price':{'prompt':1,'completion':3}},'response_format':{'type':'json_object'}}
                raw=request_json('https://openrouter.ai/api/v1/chat/completions',body,timeout=row['hard_timeout_seconds'],bearer_env='OPENROUTER_API_KEY')
                row['raw_response']=raw
                cost=raw.get('usage',{}).get('cost');row['reported_cost_usd']=cost
                if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:report['cost_unknown']=True
                else:paid+=cost
                result=_parse_response(json.dumps(raw).encode(),include_raw=True,latency=time.monotonic()-start)
            errors=0;row.update(content=result.content,finish_reason=result.finish_reason,usage=result.usage)
            return result
        except Exception as exc:
            errors+=1;row['error_type']=type(exc).__name__;raise
        finally:
            row['wall_seconds']=time.monotonic()-start;report['reported_cost_sum_usd']=paid;save()
            print(json.dumps({'call':len(rows),'model':kw['model'],'phase':row['phase'],'seconds':round(row['wall_seconds'],3),'error':row.get('error_type')}),flush=True)
    common={'provider':provider,'base_url':'http://127.0.0.1:11434/v1','model':MODELS[0],'api_key':'','max_solver_calls':8}
    adapter=StagingAdapter(root/'development',{dev['id']:task(dev)},{dev['id']:canonical(dev)},[dev['id']],**common)
    editor=ProductionImprover(adapter.spec.channels['proposer'],provider=provider,base_url='https://openrouter.ai/api/v1',model=EDITOR,
        audit_dir=root/'editor',max_editor_calls=3,max_output_tokens=1024,request_timeout=35,
        guidance_domain='compact actor staging',public_rule='The host owns schema, geometry, timing and acceptance checks. Improve generic interpretation of actor identities, side assignment, chronological cues and amendments. Do not embed specific actor IDs or task answers.')
    try:
        report['framework']=run_domain(adapter.domain_of(dev['id']),[dev['id']],1,adapter=adapter,prop=editor,runs_root=adapter.spec.runs_root,library_root=root/'library',modes=('seq',))
        summary=json.loads((adapter.spec.runs_root/(adapter.spec.name+'-oc-agg1')/dev['id']/'summary.json').read_text())
        selection=summary['selections']['seq'];report['selection']=selection
        if not selection.get('ok'):raise RuntimeError('no selected harness')
        candidate=adapter.spec.runs_root/(adapter.spec.name+'-oc-seq1')/dev['id']/'harnesses'/selection['chosen_label']
        guidance=(candidate/'systemprompt.md').read_text();baseline=(adapter.base_harness()/'systemprompt.md').read_text()
        if any(identifier in guidance for identifier in dev['scene']['actor_ids']+[dev['scene']['anchor']['id'],dev['id']]):
            raise ValueError('candidate embeds development identifiers')
        report.update(selected_guidance=guidance,baseline_guidance=baseline,public_contract=PUBLIC_CONTRACT,guidance_changed=guidance!=baseline,
                      selected_guidance_sha256=hashlib.sha256(guidance.encode()).hexdigest(),editor_finished_before_evaluation=True)
        save()
        # No editor calls after this boundary. Alternate fixed/adapted order, then Qwen control.
        for model in MODELS:
            report['phase']='evaluation-'+model
            for ci,c in enumerate(evaluation):
                conditions=[('fixed',baseline),('adapted',guidance)] if model==MODELS[0] else [('fixed',baseline)]
                if ci%2:conditions.reverse()
                for name,text in conditions:
                    row={'model':model,'case_id':c['id'],'condition':name,'attempts':[]};report['evaluation'].append(row)
                    public_task={'scene':c['scene'],'request':c['request']}
                    prompt=json.dumps(public_task,sort_keys=True)
                    for attempt in range(2 if name=='fixed' else 1):
                        index=len(rows)
                        result=provider(model=model,system=text+'\n'+PUBLIC_CONTRACT,user=prompt)
                        v=verdict(result.content,task(c),canonical(c)) if result.finish_reason=='stop' else {'valid':False,'semantic_correct':False,'reason':'incomplete native response'}
                        row['attempts'].append({'call_index':index,'verdict':v});save()
                        if v['valid']:break
                        prompt=json.dumps({'task':public_task,'previous_proposal':result.content,'host_feedback':'The previous plan failed acceptance. '+v['reason']+'. Re-read the requested actor, side, chronological order and variation; return a complete corrected JSON plan.'},sort_keys=True)
        report['complete']=True
    except Exception as exc:report['error_type']=type(exc).__name__
    finally:
        report['editor_receipts']=[json.loads(p.read_text()) for p in sorted((root/'editor').glob('*.json'))]
        report['development_receipts']=[json.loads(p.read_text()) for p in sorted((root/'development'/'executions').rglob('receipt.json'))]
        save();print(json.dumps({'complete':report.get('complete',False),'error':report.get('error_type'),'calls':len(rows),'cost':paid,'guidance_changed':report.get('guidance_changed')}),flush=True)

if __name__=='__main__':main()

"""Corrected H2 composer context and pre-evaluation admission, with fresh cases."""
import copy,hashlib,json,math,threading,time
from pathlib import Path
from urllib.request import urlopen
from harness2.actor_provider import ChatResult,_parse_response
from harness2.bounded_json_http import request_json
from harness2.core.schedule import run_domain
from harness2.dance_step_improver import StepImprover
from harness2.dance_guidance_admission import choose_admitted
from harness2.dance_step_task import feasible_plans,compile_task
from experiments.dance_step_task_cases import CASES
from experiments.dance_steps_contract_probe import ENUM_SCHEMA
from experiments.dance_visual_probe import NATIVE_KEYS

EDITOR='google/gemma-4-31b-it'
MODELS=['gemma4:e2b','hermes-lab-qwen3-8b:latest']
DEV_ID='offset_return_to_mark_with_endpoint_direction'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def task(c):return {'task':copy.deepcopy(c['task']),'request':c['request']}

def main():
    from harness2.dance_step_h2 import StepAdapter,BASE_GUIDANCE,PUBLIC_CONTRACT,verdict
    from experiments.dance_step_h2_holdouts_v2 import CASES as EVALUATION
    output=Path('evidence/dance-step-h2-v2.json');root=Path('runs/dance-step-h2-v2')
    if output.exists() or root.exists():raise ValueError('refusing overwrite')
    evaluation=copy.deepcopy(EVALUATION);dev=copy.deepcopy(next(c for c in CASES if c['id']==DEV_ID))
    counts={c['id']:len(feasible_plans(c['task'])) for c in evaluation}
    if len(counts)!=8 or not all(counts.values()):raise ValueError('bad evaluation fixture')
    with urlopen('https://openrouter.ai/api/v1/models',timeout=15) as r:listing=json.load(r)['data']
    metadata=next(t for t in listing if t['id']==EDITOR)
    if float(metadata['pricing']['prompt'])>1e-6 or float(metadata['pricing']['completion'])>3e-6:raise ValueError('editor price cap')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
    root.mkdir()
    paths=['harness2/dance_step_h2.py','harness2/dance_step_task.py','harness2/dance_steps.py','harness2/dance_motion.py','harness2/production_h2.py','harness2/actor_improver.py','harness2/bounded_json_http.py','experiments/dance_step_task_cases.py','experiments/dance_step_h2_holdouts_v2.py','experiments/dance_step_h2_probe_v2.py','harness2/dance_step_improver.py','harness2/dance_guidance_admission.py','experiments/dance_steps_contract_probe.py']
    report={'scope':'Actual k=1 sequential H2 refinement with full bounded composer pool evidence and host admission on one observed task; eight new within-family cases, fixed/one-repair/admitted conditions for both local models. No animation executed. Host accepts any constraint-satisfying plan, no expected sequence.',
      'sources':{p:digest(p) for p in paths},'development_case':dev,'frozen_evaluation':evaluation,'evaluation_feasible_counts':counts,
      'editor_metadata':{k:metadata.get(k) for k in ['id','pricing','supported_parameters']},'local_metadata':{m:{k:next(t for t in tags if t['name']==m).get(k) for k in ['name','digest','size']} for m in MODELS},
      'max_calls':60,'max_editor_calls':3,'editor_max_input_bytes':30000,'editor_max_output_tokens':1024,'reported_cost_stop_usd':.10,'editor_price_caps_per_million':{'prompt':1,'completion':3},
      'limitations':['Upstream k=1 selection and experience stay scripted; separate host admission is applied before evaluation.','Baseline includes short guidance in addition to previous contract; do not equate with prior-run scores.','One sample per case/condition; initial baseline/adapted order alternates, repair follows a failure.','Authoritative structured tasks provided; no natural-language extraction, taste or live avatar guarantee.'],
      'calls':[],'evaluation':[],'phase':'development'}
    rows=report['calls'];paid=0.0;editor_calls=0;errors=0;lock=threading.RLock()
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    def provider(**kw):
        nonlocal paid,editor_calls,errors
        with lock:
            if len(rows)>=60 or errors>=2:raise RuntimeError('call/error cap')
            local=kw['model'] in MODELS
            if not local:
                if report.get('editor_finished_before_evaluation') or editor_calls>=3 or paid>=.10 or report.get('cost_unknown'):raise RuntimeError('editor call/cost/phase cap')
                text=kw['system']+'\n'+kw['user']
                if len(text.encode())>30000:raise ValueError('editor context byte cap')
                if any(c['id'] in text for c in evaluation):raise ValueError('evaluation id leakage')
                editor_calls+=1
            limit=min(20 if local else 35,kw.get('timeout',35))
            row={'phase':report['phase'],'model_requested':kw['model'],'system':kw['system'],'user':kw['user'],'input_text_characters':len(kw['system'])+len(kw['user']),'hard_timeout_seconds':limit}
            rows.append(row);save();start=time.monotonic()
            try:
                if local:
                    raw=request_json('http://127.0.0.1:11434/api/chat',{'model':kw['model'],'messages':[{'role':'system','content':kw['system']},{'role':'user','content':kw['user']}],'stream':False,'think':False,'format':ENUM_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=limit)
                    row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS})
                    result=ChatResult(raw.get('message',{}).get('content',''),raw.get('done_reason','unknown'),{'prompt_tokens':raw.get('prompt_eval_count'),'completion_tokens':raw.get('eval_count')},time.monotonic()-start,raw.get('model',''),raw)
                else:
                    raw=request_json('https://openrouter.ai/api/v1/chat/completions',{'model':EDITOR,'messages':[{'role':'system','content':kw['system']},{'role':'user','content':kw['user']}],'temperature':0,'max_tokens':1024,'reasoning':{'enabled':False},'provider':{'max_price':{'prompt':1,'completion':3}},'response_format':{'type':'json_object'}},timeout=limit,bearer_env='OPENROUTER_API_KEY')
                    row['raw_response']=raw;cost=raw.get('usage',{}).get('cost');row['reported_cost_usd']=cost
                    if type(cost) not in (float,int) or not math.isfinite(cost) or cost<0:report['cost_unknown']=True
                    else:paid+=cost
                    result=_parse_response(json.dumps(raw).encode(),include_raw=True,latency=time.monotonic()-start)
                row.update(content=result.content,finish_reason=result.finish_reason,usage=result.usage);errors=0;return result
            except Exception as exc:
                errors+=1;row.update(error_type=type(exc).__name__,error=str(exc))
                if not local and 'raw_response' not in row:report['cost_unknown']=True
                raise
            finally:
                row['wall_seconds']=time.monotonic()-start;report['reported_cost_sum_usd']=paid;save()
                print(json.dumps({'call':len(rows),'model':kw['model'],'phase':row['phase'],'seconds':round(row['wall_seconds'],3),'error':row.get('error_type')}),flush=True)
    adapter=StepAdapter(root/'development',{dev['id']:task(dev)},[dev['id']],provider=provider,base_url='http://127.0.0.1:11434/v1',model=MODELS[0],api_key='',max_solver_calls=8)
    editor=StepImprover(adapter.spec.channels['proposer'],provider=provider,base_url='https://openrouter.ai/api/v1',model=EDITOR,audit_dir=root/'editor',max_editor_calls=3,max_output_tokens=1024,request_timeout=35,
      guidance_domain='four-step constrained motion planning',public_rule='The immutable host contract owns step size, exact task fields, schema, geometry and acceptance checks. Improve generic planning of directions and accents under endpoint, lane and slot constraints. Do not embed task IDs, numeric task-specific answers or concrete four-move solutions.')
    try:
        report['framework']=run_domain(adapter.domain_of(dev['id']),[dev['id']],1,adapter=adapter,prop=editor,runs_root=adapter.spec.runs_root,library_root=root/'library',modes=('seq',))
        summary=json.loads((adapter.spec.runs_root/(adapter.spec.name+'-oc-agg1')/dev['id']/'summary.json').read_text());selection=summary['selections']['seq'];report['selection']=selection
        if not selection.get('ok'):raise RuntimeError('no selected harness')
        candidates=[]
        for rp in sorted((root/'development'/'executions').rglob('receipt.json')):
            receipt=json.loads(rp.read_text());label=receipt['run_id'].split('/')[-1]
            prompt=(adapter.base_harness()/'systemprompt.md' if label=='base1' else adapter.spec.runs_root/(adapter.spec.name+'-oc-seq1')/dev['id']/'harnesses'/label/'systemprompt.md')
            candidates.append({'label':label,'guidance':prompt.read_text(),'receipt':receipt})
        admission=choose_admitted(candidates,task(dev));report.update(admission=admission,development_candidates=candidates)
        if admission['selected'] is None:raise RuntimeError('no development-valid harness admitted')
        guidance=admission['selected']['guidance'];baseline=(adapter.base_harness()/'systemprompt.md').read_text()
        if dev['id'] in guidance or any(c['id'] in guidance for c in evaluation):raise ValueError('candidate embeds task identifiers')
        report.update(selected_guidance=guidance,baseline_guidance=baseline,public_contract=PUBLIC_CONTRACT,guidance_changed=guidance!=baseline,selected_guidance_sha256=hashlib.sha256(guidance.encode()).hexdigest(),editor_finished_before_evaluation=True)
        save()
        for mi,model in enumerate(MODELS):
            report['phase']='evaluation-'+model
            for ci,c in enumerate(evaluation):
                conditions=[('fixed',baseline),('adapted',guidance)]
                if (mi+ci)%2:conditions.reverse()
                for name,text in conditions:
                    result={'model':model,'case_id':c['id'],'condition':name,'attempts':[]};report['evaluation'].append(result)
                    public=task(c);prompt=json.dumps(public,sort_keys=True)
                    for attempt in range(2 if name=='fixed' else 1):
                        index=len(rows);response=provider(model=model,system=text+'\n'+PUBLIC_CONTRACT,user=prompt)
                        v=verdict(response.content,public) if response.finish_reason=='stop' else {'valid':False,'reason':'incomplete response'}
                        compiled=v.pop('compiled',None)
                        if compiled is not None:v.update(receipt=compiled['receipt'],placement=compiled['placement'])
                        result['attempts'].append({'call_index':index,'verdict':v});save()
                        if v['valid'] or response.finish_reason!='stop':break
                        prompt=json.dumps({'task':public,'previous_proposal':response.content,'host_feedback':'The plan was rejected: '+v['reason']+'. Re-read the approved task and return a corrected four-pair plan.'},sort_keys=True)
        report['complete']=True
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:
        report['editor_receipts']=[json.loads(p.read_text()) for p in sorted((root/'editor').glob('*.json'))]
        report['development_receipts']=[json.loads(p.read_text()) for p in sorted((root/'development'/'executions').rglob('receipt.json'))]
        save();print(json.dumps({'complete':report.get('complete'),'calls':len(rows),'cost':paid,'error':report.get('error')}),flush=True)

if __name__=='__main__':main()

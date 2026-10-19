"""Actual Harness2 adaptation of a local solver, with separately frozen evaluation."""
import hashlib
import json
import os
from pathlib import Path
import signal
import time
from urllib.request import Request, urlopen
from harness2.actor_provider import ChatResult, chat_completion
from harness2.core.schedule import run_domain
from harness2.priority_h2 import PriorityAdapter, _verdict
from harness2.production_h2 import ProductionImprover
from experiments.creative_menu_comparison import CASES


def main():
    root = Path('runs/local-priority-h2-v1')
    output = Path('evidence/local-priority-h2-v1.json')
    if root.exists() or output.exists():
        raise SystemExit('refusing overwrite')
    root.mkdir(parents=True)
    report = {'scope': 'Local 8B priority solver, hosted editor, actual Harness2 recursion',
              'calls': [], 'evaluation': [], 'max_calls': 32, 'paid_editor_cap': 3}
    def save():
        output.write_text(json.dumps(report, indent=2)+'\n')
    def deadline(*_):
        raise TimeoutError('call deadline')
    signal.signal(signal.SIGALRM, deadline)
    def provider(**kw):
        if len(report['calls']) >= 32:
            raise RuntimeError('call cap')
        row = {'model_requested': kw['model'], 'input_chars': len(kw['system'])+len(kw['user'])}
        report['calls'].append(row)
        save()
        signal.alarm(30)
        started = time.monotonic()
        try:
            if kw['model'].startswith('hermes-lab-'):
                body = {'model': kw['model'], 'messages': [{'role':'system','content':kw['system']},
                        {'role':'user','content':kw['user']}], 'stream':False,'think':False,
                        'options':{'num_ctx':4096,'num_predict':kw['max_output_tokens'],'temperature':0}, 'keep_alive':'2m'}
                req = Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
                with urlopen(req,timeout=kw['timeout']) as response:
                    raw = response.read(1048577)
                if len(raw)>1048576:
                    raise ValueError('oversized response')
                raw = json.loads(raw)
                for key in ('load_duration','prompt_eval_duration','eval_duration','prompt_eval_count','eval_count'):
                    row[key] = raw.get(key)
                result = ChatResult(raw.get('message',{}).get('content',''), raw.get('done_reason','unknown'),
                    {'prompt_tokens':raw.get('prompt_eval_count'), 'completion_tokens':raw.get('eval_count')},
                    time.monotonic()-started, raw.get('model',''), raw)
            else:
                kw['api_key'] = os.environ['OPENROUTER_API_KEY']
                result = chat_completion(**kw)
            row.update(content=result.content, usage=result.usage, latency_seconds=result.latency_seconds,
                       cost=result.raw_response.get('usage',{}).get('cost'))
            return result
        except Exception as exc:
            row['error_type'] = type(exc).__name__
            raise
        finally:
            signal.alarm(0)
            save()
    # Freeze independent holdouts before development; never pass them to the editor.
    from experiments.priority_holdouts import TASKS as source_tasks, EXPECTED_INDICES as source_expected
    # Deterministic balancing prevents a constant-position answer strategy.
    TASKS, EXPECTED_INDICES = [], {}
    for index, source in enumerate(source_tasks):
        shift = index % len(source['options'])
        task = dict(source, options=source['options'][shift:]+source['options'][:shift])
        TASKS.append(task)
        EXPECTED_INDICES[task['task_id']] = (source_expected[task['task_id']]-shift) % len(task['options'])
    frozen = json.dumps({'tasks':TASKS,'expected_indices':EXPECTED_INDICES},sort_keys=True)
    report['heldout_sha256'] = hashlib.sha256(frozen.encode()).hexdigest()
    case = next(c for c in CASES if c[0]=='budget-preview')
    dev = dict(task_id=case[0],brief=case[1],options=case[2])
    common = dict(provider=provider,base_url='http://127.0.0.1:11434/v1',model='hermes-lab-qwen3-8b:latest',api_key='',request_timeout=20)
    adapter = PriorityAdapter(root/'development',{dev['task_id']:dev},{dev['task_id']:case[3]},[dev['task_id']],
                              max_solver_calls=8,max_output_tokens=96,**common)
    editor = ProductionImprover(adapter.spec.channels['proposer'],provider=provider,
            base_url='https://openrouter.ai/api/v1',model='google/gemma-4-31b-it',audit_dir=root/'editor',
            max_editor_calls=3,max_output_tokens=512,request_timeout=20)
    try:
        report['framework'] = run_domain('creative-priority',[dev['task_id']],1,adapter=adapter,prop=editor,
                runs_root=adapter.spec.runs_root,library_root=root/'library',modes=('seq',))
        summary = json.loads((adapter.spec.runs_root/'priority_h2-oc-agg1'/dev['task_id']/'summary.json').read_text())
        selection = summary['selections']['seq']
        report['selection'] = selection
        if not selection.get('ok'):
            raise RuntimeError('no selected harness')
        candidate = adapter.spec.runs_root/'priority_h2-oc-seq1'/dev['task_id']/'harnesses'/selection['chosen_label']
        guidance = (candidate/'systemprompt.md').read_text()
        baseline = (adapter.base_harness()/'systemprompt.md').read_text()
        report.update(selected_guidance=guidance,guidance_changed=guidance!=baseline,development_call_count=len(report['calls']))
        # Editor is finished before evaluation starts. Feedback never discloses expected option.
        for task in TASKS:
            row = {'task_id':task['task_id'],'conditions':{}}
            report['evaluation'].append(row)
            for name,text in [('fixed',baseline),('adapted',guidance)]:
                prompt = {'brief':task['brief'],'legal_options':[{'choice_id':f'option_{i}','description':s} for i,s in enumerate(task['options'])]}
                attempts=[]
                row['conditions'][name]=attempts
                for attempt in range(2 if name=='fixed' else 1):
                    result=provider(base_url=common['base_url'],model=common['model'],api_key='',
                        system=text+'\nReturn strict JSON only; no Markdown.',user=json.dumps(prompt,sort_keys=True),timeout=20,max_output_tokens=96,include_raw=True)
                    verdict=_verdict(result.content,len(task['options']),EXPECTED_INDICES[task['task_id']])
                    attempts.append({'content':result.content,'verdict':verdict,'finish_reason':result.finish_reason})
                    save()
                    if verdict['valid'] and result.finish_reason=='stop':break
                    prompt.update(previous_proposal=result.content,host_feedback='The previous choice failed acceptance. Recheck every stated constraint and compute combined costs before choosing. Return the required JSON.')
    except Exception as exc:
        report.update(error_type=type(exc).__name__,error_message=str(exc)[:200])
    finally:
        report['editor_receipts']=[json.loads(p.read_text()) for p in sorted((root/'editor').glob('*.json'))]
        report['development_verdicts']=[json.loads(p.read_text()) for p in sorted((root/'development'/'executions').rglob('verdict.json'))]
        save()
        print(json.dumps({'error':report.get('error_type'),'calls':len(report['calls']),'guidance_changed':report.get('guidance_changed'),'evaluation':report['evaluation']},indent=2))

if __name__=='__main__':main()

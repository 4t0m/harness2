"""Small live Harness² production trial with evaluation isolated from editor."""
import argparse
import json
import os
from pathlib import Path
import signal
from harness2.actor_provider import chat_completion
from harness2.core.schedule import run_domain
from harness2.production_dispatch import TASKS, evaluate, model_brief, rejection_feedback
from harness2.production_h2 import ProductionAdapter, ProductionImprover
from experiments.production_holdouts import fixtures, PUBLIC_RULE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='production-h2-gemma-v1')
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum():
        raise SystemExit('invalid run name')
    root = Path('runs') / args.name
    output = Path('evidence') / (args.name + '.json')
    if root.exists() or output.exists():
        raise SystemExit('refusing to overwrite prior run')
    root.mkdir(parents=True)
    calls = []
    report = {'scope':'live Harness2 development adaptation with separate frozen combination evaluation',
              'selection':'scripted k=1; not learned selection', 'external_dispatch':False, 'calls':calls}
    def persist():
        output.write_text(json.dumps(report, indent=2) + '\n')
    def deadline(*_):
        raise TimeoutError('provider hard deadline')
    signal.signal(signal.SIGALRM, deadline)
    def provider(**kwargs):
        if len(calls) >= 24:
            raise RuntimeError('global provider call cap reached')
        entry = {'index':len(calls)+1}
        calls.append(entry)
        persist()
        signal.alarm(30)
        try:
            kwargs['api_key'] = os.environ['OPENROUTER_API_KEY']
            kwargs['include_raw'] = True
            result = chat_completion(**kwargs)
            entry.update(model=result.model, usage=result.usage, latency_seconds=result.latency_seconds,
                         cost=result.raw_response.get('usage',{}).get('cost'), content=result.content)
            return result
        except Exception as exc:
            entry['error_type'] = type(exc).__name__
            for field in ('usage', 'finish_reason', 'latency_seconds', 'model'):
                if hasattr(exc, field):
                    entry[field] = getattr(exc, field)
            raise
        finally:
            signal.alarm(0)
            persist()
    common = dict(base_url='https://openrouter.ai/api/v1', model='google/gemma-4-26b-a4b-it', provider=provider,
                  request_timeout=20)
    dev = next(t for t in TASKS if t['task_id']=='blocked-02')
    adapter = ProductionAdapter(root/'development', {dev['task_id']:dev}, [dev['task_id']],
                                max_solver_calls=8, max_output_tokens=256, **common)
    editor = ProductionImprover(adapter.spec.channels['proposer'], audit_dir=root/'editor',
                                max_editor_calls=3, max_output_tokens=512, **common)
    try:
        report['framework'] = run_domain('production-planning', [dev['task_id']], 1,
            adapter=adapter, prop=editor, runs_root=adapter.spec.runs_root,
            library_root=root/'library', modes=('seq',))
        summary_path = adapter.spec.runs_root/(adapter.spec.name+'-oc-agg1')/dev['task_id']/'summary.json'
        summary = json.loads(summary_path.read_text())
        report['selection'] = summary.get('selections',{}).get('seq',{})
        chosen = report['selection'].get('chosen_label')
        if not chosen or not report['selection'].get('ok'):
            raise RuntimeError('no selected harness')
        candidate = adapter.spec.runs_root/(adapter.spec.name+'-oc-seq1')/dev['task_id']/'harnesses'/chosen
        guidance = (candidate/'systemprompt.md').read_text()
        report['selected_guidance'] = guidance
        report['guidance_changed'] = guidance != (adapter.base_harness()/'systemprompt.md').read_text()
        # No calls to the editor after this point. Evaluation sources never enter its adapter.
        report['development_call_count'] = len(calls)
        heldouts = fixtures()
        report['evaluation_fixtures'] = heldouts
        report['evaluation'] = []
        baseline = (adapter.base_harness()/'systemprompt.md').read_text()
        for task in heldouts:
            row = {'task_id':task['task_id'], 'conditions':{}}
            report['evaluation'].append(row)
            for name, text in [('fixed',baseline), ('adapted',guidance)]:
                prompt = model_brief(task)
                system = 'Select a legal production action. Return only strict JSON, no Markdown. '+PUBLIC_RULE+'\n'+text
                attempts=[]
                for index in range(2 if name=='fixed' else 1):
                    r=provider(**common_without_provider(common),system=system,user=json.dumps(prompt),max_output_tokens=256)
                    verdict=evaluate(task,r.content)
                    attempts.append({'content':r.content,'valid':verdict['valid'],'reason':verdict.get('reason')})
                    row['conditions'][name]=attempts
                    persist()
                    if verdict['valid']:
                        break
                    prompt={**model_brief(task),'previous_proposal':r.content,'host_feedback':rejection_feedback(task,r.content)}
    except Exception as exc:
        report['error_type']=type(exc).__name__
        report['error_message']=str(exc)[:300]
    finally:
        report['editor_receipts']=[json.loads(p.read_text()) for p in sorted((root/'editor').glob('*.json'))]
        report['development_verdicts']=[{'run':str(p.parent.relative_to(root)), 'verdict':json.loads(p.read_text())}
            for p in sorted((root/'development'/'executions').rglob('verdict.json'))]
        persist()
        print(json.dumps({'calls':len(calls),'error':report.get('error_type'), 'evaluation':report.get('evaluation')},indent=2))


def common_without_provider(common):
    return {k:v for k,v in common.items() if k not in ('provider','request_timeout')} | {'timeout':common['request_timeout']}


if __name__ == '__main__':
    main()

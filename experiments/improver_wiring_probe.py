"""Bounded live improver with a scripted solver; no real-agent improvement claim."""
import json
import os
from pathlib import Path
import signal
from harness2.actor_demo import ActorAdapter
from harness2.actor_improver import ActorImprover
from harness2.core.schedule import run_domain


def main():
    root=Path('runs/gemma-improver-wiring')
    root.mkdir(parents=True,exist_ok=False)
    os.environ['HARNESS2_ACTOR_API_KEY']=os.environ['OPENROUTER_API_KEY']
    adapter=ActorAdapter(root)
    proposer=ActorImprover(adapter.spec.channels['proposer'],base_url='https://openrouter.ai/api/v1',
        model='google/gemma-4-26b-a4b-it',audit_dir=root/'improver-receipts',max_provider_calls=3,
        request_timeout=25,max_output_tokens=512)
    report={'scope':'live model guidance edits within actual Harness2; scripted solver; deliberately planted policy fault',
            'limits':['Four possible policy combinations only','Scripted selection and NO_ENTRY memory','Not evidence of real solver improvement or general creative quality'],
            'heldout_used_for_editing':False}
    def deadline(*_):
        raise TimeoutError('outer improver trial deadline')
    signal.signal(signal.SIGALRM,deadline)
    signal.alarm(150)
    try:
        report['run_domain']=run_domain('actor-planning',['left-mirror'],1,adapter=adapter,prop=proposer,
            runs_root=adapter.spec.runs_root,library_root=root/'library',modes=('seq',))
        summary=json.loads((adapter.spec.runs_root/'actor_demo-oc-agg1'/'left-mirror'/'summary.json').read_text())
        selection=summary.get('selections',{}).get('seq',{})
        report['selection']={k:selection.get(k) for k in ('ok','chosen_label')}
        harness=adapter.spec.runs_root/'actor_demo-oc-seq1'/'left-mirror'/'harnesses'/'c1'
        if selection.get('ok') and harness.exists():
            report['selected_guidance']=(harness/'systemprompt.md').read_text()
            report['heldout']={}
            for kind, candidate in [('base',None),('adapted',harness)]:
                run=adapter.execute('heldout-diagonal',candidate,'heldout-'+kind)
                report['heldout'][kind]=json.loads((run/'verdict.json').read_text())
    except Exception as exc:
        report['error_type']=type(exc).__name__
    finally:
        signal.alarm(0)
        report['provider_calls']=proposer.provider_calls
        report['editor_receipts']=[json.loads(p.read_text()) for p in sorted((root/'improver-receipts').glob('*.json'))]
        report['solver_verdicts']=[{'run':str(p.parent.relative_to(root/'executions')),
            'verdict':json.loads(p.read_text())} for p in sorted((root/'executions').rglob('verdict.json'))]
        Path('evidence/improver-wiring-live.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))

if __name__=='__main__':main()

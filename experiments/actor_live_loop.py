"""Small actual-provider solver run through Harness2; improver remains scripted."""
import json
import os
import signal
from pathlib import Path
from harness2.actor_model import ModelActorAdapter
from harness2.actor_demo import ActorProposer
from harness2.core.schedule import run_domain


def main():
    signal.alarm(150)
    root=Path('runs/gemma-actor-loop')
    root.mkdir(parents=True,exist_ok=False)
    os.environ['HARNESS2_ACTOR_API_KEY']=os.environ['OPENROUTER_API_KEY']
    adapter=ModelActorAdapter(root,base_url='https://openrouter.ai/api/v1',model='google/gemma-4-26b-a4b-it',max_attempts=1,max_output_tokens=512,request_timeout=25)
    proposer=ActorProposer(adapter.spec.channels['proposer'])
    result=run_domain('actor-planning',['left-mirror'],1,adapter=adapter,prop=proposer,runs_root=adapter.spec.runs_root,library_root=root/'library',modes=('seq',))
    summary=json.loads((adapter.spec.runs_root/'actor_model-oc-agg1'/'left-mirror'/'summary.json').read_text())
    selected=summary.get('selections',{}).get('seq',{})
    harness=adapter.spec.runs_root/'actor_model-oc-seq1'/'left-mirror'/'harnesses'/'c1'
    if selected.get('ok') and harness.exists():
        adapter.execute('heldout-diagonal',harness,'heldout-adapted')
        adapter.execute('heldout-diagonal',None,'heldout-base')
    receipts=[]
    for p in sorted((root/'executions').rglob('verdict.json')):
        attempts=json.loads((p.parent/'attempts.json').read_text())
        receipts.append({'run_id':str(p.parent.relative_to(root/'executions')),'verdict':json.loads(p.read_text()),'attempts':attempts})
    evidence={'scope':'Actual OpenRouter solver within Harness2 sequential k1 loop; scripted improver/selector; no rendered avatar','model':adapter.model,'run_domain':result,'selection':{k:selected.get(k) for k in ('ok','chosen_label')},'receipts':receipts,'limits':['One adaptation task and one holdout; not statistical reliability','Baseline guidance intentionally flawed; not a fair generic-harness benchmark','No model-backed improver or persistent learned memory']}
    (root/'summary.json').write_text(json.dumps(evidence,indent=2)+'\n')
    Path('evidence/gemma-actor-loop.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'result':result,'runs':len(receipts),'verdicts':[(r['run_id'],r['verdict']['status']) for r in receipts]},indent=2))

if __name__=='__main__':main()

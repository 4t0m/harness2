"""Replay saved model responses through actual recursion; no provider calls."""
import json
from pathlib import Path
from harness2.actor_demo import ActorAdapter
from harness2.actor_improver import ActorImprover
from harness2.actor_provider import ChatResult
from harness2.core.schedule import run_domain
from experiments.creative_retry_probe import normalize_single_json_fence


def main():
    source=json.loads(Path('evidence/gemma-improver-typed-loop-live.json').read_text())
    responses={r['label'].split('.')[0]:r['response_content'] for r in source['editor_receipts'] if r.get('provider_called')}
    root=Path('runs/improver-saved-repair');root.mkdir(exist_ok=False)
    adapter=ActorAdapter(root); replayed=[]
    def replay(**kw):
        prompt=kw['user']
        stage='dom1' if 'YOUR DIMENSION: DOM' in prompt else 'inv1' if 'YOUR DIMENSION: INV' in prompt else 'c1'
        raw,repaired=normalize_single_json_fence(responses[stage])
        replayed.append({'stage':stage,'format_repaired':repaired,'source_content':responses[stage]})
        return ChatResult(raw,'stop',None,0,'saved-gemma-response')
    prop=ActorImprover(adapter.spec.channels['proposer'],base_url='http://127.0.0.1:1',model='recorded',audit_dir=root/'receipts',provider=replay,policy_fields=True)
    result=run_domain('actor-planning',['left-mirror'],1,adapter=adapter,prop=prop,runs_root=adapter.spec.runs_root,library_root=root/'library',modes=('seq',))
    harness=adapter.spec.runs_root/'actor_demo-oc-seq1'/'left-mirror'/'harnesses'/'c1'
    checks={}
    for task in ('left-mirror','heldout-diagonal'):
        p=adapter.execute(task,harness,'check-'+task)
        checks[task]=json.loads((p/'verdict.json').read_text())
    out={'scope':'offline replay of saved responses with exact fence normalization through actual Harness2; not fresh model adaptation',
         'provider_calls':0,'run_domain':result,'replayed':replayed,'checks':checks,
         'limitations':['Recorded composer response did not see repaired upstream stages; a fresh causal model loop is not established','Scripted solver, planted fault, deterministic selector, no persistent learned memory']}
    Path('evidence/improver-saved-repair.json').write_text(json.dumps(out,indent=2)+'\n')
    assert len(replayed)==3 and all(v['valid'] for v in checks.values())
    print(json.dumps({'provider_calls':0,'stages':replayed,'checks':checks},indent=2))

if __name__=='__main__':main()

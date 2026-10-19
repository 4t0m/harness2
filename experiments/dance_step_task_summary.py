"""Replay structured-task evidence and compare a zero-provider feasible solver."""
import hashlib,json,statistics
from pathlib import Path
from harness2.dance_step_task import compile_task,verify_task,feasible_plans

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def span(v):return [min(v),max(v)]

def main():
    source=Path('evidence/dance-step-task-model-v1.json');data=json.loads(source.read_text())
    if not data.get('complete'):raise ValueError('incomplete trial')
    for p,h in data['sources'].items():
        if digest(p)!=h:raise ValueError('source changed')
    tasks={c['id']:c for c in data['cases']};replays=[]
    for i,c in enumerate(data['calls']):
        try:
            result=compile_task(c['content'],tasks[c['case_id']]['task']);verify_task(result,tasks[c['case_id']]['task']);accepted=True
            if result['receipt']!=c['receipt'] or result['placement']!=c['placement']:raise AssertionError('saved result mismatch')
        except ValueError as exc:
            accepted=False
            if str(exc)!=c.get('reason'):raise AssertionError('rejection mismatch')
        if accepted!=c['accepted']:raise AssertionError('acceptance mismatch')
        replays.append({'call_index':i,'accepted':accepted})
    groups=[]
    for m in data['models']:
        rr=[r for r in data['results'] if r['model']==m];cc=[c for c in data['calls'] if c['model']==m];first=[c for c in cc if c['attempt']==0]
        groups.append({'model':m,'tasks':len(rr),'first_accepted':sum(r['first_accepted'] for r in rr),'final_accepted':sum(r['final_accepted'] for r in rr),'calls':len(cc),
          'median_first_wall_seconds':statistics.median(c['wall_seconds'] for c in first),
          'median_total_wall_seconds':statistics.median(sum(data['calls'][i]['wall_seconds'] for i in r['call_indices']) for r in rr),
          'initial_prompt_tokens_range':span([c['prompt_eval_count'] for c in first]),'initial_input_characters_range':span([c['input_text_characters'] for c in first]),
          'output_tokens_range':span([c['eval_count'] for c in cc]),'total_prompt_tokens':sum(c['prompt_eval_count'] for c in cc),'total_output_tokens':sum(c['eval_count'] for c in cc)})
    deterministic=[]
    for c in data['cases']:
        plans=feasible_plans(c['task']);row={'case_id':c['id'],'supported':bool(plans),'feasible_plan_count':len(plans),'provider_calls':0}
        if bool(plans)!=c['feasible']:raise AssertionError('feasibility mismatch')
        if plans:
            # Fixed lexicographic selection; this is not a subjective quality choice.
            result=compile_task(json.dumps({'moves':plans[0]}),c['task']);verify_task(result,c['task']);row.update(moves=plans[0],receipt=result['receipt'],placement=result['placement'])
        deterministic.append(row)
    summary={'source_sha256':digest(source),'scope':'Host-approved structured constraints, not natural-language extraction. Host solver enumerates at most256plans and selects first feasible; no model reasoning, taste, live execution or H2 adaptation inferred.',
      'models':groups,'raw_replays':replays,'deterministic_baseline':deterministic,'max_search_plans_per_task':256,'paid_provider_calls':0}
    Path('evidence/dance-step-task-summary-v1.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(groups,indent=2));print('Replayed',len(replays),'raw calls; deterministic feasible',sum(r['supported'] for r in deterministic),'unsupported',sum(not r['supported'] for r in deterministic))

if __name__=='__main__':main()

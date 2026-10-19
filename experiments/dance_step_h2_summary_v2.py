"""Reproduce H2 heldout task outcomes, raw checks and native token costs."""
import hashlib,json,statistics
from pathlib import Path
from harness2.dance_step_h2 import verdict
from harness2.dance_guidance_admission import choose_admitted
from harness2.dance_step_task import feasible_plans,compile_task,verify_task

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def span(xs):return [min(xs),max(xs)]

def compact(raw,task):
    v=verdict(raw,task);compiled=v.pop('compiled',None)
    if compiled is not None:v.update(receipt=compiled['receipt'],placement=compiled['placement'])
    return v

def main():
    path=Path('evidence/dance-step-h2-v2.json');data=json.loads(path.read_text())
    if not data.get('complete'):raise ValueError('incomplete trial')
    for p,h in data['sources'].items():
        if digest(p)!=h:raise ValueError('source changed: '+p)
    dev=data['development_case'];task={'task':dev['task'],'request':dev['request']}
    admission=choose_admitted(data['development_candidates'],task)
    if admission!=data['admission'] or admission['selected']['guidance']!=data['selected_guidance']:raise ValueError('admission mismatch')
    if admission['selected']['guidance_sha256']!=data['selected_guidance_sha256']:raise ValueError('selected guidance hash mismatch')
    for candidate in data['development_candidates']:
        receipt=candidate['receipt'];v=verdict(receipt['content'],task)
        if v['valid']!=receipt['verdict']['valid'] or v['reason']!=receipt['verdict']['reason']:raise ValueError('development verdict mismatch')
    cases={c['id']:c for c in data['frozen_evaluation']};calls=data['calls'];groups=[]
    for result in data['evaluation']:
        case=cases[result['case_id']];public={'task':case['task'],'request':case['request']}
        for a in result['attempts']:
            call=calls[a['call_index']]
            if call['finish_reason']!='stop':raise ValueError('incomplete call requires separate classification')
            if compact(call['content'],public)!=a['verdict']:raise ValueError('raw verdict drift')
    for model in data['local_metadata']:
        for condition in ['fixed','adapted']:
            rows=[r for r in data['evaluation'] if r['model']==model and r['condition']==condition]
            first=[calls[r['attempts'][0]['call_index']] for r in rows]
            allcalls=[calls[a['call_index']] for r in rows for a in r['attempts']]
            groups.append({'model':model,'condition':condition,'tasks':len(rows),'first_accepted':sum(r['attempts'][0]['verdict']['valid'] for r in rows),'final_accepted':sum(r['attempts'][-1]['verdict']['valid'] for r in rows),'calls':len(allcalls),
              'median_first_provider_seconds':statistics.median(c['wall_seconds'] for c in first),'median_total_provider_seconds':statistics.median(sum(calls[a['call_index']]['wall_seconds'] for a in r['attempts']) for r in rows),
              'initial_prompt_tokens_range':span([c['prompt_eval_count'] for c in first]),'output_tokens_range':span([c['eval_count'] for c in allcalls]),'initial_input_characters_range':span([c['input_text_characters'] for c in first]),'total_prompt_tokens':sum(c['prompt_eval_count'] for c in allcalls),'total_output_tokens':sum(c['eval_count'] for c in allcalls)})
    deterministic=[]
    for c in cases.values():
        plans=feasible_plans(c['task']);compiled=compile_task(json.dumps({'moves':plans[0]}),c['task']);verify_task(compiled,c['task']);deterministic.append({'case_id':c['id'],'feasible_plans':len(plans),'receipt':compiled['receipt']})
    editor=[c for c in calls if c['model_requested'] not in data['local_metadata']]
    if any(c['id'] in r['system']+'\n'+r['user'] for c in cases.values() for r in editor):raise ValueError('eval id in editor context')
    compose=editor[-1]
    for label in ('inv1','dom1'):
        for name in ('harness.diff','rollout.md'):
            if 'pool/'+label+'/'+name not in compose['user']:raise ValueError('missing composed development pool file')
    editor_indices=[i for i,r in enumerate(calls) if r['model_requested'] not in data['local_metadata']]
    eval_indices=[a['call_index'] for r in data['evaluation'] for a in r['attempts']]
    if max(editor_indices)>=min(eval_indices):raise ValueError('editor ran after evaluation started')
    summary={'source_sha256':digest(path),'conditions':groups,'reported_editor_cost_usd':sum(c['reported_cost_usd'] for c in editor),'editor_calls':len(editor),'total_calls':len(calls),
      'admission':admission,'composer_pool_in_request':True,'development':[{'run_id':r['run_id'],'valid':r.get('verdict',{}).get('valid',False),'reason':r.get('verdict',{}).get('reason',r.get('error'))} for r in data['development_receipts']],
      'guidance_changed':data['guidance_changed'],'selected_guidance':data['selected_guidance'],'deterministic_solver':deterministic,'evaluation_ids_absent_from_all_editor_requests':True,'editor_completed_before_evaluation':True,
      'scope':'Frozen within-family eval; raw replies rechecked. H2 final selection at k=1 is scripted; independent development admission precedes evaluation. Composer sees both development candidates; this combined pipeline does not isolate the effects of context repair and admission. Deterministic solver success is separate from local-model capability. Provider times exclude host validation.'}
    Path('evidence/dance-step-h2-summary-v2.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['deterministic_solver','selected_guidance']},indent=2))

if __name__=='__main__':main()

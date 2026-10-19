import json,statistics,hashlib
from pathlib import Path
from harness2.actor_staging import _unique_pairs,_reject_constant
r=json.loads(Path('evidence/actor-staging-steps-v1.json').read_text());d=json.loads(Path('evidence/actor-staging-question-order-v1.json').read_text())
assert r['complete'] and d['complete'] and len(r['calls'])==120 and len(d['calls'])==16
out={'scope':r['scope'],'source_sha256':hashlib.sha256(Path('evidence/actor-staging-steps-v1.json').read_bytes()).hexdigest(),'conditions':[],'paired':[],'diagnostic':[],'total_local_calls':136,'paid_provider_calls':0}
for m in r['models']:
 for cond in ['one_shot','four_questions']:
  rs=[x for x in r['results'] if x['model']==m and x['condition']==cond];a={'model':m,'condition':cond,'n':len(rs),'correct':sum(x['semantic_correct'] for x in rs),'compiled':sum(x['compiled'] for x in rs),'median_wall_seconds':statistics.median(x['wall_seconds'] for x in rs)}
  for k in ['prompt_eval_count','eval_count','input_text_characters']:
   vs=[sum(r['calls'][i].get(k,0) for i in x['call_indices']) for x in rs];a[k]={'min_total_per_plan':min(vs),'max_total_per_plan':max(vs),'median_total_per_plan':statistics.median(vs)}
  a['compile_failures']=[{'case_id':x['case_id'],'reason':x['reason']} for x in rs if not x['compiled']]
  if cond=='four_questions':
   counts=[0,0,0,0]
   for x in rs:
    case=next(c for c in r['cases'] if c['id']==x['case_id']);p=[json.loads(r['calls'][i]['content'],object_pairs_hook=_unique_pairs,parse_constant=_reject_constant) for i in x['call_indices']]
    left=next(v['actor_id'] for v in case['expected']['placements'] if v['side']=='left');counts[0]+=p[0]=={'left':left}
    for slot,c in enumerate(case['expected']['cues']):counts[slot+1]+=p[slot+1]=={'actor':c['actor_id'],'gesture':c['gesture'],'variation':c['variation']}
   a['piece_correct_placement_cue0_cue1_cue2']=counts
  out['conditions'].append(a)
 a={x['case_id']:x for x in r['results'] if x['model']==m and x['condition']=='one_shot'};b={x['case_id']:x for x in r['results'] if x['model']==m and x['condition']=='four_questions'}
 out['paired'].append({'model':m,'split_gains':[k for k in a if not a[k]['semantic_correct'] and b[k]['semantic_correct']],'split_regressions':[k for k in a if a[k]['semantic_correct'] and not b[k]['semantic_correct']]})
 for order in ['early','late']:
  cs=[c for c in d['calls'] if c['model']==m and c['order']==order]
  for c in cs:json.loads(c['raw_response']['message']['content'],object_pairs_hook=_unique_pairs,parse_constant=_reject_constant)
  out['diagnostic'].append({'model':m,'order':order,'correct':sum(c['correct'] for c in cs),'n':len(cs)})
Path('evidence/actor-staging-steps-summary-v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

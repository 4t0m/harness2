"""Replay motif proposals, keep grammar and brief accuracy distinct."""
import hashlib,json,statistics
from pathlib import Path
from harness2.dance_motif_score import compile_intent,compile_expanded,verify_score
from experiments.dance_motif_cases import score_intent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def span(xs):return [min(xs),max(xs)]
def main():
 path=Path('evidence/dance-motif-model-v1.json');d=json.loads(path.read_text())
 if not d.get('complete'):raise ValueError('incomplete trial')
 for p,h in d['sources'].items():
  if sha(p)!=h:raise ValueError('source drift '+p)
 cases={c['id']:c for c in d['cases']};calls=d['calls'];seen=[]
 for r in d['results']:
  if not 1<=len(r['attempts'])<=2:raise ValueError('attempt count')
  for attempt,i in enumerate(r['attempts']):
   row=calls[i];seen.append(i)
   if any(row[k]!=r[k] for k in ['model','case_id','condition']) or row['attempt']!=attempt:raise ValueError('call binding')
   if row['messages'][:2]!=[{'role':'system','content':d['systems'][r['condition']]},{'role':'user','content':cases[r['case_id']]['request']}]:raise ValueError('prompt mismatch')
   if attempt and calls[r['attempts'][0]]['compiled']:raise ValueError('semantic oracle triggered correction')
   if row.get('finish_reason')!='stop':continue
   compiler=compile_intent if r['condition']=='compact' else compile_expanded
   try:result=compiler(row['content']);verify_score(result)
   except ValueError as exc:
    if row['compiled'] or str(exc)!=row['error']:raise ValueError('compiler rejection mismatch')
   else:
    if not row['compiled'] or result['intent']!=row['intent'] or result['receipt']!=row['motion_receipt']:raise ValueError('motion replay mismatch')
    errors=score_intent(result['intent'],cases[r['case_id']])
    if errors!=row['violations'] or bool(errors)==row['brief_correct']:raise ValueError('brief replay mismatch')
 if sorted(seen)!=list(range(len(calls))):raise ValueError('unbound calls')
 groups=[]
 for model in list(d['local_metadata'])+list(d['hosted_metadata']):
  for condition in ['compact','expanded']:
   rows=[r for r in d['results'] if r['model']==model and r['condition']==condition]
   if len(rows)!=len(cases) or len({r['case_id'] for r in rows})!=len(cases):raise ValueError('case coverage')
   first=[calls[r['attempts'][0]] for r in rows];last=[calls[r['attempts'][-1]] for r in rows];allcalls=[calls[i] for r in rows for i in r['attempts']]
   groups.append({'model':model,'condition':condition,'tasks':len(rows),'first_compiled':sum(c['compiled'] for c in first),'final_compiled':sum(c['compiled'] for c in last),'first_brief_correct':sum(c['brief_correct'] for c in first),'final_brief_correct':sum(c['brief_correct'] for c in last),'calls':len(allcalls),
    'initial_prompt_tokens_range':span([c['usage']['prompt_tokens'] for c in first]),'output_tokens_range':span([c['usage']['completion_tokens'] for c in allcalls]),
    'initial_characters_range':span([c['input_text_characters'] for c in first]),'total_input_tokens':sum(c['usage']['prompt_tokens'] for c in allcalls),'total_output_tokens':sum(c['usage']['completion_tokens'] for c in allcalls),
    'median_first_provider_seconds':statistics.median(c['provider_seconds'] for c in first),'median_total_provider_seconds':statistics.median(sum(calls[i]['provider_seconds'] for i in r['attempts']) for r in rows),'median_native_decode_tokens_per_second':statistics.median(c['raw_response']['eval_count']/(c['raw_response']['eval_duration']/1e9) for c in allcalls) if model in d['local_metadata'] else None,'hosted_cost_usd':sum(c.get('reported_cost_usd',0) for c in allcalls)})
 report={'scope':'Raw proposal replay. Tool representation comparison; compiler owns movement expansion and grammar. Brief fidelity is an offline metric, not aesthetic quality. Hosted and local runtimes/schema implementations differ; latency is not a hardware comparison.','source_sha256':sha(path),'summary_source_sha256':sha(__file__),'conditions':groups,'total_calls':len(calls),'hosted_calls':sum(c['model'] in d['hosted_metadata'] for c in calls),'reported_hosted_cost_usd':d['reported_hosted_cost_usd'],'complete':True}
 Path('evidence/dance-motif-summary-v1.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

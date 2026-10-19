"""Replay raw scores against sampled playback without consulting runtime internals."""
import hashlib,json,statistics
from pathlib import Path
from harness2.dance_motif_score import compile_intent,verify_score
from experiments.dance_motif_runtime_cases import score_response

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 path=Path('evidence/dance-motif-runtime-v1.json');d=json.loads(path.read_text())
 if not d.get('complete'):raise ValueError('incomplete live probe')
 for p,h in d['sources'].items():
  if sha(p)!=h:raise ValueError('source drift '+p)
 cases={c['id']:c for c in d['cases']};compiled={};rows=[]
 for call in d['calls']:
  if call.get('finish_reason')!='stop' or call.get('error'):raise ValueError('failed call needs separate classification')
  case=cases[call['case_id']];role=call['role']
  if call['user']!=case[role]['request']:raise ValueError('model request mismatch')
  c=compile_intent(call['content']);verify_score(c);compiled[(call['case_id'],role)]=c
  v=score_response(call['content'],case[role]['expected_intent'])
  if v!=call['brief_violations'] or bool(v)==call['brief_correct']:raise ValueError('brief score drift')
 for run in d['runs']:
  cid=run['case_id'];calls={c['role']:c for c in d['calls'] if c['case_id']==cid}
  if set(calls)!={'initial','replacement','delayed_after_stop'}:raise ValueError('call coverage')
  initial,replace,late=(calls[r] for r in ['initial','replacement','delayed_after_stop'])
  epoch=run['playback_epoch_ms'];switch=replace['delivery'].get('switch_at_ms')
  stops=[e for e in run['events'] if e['kind']=='interrupt']
  if len(stops)!=1:raise ValueError('interrupt count')
  stop=stops[0];stop_ms=stop['at_ms']
  if initial['delivery']['status']!='applied' or initial['delivered_at_ms']!=epoch:raise ValueError('initial admission')
  if replace['delivery']['status']!='queued' or switch!=epoch+4000 or replace['delivered_at_ms']>=switch:raise ValueError('replacement missed first boundary')
  if not late['request_at_ms']<stop_ms<late['provider_finished_ms']<=late['delivered_at_ms']:raise ValueError('late inference did not actually straddle stop')
  if late['delivery']['status']!='rejected_stale':raise ValueError('late reply was not rejected')
  if not switch<stop_ms<epoch+7000:raise ValueError('stop timing coverage')
  for role in ['initial','replacement']:
   if calls[role]['delivery']['score_sha256']!=compiled[(cid,role)]['receipt']['sequence_sha256']:raise ValueError('admitted score hash')
  def expected(at):
   role='replacement' if at>=switch else 'initial';start=switch if role=='replacement' else epoch
   idx=min((at-start)//50,320)
   return compiled[(cid,role)]['sequence']['frames'][idx],role,idx
  freeze,freeze_role,freeze_index=expected(stop_ms)
  if stop['sample']['frame']!=freeze or stop['sample']['status']!='frozen':raise ValueError('stop captured wrong pose')
  samples=run['samples']
  if len(samples)!=141:raise ValueError('sample count')
  post=0;before=0;after=0
  for index,row in enumerate(samples):
   s=row['sample'];at=s['now_ms']
   if row['target_relative_ms']!=index*50 or row['actual_relative_ms']!=at-epoch or row['lateness_ms']!=at-epoch-index*50:raise ValueError('sample timing bookkeeping')
   if at>=stop_ms:
    if s['status']!='frozen' or s['frame']!=freeze:raise ValueError('pose changed after stop')
    post+=1
   else:
    frame,role,source_index=expected(at)
    if s['frame']!=frame or s['source_frame_index']!=source_index or s['score_sha256']!=compiled[(cid,role)]['receipt']['sequence_sha256']:raise ValueError('sample differs from admitted source')
    before+=at<switch;after+=at>=switch
  if not(before and after and post):raise ValueError('missing playback phase')
  if run['snapshot']['pending'] is not None or run['snapshot']['queued_switch_ms'] is not None:raise ValueError('stop left pending work')
  if run['final_snapshot']['frame']!=freeze:raise ValueError('late completion changed final pose')
  usages=[c['raw_response'] for c in calls.values()]
  rows.append({'case_id':cid,'model':run['model'],'brief_correct':sum(c['brief_correct'] for c in calls.values()),'calls':3,'replacement_switch_relative_ms':switch-epoch,'replacement_ready_relative_ms':replace['delivered_at_ms']-epoch,'interrupt_relative_ms':stop_ms-epoch,'stale_completion_after_stop_ms':late['delivered_at_ms']-stop_ms,'sample_count':len(samples),'post_stop_frozen_samples':post,'stop_source_frame':freeze_index,'max_sample_lateness_ms':max(r['lateness_ms'] for r in samples),'median_sample_lateness_ms':statistics.median(r['lateness_ms'] for r in samples),'initial_context_tokens':[u['prompt_eval_count'] for u in usages],'output_tokens':[u['eval_count'] for u in usages],'provider_seconds':[c['provider_seconds'] for c in calls.values()],'preparation_seconds':[c['preparation_seconds'] for c in calls.values()],'control_checks_pass':True})
 out={'source_sha256':sha(path),'checker_sha256':sha(__file__),'scope':'Independent replay from raw accepted scores and wall-clock event/sample logs. Finite orchestration; no persistent display, aesthetic judgment, repeated latency benchmark or H2 adaptation.','runs':rows,'provider_calls':len(d['calls']),'hosted_calls':0,'complete':True}
 Path('evidence/dance-motif-runtime-check-v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

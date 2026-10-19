"""Finite wall-clock sampling while real local inference prepares replacements."""
import copy,hashlib,json,threading,time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from experiments.dance_motif_probe import SYSTEMS,SCHEMAS

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 from harness2.dance_motif_runtime import MotifRuntime
 from experiments.dance_motif_runtime_cases import CASES,score_response
 out=Path('evidence/dance-motif-runtime-v1.json')
 if out.exists():raise ValueError('refusing overwrite')
 with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:tags=json.load(r)['models']
 sources=['harness2/dance_motif_runtime.py','harness2/dance_motif_score.py','harness2/dance_phrases.py','harness2/dance_motion.py','harness2/bounded_json_http.py','experiments/dance_motif_probe.py','experiments/dance_motif_runtime_cases.py','experiments/dance_motif_runtime_probe.py']
 report={'scope':'Finite real wall-clock inference and host playback sampling. Video is rendered afterward. No persistent viewer, H2 refinement or continuous service benchmark.',
  'sources':{p:digest(p) for p in sources},'cases':copy.deepcopy(CASES),'models':{c['model']:{k:next(t for t in tags if t['name']==c['model']).get(k) for k in ['name','digest','size']} for c in CASES},
  'max_calls':6,'max_provider_seconds':20,'max_output_tokens':128,'provider_calls_paid':0,'sample_period_ms':50,'playback_observation_ms':7000,'planned_events_relative_ms':{'replacement_request':500,'third_request':4250,'interrupt':4350},'calls':[],'runs':[]}
 save_lock=threading.RLock()
 def save():
  with save_lock:out.write_text(json.dumps(report,indent=2)+'\n')
 save()
 try:
  for case in CASES:
   rt=MotifRuntime();gate=threading.RLock();origin=time.perf_counter()
   run={'case_id':case['id'],'model':case['model'],'events':[],'samples':[],'request_ids':{}};report['runs'].append(run)
   def now():return int((time.perf_counter()-origin)*1000)
   def event(kind,**fields):run['events'].append({'kind':kind,**fields})
   def request(role):
    with gate:
     at=now();req=rt.request(at,5000);run['request_ids'][role]=req['request_id'];event('request',role=role,at_ms=at,request=req)
    return req
   def infer(role,req):
    row={'case_id':case['id'],'model':case['model'],'role':role,'request_id':req['request_id'],'system':SYSTEMS['compact'],'user':case[role]['request'],'request_at_ms':req['deadline_ms']-5000}
    with save_lock:
     if len(report['calls'])>=6:raise RuntimeError('call cap')
     report['calls'].append(row);save()
    started=time.perf_counter();row['provider_start_ms']=now()
    try:
     raw=request_json('http://127.0.0.1:11434/api/chat',{'model':case['model'],'messages':[{'role':'system','content':row['system']},{'role':'user','content':row['user']}],'stream':False,'think':False,'format':SCHEMAS['compact'],'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
     row.update(raw_response=raw,content=raw.get('message',{}).get('content',''),finish_reason=raw.get('done_reason'),provider_seconds=time.perf_counter()-started,provider_finished_ms=now())
     if row['finish_reason']!='stop':raise ValueError('incomplete model response')
     prep=time.perf_counter();prepared=rt.prepare(row['content']);row.update(preparation_seconds=time.perf_counter()-prep,prepared_at_ms=now())
     with gate:
      at=now();result=rt.deliver_prepared(req['request_id'],prepared,at);row['delivery']=result;row['delivered_at_ms']=at;event('delivery',role=role,at_ms=at,result=result)
    except Exception as exc:
     row.update(error_type=type(exc).__name__,error=str(exc))
     with gate:event('inference_error',role=role,at_ms=now(),error_type=type(exc).__name__)
    finally:
     row['worker_seconds']=time.perf_counter()-started;save()
     print(json.dumps({k:row.get(k) for k in ['model','role','provider_seconds','preparation_seconds','delivery','brief_correct','error']}),flush=True)
   initial=request('initial');infer('initial',initial)
   with gate:
    state=rt.sample(now());run['initial_state']=state
    if state['status']!='playing':raise RuntimeError('initial score not playing')
    epoch=state['epoch_ms'];run['playback_epoch_ms']=epoch
   workers=[];launched=set();stopped=False
   for index in range(141):
    due=epoch+index*50
    remaining=(due-now())/1000
    if remaining>0:time.sleep(remaining)
    for role,trigger in [('replacement',500),('delayed_after_stop',4250)]:
     if index*50>=trigger and role not in launched:
      req=request(role);worker=threading.Thread(target=infer,args=(role,req),daemon=True);workers.append(worker);worker.start();launched.add(role)
    with gate:
     if index*50>=4350 and not stopped:
      at=now();frozen=rt.interrupt(at);event('interrupt',at_ms=at,sample=frozen);stopped=True
     at=now();sample=rt.sample(at);run['samples'].append({'target_relative_ms':index*50,'actual_relative_ms':at-epoch,'lateness_ms':at-due,'sample':sample})
   for worker in workers:worker.join(timeout=22)
   if any(worker.is_alive() for worker in workers):raise RuntimeError('worker still running after bounded observation')
   with gate:run['final_snapshot']=rt.sample(now());run['snapshot']=rt.snapshot()
   # Offline scoring happens after timed sampling, outside control decisions.
   for row in report['calls']:
    if row['case_id']==case['id'] and row.get('finish_reason')=='stop':
     row['brief_violations']=score_response(row['content'],case[row['role']]['expected_intent']);row['brief_correct']=not row['brief_violations']
   run['complete']=True;save()
  report['complete']=True
 except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
 finally:save();print(json.dumps({'complete':report.get('complete'),'calls':len(report['calls']),'error':report.get('error')}),flush=True)

if __name__=='__main__':main()

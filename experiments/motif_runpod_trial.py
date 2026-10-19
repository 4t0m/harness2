"""Bounded single-pod qualification; credentials and endpoints remain private.

One allocation attempt, no replacement hardware or retry allocation. The remote
termination timestamp includes image pulls and model startup. A local supervisor
also terminates in finally and verifies disappearance. No account key goes to pod.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
import re
from pathlib import Path
import secrets
import signal
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError

GRAPHQL='https://api.runpod.io/graphql'
REST='https://rest.runpod.io/v1'
GPU='NVIDIA GeForce RTX 5090'
# Set only after the Linux amd64 image manifest is verified against the index.
IMAGE='vllm/vllm-openai@sha256:a77ed1c057e0458dbed205dea0ecaacd0ca2405721be6e58182bf9ee42c359f6'
MODEL='nvidia/Qwen3.6-35B-A3B-NVFP4'
REVISION='6c7f09d4036e97393f82e9f9ecd1a5c35ca5ee92'
MAX_RATE=2.0
CAP_USD=5.0

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def http(method,url,token,body=None,timeout=15):
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json',
             'Accept':'application/json','User-Agent':'Harness2-Motif-Experiment/1.0'}
    data=None if body is None else json.dumps(body,allow_nan=False).encode()
    request=Request(url,data=data,method=method,headers=headers)
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=timeout) as r:
            raw=r.read(1048577)
            if len(raw)>1048576: raise RuntimeError('response_bound')
            return json.loads(raw) if raw else None
    except HTTPError as e:
        raise RuntimeError('http_status_'+str(e.code)) from None
    except Exception as e:
        raise RuntimeError(type(e).__name__) from None


def gql(query,variables=None):
    raw=http('POST',GRAPHQL,os.environ['RUNPOD_API_KEY'],{'query':query,'variables':variables or {}})
    if type(raw) is not dict or raw.get('errors') or type(raw.get('data')) is not dict:
        raise RuntimeError('graphql_operation_failed')
    return raw['data']


def pods():
    return gql('query {myself {pods {id name desiredStatus costPerHr adjustedCostPerHr gpuCount volumeInGb containerDiskInGb networkVolumeId}}}')['myself']['pods']


def preflight():
    account=gql('query {myself {clientBalance currentSpendPerHr pods {id}}}')['myself']
    if account['pods'] or float(account['clientBalance'])<CAP_USD:
        raise RuntimeError('account_preflight_failed')
    quote=gql('query {gpuTypes(input:{id:"NVIDIA GeForce RTX 5090"}) {id secure:lowestPrice(input:{gpuCount:1,secureCloud:true}) {stockStatus uninterruptablePrice}}}')['gpuTypes']
    selected=next(row for row in quote if row['id']==GPU)['secure']
    price=selected.get('uninterruptablePrice')
    if type(price) not in (int,float) or not math.isfinite(price) or not 0<price<MAX_RATE:
        raise RuntimeError('rate_preflight_failed')
    return {'gpu':GPU,'quote':selected,'balance_covers_cap':True,'pod_count':0}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--private-dir',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not args.execute or IMAGE=='UNQUALIFIED':
        raise ValueError('deployment is not qualified')
    root=args.private_dir
    if not root.is_absolute() or root.exists(): raise ValueError('new absolute private directory required')
    root.mkdir(parents=True,mode=0o700)
    os.chmod(root,0o700)
    name='h2-motif-'+secrets.token_hex(5)
    private={'name':name,'pod_id':None,'template_id':None}
    report={'scope':__doc__,'planned_spend_ceiling_usd':CAP_USD,'provider_billing_cap_enforced':False,'max_rate_usd_per_hour':MAX_RATE,
            'total_provider_lifetime_seconds':1800,'local_cleanup_starts_by_seconds':1500,'readiness_cutoff_seconds':1080,
            'storage_assumption_usd_per_gb_month':0.10,'storage_gb':100,
            'budget_basis':'Bound rate and lifetime, provider deadline request and verified deletion; not a provider account spending limit',
            'allocation_attempts':0,'events':[],'pod_absent_verified':False,
            'template_absent_verified':False,'model_calls':0}
    def save():
        (root/'private-state.json').write_text(json.dumps(private,indent=2)+'\n')
        os.chmod(root/'private-state.json',0o600)
        (root/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    def event(kind,**fields):
        report['events'].append({'utc':datetime.now(timezone.utc).isoformat(),'kind':kind,**fields})
        save()
        print(json.dumps({'kind':kind,**fields}),flush=True)
    def terminate():
        if private['pod_id']:
            try:
                gql('mutation($input:PodTerminateInput!){podTerminate(input:$input)}',{'input':{'podId':private['pod_id']}})
                return True
            except Exception:
                return False
        return False
    def absent_by_id():
        if not private['pod_id']: return False
        try:
            http('GET',REST+'/pods/'+private['pod_id'],os.environ['RUNPOD_API_KEY'])
        except RuntimeError as exc:
            return str(exc)=='http_status_404'
        return False
    def watchdog_cleanup():
        for _ in range(3):
            terminate()
            if absent_by_id(): return
            time.sleep(5)
    def interrupted(_signum,_frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted)
    watchdog=None
    try:
        report['preflight']=preflight()
        source=Path('experiments/motif_pod_gate.py').read_bytes()
        report['gate_sha256']=hashlib.sha256(source).hexdigest()
        report['image']=IMAGE
        report['checkpoint']={'model':MODEL,'revision':REVISION}
        launcher="import base64;exec(compile(base64.b64decode('"+base64.b64encode(source).decode()+"'),'<motif-gate>','exec'))"
        template={'name':name,'imageName':IMAGE,'category':'NVIDIA','containerDiskInGb':100,
                  'volumeInGb':0,'isPublic':False,'isServerless':False,'env':{},
                  'dockerEntrypoint':['python3','-u','-c',launcher],
                  'dockerStartCmd':['--startup-timeout','600'],
                  'ports':['8080/http']}
        try:
            made=http('POST',REST+'/templates',os.environ['RUNPOD_API_KEY'],template)
            private['template_id']=made['id']; save()
        except Exception:
            # Never repeat creation after an ambiguous response.
            known=http('GET',REST+'/templates',os.environ['RUNPOD_API_KEY'])
            matches=[t for t in known if t.get('name')==name]
            if len(matches)==1: private['template_id']=matches[0]['id']; save()
            raise
        readback=http('GET',REST+'/templates/'+private['template_id'],os.environ['RUNPOD_API_KEY'])
        for field in ('dockerEntrypoint','dockerStartCmd','ports','imageName'):
            if readback.get(field)!=template[field]: raise RuntimeError('template_readback_mismatch_'+field)
        stored=gql('query{myself{podTemplates{id isPublic volumeInGb containerDiskInGb isServerless}}}')['myself']['podTemplates']
        exact=[row for row in stored if row['id']==private['template_id']]
        if (len(exact)!=1 or exact[0]['isPublic'] is not False or
                exact[0]['volumeInGb']!=0 or exact[0]['containerDiskInGb']!=100 or
                exact[0]['isServerless'] is not False):
            raise RuntimeError('template_privacy_or_storage_mismatch')
        report['template_privacy_and_storage_verified_via_graphql']=True
        event('private_template_verified')
        report['preflight']=preflight() # Refresh immediately before paid allocation.
        token=secrets.token_urlsafe(32)
        os.environ['MOTIF_GATE_TOKEN']=token
        started=time.monotonic()
        deadline=datetime.now(timezone.utc)+timedelta(seconds=1800)
        report['terminate_after_utc']=deadline.isoformat().replace('+00:00','Z')
        report['allocation_attempts']=1
        request={'name':name,'templateId':private['template_id'],'imageName':IMAGE,
                 'cloudType':'SECURE','gpuTypeId':GPU,'gpuCount':1,'containerDiskInGb':100,
                 'volumeInGb':0,'ports':'8080/http','startSsh':False,'startJupyter':False,
                 'minCudaVersion':'13.0','terminateAfter':deadline.isoformat().replace('+00:00','Z'),
                 'env':[{'key':'MOTIF_GATE_TOKEN','value':token},
                        {'key':'VLLM_HAS_FLASHINFER_CUBIN','value':'1'},
                        {'key':'HF_HOME','value':'/tmp/motif-hf-cache'}]}
        event('allocation_requested',terminate_after_utc=report['terminate_after_utc'])
        try:
            made=gql('mutation($input:PodFindAndDeployOnDemandInput){podFindAndDeployOnDemand(input:$input){id name costPerHr adjustedCostPerHr gpuCount volumeInGb containerDiskInGb networkVolumeId}}',{'input':request})['podFindAndDeployOnDemand']
            if type(made) is not dict: raise RuntimeError('allocation_returned_no_pod')
            private['pod_id']=made['id'];save()
        except Exception:
            for _ in range(6):
                matches=[p for p in pods() if p['name']==name]
                if len(matches)==1:
                    private['pod_id']=matches[0]['id'];save();break
                time.sleep(5)
            raise
        watchdog=threading.Timer(max(1,1500-(time.monotonic()-started)),watchdog_cleanup)
        watchdog.daemon=True;watchdog.start()
        rate=made.get('adjustedCostPerHr') or made.get('costPerHr')
        if (type(rate) not in (int,float) or not math.isfinite(rate) or not 0<rate<=MAX_RATE or
            made['gpuCount']!=1 or made['volumeInGb']!=0 or made['containerDiskInGb']!=100 or made['networkVolumeId']):
            raise RuntimeError('allocated_bounds_mismatch')
        report['allocated_rate_usd_per_hour']=rate
        report['thirty_minute_rate_plus_disk_estimate_usd']=rate*0.5+100*0.10/(30*24)*0.5
        report['allocation_elapsed_seconds']=time.monotonic()-started
        # Request acceptance is recorded separately from schedule execution/readback.
        report['terminate_after_requested']=True
        event('pod_allocated',rate_usd_per_hour=rate)
        origin='https://'+private['pod_id']+'-8080.proxy.runpod.net'
        private['origin']=origin;save()
        ready=False
        while time.monotonic()-started<1080:
            try:
                status=http('GET',origin+'/trial-status',token,timeout=8)
                report['last_remote_status']=status
                if status.get('child_exit_code') is not None:
                    raise RuntimeError('model_process_exited')
                http('GET',origin+'/health',token,timeout=8)
                registered=http('GET',origin+'/v1/models',token,timeout=8)
                if not any(m.get('id')=='qwen' for m in registered.get('data',[])):
                    raise RuntimeError('model_registration_mismatch')
                status=http('GET',origin+'/trial-status',token,timeout=8)
                report['last_remote_status']=status
                if status.get('vllm_ready'):
                    ready=True;break
                if status.get('child_exit_code') is not None: raise RuntimeError('model_process_exited')
            except RuntimeError as e:
                if str(e) in ('model_process_exited','model_registration_mismatch'): raise
            event('waiting_for_model',elapsed_seconds=round(time.monotonic()-started))
            time.sleep(15)
        report['ready']=ready;report['ready_elapsed_seconds']=time.monotonic()-started
        if not ready: raise RuntimeError('readiness_deadline')
        facts=report['last_remote_status'].get('gpu',{})
        if ('RTX 5090' not in str(facts.get('name')) or
                int(str(facts.get('driver','0')).split('.')[0])<580):
            raise RuntimeError('hardware_identity_mismatch')
        event('model_ready',elapsed_seconds=round(report['ready_elapsed_seconds']))
        from harness2.motif_remote_provider import OpenAICompatibleMotifProvider
        from experiments.motif_remote_probe import run
        provider=OpenAICompatibleMotifProvider(origin+'/v1/chat/completions','qwen','MOTIF_GATE_TOKEN',checkpoint_name=MODEL+'@'+REVISION)
        probe=run(provider,root/'probe.json')
        report['model_calls']=len(probe['calls']);save()
        if not probe['complete'] or probe['summary']['compiled']!=8: raise RuntimeError('probe_failed')
        from harness2.motif_viewer import MotifViewer
        viewer=MotifViewer('qwen',root/'viewer.json',lifetime=180,provider=provider,
                          provider_metadata=provider.metadata,
                          extra_source_files=('harness2/motif_remote_provider.py','experiments/motif_remote_probe.py'))
        event('viewer_ready',local_viewer_url=viewer.url)
        viewer.serve()
        report['viewer_calls']=len(json.loads((root/'viewer.json').read_text())['calls'])
    except BaseException as exc:
        event('trial_ended',error_type=type(exc).__name__,reason=str(exc) if str(exc) in (
            'readiness_deadline','model_process_exited','probe_failed','allocated_bounds_mismatch',
            'allocation_returned_no_pod','graphql_operation_failed','account_preflight_failed',
            'rate_preflight_failed','hardware_identity_mismatch','model_registration_mismatch') or
            re.fullmatch(r'(?:http_status_[0-9]{3}|template_readback_mismatch_[A-Za-z]+|template_privacy_or_storage_mismatch)',str(exc)) else 'see_stage')
    finally:
        if watchdog: watchdog.cancel()
        for _ in range(3):
            terminate()
            try:
                matches=[p for p in pods() if p['name']==name]
                if not matches and absent_by_id():
                    time.sleep(2)
                    report['pod_absent_verified']=absent_by_id()
                    if report['pod_absent_verified']: break
                if not matches and report['allocation_attempts']==0:
                    report['pod_absent_verified']=True;break
                if not private['pod_id'] and len(matches)==1:
                    private['pod_id']=matches[0]['id'];save()
            except Exception: pass
            time.sleep(5)
        if private['template_id']:
            try:
                http('DELETE',REST+'/templates/'+private['template_id'],os.environ['RUNPOD_API_KEY'])
                left=http('GET',REST+'/templates',os.environ['RUNPOD_API_KEY'])
                report['template_absent_verified']=not any(t['id']==private['template_id'] for t in left)
            except Exception: pass
        report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        event('cleanup',pod_absent_verified=report['pod_absent_verified'],template_absent_verified=report['template_absent_verified'])
        os.environ.pop('MOTIF_GATE_TOKEN',None)

if __name__=='__main__':main()

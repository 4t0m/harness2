"""Bounded hosted-model comparison on the frozen six-image local vision pilot."""
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import time
from urllib.request import Request, urlopen
from experiments.dance_visual_probe import SYSTEM, USER, SCHEMA, CASES, _verdict

MODELS=['google/gemma-4-26b-a4b-it','google/gemma-4-31b-it']

def deadline(*_):raise TimeoutError('45second hard request limit')

def main():
    evidence=Path('evidence/dance-hosted-vision-v1.json')
    if evidence.exists():raise ValueError('refusing overwrite')
    key=os.environ['OPENROUTER_API_KEY']
    folder=Path('/Users/adom/Development/hermes-testing/runs/harness2-dance-vision-v1')
    manifest=json.loads((folder/'manifest.json').read_text())
    with urlopen('https://openrouter.ai/api/v1/models',timeout=15) as r:listing=json.load(r)['data']
    metadata={m:{k:next(x for x in listing if x['id']==m).get(k) for k in ['id','architecture','pricing','supported_parameters']} for m in MODELS}
    if not all('image' in v['architecture']['input_modalities'] for v in metadata.values()):raise ValueError('image support unavailable')
    rows=[]
    report={'scope':'hosted same-fixture visual baseline; provider/model differences confounded; not local quantized equivalence',
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'metadata':metadata,'system_prompt':SYSTEM,'user_prompt':USER,'schema':SCHEMA,
            'max_calls':12,'max_output_tokens':96,'stop_when_reported_cost_reaches_usd':.10,
            'provider_max_price_per_million':{'prompt':.25,'completion':1},'calls':rows}
    def save():evidence.write_text(json.dumps(report,indent=2)+'\n')
    save();cost=0.;errors=0
    for mi,model in enumerate(MODELS):
        # Reuse each corresponding local model's order to match presentation.
        order=manifest['order_by_model'][['gemma4:e2b','gemma4:e4b'][mi]]
        for case_id in order:
            case=next(c for c in manifest['cases'] if c['case_id']==case_id)
            data=(folder/case['image']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=case['image_sha256']:raise ValueError('image changed')
            body={'model':model,'messages':[{'role':'system','content':SYSTEM},
                 {'role':'user','content':[{'type':'text','text':USER},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(data).decode()}}]}],
                 'max_tokens':96,'temperature':0,'reasoning':{'enabled':False},
                 'response_format':{'type':'json_schema','json_schema':{'name':'pose_comparison','strict':True,'schema':SCHEMA}},
                 'provider':{'require_parameters':True,'max_price':{'prompt':.25,'completion':1}}}
            row={'model_requested':model,'case_id':case_id,'expected_host_only':case['expected_host_only'],'image_sha256':case['image_sha256']}
            started=time.monotonic();old=signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,45)
            try:
                req=Request('https://openrouter.ai/api/v1/chat/completions',json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
                with urlopen(req,timeout=35) as r:raw=json.load(r)
                row['raw_response']=raw
                choice=raw['choices'][0]
                row.update(_verdict(choice['message']['content'],case['expected_host_only']))
                if choice.get('finish_reason')!='stop':row.update(strict_json=False,semantic_correct=False,reason='incomplete response')
                value=raw.get('usage',{}).get('cost')
                row['reported_cost_usd']=value
                if not isinstance(value,(int,float)):report['stopped']='missing cost receipt'
                else:cost+=value
                errors=0
            except Exception as exc:
                row.update(error_type=type(exc).__name__,strict_json=False,semantic_correct=False);errors+=1
                if hasattr(exc,'code'):row['http_status']=exc.code
            finally:
                signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
                row['wall_seconds']=time.monotonic()-started;rows.append(row);report['reported_cost_sum_usd']=cost;save()
            if errors>=2 or cost>=.10 or report.get('stopped'):
                report.setdefault('stopped','cost threshold or consecutive errors');save();return
    report['complete']=True;save()
    print(json.dumps({'cost':cost,'rows':[{k:r.get(k) for k in ['model_requested','case_id','answer','semantic_correct','wall_seconds','error_type']} for r in rows]},indent=2))

if __name__=='__main__':main()

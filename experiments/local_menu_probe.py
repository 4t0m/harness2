"""Bounded native Ollama menu trial with load/prefill/decode accounting."""
import argparse
import json
from pathlib import Path
import signal
import time
from urllib.request import Request,urlopen
from experiments.creative_menu_comparison import CASES,build
from experiments.creative_retry_probe import normalize_single_json_fence
from harness2.production_menu import resolve


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',default='hermes-lab-qwen3-8b:latest');parser.add_argument('--name',default='local-menu-qwen8-v1');args=parser.parse_args()
    if not args.name.replace('-','').isalnum():raise SystemExit('invalid name')
    output=Path('evidence')/(args.name+'.json')
    if output.exists():raise SystemExit('refusing overwrite')
    report={'scope':'local Mac inference on existing model; no avatar dispatch', 'requested_model':args.model,
            'options':{'num_ctx':2048,'num_predict':96,'temperature':0},'think':False,'rows':[]}
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    def deadline(*_):raise TimeoutError('local call deadline')
    signal.signal(signal.SIGALRM,deadline)
    for case in CASES:
        task,labels,brief,packet,expected=build(case,0)
        row={'task_id':task['task_id'],'request':packet['prompt'],'expected_job':expected}
        body={'model':args.model,'messages':[{'role':'system','content':'Choose the legal option that satisfies the user brief. Return strict JSON only.'},
              {'role':'user','content':json.dumps(packet['prompt'])}],'stream':False,'think':False,
              'options':report['options'],'keep_alive':'2m'}
        started=time.monotonic();signal.alarm(60)
        try:
            req=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urlopen(req,timeout=55) as response:
                raw=response.read(1048577)
            if len(raw)>1048576:raise ValueError('oversized response')
            result=json.loads(raw);content=result.get('message',{}).get('content','')
            row.update(content=content,thinking=result.get('message',{}).get('thinking'),served_model=result.get('model'),
                       done=result.get('done'),done_reason=result.get('done_reason'))
            for field in ['total_duration','load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration']:row[field]=result.get(field)
            strict=resolve(task,labels,brief,packet['revision'],content)
            text,changed=normalize_single_json_fence(content)
            repaired=resolve(task,labels,brief,packet['revision'],text)
            row.update(strict_match=strict.get('action',{}).get('job_id')==expected,format_changed=changed,
                       repaired_match=repaired.get('action',{}).get('job_id')==expected)
            if row.get('eval_duration'):row['decode_tokens_per_second']=row['eval_count']/(row['eval_duration']/1e9)
            if row.get('prompt_eval_duration'):row['prompt_tokens_per_second']=row['prompt_eval_count']/(row['prompt_eval_duration']/1e9)
        except Exception as exc:row.update(error_type=type(exc).__name__)
        finally:signal.alarm(0)
        row['wall_seconds']=time.monotonic()-started;report['rows'].append(row);save()
        print(json.dumps({k:v for k,v in row.items() if k not in ('request','thinking','content')}),flush=True)
        if 'error_type' in row:break


if __name__=='__main__':main()

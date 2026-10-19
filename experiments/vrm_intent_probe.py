"""Model intent -> host relative placement -> existing trusted VRM renderer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
from harness2.actor_provider import chat_completion
from harness2.vrm_intent import compile_intent
from experiments.creative_retry_probe import normalize_single_json_fence


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--local-qwen30',action='store_true');args=parser.parse_args()
    evidence=Path('evidence/vrm-intent-local-qwen30.json' if args.local_qwen30 else 'evidence/vrm-intent-live.json')
    lab=Path('/Users/adom/Development/hermes-testing')
    relative='runs/round6/eidoverse-harness2-local-qwen30-v1' if args.local_qwen30 else 'runs/round6/eidoverse-harness2-relative-v1'
    if evidence.exists() or (lab/relative).exists():raise SystemExit('refusing overwrite')
    report={'scope':'model relative intent applied to an existing offline VRM clip',
            'brief':'Say farewell with a goodbye wave. Stand to the right of the anchor.',
            'anchor_x':0.1,'offset':0.25,'visible_anchor':False,'inference_location':'local Ollama' if args.local_qwen30 else 'OpenRouter'}
    def save():evidence.write_text(json.dumps(report,indent=2)+'\n')
    def deadline(*_):raise TimeoutError('provider deadline')
    signal.signal(signal.SIGALRM,deadline)
    try:
        signal.alarm(30)
        r=chat_completion(base_url='http://127.0.0.1:11434/v1' if args.local_qwen30 else 'https://openrouter.ai/api/v1',
            model='hermes-lab-qwen30:latest' if args.local_qwen30 else 'google/gemma-4-26b-a4b-it',
            api_key='' if args.local_qwen30 else os.environ['OPENROUTER_API_KEY'],system='Return only JSON with gesture (salute or wave_goodbye) and side (left or right). No other keys.',
            user=report['brief'],timeout=20,max_output_tokens=128,include_raw=True)
        signal.alarm(0)
        text,changed=normalize_single_json_fence(r.content)
        command=compile_intent(text,report['anchor_x'],report['offset'])
        report.update(content=r.content,format_repaired=changed,usage=r.usage,model=r.model,
                      latency_seconds=r.latency_seconds,cost=r.raw_response.get('usage',{}).get('cost'),command=command)
        save()
        code='import json,sys; from tools.eidoverse_mcp import render_vrm_gesture; print(json.dumps(render_vrm_gesture(sys.argv[1],float(sys.argv[2]),sys.argv[3])))'
        run=subprocess.run(['/Users/adom/.hermes/hermes-agent/venv/bin/python','-c',code,command['gesture'],str(command['x_position']),relative],
            cwd=lab,capture_output=True,text=True,timeout=110,check=True)
        result=json.loads(run.stdout.strip().splitlines()[-1]);report['renderer']=result;save()
        if result['status']!='completed':raise ValueError('renderer incomplete')
        receipt=json.loads((lab/relative/'receipt.json').read_text())
        for name,expected in receipt['files_sha256'].items():
            if hashlib.sha256((lab/relative/name).read_bytes()).hexdigest()!=expected:raise ValueError('hash mismatch')
        if receipt['state']['rootPosition']!=[command['x_position'],0,0]:raise ValueError('placement mismatch')
        report.update(receipt=receipt,complete=True,visual_review='pending')
    except Exception as exc:report.update(error_type=type(exc).__name__,complete=False)
    finally:signal.alarm(0);save();print(json.dumps({'complete':report['complete'],'error':report.get('error_type'),'command':report.get('command')}))


if __name__=='__main__':main()

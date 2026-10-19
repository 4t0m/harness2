"""Small matched production-state trial; no generation or external job dispatch."""
import argparse
import json
import os
from pathlib import Path
import signal
from harness2.production_dispatch import TASKS, model_brief, evaluate
from harness2.actor_provider import chat_completion, ProviderError, ProviderIncomplete
from experiments.creative_retry_probe import normalize_single_json_fence


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',default='google/gemma-4-26b-a4b-it')
    parser.add_argument('--output',type=Path,default=Path('evidence/production-dispatch-gemma-live.json'))
    args=parser.parse_args()
    if args.output.exists(): raise SystemExit('refusing to overwrite evidence')
    rows=[]
    def deadline(*_): raise TimeoutError('bounded call expired')
    signal.signal(signal.SIGALRM,deadline)
    for task in TASKS:
        row={'task_id':task['task_id'],'external_dispatch':False}
        signal.alarm(30)
        try:
            r=chat_completion(base_url='https://openrouter.ai/api/v1',model=args.model,
                api_key=os.environ['OPENROUTER_API_KEY'],system='Select a legal production action. Return only strict JSON, no Markdown.',
                user=json.dumps(model_brief(task)),timeout=20,max_output_tokens=256,include_raw=True)
            row.update(content=r.content,model=r.model,usage=r.usage,latency_seconds=r.latency_seconds,
                       cost=r.raw_response.get('usage',{}).get('cost'))
            strict=evaluate(task,r.content)
            row['strict']={k:strict.get(k) for k in ['valid','reason','action','state_preserved']}
            try:
                normalized,repaired=normalize_single_json_fence(r.content)
                fixed=evaluate(task,normalized)
                row['format_replay']={'changed':repaired,**{k:fixed.get(k) for k in ['valid','reason','action','state_preserved']}}
            except ValueError:
                row['format_replay']={'valid':False,'reason':'not exact single JSON fence'}
        except ProviderIncomplete as exc:
            row.update(status='incomplete',usage=exc.usage,finish_reason=exc.finish_reason)
        except (ProviderError,TimeoutError) as exc:
            row.update(status=type(exc).__name__)
        finally: signal.alarm(0)
        rows.append(row)
        args.output.write_text(json.dumps({'scope':'single-step synthetic ledger choices; strict and deterministic formatting replay on same responses; no real jobs','rows':rows},indent=2)+'\n')
        print(json.dumps(row),flush=True)

if __name__=='__main__':main()

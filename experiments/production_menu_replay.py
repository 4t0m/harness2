"""Replay exact fence repair without further inference."""
import json
from pathlib import Path
from experiments.production_menu_probe import CASES
from experiments.creative_retry_probe import normalize_single_json_fence
from harness2.production_dispatch import _job, _task
from harness2.production_menu import menu, resolve


def main():
    source=Path('evidence/production-menu-gemma-live.json')
    output=Path('evidence/production-menu-format-replay.json')
    if output.exists():raise SystemExit('refusing overwrite')
    saved={r['task_id']:r for r in json.loads(source.read_text())['rows']}
    rows=[]
    for task_id,brief,descriptions,expected in CASES:
        task=_task(task_id,[_job('job_'+str(i),'pending') for i in range(3)])
        labels={'job_'+str(i):v for i,v in enumerate(descriptions)}
        packet=menu(task,labels,brief)
        raw,changed=normalize_single_json_fence(saved[task_id]['content'])
        verdict=resolve(task,labels,brief,packet['revision'],raw)
        rows.append({'task_id':task_id,'format_changed':changed,'legal':verdict['valid'],
                     'priority_match':verdict.get('action',{}).get('job_id')=='job_'+str(expected)})
    output.write_text(json.dumps({'source':str(source),'provider_calls':0,'rows':rows},indent=2)+'\n')
    print(json.dumps(rows))


if __name__=='__main__':main()

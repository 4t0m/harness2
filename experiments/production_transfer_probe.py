"""Frozen fresh retry-cap cases, with at most one host-feedback correction."""
import json
import os
from pathlib import Path
import signal
from harness2.production_dispatch import _task, _job, model_brief, evaluate, rejection_feedback
from harness2.actor_provider import chat_completion, ProviderError, ProviderIncomplete

# Freeze before the first provider request. These are near-transfer cases, not new task families.
CASES = (
    _task('cap-one', [_job('paint_base', 'failed'), _job('paint_detail', 'pending', deps=('paint_base',))], max_attempts=1),
    _task('below-two', [_job('motion_seed', 'failed'), _job('motion_finish', 'pending', deps=('motion_seed',))], max_attempts=2),
    _task('cap-two', [_job('render_finish', 'pending', deps=('render_seed',)), _job('render_seed', 'failed', attempt=2)], max_attempts=2),
    _task('below-three', [_job('rig_finish', 'pending', deps=('rig_seed',)), _job('rig_seed', 'failed', attempt=2)], max_attempts=3),
)


def main():
    output = Path('evidence/production-transfer-gemma-live.json')
    if output.exists():
        raise SystemExit('refusing to overwrite evidence')
    receipt = {'scope': 'fresh near-transfer cases; one correction maximum; no external dispatch',
               'fixtures': CASES, 'rows': []}
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    def timeout(*_):
        raise TimeoutError('call deadline')
    signal.signal(signal.SIGALRM, timeout)
    for task in CASES:
        row = {'task_id': task['task_id'], 'attempts': []}
        receipt['rows'].append(row)
        prompt = model_brief(task)
        for attempt in range(2):
            record = {'request': prompt}
            signal.alarm(30)
            try:
                r = chat_completion(base_url='https://openrouter.ai/api/v1',
                    model='google/gemma-4-26b-a4b-it', api_key=os.environ['OPENROUTER_API_KEY'],
                    system='Select a legal production action. Return only strict JSON, no Markdown.',
                    user=json.dumps(prompt), timeout=20, max_output_tokens=256, include_raw=True)
                verdict = evaluate(task, r.content)
                record.update(content=r.content, usage=r.usage, model=r.model,
                              latency_seconds=r.latency_seconds,
                              cost=r.raw_response.get('usage', {}).get('cost'),
                              verdict={k:verdict.get(k) for k in ('valid','reason','action','state_preserved')})
                feedback = rejection_feedback(task, r.content)
                if feedback is not None:
                    prompt = {**model_brief(task), 'previous_proposal': r.content, 'host_feedback': feedback}
            except ProviderIncomplete as exc:
                record.update(status='incomplete', usage=exc.usage, finish_reason=exc.finish_reason)
            except (ProviderError, TimeoutError) as exc:
                record.update(status=type(exc).__name__)
            finally:
                signal.alarm(0)
            row['attempts'].append(record)
            output.write_text(json.dumps(receipt, indent=2) + '\n')
            print(json.dumps({'task_id':task['task_id'], 'attempt':attempt, **{k:v for k,v in record.items() if k!='request'}}), flush=True)
            if record.get('status') or record.get('verdict', {}).get('valid'):
                break


if __name__ == '__main__':
    main()

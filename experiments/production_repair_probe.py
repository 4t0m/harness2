"""Three bounded development-only diagnostics; no external dispatch."""
import json
import os
from pathlib import Path
import signal
from harness2.production_dispatch import TASKS, model_brief, evaluate
from harness2.actor_provider import chat_completion, ProviderError, ProviderIncomplete


def main():
    output = Path('evidence/production-repair-gemma-live.json')
    if output.exists():
        raise SystemExit('refusing to overwrite evidence')
    task = next(t for t in TASKS if t['task_id'] == 'blocked-02')
    source = Path('evidence/production-dispatch-gemma-live.json')
    prior = next(r for r in json.loads(source.read_text())['rows'] if r['task_id'] == task['task_id'])
    if evaluate(task, prior['content'])['valid']:
        raise SystemExit('source is not a rejected proposal')
    prompts = [
        ('fresh_repeat', None),
        ('generic_rejection', 'Host rejected the previous proposal. Select a legal action.'),
        ('specific_rejection', 'Host rejected retry: dead_parent has attempt=3 and max_attempts=3. Retry requires attempt < max_attempts. Reconsider the current ledger.'),
    ]
    receipt = {'scope': 'development-only single-sample correction diagnostic; no external jobs',
               'source': str(source), 'task_id': task['task_id'], 'rows': []}
    def timeout(*_):
        raise TimeoutError('call deadline')
    signal.signal(signal.SIGALRM, timeout)
    for condition, feedback in prompts:
        prompt = model_brief(task)
        if feedback:
            prompt.update(previous_proposal=prior['content'], host_feedback=feedback)
        row = {'condition': condition, 'request': prompt}
        signal.alarm(30)
        try:
            response = chat_completion(base_url='https://openrouter.ai/api/v1',
                model='google/gemma-4-26b-a4b-it', api_key=os.environ['OPENROUTER_API_KEY'],
                system='Select a legal production action. Return only strict JSON, no Markdown.',
                user=json.dumps(prompt), timeout=20, max_output_tokens=256, include_raw=True)
            verdict = evaluate(task, response.content)
            row.update(content=response.content, usage=response.usage, model=response.model,
                       latency_seconds=response.latency_seconds,
                       cost=response.raw_response.get('usage', {}).get('cost'),
                       verdict={k: verdict.get(k) for k in ('valid', 'reason', 'action', 'state_preserved')})
        except ProviderIncomplete as exc:
            row.update(status='incomplete', usage=exc.usage, finish_reason=exc.finish_reason)
        except (ProviderError, TimeoutError) as exc:
            row.update(status=type(exc).__name__)
        finally:
            signal.alarm(0)
        receipt['rows'].append(row)
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({k:v for k,v in row.items() if k != 'request'}), flush=True)


if __name__ == '__main__':
    main()

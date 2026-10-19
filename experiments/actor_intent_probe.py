"""Bounded live intent probe; no runtime actions are executed here."""
import json
import os
from pathlib import Path
import signal
from harness2.actor_intent import TASKS, model_brief, evaluate_intent
from harness2.actor_provider import chat_completion, ProviderError, ProviderIncomplete


def main():
    output = Path('evidence/actor-intent-live.json')
    rows = []
    def deadline(*_):
        raise TimeoutError('intent probe deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(120)
    try:
        for task in TASKS:
            row = {'task': task, 'runtime_executed': False}
            try:
                response = chat_completion(base_url='https://openrouter.ai/api/v1',
                    model='google/gemma-4-26b-a4b-it', api_key=os.environ['OPENROUTER_API_KEY'],
                    system='Select an actor intent. Return only the requested JSON.',
                    user=model_brief(task), timeout=20, max_output_tokens=256, include_raw=True)
                row.update(model=response.model, usage=response.usage,
                    latency_seconds=response.latency_seconds, content=response.content,
                    cost=response.raw_response.get('usage', {}).get('cost'),
                    verdict=evaluate_intent(task, response.content))
            except ProviderIncomplete as exc:
                row.update(status='incomplete', usage=exc.usage, finish_reason=exc.finish_reason)
            except (ProviderError, TimeoutError) as exc:
                row.update(status=type(exc).__name__)
            rows.append(row)
            output.write_text(json.dumps({'scope':'live model intent selection; host compilation; no runtime action', 'trials':rows}, indent=2)+'\n')
            print(json.dumps(row), flush=True)
    finally:
        signal.alarm(0)

if __name__ == '__main__':
    main()

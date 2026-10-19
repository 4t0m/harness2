"""Frozen renamed/reordered target-selection holdouts; never executes an avatar."""
import argparse
import json
import os
from pathlib import Path
import signal
from harness2.actor_intent import parse_intent, compile_intent
from harness2.actor_provider import chat_completion, ProviderError, ProviderIncomplete

# Hand-authored expectations are separate from model-visible packets.
CASES = (
    ('amber', [('far', .9, .5), ('amber', .2, .5), ('near', .55, .5), ('wrongside', .1, .5)], 'right', 'near'),
    ('teal', [('teal', .8, .5), ('near', .45, .5), ('far', .1, .5), ('wrongside', .9, .5)], 'left', 'near'),
    ('u7', [('m2', .88, .5), ('z4', .51, .5), ('u7', .25, .5), ('n8', .15, .5)], 'right', 'z4'),
    ('u7', [('n8', .15, .5), ('u7', .25, .5), ('z4', .51, .5), ('m2', .88, .5)], 'right', 'z4'),
    ('nova', [('east', .85, .5), ('west', .2, .5), ('nova', .5, .5), ('close_wrong', .52, .5)], 'left', 'west'),
    ('lark', [('low', .52, .85), ('lark', .2, .5), ('level', .6, .5), ('behind', .1, .5)], 'right', 'level'),
)


def packet(index):
    actor, points, side, expected = CASES[index]
    scene = {'revision': f'heldout-{index}', 'actors': [
        {'id': identity, 'x': x, 'y': y, 'radius': .02, 'facing': 'toward_camera'}
        for identity, x, y in points]}
    request = f'{actor} should look at the nearest actor on its screen-{side}. Use Euclidean center distance among actors on that side.'
    brief = ('Return only JSON with exactly scene_revision,actor_id,target_id,action. '
             'action is look_at. No Markdown. Screen x increases right and y increases down.\n'
             + json.dumps(scene) + '\n' + request)
    return scene, brief, {'actor_id': actor, 'target_id': expected, 'action': 'look_at'}


def assess(index, raw):
    scene, _, expected = packet(index)
    try:
        intent = parse_intent(raw)
        plan = compile_intent(intent, scene)
        correct = all(intent[k] == v for k, v in expected.items())
        return {'accepted': correct, 'reason': None if correct else 'incorrect task selection', 'plan': plan}
    except ValueError as exc:
        return {'accepted': False, 'reason': str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='google/gemma-4-26b-a4b-it')
    parser.add_argument('--output', type=Path, default=Path('evidence/actor-holdout-gemma.json'))
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('refusing to overwrite existing evidence')
    rows = []
    def deadline(*_):
        raise TimeoutError('per-call hard deadline')
    signal.signal(signal.SIGALRM, deadline)
    for index in range(len(CASES)):
        row = {'case': index, 'runtime_executed': False}
        signal.alarm(30)
        try:
            _, brief, _ = packet(index)
            response = chat_completion(base_url='https://openrouter.ai/api/v1', model=args.model,
                api_key=os.environ['OPENROUTER_API_KEY'], system='Select the requested actor intent.',
                user=brief, timeout=20, max_output_tokens=256, include_raw=True)
            row.update(model=response.model, content=response.content, usage=response.usage,
                latency_seconds=response.latency_seconds, cost=response.raw_response.get('usage',{}).get('cost'),
                verdict=assess(index, response.content))
        except ProviderIncomplete as exc:
            row.update(status='incomplete', usage=exc.usage, finish_reason=exc.finish_reason)
        except (ProviderError, TimeoutError) as exc:
            row.update(status=type(exc).__name__)
        finally:
            signal.alarm(0)
        rows.append(row)
        args.output.write_text(json.dumps({'scope':'fixed-harness heldout selection; no adaptation or execution', 'trials':rows},indent=2)+'\n')
        print(json.dumps(row),flush=True)

if __name__ == '__main__':
    main()

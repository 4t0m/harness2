"""Eight frozen compact briefs against one operator-configured remote model.

Repeated baseline fixtures, not new holdouts. No correction calls. The elapsed
rate includes network/prefill/decoding; it is not native generation throughput.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time

from experiments.dance_motif_cases import CASES, score_intent
from experiments.dance_motif_probe import SYSTEMS
from harness2.dance_motif_score import compile_intent, verify_score
from harness2.motif_remote_provider import OpenAICompatibleMotifProvider


def run(provider, output: Path):
    if not output.is_absolute() or output.exists():
        raise ValueError('requires a new absolute output path')
    sources = ['experiments/motif_remote_probe.py', 'experiments/dance_motif_cases.py',
               'experiments/dance_motif_probe.py', 'harness2/motif_remote_provider.py',
               'harness2/dance_motif_score.py', 'harness2/bounded_json_http.py']
    report = {'scope': __doc__, 'provider': provider.metadata,
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'sources': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
              'max_calls': 8, 'timeout_per_call_seconds': 20,
              'max_output_tokens': 128, 'calls': [], 'complete': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    save()
    failures = 0
    for case in CASES:
        row = {'case_id': case['id'], 'request': case['request'],
               'expected': case['expected'], 'compiled': False, 'brief_correct': False}
        report['calls'].append(row)
        request = {'model': provider.model, 'messages': [
            {'role': 'system', 'content': SYSTEMS['compact']},
            {'role': 'user', 'content': case['request']}]}
        row['initial_text_characters'] = sum(len(m['content']) for m in request['messages'])
        save()
        start = time.monotonic()
        try:
            raw = provider(request)
            row['provider_seconds'] = time.monotonic() - start
            row['raw_response'] = raw
            row['usage'] = raw['usage']
            prepared = time.monotonic()
            score = compile_intent(raw['message']['content'])
            verify_score(score)
            row.update(compiled=True, brief_correct=not score_intent(score['intent'], case),
                       intent=score['intent'], sequence_sha256=score['receipt']['sequence_sha256'],
                       prepare_seconds=time.monotonic()-prepared)
            row['ready_within_five_seconds'] = time.monotonic()-start <= 5
            row['output_tokens_per_end_to_end_second'] = raw['usage']['completion_tokens'] / row['provider_seconds']
            failures = 0
        except Exception as exc:
            row['elapsed_seconds'] = time.monotonic()-start
            row['error_type'] = type(exc).__name__
            failures += 1
        save()
        if failures >= 2:
            report['stop_reason'] = 'two consecutive errors; no retry'
            break
    report['complete'] = len(report['calls']) == len(CASES)
    report['ended_at_utc'] = datetime.now(timezone.utc).isoformat()
    valid = [r for r in report['calls'] if r.get('compiled')]
    report['summary'] = {'attempted': len(report['calls']), 'compiled': len(valid),
                         'brief_correct': sum(r['brief_correct'] for r in valid),
                         'ready_within_five_seconds': sum(r['ready_within_five_seconds'] for r in valid),
                         'first_request_seconds': report['calls'][0].get('provider_seconds'),
                         'subsequent_median_seconds': statistics.median(
                             [r['provider_seconds'] for r in report['calls'][1:] if 'provider_seconds' in r])
                             if any('provider_seconds' in r for r in report['calls'][1:]) else None}
    save()
    print(json.dumps(report['summary']), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--auth-env', required=True)
    parser.add_argument('--checkpoint-name')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    provider = OpenAICompatibleMotifProvider(args.endpoint, args.model, args.auth_env,
                                             checkpoint_name=args.checkpoint_name)
    run(provider, args.output)


if __name__ == '__main__':
    main()

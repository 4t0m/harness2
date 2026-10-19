"""Reconstruct served viewer sample hashes from raw model replies and events."""
import argparse
import hashlib
import json
from pathlib import Path
from harness2.dance_motif_score import compile_intent, verify_score


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing overwrite')
    d = json.loads(args.server.read_text())
    trial = json.loads(args.trial.read_text())
    assert trial['complete']
    for name, digest in d['sources'].items():
        assert sha(name) == digest, name
    assert len(d['calls']) == 3
    scores = []
    expected = [dict(motif='sway', accents=['soft','clear','soft','clear']),
                dict(motif='pulse', accents=['clear','soft','clear','soft']),
                dict(motif='sway', accents=['clear','clear','soft','soft'])]
    briefs_ok = []
    for index, call in enumerate(d['calls']):
        assert call['finish_reason'] == 'stop'
        score = compile_intent(call['content'])
        verify_score(score)
        scores.append(score)
        briefs_ok.append(score['intent'] == expected[index])
        assert call['raw_response']['message']['content'] == call['content']
        assert call['brief'] == trial['briefs'][['initial','replacement','interrupted'][index]]
    first, replacement, late = d['calls']
    assert first['delivery']['status'] == 'applied'
    assert replacement['delivery']['status'] == 'queued'
    assert late['delivery']['status'] == 'rejected_stale'
    epoch = first['delivery']['switch_at_ms']
    switch = replacement['delivery']['switch_at_ms']
    assert switch > replacement['delivered_at_ms'] and (switch-epoch) % 4000 == 0
    for call, score in zip(d['calls'][:2], scores):
        assert call['delivery']['score_sha256'] == score['receipt']['sequence_sha256']
    stops = [e['at_ms'] for e in d['events'] if e['kind'] == 'stop']
    assert len(stops) == 1
    stop = stops[0]
    assert switch < stop
    assert late['provider_started_ms'] < stop < late['provider_finished_ms'] <= late['delivered_at_ms']
    rest = compile_intent('{"motif":"sway","accents":["soft","soft","soft","soft"]}')['sequence']['frames'][0]
    def source(at):
        if at < epoch:
            return rest, None, None, 'idle'
        which = int(at >= switch)
        start = switch if which else epoch
        index = min((at-start)//50, 320)
        return scores[which]['sequence']['frames'][index], index, scores[which]['receipt']['sequence_sha256'], ('holding_end' if index == 320 else 'playing')
    frozen, _, frozen_hash, _ = source(stop)
    phases = {'idle': 0, 'playing': 0, 'frozen': 0, 'holding_end': 0}
    for sample in d['samples']:
        at = sample['at_ms']
        if at >= stop:
            frame, index, digest, status = frozen, None, frozen_hash, 'frozen'
        else:
            frame, index, digest, status = source(at)
        frame_hash = hashlib.sha256(json.dumps(frame, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert sample['frame_sha256'] == frame_hash
        assert sample['score_sha256'] == digest
        assert sample['source_frame_index'] == index
        assert sample['status'] == status
        phases[status] += 1
    assert d['worker_drained'] and d['ended_at_utc'] and d['termination_reason'] == 'user_shutdown'
    result = {'complete': True, 'server_sha256': sha(args.server), 'trial_sha256': sha(args.trial),
              'checker_sha256': sha(__file__), 'samples_checked': len(d['samples']),
              'served_samples_total': d['served_samples_total'], 'phases': phases,
              'brief_correct': briefs_ok, 'provider_calls': len(d['calls']),
              'model': d['model'], 'replacement_boundary_ms': switch-epoch,
              'stop_relative_ms': stop-epoch, 'late_delivery_after_stop_ms': late['delivered_at_ms']-stop,
              'native_input_tokens': [c['raw_response']['prompt_eval_count'] for c in d['calls']],
              'native_output_tokens': [c['raw_response']['eval_count'] for c in d['calls']],
              'provider_seconds': [(c['provider_finished_ms']-c['provider_started_ms'])/1000 for c in d['calls']],
              'prepare_seconds': [(c['prepared_at_ms']-c['provider_finished_ms'])/1000 for c in d['calls']],
              'scope': 'Raw response, compiler, served-pose hash and lifecycle replay; browser visibility requires separate UI evidence.'}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()

"""Verify visible readbacks and the separate browser-button-only trial."""
import hashlib
import json
from pathlib import Path
import socket
from urllib.parse import urlparse
from harness2.dance_motif_score import compile_intent, verify_score

ASSETS = Path('/Users/adom/Development/hermes-testing/runs/harness2-motif-live-v1')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def parse_readback(path):
    text = path.read_text()
    start = text.index('{\n  "now_ms"')
    return json.JSONDecoder().raw_decode(text[start:])[0]

def main():
    rows = []
    for prefix, report_name in [('qwen','motif-live-qwen-server-v1.json'), ('e2b','motif-live-e2b-server-v1.json'), ('ui','motif-live-ui-controls-server-v1.json')]:
        path = Path('evidence') / report_name
        report = json.loads(path.read_text())
        for source, digest in report['sources'].items():
            assert sha(source) == digest
        readback = parse_readback(ASSETS / f'{prefix}-frozen-ax.txt')
        stop = next(e['at_ms'] for e in report['events'] if e['kind'] == 'stop')
        call = report['calls'][0 if prefix == 'ui' else 1]
        score = compile_intent(call['content'])
        verify_score(score)
        epoch = call['delivery']['switch_at_ms']
        frozen = score['sequence']['frames'][min((stop-epoch)//50,320)]
        assert readback['frame'] == frozen
        assert readback['status'] == 'frozen'
        assert readback['score_sha256'] == score['receipt']['sequence_sha256']
        assert readback['pending'] is None and readback['queued_switch_ms'] is None
        assert report['worker_drained'] and report['ended_at_utc']
        assert report['termination_reason'] == 'user_shutdown'
        assert 'Shutdown requested' in (ASSETS / f'{prefix}-shutdown-ax.txt').read_text()
        url = urlparse(report['url'])
        with socket.socket() as connection:
            connection.settimeout(2)
            connection_result = connection.connect_ex((url.hostname, url.port))
        assert connection_result != 0
        row = {'session': prefix, 'server_sha256': sha(path), 'visible_readback_matches_source': True,
               'listener_connect_result': connection_result, 'worker_drained': True,
               'provider_calls': len(report['calls'])}
        if prefix == 'ui':
            assert len(report['calls']) == 1
            assert call['brief'] == 'Use pulse as the returning motif. Make the four sections soft, clear, soft, clear in that order.'
            assert score['intent'] == {'motif':'pulse','accents':['soft','clear','soft','clear']}
            assert call['raw_response']['message']['content'] == call['content']
            assert call['delivery']['status'] == 'applied'
            assert 'Preparing' in (ASSETS / 'ui-direct-ax.txt').read_text()
            assert 'Movement stopped' in (ASSETS / 'ui-stop-ax.txt').read_text()
            rest = compile_intent('{"motif":"sway","accents":["soft","soft","soft","soft"]}')['sequence']['frames'][0]
            for sample in report['samples']:
                at = sample['at_ms']
                frame = rest if at < epoch else frozen if at >= stop else score['sequence']['frames'][min((at-epoch)//50,320)]
                digest = hashlib.sha256(json.dumps(frame, sort_keys=True, separators=(',',':')).encode()).hexdigest()
                assert sample['frame_sha256'] == digest
            row.update(samples_checked=len(report['samples']), native_input_tokens=call['raw_response']['prompt_eval_count'], native_output_tokens=call['raw_response']['eval_count'], brief_correct=True)
        rows.append(row)
    result = {'complete':True, 'checker_sha256':sha(__file__), 'sessions':rows,
              'ui_artifacts':{str(p):sha(p) for p in sorted(ASSETS.iterdir()) if p.suffix in ('.png','.txt')},
              'scope':'Actual browser screenshots and visible AX readbacks captured through CUA. Matched trials use timed HTTP direction/stop; third session submits direction, stop and shutdown through page buttons. Snapshot evidence does not measure continuous displayed frame rate.'}
    Path('evidence/motif-live-ui-check-v1.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='ui_artifacts'}))

if __name__ == '__main__':
    main()

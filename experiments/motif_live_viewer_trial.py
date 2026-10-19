"""Bounded API orchestration while a real browser displays the local viewer."""
import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

BRIEFS = {
    'initial': 'Use sway as the returning motif. Across the four sections, use soft, clear, soft, clear accents in that order.',
    'replacement': 'Replace the sequence with pulse as the returning motif. Set section accents to clear, soft, clear, soft in that order.',
    'interrupted': 'Use sway as the returning motif, with clear accents in the first two sections and soft accents in the last two.'
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.url.startswith('http://127.0.0.1:') or '/' in args.url.removeprefix('http://127.0.0.1:'):
        raise ValueError('expected loopback origin without path')
    if args.output.exists():
        raise FileExistsError('refusing overwrite')
    report = {'scope': 'API orchestration during a separately observed live browser session; API success alone does not prove rendered pixels.',
              'briefs': BRIEFS, 'events': [], 'states': [], 'complete': False}
    start = time.monotonic()
    def save():
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    def call(path, payload=None):
        headers = {'Origin': args.url}
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload).encode()
        with urlopen(Request(args.url + path, data=data, headers=headers), timeout=3) as response:
            result = json.load(response)
        report['events'].append({'elapsed_seconds': time.monotonic()-start, 'path': path, 'payload': payload, 'response': result}) if payload is not None else None
        return result
    def state():
        value = call('/state')
        report['states'].append({'elapsed_seconds': time.monotonic()-start, 'state': value})
        return value
    def until(predicate, limit=12):
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            value = state()
            if predicate(value):
                save()
                return value
            time.sleep(.1)
        raise TimeoutError('expected playback phase not observed within bound')
    try:
        report['before'] = state()
        if report['before']['sample']['status'] != 'idle':
            raise ValueError('requires a fresh viewer runtime')
        call('/direct', {'brief': BRIEFS['initial']})
        playing = until(lambda s: s['sample']['status'] == 'playing')
        report['initial_playing'] = playing
        print('initial playing', flush=True)
        time.sleep(1)
        call('/direct', {'brief': BRIEFS['replacement']})
        initial_hash = playing['sample']['score_sha256']
        replacement = until(lambda s: s['sample']['score_sha256'] != initial_hash)
        report['replacement_playing'] = replacement
        print('replacement playing', flush=True)
        time.sleep(1)
        call('/direct', {'brief': BRIEFS['interrupted']})
        time.sleep(.12)
        stopped = call('/stop', {})
        report['stop_response'] = stopped
        frozen = until(lambda s: not s['worker_busy'])
        report['after_worker'] = frozen
        if frozen['sample']['status'] != 'frozen':
            raise ValueError('stop did not remain frozen')
        stop_frame = stopped['sample']['frame']
        if frozen['sample']['frame'] != stop_frame:
            raise ValueError('pose changed after stop')
        time.sleep(.25)
        report['final'] = state()
        if report['final']['sample']['frame'] != stop_frame:
            raise ValueError('frozen pose drifted')
        report['complete'] = True
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    finally:
        report['wall_seconds'] = time.monotonic()-start
        save()
        print(json.dumps({'complete': report['complete'], 'error': report.get('error'), 'output': str(args.output)}), flush=True)

if __name__ == '__main__':
    main()

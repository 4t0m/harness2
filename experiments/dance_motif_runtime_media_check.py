"""Independent projection/source-image check of the finite runtime preview."""
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    preview_path = ROOT / 'evidence/dance-motif-runtime-preview-v1.json'
    p = json.loads(preview_path.read_text())
    raw_path = ROOT / p['runtime_evidence_path']
    assert sha(raw_path) == p['runtime_evidence_sha256']
    raw = json.loads(raw_path.read_text())
    assert sha(ROOT / 'experiments/dance_motif_runtime_preview.py') == p['renderer_sha256']
    for name, expected in p['source_hashes'].items():
        assert sha(ROOT / name) == expected
    for prefix in ('runtime', 'runtime_checker', 'helper'):
        assert sha(ROOT / p[prefix + '_path']) == p[prefix + '_sha256']
    media = p['media']
    video = Path(media['video'])
    assert sha(video) == media['video_sha256']
    runs = {r['model']: r for r in raw['runs']}
    records = media['sampled_joint_projection_log'] + [media['terminal_sample_projection_log']]
    points = markers = 0
    for entry in records:
        index = entry['sample_index']
        png = video.parent / 'frames' / f'frame_{index:03d}.png' if index < 140 else Path(media['terminal_sample_png'])
        with Image.open(png) as image:
            assert image.size == (800, 550)
            for actor_index, actor in enumerate(entry['actors']):
                sample = runs[actor['model']]['samples'][index]['sample']
                frame = sample['frame']
                encoded = json.dumps(frame, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
                assert hashlib.sha256(encoded).hexdigest() == actor['source_frame_sha256']
                assert sample['now_ms'] == actor['actual_now_ms']
                for joint, xyz in frame['joints'].items():
                    expected = [round((205, 595)[actor_index] + xyz[0] * 160), round(460 - xyz[2] * 160)]
                    assert expected == actor['projected_joint_pixels'][joint]
                    points += 1
                root_x = round((205, 595)[actor_index] + frame['joints']['pelvis'][0] * 160)
                assert image.convert('RGB').getpixel((root_x, 486)) == (21, 139, 136)
                markers += 1
    decoded = video.parent / 'decoded-check.png'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-vf',
                    r'select=eq(n\,40)+eq(n\,80)+eq(n\,88)+eq(n\,120),tile=2x2',
                    '-frames:v', '1', str(decoded)], check=True, timeout=30)
    result = {'complete': True, 'preview_sha256': sha(preview_path), 'checker_sha256': sha(__file__),
              'projected_points_checked': points, 'source_png_root_markers_checked': markers,
              'decoded_grid': str(decoded), 'decoded_grid_sha256': sha(decoded),
              'decoded_frame_indices': [40, 80, 88, 120], 'provider_calls': 0,
              'scope': 'Source projection and PNG marker verification, with sparse decoded frames for human-facing visual inspection; not a dance-quality judgment.'}
    (ROOT / 'evidence/dance-motif-runtime-media-check-v1.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()

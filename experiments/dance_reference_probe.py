"""Prepare a bounded RGB reference and inspect H3's installed frame cropping code.

Does not upload, queue, or load H3 models. The saved graph patch is preparation.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import time

from harness2.motion_reference import resample_for_render


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_crop(source):
    """Execute only the reviewed frame-count slice of the installed node AST."""
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MiniMaxH3ReferenceToVideo')
    method = next(n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'execute')
    loop = next(n for n in method.body if isinstance(n, ast.For) and ast.unparse(n.target) == '(name, video_frames)')
    first = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.If) and ast.unparse(n.test) == 'frames.shape[0] > frame_count')
    last = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == 'z')
    statements = loop.body[first:last]
    snippet = '\n'.join(ast.unparse(n) for n in statements)
    expected = """if frames.shape[0] > frame_count:
    frames = frames[:frame_count]
n = frames.shape[0]
if n < 5:
    raise ValueError('MiniMax H3 reference videos need at least 5 frames (~0.2s at 24 fps)')
while n % 17 != 5:
    n -= 1
frames = frames[:n]"""
    if snippet != expected:
        raise ValueError('installed cropping code changed; review before executing slice')
    code = compile(ast.Module(body=statements, type_ignores=[]), str(source), 'exec')
    class Frames:
        def __init__(self, count): self.shape = (count, 320, 512, 3)
        def __getitem__(self, index): return Frames(min(self.shape[0], index.stop))
    cases = []
    for count, output, expected_count in [(96,124,90), (107,124,107), (107,90,90), (4,124,None)]:
        env = {'frames': Frames(count), 'frame_count': output, 'ValueError': ValueError}
        try:
            exec(code, {'__builtins__': {}}, env)
            result = env['frames'].shape[0]
        except ValueError:
            result = None
        if result != expected_count:
            raise ValueError('unexpected installed crop result')
        cases.append({'input_frames': count, 'output_frame_limit': output,
                      'retained_frames': result, 'rejected': result is None})
    return {'scope': 'executed isolated installed count-cropping statements; no VAE/model execution',
            'source_path': str(source), 'source_sha256': digest(source), 'executed_source': snippet, 'cases': cases}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=int, default=1)
    args = parser.parse_args()
    if args.version < 1: raise ValueError('invalid version')
    work = Path('/Users/adom/Development/hermes-testing/runs') / f'harness2-dance-reference-v{args.version}'
    evidence = Path('evidence') / f'dance-reference-v{args.version}.json'
    if work.exists() or evidence.exists(): raise ValueError('refusing overwrite')
    work.mkdir()
    start = time.monotonic()
    report = {'scope': 'prepared RGB reference; no H3 inference or compatibility acceptance',
              'sources': {p: digest(Path(p)) for p in ['harness2/motion_reference.py', 'experiments/dance_reference_render.py', 'experiments/dance_reference_probe.py']}}
    def save(): evidence.write_text(json.dumps(report, indent=2)+'\n')
    save()
    try:
        original = Path('/Users/adom/Development/hermes-testing/runs/harness2-dance-model-edit-v1/tracks.json')
        before = digest(original)
        sequence = json.loads(original.read_text())['sequences'][1]
        sampled = resample_for_render(sequence)
        samples = work / 'render-samples.json'
        samples.write_text(json.dumps(sampled, indent=2)+'\n')
        report.update(source_tracks_sha256=before, samples_sha256=digest(samples),
                      resampling={k:v for k,v in sampled.items() if k!='frames'})
        renderer = Path('experiments/dance_reference_render.py').resolve()
        with (work/'render.log').open('w') as log:
            subprocess.run(['/Users/adom/Development/hermes-testing/runs/blender-runtime/Blender.app/Contents/MacOS/Blender',
                '-b','--python-exit-code','2','--python',str(renderer),'--',str(samples),str(work/'frames')],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
        report['render'] = json.loads((work/'frames/render.json').read_text())
        video = work / 'reference.mp4'
        subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(work/'frames/%03d.png'),
                        '-vf','tpad=stop_mode=clone:stop=11','-frames:v','107','-c:v','libx264',
                        '-crf','0','-pix_fmt','yuv420p',str(video)],check=True,timeout=30)
        run = subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
            '-show_entries','stream=width,height,nb_read_frames,avg_frame_rate,duration','-of','json',str(video)],
            check=True,capture_output=True,text=True,timeout=10)
        actual = json.loads(run.stdout)['streams'][0]
        if actual['nb_read_frames']!='107' or actual['avg_frame_rate']!='24/1' or actual['width']!=512 or actual['height']!=320 or abs(float(actual['duration'])-107/24)>.00001:
            raise ValueError('encoded stream contract mismatch')
        frame_hashes = subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','framemd5','-'],
            check=True,capture_output=True,text=True,timeout=10).stdout
        hashes = [line.split(',')[-1].strip() for line in frame_hashes.splitlines() if line and not line.startswith('#')]
        if len(hashes)!=107 or len(set(hashes[95:]))!=1: raise ValueError('decoded final hold changed')
        if digest(original)!=before: raise ValueError('source changed')
        crop = inspect_crop(Path('/Users/adom/ComfyUI-h3/comfy_extras/nodes_minimax_h3.py'))
        patch = {'scope':'staged patch only; not uploaded or submitted',
                 'target_template':'/Users/adom/ComfyUI-h3-setup/demo_api.json',
                 'add_nodes':{'901':{'class_type':'LoadVideo','inputs':{'file':f'dance-reference-v{args.version}.mp4'}},
                              '902':{'class_type':'GetVideoComponents','inputs':{'video':['901',0]}}},
                 'set_inputs':{'145':{'value':True},'148':{'ref_image_size':'match','ref_videos.ref_video_0':['902',0]}},
                 'prerequisites':['Upload verified media under declared input filename','Ensure new node IDs are unused',
                                  'Confirm output frame limit at least107','Validate complete graph against live server',
                                  'Verify checkpoint/reference-mode support before bounded generation']}
        (work/'reference-node-patch.json').write_text(json.dumps(patch,indent=2)+'\n')
        report.update(complete=True, video=actual, path=str(video), video_sha256=digest(video),
                      preserved_source=True, motion_frames=96, final_hold_frames=11,
                      decoded_final_hold_equal=True, installed_crop_probe=crop, staged_graph_patch=patch,
                      visual_review='pending')
        (work/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    except Exception as exc:
        report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:
        report['wall_seconds']=time.monotonic()-start
        save()
        print(json.dumps({k:report.get(k) for k in ['complete','path','video','resampling','error','wall_seconds']},indent=2))

if __name__ == '__main__': main()

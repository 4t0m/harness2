"""Generate, validate and render two procedural motion variants in a bounded run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from harness2.dance_motion import generate,validate


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',type=int,default=3);args=parser.parse_args()
    if args.version<1:raise SystemExit('invalid version')
    work=Path('/Users/adom/Development/hermes-testing/runs')/f'harness2-dance-motion-v{args.version}'
    output=Path('evidence')/f'dance-motion-render-v{args.version}.json'
    if work.exists() or output.exists():raise SystemExit('refusing overwrite')
    work.mkdir()
    report={'scope':'procedural generic step-touch-like stick rig; no model choreography or artistic acceptance',
            'sources':{p:digest(Path(p)) for p in ['harness2/dance_motion.py','experiments/dance_motion_render.py']}}
    start=time.monotonic()
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        sequences=[generate(name) for name in ['restrained','broad']]
        report['validation']=[validate(s) for s in sequences]
        tracks=work/'tracks.json';tracks.write_text(json.dumps({'sequences':sequences},indent=2)+'\n')
        report['tracks_sha256']=digest(tracks);save()
        with (work/'render.log').open('w') as log:
            subprocess.run(['/Users/adom/Development/hermes-testing/runs/blender-runtime/Blender.app/Contents/MacOS/Blender',
                '-b','--python-exit-code','2','--python',str(Path('experiments/dance_motion_render.py').resolve()),'--',str(tracks),str(work/'frames')],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
        subprocess.run(['ffmpeg','-v','error','-framerate','10','-i',str(work/'frames/%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(work/'comparison.mp4')],check=True,timeout=30)
        result=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,width,height,duration','-of','json',str(work/'comparison.mp4')],capture_output=True,text=True,check=True,timeout=10)
        report['video']=json.loads(result.stdout)['streams'][0]
        if report['video']['nb_read_frames']!='40':raise ValueError('unexpected frame count')
        report.update(complete=True,video_sha256=digest(work/'comparison.mp4'),path=str(work/'comparison.mp4'),visual_review='pending')
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__)
    finally:
        report['wall_seconds']=time.monotonic()-start;save();print(json.dumps(report,indent=2))

if __name__=='__main__':main()

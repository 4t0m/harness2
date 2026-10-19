"""One bounded model choice, compiled edit, isolated verification and preview."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
from harness2.actor_provider import chat_completion
from harness2.gesture_variation import compile_variation
from experiments.creative_retry_probe import normalize_single_json_fence

LAB=Path('/Users/adom/Development/hermes-testing')
ROOT=Path(__file__).resolve().parents[1]
SOURCE=LAB/'runs/harness2-menu-preview-v1/avatar.blend'
OUTPUT=LAB/'runs/harness2-model-variation-v1'


def main():
    evidence=ROOT/'evidence/gesture-variation-live.json'
    if evidence.exists() or OUTPUT.exists():raise SystemExit('refusing overwrite')
    OUTPUT.mkdir()
    report={'scope':'model selection of bounded motion variation; host applies and verifies edit',
            'brief':'Make the middle of the greeting as restrained as the available variants allow. Preserve the opening, ending, camera and all other body parts.',
            'options':{'soft':'Lower the middle arm peak to 2.35 radians.', 'restrained':'Lower the middle arm peak further, to 2.10 radians.'}}
    def save():evidence.write_text(json.dumps(report,indent=2)+'\n')
    def deadline(*_):raise TimeoutError('provider deadline')
    signal.signal(signal.SIGALRM,deadline)
    try:
        signal.alarm(30)
        r=chat_completion(base_url='https://openrouter.ai/api/v1',model='google/gemma-4-26b-a4b-it',
            api_key=os.environ['OPENROUTER_API_KEY'],system='Return only JSON with variation set to one listed option.',
            user=json.dumps({'brief':report['brief'],'options':report['options']}),timeout=20,max_output_tokens=128,include_raw=True)
        signal.alarm(0)
        raw,changed=normalize_single_json_fence(r.content)
        plan=compile_variation(raw,hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        report.update(content=r.content,format_repaired=changed,usage=r.usage,cost=r.raw_response.get('usage',{}).get('cost'),
                      latency_seconds=r.latency_seconds,model=r.model,plan=plan)
        save();(OUTPUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        code='import sys; sys.path[:0]='+repr([str(ROOT),str(ROOT/'experiments')])+'; import gesture_variation_blender'
        for mode in ['apply','verify-render']:
            with (OUTPUT/(mode+'.log')).open('w') as log:
                run=subprocess.run([str(LAB/'runs/blender-runtime/Blender.app/Contents/MacOS/Blender'),
                    '--background','--factory-startup','--disable-autoexec','--python-exit-code','1',
                    '--python-expr',code,'--',mode],stdout=log,stderr=subprocess.STDOUT,timeout=100)
            report[mode+'_exit']=run.returncode;save()
            if run.returncode:raise ValueError('Blender stage failed')
        receipt=json.loads((OUTPUT/'receipt.json').read_text())
        if not receipt['render_completed']:raise ValueError('incomplete render')
        video=OUTPUT/'preview.mp4'
        subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-n','-framerate','6','-i',str(OUTPUT/'frames/%03d.png'),
                        '-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True,timeout=20)
        probe=subprocess.run(['/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-select_streams','v:0',
            '-show_entries','stream=width,height,nb_read_frames,duration','-of','json',str(video)],capture_output=True,text=True,check=True)
        stream=json.loads(probe.stdout)['streams'][0]
        if stream['nb_read_frames']!='12' or stream['width']!=320 or stream['height']!=320:raise ValueError('video mismatch')
        report.update(receipt=receipt,video=stream,video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
                      source_unchanged=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==plan['source_sha256'],complete=True)
    except Exception as exc:report.update(error_type=type(exc).__name__,complete=False)
    finally:signal.alarm(0);save();print(json.dumps(report,indent=2))


if __name__=='__main__':main()

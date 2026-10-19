"""One model-selected gesture -> fixed trusted Blender tool -> artifact checks."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
from harness2.actor_provider import chat_completion
from harness2.production_dispatch import _job, _task
from harness2.production_menu import menu, resolve
from experiments.creative_retry_probe import normalize_single_json_fence

LAB=Path('/Users/adom/Development/hermes-testing')
PYTHON=Path('/Users/adom/.hermes/hermes-agent/venv/bin/python')
RELATIVE_OUTPUT='runs/harness2-menu-preview-v1'
ACTIONS={'gesture_a':'nod','gesture_b':'wave','gesture_c':'point'}
DESCRIPTIONS={'gesture_a':'Nod the head in acknowledgment.', 'gesture_b':'Raise and wave a hand to greet the viewer.',
              'gesture_c':'Point outward toward something beside the character.'}
BRIEF='Greet an arriving viewer with a visible hand wave. Keep a fixed front camera.'


def main():
    evidence=Path('evidence/menu-blender-preview-v1.json')
    if evidence.exists() or (LAB/RELATIVE_OUTPUT).exists():raise SystemExit('refusing overwrite')
    task=_task('avatar-greeting',[_job(k,'pending') for k in ACTIONS])
    packet=menu(task,DESCRIPTIONS,BRIEF)
    report={'scope':'model-selected procedural Blender gesture; not dance or H3 generation',
            'request':packet['prompt'],'external_generation_service':False}
    def save():evidence.write_text(json.dumps(report,indent=2)+'\n')
    def deadline(*_):raise TimeoutError('provider deadline')
    signal.signal(signal.SIGALRM,deadline)
    try:
        signal.alarm(30)
        r=chat_completion(base_url='https://openrouter.ai/api/v1',model='google/gemma-4-26b-a4b-it',
            api_key=os.environ['OPENROUTER_API_KEY'],system='Choose the gesture matching the brief. Return strict JSON only.',
            user=json.dumps(packet['prompt']),timeout=20,max_output_tokens=128,include_raw=True)
        signal.alarm(0)
        raw_verdict=resolve(task,DESCRIPTIONS,BRIEF,packet['revision'],r.content)
        normalized,changed=normalize_single_json_fence(r.content)
        verdict=resolve(task,DESCRIPTIONS,BRIEF,packet['revision'],normalized)
        report.update(content=r.content,usage=r.usage,latency_seconds=r.latency_seconds,
                      cost=r.raw_response.get('usage',{}).get('cost'),strict_valid=raw_verdict['valid'],
                      format_repaired=changed,accepted=verdict['valid'])
        save()
        if not verdict['valid']:raise ValueError('no accepted gesture')
        action=ACTIONS[verdict['action']['job_id']]
        report['selected_action']=action
        # Fixed code and fixed output location; model can supply only enum action.
        code='import json,sys; from tools.blender_mcp import stage; print(json.dumps(stage(sys.argv[1],"front",sys.argv[2])))'
        run=subprocess.run([str(PYTHON),'-c',code,action,RELATIVE_OUTPUT],cwd=LAB,
                           capture_output=True,text=True,timeout=170,check=True)
        result=json.loads(run.stdout.strip().splitlines()[-1])
        report['render_status']=result.get('status')
        save()
        if result.get('status')!='completed':raise ValueError('renderer did not complete')
        output=LAB/RELATIVE_OUTPUT
        receipt=json.loads((output/'receipt.json').read_text())
        scene=json.loads((output/'scene-report.json').read_text())
        hashes={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in receipt['artifacts']}
        if hashes!=receipt['artifacts']:raise ValueError('artifact hash mismatch')
        if scene['request']['action']!=action or scene['camera']['choice']!='front':raise ValueError('scene/request mismatch')
        # Decode all PNG pixels independently of the Blender success report.
        decode='from PIL import Image; import json,sys; from pathlib import Path; p=Path(sys.argv[1]); out=[]\nfor f in sorted(p.glob("frame_*.png")):\n im=Image.open(f); im.load(); out.append({"name":f.name,"size":list(im.size),"extrema":im.convert("RGB").getextrema()})\nprint(json.dumps(out))'
        checked=subprocess.run([str(PYTHON),'-c',decode,str(output)],capture_output=True,text=True,timeout=15,check=True)
        images=json.loads(checked.stdout)
        if len(images)!=3 or any(i['size']!=[640,640] for i in images):raise ValueError('unexpected decoded frames')
        report.update(output_dir=RELATIVE_OUTPUT,artifact_hashes=hashes,decoded_images=images,
                      evaluated_transforms=scene['evaluated_transforms'],gesture_matches_brief=action=='wave',
                      visual_review='pending',verified=True)
    except Exception as exc:
        report.update(error_type=type(exc).__name__,verified=False)
    finally:
        signal.alarm(0);save();print(json.dumps(report,indent=2))


if __name__=='__main__':main()

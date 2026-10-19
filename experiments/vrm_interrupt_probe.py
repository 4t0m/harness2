"""Deterministic interruption of an actual rendered VRM animation, not live I/O."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess


def rotation_distance(a,b):
    denominator=math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
    if denominator==0:raise ValueError('invalid zero quaternion')
    dot=abs(sum(x*y for x,y in zip(a,b)))/denominator
    return 2*math.acos(min(1.0,dot))


def main():
    lab=Path('/Users/adom/Development/hermes-testing')
    source=lab/'runs/round6/eidoverse-video'
    work=source/'work/eidoverse-harness2-interrupt-v1'
    evidence=Path('evidence/vrm-interrupt-live.json')
    if work.exists() or evidence.exists():raise SystemExit('refusing overwrite')
    expected='9acc1528b2febac11338107645ef500a95985ca5'
    revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if revision!=expected:raise ValueError('unqualified renderer revision')
    report={'scope':'deterministic frame event in actual offline VRM render; not asynchronous live interruption','source_commit':revision}
    with (lab/'runs/round6/eidoverse-render.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        work.mkdir()
        shutil.copy2('experiments/vrm_interrupt_scene.js',work/'scene.js')
        (work/'command.json').write_text(json.dumps({'gesture':'wave_goodbye','position':[0.35,0,0]}))
        relative='work/'+work.name
        (work/'scene.json').write_text(json.dumps({'width':640,'height':360,'fps':15,'duration':2,
            'script':relative+'/scene.js','outputVideo':relative+'/avatar.mp4','skipPreflightQA':True,
            'assets':{'character_vrm':'eidoverse/assets/vrms/claude.vrm'}}))
        env=os.environ.copy();deno=lab/'runs/round6/eidoverse-deno'
        env.update(PATH=str(deno)+os.pathsep+env.get('PATH',''),DENO_DIR=str(deno/'cache'),
                   RENDER_CODEC='libx264',EIDOVERSE_TRIAL_WORK=relative)
        try:
            with (work/'render.log').open('w') as log:
                result=subprocess.run(['python3','eido.py','render',relative+'/scene.json','--probe','--frames','24'],
                    cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
            report['exit']=result.returncode
            if result.returncode:raise ValueError('render failed')
            state=json.loads((work/'interrupt-state.json').read_text())
            def delta(pose):
                return max(abs(a-b) for name,p in pose.items() for field,values in p.items()
                           for a,b in zip(values,state['neutral'][name][field]))
            before=[delta(s['pose']) for s in state['samples'] if s['frameIndex']<12]
            after=[delta(s['pose']) for s in state['samples'] if s['frameIndex']>=12]
            arm_angle=max(rotation_distance(s['pose']['rightUpperArm']['quaternion'],state['neutral']['rightUpperArm']['quaternion']) for s in state['samples'][:12])
            report['pre_interrupt_right_arm_max_angle_radians']=arm_angle
            restored=max(after)<1e-7
            stopped=all(not s['mixerRegistered'] for s in state['samples'][12:])
            roots=all(s['root']==[0.35,0,0] for s in state['samples'])
            report.update(pre_interrupt_max_difference=max(before),post_interrupt_max_difference=max(after),
                          restored_all_bones=restored,mixer_removed=stopped,root_preserved=roots,
                          sample_count=len(state['samples']),state=state)
            if not (restored and stopped and roots and arm_angle>0.1 and len(state['samples'])==24):raise ValueError('interruption checks failed')
            video=work/'avatar_probe.mp4'
            probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries',
                'stream=width,height,nb_read_frames,duration','-of','json',str(video)],capture_output=True,text=True,check=True)
            stream=json.loads(probe.stdout)['streams'][0]
            if stream['nb_read_frames']!='24':raise ValueError('wrong video length')
            report.update(complete=True,video=stream,video_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
        except Exception as exc:report.update(complete=False,error_type=type(exc).__name__)
        evidence.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='state'},indent=2))


if __name__=='__main__':main()

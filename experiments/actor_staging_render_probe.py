"""Render accepted model staging plans and independently check joint readback."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from harness2.dance_motion import generate


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_motion(plan,motion):
    base=generate('restrained');neutral=base['frames'][8]['joints']
    if len(motion['frames'])!=48:raise ValueError('wrong motion count')
    targets={a['id']:a for a in plan['actors']};max_length=0.;max_protected=0.;movements={}
    for index,frame in enumerate(motion['frames']):
        if frame['frame_index']!=index or frame['time_s']!=index/8:raise ValueError('wrong sample timeline')
        cue=plan['cues'][index//16]
        if frame['active_cue']!=cue:raise ValueError('wrong activecue')
        poses={a['id']:a['joints_world_m'] for a in frame['actors']}
        if set(poses)!=set(targets):raise ValueError('actor readback identity mismatch')
        for identity,joints in poses.items():
            if set(joints)!=set(neutral):raise ValueError('joint set changed')
            if any(len(v)!=3 or not all(type(n) in (float,int) and math.isfinite(n) for n in v) for v in joints.values()):raise ValueError('nonfinite joint')
            origin=[targets[identity][axis+'_m'] for axis in ['x','y','z']]
            permitted=set()
            if cue['actor_id']==identity:
                permitted={'right_elbow','right_wrist'} if cue['gesture']=='wave' else {'head'} if cue['gesture']=='nod' else set()
            boundary=index%16 in (0,15)
            if boundary:permitted=set()
            for name,point in joints.items():
                expected=[neutral[name][i]+origin[i] for i in range(3)]
                distance=math.dist(point,expected)
                if name not in permitted:
                    max_protected=max(max_protected,distance)
                    if distance>1e-6:raise ValueError('protected actor/joint/neutral boundary changed')
                elif distance>1e-5:movements.setdefault(str(cue['slot']),set()).add(index)
            for edge,target in base['segment_lengths_m'].items():
                a,b=edge.split(':');max_length=max(max_length,abs(math.dist(joints[a],joints[b])-target))
    if max_length>1e-6:raise ValueError('segment length drift')
    for cue in plan['cues']:
        if cue['gesture']!='neutral' and not movements.get(str(cue['slot'])):raise ValueError('gesture did not move')
    return {'passed':True,'max_protected_position_error_m':max_protected,'max_segment_length_error_m':max_length,
            'changed_frames_by_slot':{k:sorted(v) for k,v in movements.items()},'neutral_boundary_frames':[0,15,16,31,32,47],
            'scope':'sampled scene joint readback, not biomechanics, collisions, interpolation or human acting acceptance'}


def main():
    evidence=Path('evidence/actor-staging-render-v1.json')
    if evidence.exists():raise ValueError('refusing overwrite')
    modelrun=json.loads(Path('evidence/actor-staging-v1.json').read_text())
    if not modelrun.get('complete'):raise ValueError('model run incomplete')
    cases=['plinth_pair_intro','gallery_roles_reversed'];rows=[]
    report={'scope':'two offline model-planned procedural actor scenes','model_evidence_sha256':digest(Path('evidence/actor-staging-v1.json')),
            'sources':{p:digest(Path(p)) for p in ['experiments/actor_staging_render.py','experiments/actor_staging_render_probe.py']},'renders':rows}
    def save():evidence.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for case_id in cases:
        chosen=next(r for r in modelrun['calls'] if r['case_id']==case_id and r['verdict']['semantic_correct'])
        plan=chosen['verdict']['plan'];root=Path('/Users/adom/Development/hermes-testing/runs')/('harness2-actor-scene-v1-'+case_id)
        if root.exists():raise ValueError('refusing overwrite')
        root.mkdir();p=root/'plan.json';p.write_text(json.dumps(plan,indent=2)+'\n')
        row={'case_id':case_id,'model':chosen['model'],'model_call_kind':chosen['kind'],'plan_sha256':digest(p),'source_plan':plan};rows.append(row);save();start=time.monotonic()
        try:
            with (root/'render.log').open('w') as log:
                subprocess.run(['/Users/adom/Development/hermes-testing/runs/blender-runtime/Blender.app/Contents/MacOS/Blender','-b','--python-exit-code','2','--python',str(Path('experiments/actor_staging_render.py').resolve()),'--',str(p),str(root/'frames')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
            motion=json.loads((root/'frames/motion.json').read_text())
            if motion['source_plan_sha256']!=digest(p):raise ValueError('plan hash mismatch')
            row['verification']=verify_motion(plan,motion);row['motion_sha256']=digest(root/'frames/motion.json');row['render_metadata']=motion['render']
            video=root/'scene.mp4'
            subprocess.run(['ffmpeg','-v','error','-framerate','8','-i',str(root/'frames/%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True,timeout=20)
            run=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,avg_frame_rate,duration','-of','json',str(video)],check=True,capture_output=True,text=True,timeout=10)
            meta=json.loads(run.stdout)['streams'][0]
            if meta['nb_read_frames']!='48' or meta['avg_frame_rate']!='8/1' or abs(float(meta['duration'])-6)>1e-6:raise ValueError('encoded timeline mismatch')
            row.update(complete=True,video=meta,path=str(video),video_sha256=digest(video),visual_review='pending')
        except Exception as exc:row.update(complete=False,error_type=type(exc).__name__,error=str(exc))
        finally:row['wall_seconds']=time.monotonic()-start;save()
    report['complete']=all(r.get('complete') for r in rows);save();print(json.dumps(report,indent=2))

if __name__=='__main__':main()

"""Render a disclosed paired improvement example from the frozen H2 evaluation."""
import json
from pathlib import Path
import subprocess
import time
from experiments.actor_staging_render_probe import digest,verify_motion


def main():
    source=Path('evidence/actor-staging-h2-v2.json');out=Path('evidence/actor-staging-h2-render-v1.json')
    root=Path('/Users/adom/Development/hermes-testing/runs/harness2-staging-h2-render-v1')
    if root.exists() or out.exists():raise ValueError('refusing overwrite')
    r=json.loads(source.read_text())
    if not r.get('complete'):raise ValueError('incomplete inference')
    fixed={x['case_id']:x for x in r['evaluation'] if x['model']=='gemma4:e2b' and x['condition']=='fixed'}
    adapted={x['case_id']:x for x in r['evaluation'] if x['model']=='gemma4:e2b' and x['condition']=='adapted'}
    case_id=next(k for k in fixed if not fixed[k]['attempts'][0]['verdict']['valid'] and adapted[k]['attempts'][0]['verdict']['valid'])
    case=next(c for c in r['frozen_evaluation'] if c['id']==case_id)
    root.mkdir();(root/'request.txt').write_text(case['request']+'\n')
    report={'model_evidence_sha256':digest(source),'case_id':case_id,'request':case['request'],
            'selection':'Post-evaluation illustrative paired gain, not a new heldout or aggregate evidence.',
            'scope':'Offline procedural actors; render follows each proposed plan, including the semantically incorrect baseline.',
            'sources':{p:digest(Path(p)) for p in ['experiments/actor_staging_h2_render.py','experiments/actor_staging_render.py','experiments/actor_staging_render_probe.py']},'renders':[]}
    def save():out.write_text(json.dumps(report,indent=2)+'\n')
    save()
    for label,entry in [('fixed',fixed[case_id]),('adapted',adapted[case_id])]:
        attempt=entry['attempts'][0];plan=attempt['verdict']['plan'];folder=root/label;folder.mkdir()
        p=folder/'plan.json';p.write_text(json.dumps(plan,indent=2)+'\n')
        row={'condition':label,'call_index':attempt['call_index'],'semantic_correct':attempt['verdict']['valid'],'plan_sha256':digest(p)}
        report['renders'].append(row);save();start=time.monotonic()
        with (folder/'render.log').open('w') as log:
            subprocess.run(['/Users/adom/Development/hermes-testing/runs/blender-runtime/Blender.app/Contents/MacOS/Blender','-b','--python-exit-code','2','--python',str(Path('experiments/actor_staging_render.py').resolve()),'--',str(p),str(folder/'frames')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
        motion=json.loads((folder/'frames/motion.json').read_text())
        if motion['source_plan_sha256']!=digest(p):raise ValueError('source mismatch')
        row['verification']=verify_motion(plan,motion);row['motion_sha256']=digest(folder/'frames/motion.json')
        video=folder/'scene.mp4'
        subprocess.run(['ffmpeg','-v','error','-framerate','8','-i',str(folder/'frames/%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True,timeout=20)
        result=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,avg_frame_rate,duration','-of','json',str(video)],check=True,capture_output=True,text=True,timeout=10)
        meta=json.loads(result.stdout)['streams'][0]
        if meta['nb_read_frames']!='48' or meta['avg_frame_rate']!='8/1' or abs(float(meta['duration'])-6)>1e-6:raise ValueError('video timing mismatch')
        row.update(video=meta,path=str(video),video_sha256=digest(video),wall_seconds=time.monotonic()-start,complete=True);save()
    report['complete']=True;save();print(json.dumps(report,indent=2))

if __name__=='__main__':main()

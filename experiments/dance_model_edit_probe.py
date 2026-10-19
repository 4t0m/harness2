"""Local model selects bounded arm accent; host preserves footwork and approved spans."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
from experiments.avatar_capability_probe import ollama_call,NATIVE_TIMING
from harness2.dance_motion import generate
from harness2.dance_edit import edit_arms


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    work=Path('/Users/adom/Development/hermes-testing/runs/harness2-dance-model-edit-v1')
    output=Path('evidence/dance-model-edit-v1.json')
    if work.exists() or output.exists():raise SystemExit('refusing overwrite')
    work.mkdir()
    report={'scope':'local model selects named arm accent; deterministic span edit and geometry checks; no model-created dance or taste judgment',
            'host_span_zero_based_beats':[2,6],'model':'gemma4:e2b','attempts':[],
            'sources':{p:digest(Path(p)) for p in ['harness2/dance_motion.py','harness2/dance_edit.py','experiments/dance_motion_render.py']}}
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save();started=time.monotonic()
    try:
        source=generate('restrained');original=work/'original.json';original.write_text(json.dumps(source,indent=2)+'\n')
        report['original_sha256']=digest(original)
        system='Select one available motion edit. Return only strict JSON with operation=accent_arms and strength=soft or clear. soft is subtle (0.20 radians); clear is pronounced (0.45 radians). The host alone owns the edit span and preserves footwork.'
        brief='Make the arm accent clearly pronounced through the middle four beats. Preserve all footwork, the first two beats and last two beats. Use the existing motion rather than regenerating it.'
        messages=[{'role':'system','content':system},{'role':'user','content':brief}]
        accepted=None
        for attempt in range(2):
            body={'model':report['model'],'messages':messages,'stream':False,'think':False,'keep_alive':'2m',
                  'options':{'num_ctx':2048,'num_predict':96,'temperature':0},
                  'format':{'type':'object','properties':{'operation':{'type':'string','enum':['accent_arms']},'strength':{'type':'string','enum':['soft','clear']}},'required':['operation','strength'],'additionalProperties':False}}
            start=time.monotonic();raw=ollama_call(body);content=raw.get('message',{}).get('content','')
            row={'request':body,'content':content,'wall_seconds':time.monotonic()-start,'done_reason':raw.get('done_reason'),**{k:raw.get(k) for k in NATIVE_TIMING}}
            report['attempts'].append(row)
            try:
                if raw.get('done_reason')!='stop':raise ValueError('incomplete response')
                candidate=edit_arms(source,content,start_beat=2,end_beat=6)
                row['valid_command']=True
                row['matches_brief']=json.loads(content)['strength']=='clear'
                if row['matches_brief']:accepted=candidate
            except ValueError as exc:row.update(valid_command=False,error=str(exc))
            save()
            if accepted:break
            messages=messages+[{'role':'assistant','content':content[:4096]},{'role':'user','content':'The proposal did not meet the stated edit request. Recheck the requested intensity and exact schema.'}]
        if accepted is None:raise ValueError('no accepted edit')
        report['edit_receipt']=accepted['receipt'];save()
        tracks=work/'tracks.json';tracks.write_text(json.dumps({'labels':['original','model-selected arm accent'],'sequences':[source,accepted['sequence']]},indent=2)+'\n')
        report['tracks_sha256']=digest(tracks)
        with (work/'render.log').open('w') as log:
            subprocess.run(['/Users/adom/Development/hermes-testing/runs/blender-runtime/Blender.app/Contents/MacOS/Blender','-b','--python-exit-code','2','--python',str(Path('experiments/dance_motion_render.py').resolve()),'--',str(tracks),str(work/'frames')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
        subprocess.run(['ffmpeg','-v','error','-framerate','10','-i',str(work/'frames/%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(work/'comparison.mp4')],check=True,timeout=30)
        run=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,width,height,duration','-of','json',str(work/'comparison.mp4')],check=True,capture_output=True,text=True,timeout=10)
        report['video']=json.loads(run.stdout)['streams'][0]
        if report['video']['nb_read_frames']!='40':raise ValueError('incomplete video')
        if digest(original)!=report['original_sha256']:raise ValueError('source changed')
        report.update(complete=True,original_unchanged=True,video_sha256=digest(work/'comparison.mp4'),visual_review='pending',path=str(work/'comparison.mp4'))
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc)[:180])
    finally:
        report['wall_seconds']=time.monotonic()-started;save();print(json.dumps({k:v for k,v in report.items() if k!='attempts'},indent=2))

if __name__=='__main__':main()

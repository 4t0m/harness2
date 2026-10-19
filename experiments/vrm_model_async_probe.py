"""External-process interruption and stale response during actual VRM rendering."""
import concurrent.futures
from harness2.vrm_intent import compile_intent
from urllib.request import Request, urlopen
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def verify_recovery(state):
    if [e['status'] for e in state['events']] != ['interrupted','stale_rejected']:
        raise ValueError('events not verified')
    if len(state['samples']) != 48 or [s['frameIndex'] for s in state['samples']] != list(range(48)):
        raise ValueError('incomplete frame evidence')
    after=[s for s in state['samples'] if s['frameIndex']>=state['interruptedAt']]
    if len(after)<8 or any(s['maximumDifference']>1e-7 or s['mixerRegistered'] or s['root']!=[0.35,0,0] for s in after):
        raise ValueError('post-stop motion or inadequate samples')
    return len(after)


def main():
    lab=Path('/Users/adom/Development/hermes-testing')
    source=lab/'runs/round6/eidoverse-video'
    work=source/'work/eidoverse-harness2-model-async-v1'
    evidence=Path('evidence/vrm-model-async-v1.json')
    if work.exists() or evidence.exists():raise SystemExit('refusing overwrite')
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!='9acc1528b2febac11338107645ef500a95985ca5':raise ValueError('source revision changed')
    report={'scope':'local 8B model intent and genuine delayed model response during finite offline GPU render; no persistent viewer', 'sent':[]}
    def infer_intent():
        begin=time.monotonic()
        body={'model':'hermes-lab-qwen3-8b:latest','messages':[
            {'role':'system','content':'Return only strict JSON with gesture (salute or wave_goodbye) and side (left or right).'},
            {'role':'user','content':'Wave goodbye while standing to the right of the anchor.'}],
            'stream':False,'think':False,'options':{'num_ctx':2048,'num_predict':64,'temperature':0},'keep_alive':'2m'}
        req=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=20) as response: raw=response.read(1048577)
        if len(raw)>1048576:raise ValueError('oversized response')
        raw=json.loads(raw)
        if raw.get('done_reason')!='stop':raise ValueError('incomplete model reply')
        command=compile_intent(raw['message']['content'],0.1,0.25)
        if command!={'gesture':'wave_goodbye','x_position':0.35}:raise ValueError('wrong semantic intent')
        return {'content':raw['message']['content'],'command':command,'wall_seconds':time.monotonic()-begin,
                'prompt_tokens':raw.get('prompt_eval_count'),'output_tokens':raw.get('eval_count')}
    report['initial_model']=infer_intent()
    evidence.write_text(json.dumps(report,indent=2)+'\n')
    def send(event):
        temp=work/'event.tmp';temp.write_text(json.dumps(event));os.replace(temp,work/'event.json')
        report['sent'].append({'event':event,'elapsed_seconds':time.monotonic()-started})
    with (lab/'runs/round6/eidoverse-render.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        work.mkdir();shutil.copy2('experiments/vrm_model_async_scene.js',work/'scene.js')
        (work/'command.json').write_text(json.dumps({'gesture':report['initial_model']['command']['gesture'],'position':[report['initial_model']['command']['x_position'],0,0]}))
        relative='work/'+work.name
        (work/'scene.json').write_text(json.dumps({'width':640,'height':360,'fps':15,'duration':4,
            'script':relative+'/scene.js','outputVideo':relative+'/avatar.mp4','skipPreflightQA':True,
            'assets':{'character_vrm':'eidoverse/assets/vrms/claude.vrm'}}))
        env=os.environ.copy();deno=lab/'runs/round6/eidoverse-deno'
        env.update(PATH=str(deno)+os.pathsep+env.get('PATH',''),DENO_DIR=str(deno/'cache'),RENDER_CODEC='libx264',EIDOVERSE_TRIAL_WORK=relative)
        started=time.monotonic();process=None;interrupted=False;late=False
        pool=concurrent.futures.ThreadPoolExecutor(max_workers=1);future=None
        try:
            with (work/'render.log').open('w') as log:
                process=subprocess.Popen(['python3','eido.py','render',relative+'/scene.json','--probe','--frames','48'],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                while process.poll() is None:
                    if time.monotonic()-started>90:raise TimeoutError('render deadline')
                    if not interrupted and (work/'ready.json').exists():
                        future=pool.submit(infer_intent)
                        send({'eventId':1,'type':'interrupt','revision':2});interrupted=True
                    if interrupted and not late and future.done() and (work/'ack-1.json').exists():
                        report['delayed_model']=future.result()
                        send({'eventId':2,'type':'gesture','revision':1,'gesture':report['delayed_model']['command']['gesture']});late=True
                    time.sleep(0.02)
            if process.returncode:raise ValueError('renderer failed')
            state=json.loads((work/'async-state.json').read_text());report['state']=state
            post_stop_count=verify_recovery(state)
            video=work/'avatar_probe.mp4'
            result=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames,width,height,duration','-of','json',str(video)],capture_output=True,text=True,check=True)
            stream=json.loads(result.stdout)['streams'][0]
            if stream['nb_read_frames']!='48':raise ValueError('wrong frame count')
            report.update(complete=True,video=stream,post_stop_samples=post_stop_count,video_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
        except Exception as exc:report.update(complete=False,error_type=type(exc).__name__)
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            pool.shutdown(wait=True,cancel_futures=True)
            report['elapsed_seconds']=time.monotonic()-started
            evidence.write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps({k:v for k,v in report.items() if k!='state'},indent=2))


if __name__=='__main__':main()

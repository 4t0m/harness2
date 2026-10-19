"""Eight bounded local vision diagnostics following the constant-answer pilot."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time
from experiments.dance_visual_probe import _ollama_call, _model_metadata, MODELS, NATIVE_KEYS


def main():
    work=Path('/Users/adom/Development/hermes-testing/runs/harness2-dance-vision-diagnostic-v1')
    evidence=Path('evidence/dance-vision-diagnostic-v1.json')
    if work.exists() or evidence.exists():raise ValueError('refusing overwrite')
    work.mkdir()
    rows=[]
    report={'scope':'gross image dependence and free-text pose diagnosis; not reliability or taste acceptance',
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'models':_model_metadata(),'calls':rows,'max_calls':8,'api_cost_usd':None,'local_hardware_cost':'unmeasured'}
    def save():evidence.write_text(json.dumps(report,indent=2)+'\n')
    for color in ['red','blue']:
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c={color}:s=256x256','-frames:v','1',str(work/f'{color}.png')],check=True,timeout=10)
    failures=0
    for model in MODELS:
        for case in ['red','blue','normal','flip']:
            card=case in ['red','blue']
            path=work/f'{case}.png' if card else Path('/Users/adom/Development/hermes-testing/runs/harness2-dance-vision-v1/images')/f'frame20-{case}.png'
            prompt='What is the dominant color of this image? Return JSON with color.' if card else 'Describe the arm poses of the figure on the image left and the figure on the image right. Are their hands held at a similar width from their own torsos, or does one hold them farther inward? Ignore colors and shadows. Be brief; say unclear if you cannot tell.'
            body={'model':model,'messages':[{'role':'user','content':prompt,'images':[base64.b64encode(path.read_bytes()).decode()]}],
                'stream':False,'think':False,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'}
            if card:body['format']={'type':'object','required':['color'],'additionalProperties':False,'properties':{'color':{'type':'string','enum':['red','blue','green','white','black','unclear']}}}
            row={'model':model,'case':case,'prompt':prompt,'schema':body.get('format'),'options':body['options'],'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            start=time.monotonic()
            try:
                raw=_ollama_call(body);row['raw_response']=raw
                row.update({k:raw.get(k) for k in NATIVE_KEYS})
                if card:
                    try:row['color_correct']=json.loads(raw['message']['content'])=={'color':case} and raw.get('done_reason')=='stop'
                    except (ValueError,KeyError):row['color_correct']=False
                failures=0
            except Exception as exc:row['error_type']=type(exc).__name__;failures+=1
            finally:row['wall_seconds']=time.monotonic()-start;rows.append(row);save()
            if failures>=2:return
    report['complete']=True;save()
    print(json.dumps([{'model':r['model'],'case':r['case'],'color_correct':r.get('color_correct'),'content':r.get('raw_response',{}).get('message',{}).get('content'),'wall_seconds':r['wall_seconds']} for r in rows],indent=2))

if __name__=='__main__':main()

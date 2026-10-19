"""Matched enum-order-only perturbation of four inspected crop images per model."""
import base64
import hashlib
import json
from pathlib import Path
import time
from experiments.dance_crop_vision_probe import SYSTEM, USER, SCHEMA, MODELS, OPTIONS, _model_metadata, _ollama_call, NATIVE_KEYS, _verdict


def main():
    out=Path('evidence/dance-enum-order-v1.json')
    if out.exists():raise ValueError('refusing overwrite')
    root=Path('/Users/adom/Development/hermes-testing/runs/harness2-dance-crop-vision-v1')
    manifest=json.loads((root/'manifest.json').read_text())
    schema=json.loads(json.dumps(SCHEMA));schema['properties']['hands_pose']['enum']=['wide','narrow','unclear']
    ids=['frame20-normal-left','frame20-normal-right','frame20-flip-left','frame20-flip-right']
    rows=[];report={'scope':'reused-fixture enum order diagnosis; no adaptation or unseen generalization',
        'models':_model_metadata(),'schema_before':SCHEMA,'schema_after':schema,'max_calls':8,'calls':rows,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    failures=0
    for model in MODELS:
        for crop_id in ids:
            crop=next(c for c in manifest['crops'] if c['crop_id']==crop_id)
            data=(root/crop['image']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=crop['image_sha256']:raise ValueError('image changed')
            body={'model':model,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':USER,'images':[base64.b64encode(data).decode()]}], 'stream':False,'think':False,'format':schema,'options':OPTIONS,'keep_alive':'2m'}
            row={'model':model,'crop_id':crop_id,'image_sha256':crop['image_sha256'],'expected_host_only':crop['expected_host_only'],'system_prompt':SYSTEM,'user_prompt':USER,'options':OPTIONS}
            start=time.monotonic()
            try:
                raw=_ollama_call(body);row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS})
                row.update(_verdict(raw.get('message',{}).get('content'),crop['expected_host_only']));failures=0
            except Exception as exc:row['error_type']=type(exc).__name__;failures+=1
            finally:row['wall_seconds']=time.monotonic()-start;rows.append(row);out.write_text(json.dumps(report,indent=2)+'\n')
            if failures>=2:return
    report['complete']=True;out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([{k:r.get(k) for k in ['model','crop_id','answer','semantic_correct']} for r in rows],indent=2))

if __name__=='__main__':main()

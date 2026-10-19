"""Bounded fresh-process GLB roundtrip with explicit animation count and hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',type=int,default=2);args=parser.parse_args()
    if args.version<1:raise SystemExit('invalid version')
    work=Path('/Users/adom/Development/hermes-testing/runs')/f'harness2-dance-gltf-v{args.version}'
    evidence=Path('evidence')/f'dance-gltf-v{args.version}.json'
    if work.exists() or evidence.exists():raise SystemExit('refusing overwrite')
    work.mkdir();start=time.monotonic()
    source=Path('/Users/adom/Development/hermes-testing/runs/harness2-dance-model-edit-v1/tracks.json')
    script=Path('experiments/dance_gltf_roundtrip.py').resolve()
    report={'scope':'animated proxy scene portability; not skinned rig/VRM/H3',
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest()}
    try:
        for mode in ['export','verify']:
            with (work/(mode+'.log')).open('w') as log:
                subprocess.run(['/Users/adom/Development/hermes-testing/runs/blender-runtime/Blender.app/Contents/MacOS/Blender','-b','--python-exit-code','2','--python',str(script),'--',mode,str(source),str(work)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        glb=work/'edited-motion.glb';data=glb.read_bytes();magic,version,length=struct.unpack_from('<III',data)
        n,kind=struct.unpack_from('<II',data,12)
        if magic!=0x46546C67 or version!=2 or length!=len(data) or kind!=0x4E4F534A:raise ValueError('invalid GLB header')
        document=json.loads(data[20:20+n])
        if len(document.get('animations',[]))!=1:raise ValueError('expected one complete scene animation')
        report.update(roundtrip=json.loads((work/'roundtrip.json').read_text()),animation_count=1,
            animation_channels=len(document['animations'][0]['channels']),glb_bytes=len(data),glb_sha256=hashlib.sha256(data).hexdigest(),path=str(glb),complete=True)
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__)
    finally:
        report['wall_seconds']=time.monotonic()-start;evidence.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()

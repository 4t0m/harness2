"""Render two accepted phrase plans; independently verify Blender joint readback."""
import hashlib,json,math,re,subprocess,time
from pathlib import Path


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify_readback(sequences,readback):
    frames=readback['frames'];indices=list(range(0,80,2))
    if [f['source_index'] for f in frames]!=indices:raise ValueError('readback timeline mismatch')
    max_position=max_length=0.0
    for frame in frames:
        if len(frame['actors'])!=2:raise ValueError('wrong actor count')
        for ai,(sequence,actor) in enumerate(zip(sequences,frame['actors'])):
            offset=-.8 if ai==0 else .8
            if actor['offset_x']!=offset:raise ValueError('wrong actor offset')
            target=sequence['frames'][frame['source_index']]['joints'];actual=actor['joints']
            if set(actual)!=set(target):raise ValueError('joint identity mismatch')
            for name,p in actual.items():
                if len(p)!=3 or not all(type(v) in (int,float) and math.isfinite(v) for v in p):raise ValueError('invalid readback')
                want=[target[name][0]+offset,*target[name][1:]]
                error=math.dist(p,want);max_position=max(max_position,error)
                if error>1e-6:raise ValueError('rendered pose mismatch')
            for edge,length in sequence['segment_lengths_m'].items():
                a,b=edge.split(':');error=abs(math.dist(actual[a],actual[b])-length);max_length=max(max_length,error)
                if error>1e-6:raise ValueError('rendered segment deformation')
    return {'frames_checked':len(frames),'actors':2,'max_position_error_m':max_position,'max_segment_error_m':max_length,
            'scope':'Actual rendered sample joint positions and segment lengths; not skinning, taste, or unsampled dynamics.'}


def render_pair(sequences,labels,provenance,*,run_name='harness2-dance-phrases-v1',evidence_name='dance-phrase-preview-v1'):
    if any(not re.fullmatch(r'[a-z0-9-]{1,80}',name) for name in [run_name,evidence_name]):raise ValueError('invalid host artifact name')
    root=Path('/Users/adom/Development/hermes-testing/runs')/run_name
    report_path=Path('evidence')/(evidence_name+'.json')
    if root.exists() or report_path.exists():raise ValueError('refusing overwrite')
    root.mkdir();start=time.monotonic();report={'provenance':provenance,'labels':labels,'preview_helper_sha256':digest(__file__),'scope':'Illustrative accepted local-model phrase plans, not blinded human taste results.'}
    def save():report_path.write_text(json.dumps(report,indent=2)+'\n')
    try:
        source=root/'tracks.json';source.write_text(json.dumps({'sequences':sequences,'labels':labels},indent=2)+'\n')
        report['tracks_sha256']=digest(source);report['renderer_sha256']=digest('experiments/dance_phrase_render.py');save()
        with (root/'render.log').open('w') as log:
            subprocess.run(['/Users/adom/Development/hermes-testing/runs/blender-runtime/Blender.app/Contents/MacOS/Blender','-b','--python-exit-code','2','--python',str(Path('experiments/dance_phrase_render.py').resolve()),'--',str(source),str(root/'frames')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
        report['readback']=verify_readback(sequences,json.loads((root/'frames/readback.json').read_text()));report['readback_sha256']=digest(root/'frames/readback.json');save()
        video=root/'comparison.mp4'
        subprocess.run(['ffmpeg','-v','error','-framerate','10','-i',str(root/'frames/%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True,timeout=20)
        raw=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,avg_frame_rate,duration','-of','json',str(video)],check=True,capture_output=True,text=True,timeout=10)
        meta=json.loads(raw.stdout)['streams'][0]
        if meta['nb_read_frames']!='40' or meta['avg_frame_rate']!='10/1' or abs(float(meta['duration'])-4)>1e-6:raise ValueError('video timeline mismatch')
        report.update(complete=True,path=str(video),video=meta,video_sha256=digest(video),visual_review='pending')
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:report['wall_seconds']=time.monotonic()-start;save()
    return report


def main():
    from harness2.dance_phrases import compile_plan,validate_compilation
    source=Path('evidence/dance-phrase-model-v1.json');data=json.loads(source.read_text())
    if not data.get('complete'):raise ValueError('model trial incomplete')
    for p,h in data['sources'].items():
        if digest(p)!=h:raise ValueError('frozen trial source changed')
    chosen=[next(c for c in data['calls'] if c['model']==m and c['case_id']=='open_then_sway_and_pulse_either_order' and c['attempt']==0 and c['correct']) for m in data['models']]
    compiled=[compile_plan(c['content']) for c in chosen]
    for c,p in zip(chosen,compiled):
        validate_compilation(p)
        if c['motion_receipt']!=p['receipt']:raise ValueError('compiled motion no longer matches model receipt')
    provenance={'model_evidence_sha256':digest(source),'selection':'First independently authored case; first accepted plan from each local model. Illustrative only; not selected for subjective quality.',
                'models':[c['model'] for c in chosen],'moves':[c['moves'] for c in chosen],'model_calls':[data['calls'].index(c) for c in chosen]}
    print(json.dumps(render_pair([p['sequence'] for p in compiled],['A','B'],provenance),indent=2))

if __name__=='__main__':main()

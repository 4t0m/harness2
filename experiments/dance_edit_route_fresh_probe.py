"""Live E2B structural fallback test on observed editing cases; no oracle in routing."""
import hashlib,json,time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json
from experiments.dance_phrase_edit_probe import COMMON,OUTPUT
from experiments.dance_visual_probe import NATIVE_KEYS
MODEL='gemma4:e2b'


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    from harness2.dance_phrase_edit import bind_source,PATCH_SCHEMA,FULL_SCHEMA
    from harness2.dance_edit_route import route_edit
    from experiments.dance_phrase_edit_cases import CASES
    out=Path('evidence/dance-edit-route-fresh-v1.json')
    if out.exists():raise ValueError('refusing overwrite')
    previous=Path('evidence/dance-phrase-edit-model-v1.json');prior=json.loads(previous.read_text())
    if not prior['complete']:raise ValueError('paired trial incomplete')
    with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:metadata=next(x for x in json.load(r)['models'] if x['name']==MODEL)
    paths=['harness2/dance_edit_route.py','harness2/dance_phrase_edit.py','harness2/dance_phrases.py','experiments/dance_phrase_edit_cases.py','experiments/dance_phrase_edit_probe.py','experiments/dance_edit_route_probe.py','experiments/dance_edit_route_fresh_probe.py']
    report={'scope':'Fresh-context full fallback; previous raw/error retained only in audit. Exploratory live structural fallback on8observed cases. No fresh heldout/generalization claim. Route never sees expected moves; evaluation occurs after route returns.',
      'prior_sha256':digest(previous),'sources':{p:digest(p) for p in paths},'model':{k:metadata.get(k) for k in ['name','digest','size']},
      'max_calls':16,'max_calls_per_case':2,'cases':CASES,'calls':[],'results':[],'paid_provider_calls':0}
    def save():out.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for case in CASES:
            src=json.dumps({'moves':case['source_moves']});scope=case['editable_slots'];revision='approved-dance-v1';snapshot=bind_source(src,revision,scope)
            public={'source_plan':json.loads(src),'permitted_slots':scope,'request':case['request']}
            # Closure captures only public task data, not case acceptance fields.
            def provider(mode,previous_raw,rejection_reason):
                if len(report['calls'])>=16:raise RuntimeError('call cap')
                messages=[{'role':'system','content':COMMON+'\n'+OUTPUT[mode]},{'role':'user','content':json.dumps(public,sort_keys=True)}]
                # Deliberately omit rejected answer and feedback from model context.
                row={'case_id':case['id'],'mode':mode,'messages':messages,'previous_raw_audit':previous_raw,'rejection_reason_audit':rejection_reason,'input_text_characters':sum(len(x['content']) for x in messages)};start=time.monotonic()
                try:
                    raw=request_json('http://127.0.0.1:11434/api/chat',{'model':MODEL,'messages':messages,'stream':False,'think':False,'format':PATCH_SCHEMA if mode=='patch' else FULL_SCHEMA,'options':{'temperature':0,'num_ctx':4096,'num_predict':128},'keep_alive':'2m'},timeout=20)
                    row['raw_response']=raw;row.update({k:raw.get(k) for k in NATIVE_KEYS});row['content']=raw.get('message',{}).get('content','')
                    if raw.get('done_reason')!='stop':raise RuntimeError('incomplete provider response')
                    return row['content']
                except Exception as exc:row['error_type']=type(exc).__name__;raise
                finally:row['wall_seconds']=time.monotonic()-start;report['calls'].append(row);save()
            start=time.monotonic();routed=route_edit(snapshot,src,revision,scope,provider)
            row={'case_id':case['id'],'accepted':routed['accepted'],'attempts':routed['attempts'],'wall_seconds':time.monotonic()-start}
            if routed['accepted']:
                moves=[[m['id'],m['variation']] for m in routed['edit']['compiled']['moves']];row.update(moves=moves,correct=moves==case['expected_moves'],edit_receipt=routed['edit']['receipt'])
            else:row['correct']=False
            report['results'].append(row);save();print(json.dumps({k:row[k] for k in ['case_id','accepted','correct','wall_seconds']}),flush=True)
        report['complete']=True
    except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
    finally:save();print(json.dumps({'complete':report.get('complete'),'calls':len(report['calls'])}),flush=True)

if __name__=='__main__':main()

"""Matched local comparison of ordinal and semantic choice identifiers."""
import json
from pathlib import Path
import time
from experiments.avatar_capability_probe import ollama_call,NATIVE_TIMING
from harness2.priority_h2 import _unique_pairs


def main():
    source=Path('evidence/avatar-scope-h2-e2b-v1.json')
    output=Path('evidence/avatar-scope-representation-v1.json')
    if output.exists():raise SystemExit('refusing overwrite')
    tasks=json.loads(source.read_text())['frozen_evaluation']
    report={'scope':'paired identifier representation test on already-used evaluation cases; no adaptation or unseen generalization claim',
            'source':str(source),'model':'gemma4:e2b','rows':[]}
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    for index,task in enumerate(tasks['tasks']):
        for kind in (['ordinal','semantic'] if index%2==0 else ['semantic','ordinal']):
            ids=[f'option_{i}' for i in range(len(task['options']))] if kind=='ordinal' else task['options']
            expected=ids[tasks['expected_indices'][task['task_id']]]
            user=json.dumps({'brief':task['brief'],'legal_options':[{'choice_id':cid,'description':desc} for cid,desc in zip(ids,task['options'])]},sort_keys=True)
            system="Choose the one supplied option satisfying the current brief and its policy. Return only strict JSON with choice_id set to one of the supplied choice_id values."
            body={'model':report['model'],'messages':[{'role':'system','content':system},{'role':'user','content':user}],
                'stream':False,'think':False,'keep_alive':'2m','options':{'num_ctx':4096,'num_predict':96,'temperature':0},
                'format':{'type':'object','properties':{'choice_id':{'type':'string','enum':ids}},'required':['choice_id'],'additionalProperties':False}}
            row={'task_id':task['task_id'],'kind':kind,'request':body,'expected':expected,'correct':False};report['rows'].append(row);save()
            start=time.monotonic()
            try:
                result=ollama_call(body);content=result.get('message',{}).get('content','')
                row.update(content=content,done_reason=result.get('done_reason'))
                row.update({k:result.get(k) for k in NATIVE_TIMING})
                parsed=json.loads(content,object_pairs_hook=_unique_pairs)
                row['correct']=parsed=={'choice_id':expected} and result.get('done_reason')=='stop'
            except Exception as exc:row['error_type']=type(exc).__name__
            finally:row['wall_seconds']=time.monotonic()-start;save()
            if 'error_type' in row:return
    print(json.dumps({kind:sum(r['correct'] for r in report['rows'] if r['kind']==kind) for kind in ['ordinal','semantic']}))

if __name__=='__main__':main()

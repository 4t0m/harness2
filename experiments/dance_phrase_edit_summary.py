"""Summarize paired editing and context-retaining/fresh structural routing."""
import hashlib,json,statistics
from pathlib import Path

def summarize():
    paths=['dance-phrase-edit-model-v1.json','dance-edit-route-v1.json','dance-edit-route-fresh-v1.json'];data=[json.loads((Path('evidence')/p).read_text()) for p in paths]
    assert all(r['complete'] for r in data)
    out={'scope':'Eight within-shelf edit cases, then two exploratory routing runs on those observed cases. No H2 learning or broad reliability claim.','source_sha256':{p:hashlib.sha256((Path('evidence')/p).read_bytes()).hexdigest() for p in paths},'paired':[],'routes':[],'total_calls':sum(len(r['calls']) for r in data),'paid_provider_calls':0}
    paired=data[0]
    for model in paired['models']:
        for condition in ['full','patch']:
            results=[r for r in paired['results'] if r['model']==model and r['condition']==condition];calls=[paired['calls'][r['call_indices'][0]] for r in results]
            row={'model':model,'condition':condition,'first_correct':sum(r['first_correct'] for r in results),'after_one_correction':sum(r['final_correct'] for r in results),'n':len(results),'first_wall_median_seconds':statistics.median(c['wall_seconds'] for c in calls)}
            for k in ['prompt_eval_count','eval_count','input_text_characters']:row[k]={'min':min(c[k] for c in calls),'max':max(c[k] for c in calls)}
            out['paired'].append(row)
    first_patches={c['case_id']:c for c in paired['calls'] if c['model']=='gemma4:e2b' and c['condition']=='patch' and c['attempt']==0}
    first_full={c['case_id']:c for c in paired['calls'] if c['model']=='gemma4:e2b' and c['condition']=='full' and c['attempt']==0}
    for path,r in zip(paths[1:],data[1:]):
        for p,h in r['sources'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
        patchcalls=[c for c in r['calls'] if c['mode']=='patch'];fallback=[c for c in r['calls'] if c['mode']=='full']
        same_patch_prompts=all(c['messages']==first_patches[c['case_id']]['messages'] for c in patchcalls)
        same_patch_outputs=all(c['content']==first_patches[c['case_id']]['content'] for c in patchcalls)
        assert same_patch_prompts and same_patch_outputs
        out['routes'].append({'source':path,'correct':sum(x['correct'] for x in r['results']),'accepted':sum(x['accepted'] for x in r['results']),'n':len(r['results']),'calls':len(r['calls']),'fallback_cases':[c['case_id'] for c in fallback],
          'median_total_wall_per_case_seconds':statistics.median(x['wall_seconds'] for x in r['results']),'patch_prompts_equal_paired':same_patch_prompts,'patch_outputs_equal_paired':same_patch_outputs,
          'fallback_prompt_equal_standalone_full':[c['messages']==first_full[c['case_id']]['messages'] for c in fallback],
          'fallback_output_equal_standalone_full':[c['content']==first_full[c['case_id']]['content'] for c in fallback]})
    out['protected_frames_per_edit']=62;out['total_motion_samples']=81
    Path('evidence/dance-phrase-edit-summary-v1.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':print(json.dumps(summarize(),indent=2))

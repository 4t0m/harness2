"""Derive compact completion, context, latency and cost metrics from frozen receipts."""
import hashlib,json,statistics
from pathlib import Path

def summarize():
    out={'scope':'Eight newly authored within-catalog briefs, one sample/model; correctness is host brief constraints, not taste. No learned adaptation. Hosted/local latency includes different runtimes and is not a hardware comparison.','models':[],'source_sha256':{}}
    for file in ['dance-phrase-model-v1.json','dance-phrase-hosted-v1.json']:
        p=Path('evidence')/file;r=json.loads(p.read_text());assert r['complete'];out['source_sha256'][file]=hashlib.sha256(p.read_bytes()).hexdigest()
        for model in r['models']:
            results=[x for x in r['results'] if x['model']==model];calls=[x for x in r['calls'] if x['model']==model];initial=[x for x in calls if x['attempt']==0]
            row={'model':model,'cases':len(results),'first_correct':sum(x['first_correct'] for x in results),'after_one_correction':sum(x['final_correct'] for x in results),'calls':len(calls),'all_compiled':all(x.get('compiled') for x in calls),'first_wall_median_s':statistics.median(x['wall_seconds'] for x in initial),'first_wall_range_s':[min(x['wall_seconds'] for x in initial),max(x['wall_seconds'] for x in initial)]}
            for label,fn in [('input_tokens',lambda x:x.get('prompt_eval_count',x.get('usage',{}).get('prompt_tokens'))),('output_tokens',lambda x:x.get('eval_count',x.get('usage',{}).get('completion_tokens'))),('input_text_characters',lambda x:x['input_text_characters'])]:
                values=[fn(x) for x in initial];assert all(type(v) in (int,float) for v in values);row[label]={'min':min(values),'max':max(values),'median':statistics.median(values)}
            row['reported_cost_usd']=sum(x.get('reported_cost_usd',0) for x in calls)
            row['failed_case_ids']=[x['case_id'] for x in results if not x['final_correct']]
            if 'prompt_eval_count' in initial[0]:
                row['native_initial_decode_seconds_median']=statistics.median(x['eval_duration']/1e9 for x in initial)
                row['native_initial_decode_tokens_per_second_median']=statistics.median(x['eval_count']/(x['eval_duration']/1e9) for x in initial)
            out['models'].append(row)
        out[file]={'calls':len(r['calls']),'reported_cost_usd':r.get('reported_cost_usd',0),'cost_unknown':r.get('cost_unknown',False),'feasible_counts':r['feasible_plan_counts'],'infeasible_offline_counts':r['infeasible_solution_counts']}
    out['total_calls']=sum(m['calls'] for m in out['models']);out['reported_cost_usd']=sum(m['reported_cost_usd'] for m in out['models'])
    Path('evidence/dance-phrase-summary-v1.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':print(json.dumps(summarize(),indent=2))

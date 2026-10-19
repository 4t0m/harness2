"""Aggregate saved comparison receipts without more inference."""
import json
from pathlib import Path
from statistics import median


def summarize(report):
    summaries=[]
    for model in report['models']:
        rows=[r for r in report['rows'] if r['requested_model']==model]
        expected=len(report['cases'])*len(report['rotations'])
        timings=[r['latency_seconds'] for r in rows if 'latency_seconds' in r]
        costs=[r['cost'] for r in rows if isinstance(r.get('cost'),(int,float))]
        summary={'model':model,'observations':len(rows),'expected_observations':expected,
                 'complete':len(rows)==expected,'strict_matches':sum(r.get('strict_match',False) for r in rows),
                 'repaired_matches':sum(r.get('repaired_match',False) for r in rows),
                 'errors':sum('error' in r for r in rows),'known_cost_usd':sum(costs),
                 'unknown_cost_calls':len(rows)-len(costs),
                 'input_tokens':sum(r.get('usage',{}).get('prompt_tokens',0) for r in rows),
                 'output_tokens':sum(r.get('usage',{}).get('completion_tokens',0) for r in rows),
                 'median_latency_seconds':median(timings) if timings else None,
                 'latency_range_seconds':[min(timings),max(timings)] if timings else None,
                 'cases':[]}
        for case in report['cases']:
            subset=[r for r in rows if r['task_id']==case[0]]
            summary['cases'].append({'task_id':case[0], 'observations':len(subset),
                                    'repaired_matches':sum(r.get('repaired_match',False) for r in subset)})
        summaries.append(summary)
    return {'scope':'descriptive, small non-independent sample; option rotations are not independent task families',
            'models':summaries}


if __name__=='__main__':
    result=summarize(json.loads(Path('evidence/creative-menu-comparison-v1.json').read_text()))
    Path('evidence/creative-menu-comparison-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

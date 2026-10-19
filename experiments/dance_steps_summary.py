"""Reproduce per-condition step trial counts and context/latency measurements."""
import hashlib, json, statistics
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def span(values):return [min(values),max(values)]

def main():
    paths=['evidence/dance-steps-model-v1.json','evidence/dance-steps-contract-v1.json']
    records=[]
    for path in paths:
        data=json.loads(Path(path).read_text())
        if not data.get('complete'):raise ValueError('incomplete evidence')
        for p,h in data['sources'].items():
            if digest(p)!=h:raise ValueError('source drift: '+p)
        records.extend(dict(c,condition=c.get('condition','original_free')) for c in data['calls'])
    groups=[]
    for model,condition in sorted({(c['model'],c['condition']) for c in records}):
        rows=[c for c in records if (c['model'],c['condition'])==(model,condition)]
        groups.append({'model':model,'condition':condition,'calls':len(rows),'compiled':sum(bool(c.get('compiled')) for c in rows),'correct':sum(bool(c.get('correct')) for c in rows),
          'median_wall_seconds':statistics.median(c['wall_seconds'] for c in rows),'wall_seconds_range':span([c['wall_seconds'] for c in rows]),
          'prompt_tokens_range':span([c['prompt_eval_count'] for c in rows]),'output_tokens_range':span([c['eval_count'] for c in rows]),'input_text_characters_range':span([c['input_text_characters'] for c in rows]),
          'median_native_decode_tokens_per_second':statistics.median(c['eval_count']/(c['eval_duration']/1e9) for c in rows)})
    summary={'sources':{p:digest(p) for p in paths},'calls':len(records),'paid_provider_calls':0,'conditions':groups,
      'scope':'One local run, reused briefs; original_free ran before the diagnostic cells. Native decode speed excludes prefill/load/request/validation. No 5090 benchmark, human taste or H2 learning claim.'}
    Path('evidence/dance-steps-summary-v1.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

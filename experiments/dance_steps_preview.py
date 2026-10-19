"""Render accepted soft/clear stepping plans with verified scene readback."""
import json
from pathlib import Path
from harness2.dance_steps import compile_steps, verify_compilation
from experiments.dance_phrase_preview import render_pair, digest


def main():
    source=Path('evidence/dance-steps-contract-v1.json');data=json.loads(source.read_text())
    if not data.get('complete'):raise ValueError('trial incomplete')
    for p,h in data['sources'].items():
        if digest(p)!=h:raise ValueError('trial source changed')
    chosen=[next(c for c in data['calls'] if c['model']=='gemma4:e2b' and c['condition']=='explicit_enum' and c['case_id']==case and c.get('correct')) for case in ['alternating_soft','alternating_clear']]
    compiled=[compile_steps(c['content']) for c in chosen]
    for c,p in zip(chosen,compiled):
        verify_compilation(p)
        if p['receipt']!=c['receipt']:raise ValueError('trial receipt changed')
    provenance={'evidence_sha256':digest(source),'selection':'Preset soft/clear alternating-step briefs from E2B explicit_enum condition; illustrative variation comparison, not blind taste selection.',
      'calls':[data['calls'].index(c) for c in chosen],'requests':[c['user'] for c in chosen],'moves':[c['moves'] for c in chosen],
      'source_validations':[p['receipt']['validation'] for p in compiled]}
    print(json.dumps(render_pair([p['sequence'] for p in compiled],['Soft','Clear'],provenance,run_name='harness2-dance-steps-v1',evidence_name='dance-steps-preview-v1'),indent=2))

if __name__=='__main__':main()

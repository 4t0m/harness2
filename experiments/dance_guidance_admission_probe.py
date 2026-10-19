"""Admit an actually development-valid H2 intermediate without new inference."""
import hashlib,json
from pathlib import Path
from harness2.dance_guidance_admission import choose_admitted

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    source=Path('evidence/dance-step-h2-v1.json');data=json.loads(source.read_text())
    if not data.get('complete'):raise ValueError('H2 trial incomplete')
    out=Path('evidence/dance-guidance-admission-v1.json')
    if out.exists():raise ValueError('refusing overwrite')
    for p,h in data['sources'].items():
        if digest(p)!=h:raise ValueError('original trial source drift')
    dev=data['development_case'];root=Path('runs/dance-step-h2-v1/development')
    candidates=[];files={}
    for receipt in data['development_receipts']:
        label=receipt['run_id'].split('/')[-1]
        p=(root/'base/systemprompt.md' if label=='base1' else root/'runs/dance_step_h2-oc-seq1'/dev['id']/'harnesses'/label/'systemprompt.md')
        rpath=root/'executions'/receipt['run_id']/'receipt.json'
        if json.loads(rpath.read_text())!=receipt:raise ValueError('development receipt mismatch')
        files[str(p)]=digest(p);files[str(rpath)]=digest(rpath)
        candidates.append({'label':label,'guidance':p.read_text(),'receipt':receipt})
    task={'task':dev['task'],'request':dev['request']};result=choose_admitted(candidates,task)
    report={'scope':'Post-trial host admission repair using development receipts only; no new model calls or heldout testing. Original composed candidate results remain unchanged. A passed development reply does not prove repeated reliability or generalization.',
      'trial_evidence_sha256':digest(source),'source_files':files,'gate_source_sha256':digest('harness2/dance_guidance_admission.py'),'runner_source_sha256':digest(__file__),
      'task':task,'candidates':candidates,'admission':result,'provider_calls':0,'paid_provider_calls':0}
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selected':result['selected']['label'] if result['selected'] else None,'candidates':result['audited_candidates'],'provider_calls':0},indent=2))

if __name__=='__main__':main()

"""Preview a correct local model edit beside its actual protected source."""
import json
from pathlib import Path
from harness2.dance_phrases import compile_plan
from harness2.dance_phrase_edit import bind_source,apply_patch,validate_edit
from experiments.dance_phrase_preview import render_pair,digest


def main():
    source=Path('evidence/dance-phrase-edit-model-v1.json');data=json.loads(source.read_text())
    if not data.get('complete'):raise ValueError('trial incomplete')
    for p,h in data['sources'].items():
        if digest(p)!=h:raise ValueError('frozen trial source changed')
    case=next(c for c in data['cases'] if c['id']=='replace_sway_with_pulse')
    matches=[c for c in data['calls'] if c['case_id']==case['id'] and c['condition']=='patch' and c.get('correct')]
    if not matches:raise ValueError('no accepted model patch for preset demo case')
    chosen=matches[0];raw_source=json.dumps({'moves':case['source_moves']});revision='approved-dance-v1';scope=case['editable_slots']
    snapshot=bind_source(raw_source,revision,scope);edited=apply_patch(chosen['content'],snapshot,raw_source,revision,scope)
    validate_edit(edited,snapshot,raw_source,revision,scope)
    if edited['receipt']!=chosen['edit_receipt']:raise ValueError('edit receipt drift')
    original=compile_plan(raw_source)
    provenance={'evidence_sha256':digest(source),'case_id':case['id'],'request':case['request'],'model':chosen['model'],'call_index':data['calls'].index(chosen),
       'selection':'Preset move-substitution case; first successful patch, illustrative only.','source_moves':case['source_moves'],'edited_moves':chosen['moves'],'edit_receipt':edited['receipt']}
    result=render_pair([original['sequence'],edited['compiled']['sequence']],['Source','Edited'],provenance,run_name='harness2-dance-phrase-edit-v1',evidence_name='dance-phrase-edit-preview-v1')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

"""Independent projection/pixel checks of the rendered motif preview."""
import hashlib,json
from pathlib import Path
from PIL import Image
from harness2.dance_motif_score import compile_intent,verify_score

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 path=Path('evidence/dance-motif-preview-v2.json');d=json.loads(path.read_text());r=d['render']
 source=Path(d['model_evidence_path']);trial=json.loads(source.read_text())
 if sha(source)!=d['model_evidence_sha256']:raise ValueError('trial changed')
 for key,p in [('video_sha256',r['video']),('endpoint_sha256',r['endpoint_png']),('renderer_sha256','experiments/dance_motif_preview.py')]:
  if sha(p)!=d[key]:raise ValueError('artifact hash mismatch')
 seq=[]
 for chosen in d['selected_calls']:
  call=trial['calls'][chosen['call_index']]
  if call['content']!=chosen['raw_content'] or call['model']!=chosen['model'] or call['case_id']!=chosen['case_id']:raise ValueError('call binding')
  c=compile_intent(call['content']);verify_score(c)
  if c['receipt']!=chosen['compiled_receipt']:raise ValueError('motion receipt mismatch')
  seq.append(c['sequence'])
 frames=r['projected_joint_pixels_for_all_321_samples']
 if len(frames)!=321:raise ValueError('projection count')
 roots=0;points=0;head_clearance=[]
 for i,log in enumerate(frames):
  if log['sample_index']!=i or log['time_seconds']!=i/20:raise ValueError('sample timing')
  file=Path(r['endpoint_png']) if i==320 else Path(r['video']).parent/'frames'/f'frame_{i:03d}.png'
  with Image.open(file) as im:
   if im.size!=(800,520):raise ValueError('image dimensions')
   for actor,sequence in enumerate(seq):
    joints=sequence['frames'][i]['joints'];pixels=log['actors'][actor]['joint_pixels']
    expected={name:[round([205,595][actor]+p[0]*160),round(460-p[2]*160)] for name,p in joints.items()}
    if pixels!=expected:raise ValueError('source-to-projection mismatch')
    points+=len(expected)
    if im.getpixel((expected['pelvis'][0],489))[:3]!=(21,139,136):raise ValueError('actual source PNG marker mismatch')
    roots+=1;head_clearance.append(expected['head'][1]-20-153)
 if min(head_clearance)<=0:raise ValueError('head overlaps label band')
 first=json.loads(Path('evidence/dance-motif-preview-v1.json').read_text())
 if first['selected_calls']!=d['selected_calls'] or first['render']['projected_joint_pixels_for_all_321_samples']!=frames:raise ValueError('layout cleanup changed motion')
 out={'scope':'All logged projections recomputed from raw model scores; all actual PNG root markers checked. Does not verify every drawn limb pixel or every encoded video frame. Sparse decoded visual inspection is separate.',
 'source_evidence_sha256':sha(path),'checker_sha256':sha(__file__),'projected_joint_points_checked':points,'actual_png_root_markers_checked':roots,'min_head_label_clearance_px':min(head_clearance),'video_sha256':sha(r['video']),'v1_v2_model_motion_and_projection_identical':True,'complete':True}
 Path('evidence/dance-motif-preview-check-v2.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

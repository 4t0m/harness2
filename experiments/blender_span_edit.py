"""Reproducer: same-process render mutation crashed; use isolated recovery scripts."""
import hashlib
import json
from pathlib import Path
import sys
import bpy

SOURCE=Path('/Users/adom/Development/hermes-testing/runs/harness2-menu-preview-v1/avatar.blend')
OUTPUT=Path('/Users/adom/Development/hermes-testing/runs/harness2-span-preview-v1')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    frames={}
    for frame in range(1,49):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        frames[frame]={o.name:[round(v,7) for row in o.matrix_world for v in row] for o in bpy.data.objects}
    return frames


def main():
    if OUTPUT.exists():raise ValueError('refusing overwrite')
    OUTPUT.mkdir()
    original_hash=digest(SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene=bpy.context.scene
    original=snapshot()
    arm=bpy.data.objects['right_shoulder']
    curve=next(c for c in arm.animation_data.action.fcurves if c.data_path=='rotation_euler' and c.array_index==1)
    key=next(k for k in curve.keyframe_points if abs(k.co.x-24)<1e-6)
    original_peak=float(key.co.y)
    key.co.y=2.35
    curve.update()
    revised=snapshot()
    affected=[]
    for obj in bpy.data.objects:
        ancestor=obj
        while ancestor:
            if ancestor==arm:affected.append(obj.name);break
            ancestor=ancestor.parent
    outside=[f for f in range(1,49) if f<=12 or f>=36]
    preserved=all(original[f]==revised[f] for f in outside)
    other_preserved=all(original[f][name]==revised[f][name] for f in original for name in original[f] if name not in affected)
    changed=[f for f in original if original[f]!=revised[f]]
    if not preserved or not other_preserved or not changed:raise ValueError('span preservation failed')
    scene.frame_set(24)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'revised.blend'))
    # Sparse 6fps previews: 12 samples from the two-second scene, identical settings.
    scene.render.resolution_percentage=50
    scene.eevee.taa_render_samples=1
    scene.render.image_settings.file_format='PNG'
    for variant,peak in [('original',original_peak),('revised',2.35)]:
        folder=OUTPUT/variant;folder.mkdir()
        key.co.y=peak;curve.update()
        for index,frame in enumerate(range(1,49,4),1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            scene.render.filepath=str(folder/f'{index:03d}.png')
            bpy.ops.render.render(write_still=True)
    if digest(SOURCE)!=original_hash:raise ValueError('source changed')
    report={'scope':'host-authored single-key gesture edit, no new model inference',
            'source_sha256':original_hash,'revised_sha256':digest(OUTPUT/'revised.blend'),
            'source_unchanged':True,'editable_frames':[13,35],'changed_frames':changed,
            'all_objects_preserved_outside_span':preserved,'non_arm_objects_preserved_all_frames':other_preserved,
            'affected_objects':affected,'original_peak_radians':original_peak,'revised_peak_radians':2.35,
            'preview_source_frames':list(range(1,49,4)),'preview_fps':6,'preview_resolution':[320,320],
            'limits':'Transform equality only; no biomechanical or artistic-quality judgment. Sparse low-sample preview.'}
    (OUTPUT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()

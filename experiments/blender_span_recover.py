"""Fresh-process verification and immutable revised-scene rendering."""
import json
from pathlib import Path
import bpy
from blender_span_edit import SOURCE, OUTPUT, snapshot, digest


def main():
    target=OUTPUT/'revised-isolated'
    if target.exists():raise ValueError('refusing overwrite')
    target.mkdir()
    source_hash=digest(SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    original=snapshot()
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT/'revised.blend'))
    revised=snapshot()
    arm=bpy.data.objects['right_shoulder']
    affected=[]
    for obj in bpy.data.objects:
        ancestor=obj
        while ancestor:
            if ancestor==arm:affected.append(obj.name);break
            ancestor=ancestor.parent
    preserved=all(original[f]==revised[f] for f in range(1,49) if f<=12 or f>=36)
    others=all(original[f][n]==revised[f][n] for f in original for n in original[f] if n not in affected)
    changed=[f for f in original if original[f]!=revised[f]]
    if not preserved or not others or not changed:raise ValueError('preservation failed')
    report={'scope':'host-authored gesture edit; no new model inference', 'source_sha256':source_hash,
            'revised_sha256':digest(OUTPUT/'revised.blend'),'changed_frames':changed,
            'all_objects_preserved_outside_span':preserved,'non_arm_objects_preserved_all_frames':others,
            'source_unchanged':digest(SOURCE)==source_hash,'affected_objects':affected,
            'render_completed':False,'initial_attempt':'crashed after original preview; retained',
            'preview_source_frames':list(range(1,49,4)),'preview_fps':6}
    receipt=OUTPUT/'recovery-receipt.json'
    receipt.write_text(json.dumps(report,indent=2)+'\n')
    scene=bpy.context.scene
    scene.render.resolution_percentage=50
    scene.eevee.taa_render_samples=1
    scene.render.image_settings.file_format='PNG'
    for index,frame in enumerate(range(1,49,4),1):
        scene.frame_set(frame)
        scene.render.filepath=str(target/f'{index:03d}.png')
        bpy.ops.render.render(write_still=True)
    report['render_completed']=True
    receipt.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()

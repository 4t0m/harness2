"""Apply, verify or render a fixed model-selected motion plan in separate processes."""
import json
from pathlib import Path
import sys
import bpy
from blender_span_edit import SOURCE, snapshot, digest
from harness2.gesture_variation import compile_variation

OUTPUT=Path('/Users/adom/Development/hermes-testing/runs/harness2-model-variation-v1')
mode=sys.argv[-1]
plan=json.loads((OUTPUT/'plan.json').read_text())
expected=compile_variation(json.dumps({'variation':plan['variation']}),digest(SOURCE))
if plan!=expected:raise ValueError('plan does not match trusted compiler')
if mode=='apply':
    if (OUTPUT/'revised.blend').exists():raise ValueError('refusing overwrite')
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    arm=bpy.data.objects[plan['joint']]
    curve=next(c for c in arm.animation_data.action.fcurves if c.data_path==plan['property'] and c.array_index==plan['axis'])
    key=next(k for k in curve.keyframe_points if abs(k.co.x-plan['keyframe'])<1e-6)
    key.co.y=plan['peak_radians'];curve.update()
    arm.update_tag(refresh={'OBJECT'})
    bpy.context.scene.frame_set(24)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'revised.blend'))
elif mode=='verify-render':
    target=OUTPUT/'frames'
    if target.exists():raise ValueError('refusing overwrite')
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE));original=snapshot()
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT/'revised.blend'));revised=snapshot()
    affected=[]
    for obj in bpy.data.objects:
        p=obj
        while p:
            if p.name==plan['joint']:affected.append(obj.name);break
            p=p.parent
    outside=all(original[f]==revised[f] for f in original if not 13<=f<=35)
    others=all(original[f][n]==revised[f][n] for f in original for n in original[f] if n not in affected)
    changed=[f for f in original if original[f]!=revised[f]]
    if not outside or not others or not changed:raise ValueError('preservation failed')
    receipt={'plan':plan,'protected_transforms_preserved':outside,'non_arm_transforms_preserved':others,
             'changed_frames':changed,'revised_sha256':digest(OUTPUT/'revised.blend'),'render_completed':False}
    path=OUTPUT/'receipt.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    target.mkdir();scene=bpy.context.scene
    scene.render.resolution_percentage=50;scene.eevee.taa_render_samples=1
    scene.render.image_settings.file_format='PNG'
    for index,frame in enumerate(range(1,49,4),1):
        scene.frame_set(frame);scene.render.filepath=str(target/f'{index:03d}.png')
        bpy.ops.render.render(write_still=True)
    receipt['render_completed']=True;path.write_text(json.dumps(receipt,indent=2)+'\n')
else:raise ValueError('unknown stage')

"""Immutable original baseline, avoiding post-render animation mutation."""
from pathlib import Path
import bpy
SOURCE=Path('/Users/adom/Development/hermes-testing/runs/harness2-menu-preview-v1/avatar.blend')
OUTPUT=Path('/Users/adom/Development/hermes-testing/runs/harness2-span-preview-v1/original-isolated')
if OUTPUT.exists():raise ValueError('refusing overwrite')
OUTPUT.mkdir()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
scene.render.resolution_percentage=50
scene.eevee.taa_render_samples=1
scene.render.image_settings.file_format='PNG'
for index,frame in enumerate(range(1,49,4),1):
    scene.frame_set(frame)
    scene.render.filepath=str(OUTPUT/f'{index:03d}.png')
    bpy.ops.render.render(write_still=True)

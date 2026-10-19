"""Blender-only single-actor renderer of a host-prepared reference sample stream."""
import json
from pathlib import Path
import sys
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def main():
    source_name, output_name = sys.argv[sys.argv.index('--')+1:]
    data = json.loads(Path(source_name).read_text())
    output = Path(output_name)
    if output.exists():
        raise ValueError('refusing overwrite')
    frames = data['frames']
    if len(frames) != 96 or data['render']['fps'] != 24:
        raise ValueError('expected fixed four-second 24fps sample stream')
    output.mkdir()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.background_type = 'WORLD'
    scene.world.color = (.045, .055, .07)
    scene.render.resolution_x = 512
    scene.render.resolution_y = 320
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.image_settings.file_format = 'PNG'
    material = bpy.data.materials.new('motion_reference')
    material.diffuse_color = (.15, .7, .9, 1)
    joints = {}
    for name in frames[0]['joints']:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
            radius=.045 if name != 'head' else .11)
        obj = bpy.context.object
        obj.name = 'joint__' + name
        obj.data.materials.append(material)
        joints[name] = obj
    bones = []
    for a, b in data['bone_edges']:
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=.025, depth=1)
        obj = bpy.context.object
        obj.name = 'bone__' + a + '__' + b
        obj.data.materials.append(material)
        bones.append((a, b, obj))
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -.05))
    floor = bpy.data.materials.new('floor')
    floor.diffuse_color = (.16, .18, .22, 1)
    bpy.context.object.data.materials.append(floor)
    camera_location = (2.2, -6, 2.5)
    camera_target = (0, 0, .90)
    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.rotation_euler = (Vector(camera_target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 3.5
    scene.camera = camera
    bounds = {'min_x': 1., 'max_x': 0., 'min_y': 1., 'max_y': 0.}
    actor_objects = list(joints.values()) + [obj for a, b, obj in bones]
    for i, frame in enumerate(frames):
        positions = {name: Vector(pos) for name, pos in frame['joints'].items()}
        for name, obj in joints.items():
            obj.location = positions[name]
        for a, b, obj in bones:
            direction = positions[b]-positions[a]
            obj.location = (positions[a]+positions[b])/2
            obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
            obj.scale.z = direction.length
        bpy.context.view_layer.update()
        for obj in actor_objects:
            for corner in obj.bound_box:
                p = world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner))
                if p.z <= 0 or not (.03 <= p.x <= .97 and .03 <= p.y <= .97):
                    raise ValueError('actor is clipped or outside declared framing margin')
                for axis in ['x', 'y']:
                    bounds['min_'+axis] = min(bounds['min_'+axis], getattr(p, axis))
                    bounds['max_'+axis] = max(bounds['max_'+axis], getattr(p, axis))
        scene.render.filepath = str(output / f'{i:03d}.png')
        bpy.ops.render.render(write_still=True)
    result = {'scope': 'single technical proxy actor; render reference only',
              'frame_count': 96, 'fps': 24, 'duration_seconds': 4.0,
              'width': 512, 'height': 320,
              'camera': {'type': 'orthographic', 'location_m': camera_location,
                         'target_m': camera_target, 'ortho_scale': 3.5, 'fixed': True},
              'normalized_actor_bounds_all_frames': bounds, 'minimum_allowed_margin': .03}
    (output / 'render.json').write_text(json.dumps(result, indent=2)+'\n')

if __name__ == '__main__':
    main()

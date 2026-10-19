"""Trusted Blender renderer for prevalidated procedural joint tracks."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def main():
    args=sys.argv[sys.argv.index('--')+1:]
    data=json.loads(Path(args[0]).read_text());output=Path(args[1])
    if output.exists():raise ValueError('refusing overwrite')
    output.mkdir()
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
    scene.display.shading.show_shadows=True
    scene.display.shading.background_type='WORLD';scene.world.color=(.025,.035,.055)
    scene.render.resolution_x=512;scene.render.resolution_y=320;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    actors=[]
    for index,sequence in enumerate(data['sequences']):
        material=bpy.data.materials.new('restrained' if index==0 else 'broad')
        material.diffuse_color=(.15,.7,.9,1) if index==0 else (.95,.45,.15,1)
        joints={}
        for name in sequence['frames'][0]['joints']:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.045 if name!='head' else .11)
            obj=bpy.context.object;obj.name=f'{index}_{name}';obj.data.materials.append(material);joints[name]=obj
        bones=[]
        for start,end in sequence['bone_edges']:
            bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=.025,depth=1)
            obj=bpy.context.object;obj.data.materials.append(material);bones.append((start,end,obj))
        actors.append((sequence,joints,bones,-.8 if index==0 else .8))
    bpy.ops.mesh.primitive_plane_add(size=8,location=(0,0,-.05))
    bpy.context.object.color=(.14,.17,.22,1)
    bpy.ops.object.camera_add(location=(2.7,-6,2.9))
    camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,.95))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=3.7;scene.camera=camera
    indices=list(range(0,len(data['sequences'][0]['frames'])-1,2))
    if len(indices)>48:raise ValueError('render frame cap')
    for number,frame_index in enumerate(indices):
        for sequence,joints,bones,offset in actors:
            positions={name:Vector(pos)+Vector((offset,0,0)) for name,pos in sequence['frames'][frame_index]['joints'].items()}
            for name,obj in joints.items():obj.location=positions[name]
            for start,end,obj in bones:
                direction=positions[end]-positions[start]
                obj.location=(positions[start]+positions[end])/2
                obj.rotation_euler=direction.to_track_quat('Z','Y').to_euler();obj.scale.z=direction.length
        scene.render.filepath=str(output/f'{number:03d}.png');bpy.ops.render.render(write_still=True)
    (output/'render.json').write_text(json.dumps({'source_indices':indices,'left':'restrained','right':'broad','fps':10,'scope':'procedural technical motion, no model choice or taste assessment'},indent=2)+'\n')

if __name__=='__main__':main()

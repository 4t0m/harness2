"""Blender-only export/reimport of animated proxy geometry; no skin/VRM/H3 claim."""
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def main():
    mode,source_name,work_name=sys.argv[sys.argv.index('--')+1:]
    source=json.loads(Path(source_name).read_text())['sequences'][1]
    work=Path(work_name);glb=work/'edited-motion.glb'
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.fps=20;scene.frame_start=1;scene.frame_end=81
    if mode=='export':
        if glb.exists():raise ValueError('refusing overwrite')
        joints={};bones=[]
        material=bpy.data.materials.new('edited_motion');material.diffuse_color=(.95,.45,.15,1)
        for name in source['frames'][0]['joints']:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=6,radius=.04 if name!='head' else .11)
            obj=bpy.context.object;obj.name='joint__'+name;obj.data.materials.append(material);joints[name]=obj
        for a,b in source['bone_edges']:
            bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.025,depth=1)
            obj=bpy.context.object;obj.name='bone__'+a+'__'+b;obj.rotation_mode='QUATERNION';obj.data.materials.append(material);bones.append((a,b,obj))
        for index,frame in enumerate(source['frames'],1):
            positions={k:Vector(v) for k,v in frame['joints'].items()}
            for name,obj in joints.items():obj.location=positions[name];obj.keyframe_insert('location',frame=index)
            for a,b,obj in bones:
                direction=positions[b]-positions[a];q=direction.to_track_quat('Z','Y')
                if obj.rotation_quaternion.dot(q)<0:q.negate()
                obj.rotation_quaternion=q;obj.location=(positions[a]+positions[b])/2;obj.scale.z=direction.length
                for field in ['location','rotation_quaternion','scale']:obj.keyframe_insert(field,frame=index)
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',export_animations=True,export_frame_range=True,
                                  export_force_sampling=True,export_animation_mode='SCENE',export_anim_scene_split_object=False,export_yup=True)
    elif mode=='verify':
        receipt=work/'roundtrip.json'
        if receipt.exists():raise ValueError('refusing overwrite')
        bpy.ops.import_scene.gltf(filepath=str(glb))
        actions=list(bpy.data.actions)
        start=min(a.frame_range[0] for a in actions)
        maximum_joint=0.;maximum_bone=0.
        for index,frame in enumerate(source['frames']):
            scene.frame_set(int(start+index));bpy.context.view_layer.update()
            for name,pos in frame['joints'].items():
                actual=bpy.data.objects['joint__'+name].matrix_world.translation
                maximum_joint=max(maximum_joint,math.dist(tuple(actual),pos))
            for a,b in source['bone_edges']:
                matrix=bpy.data.objects['bone__'+a+'__'+b].matrix_world
                maximum_bone=max(maximum_bone,math.dist(tuple(matrix@Vector((0,0,-.5))),frame['joints'][a]),
                                 math.dist(tuple(matrix@Vector((0,0,.5))),frame['joints'][b]))
        result={'scope':'animated proxy meshes roundtripped through GLB; not skinned rig, VRM or H3 input',
                'imported_start_frame':start,'sample_count':len(source['frames']),'fps':20,
                'joint_count':len(source['frames'][0]['joints']),'bone_count':len(source['bone_edges']),
                'max_joint_error_m':maximum_joint,'max_bone_endpoint_error_m':maximum_bone,
                'passed':maximum_joint<1e-5 and maximum_bone<1e-5}
        receipt.write_text(json.dumps(result,indent=2)+'\n')
        if not result['passed']:raise ValueError('roundtrip drift')
    else:raise ValueError('unknown mode')

if __name__=='__main__':main()

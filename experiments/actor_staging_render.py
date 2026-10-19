"""Render a host-validated two-actor, three-slot staging plan in Blender Workbench."""

import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness2 import dance_motion

FPS = 8
FRAME_COUNT = 48
DURATION_S = 6.0
WIDTH = 512
HEIGHT = 320
SLOT_FRAMES = 16
GESTURES = {"wave", "nod", "neutral"}
VARIATIONS = {"soft", "clear"}
SCOPE = "Technical staging prototype only; no acting realism, taste, or quality claim."
EYE_COLOR = (0.025, 0.035, 0.055, 1.0)
COLORS = ((0.12, 0.58, 0.82, 1.0), (0.92, 0.40, 0.16, 1.0))


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_plan(plan):
    """Reject anything outside the small host-owned staging contract."""
    if not isinstance(plan, dict) or set(plan) != {
        "actors", "cues", "fps", "frame_count", "duration_s", "scene_revision", "scope"
    }:
        raise ValueError("invalid staging plan fields")
    if type(plan["fps"]) is not int or plan["fps"] != FPS:
        raise ValueError("fps must be 8")
    if type(plan["frame_count"]) is not int or plan["frame_count"] != FRAME_COUNT:
        raise ValueError("frame_count must be 48")
    if not _finite_number(plan["duration_s"]) or plan["duration_s"] != DURATION_S:
        raise ValueError("duration_s must be 6")
    if not isinstance(plan["scene_revision"], str) or not plan["scene_revision"].strip():
        raise ValueError("scene_revision must be a nonempty string")
    if not isinstance(plan["scope"], str) or not plan["scope"].strip():
        raise ValueError("scope must be a nonempty string")

    actors = plan["actors"]
    if not isinstance(actors, list) or len(actors) != 2:
        raise ValueError("exactly two actors are required")
    ids = []
    for index, actor in enumerate(actors):
        if not isinstance(actor, dict) or set(actor) != {"id", "x_m", "y_m", "z_m"}:
            raise ValueError(f"invalid actor fields at index {index}")
        if not isinstance(actor["id"], str) or not actor["id"].strip():
            raise ValueError(f"invalid actor id at index {index}")
        if actor["id"] in ids:
            raise ValueError("actor ids must be unique")
        if any(not _finite_number(actor[key]) for key in ("x_m", "y_m", "z_m")):
            raise ValueError(f"non-finite actor position at index {index}")
        if actor["y_m"] != 0 or actor["z_m"] != 0:
            raise ValueError("actors must stay on the host-owned ground plane")
        ids.append(actor["id"])
    xs = [actor["x_m"] for actor in actors]
    if any(abs(x) > 3 for x in xs):
        raise ValueError("actor position exceeds 3 m bound")
    if abs(abs(xs[0] - xs[1]) - 1.7) > 1e-9:
        raise ValueError("actor separation must be 1.7 m")
    if not -1 <= sum(xs) / 2 <= 1:
        raise ValueError("actor pair anchor must be within [-1, 1]")

    cues = plan["cues"]
    if not isinstance(cues, list) or len(cues) != 3:
        raise ValueError("exactly three two-second cues are required")
    slots = []
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {
            "slot", "start_s", "end_s", "actor_id", "gesture", "variation"
        }:
            raise ValueError("invalid cue fields")
        slot = cue["slot"]
        if type(slot) is not int or slot not in (0, 1, 2):
            raise ValueError("cue slot must be 0, 1, or 2")
        if slot in slots:
            raise ValueError("cue slots must be unique")
        slots.append(slot)
        if (not _finite_number(cue["start_s"]) or not _finite_number(cue["end_s"])
                or cue["start_s"] != slot * 2 or cue["end_s"] != (slot + 1) * 2):
            raise ValueError(f"cue {slot} must exactly cover its host-owned two-second slot")
        if not isinstance(cue["actor_id"], str) or cue["actor_id"] not in ids:
            raise ValueError(f"unknown actor in cue {slot}")
        if not isinstance(cue["gesture"], str) or cue["gesture"] not in GESTURES:
            raise ValueError(f"unsupported gesture in cue {slot}")
        if not isinstance(cue["variation"], str) or cue["variation"] not in VARIATIONS:
            raise ValueError(f"unsupported variation in cue {slot}")
    if sorted(slots) != [0, 1, 2]:
        raise ValueError("slots must be 0, 1, and 2")
    return plan


def _rotate_x(vector, angle):
    x, y, z = vector
    cosine, sine = math.cos(angle), math.sin(angle)
    return Vector((x, cosine * y - sine * z, sine * y + cosine * z))


def _rotate_y(vector, angle):
    x, y, z = vector
    cosine, sine = math.cos(angle), math.sin(angle)
    return Vector((cosine * x + sine * z, y, -sine * x + cosine * z))


def _base_joints():
    return dance_motion.generate("restrained")["frames"][8]["joints"]


def _pose(actor, cue, frame_index, base):
    origin = Vector((actor["x_m"], actor["y_m"], actor["z_m"]))
    joints = {name: Vector(point) + origin for name, point in base.items()}
    if cue is None or cue["gesture"] == "neutral":
        return joints, 0.0

    start_index = cue["slot"] * SLOT_FRAMES
    end_index = start_index + SLOT_FRAMES - 1
    progress = (frame_index - start_index) / (end_index - start_index)
    envelope = math.sin(math.pi * progress)
    if progress <= 0.0 or progress >= 1.0:
        envelope = 0.0

    if cue["gesture"] == "wave":
        shoulder = joints["right_shoulder"]
        upper = Vector(base["right_elbow"]) - Vector(base["right_shoulder"])
        forearm = Vector(base["right_wrist"]) - Vector(base["right_elbow"])
        peak = math.radians(112 if cue["variation"] == "soft" else 130)
        lift = -peak * envelope
        joints["right_elbow"] = shoulder + _rotate_y(upper, lift)
        oscillation = math.radians(10 if cue["variation"] == "soft" else 18)
        wave_phase = 2.0 * math.pi * (frame_index - start_index) / 5.0
        wrist_angle = lift + oscillation * envelope * math.sin(wave_phase)
        joints["right_wrist"] = joints["right_elbow"] + _rotate_y(forearm, wrist_angle)
    elif cue["gesture"] == "nod":
        neck = joints["neck"]
        head_offset = Vector(base["head"]) - Vector(base["neck"])
        peak = math.radians(7 if cue["variation"] == "soft" else 14)
        joints["head"] = neck + _rotate_x(head_offset, peak * envelope)
    return joints, envelope


def _cue_for_frame(cues, frame_index):
    slot = frame_index // SLOT_FRAMES
    return next(cue for cue in cues if cue["slot"] == slot)


def _face_points(head, pitch):
    offsets = {
        "nose": Vector((0.0, -0.105, 0.0)),
        "left_eye": Vector((-0.040, -0.080, 0.025)),
        "right_eye": Vector((0.040, -0.080, 0.025)),
    }
    return {name: head + _rotate_x(offset, pitch) for name, offset in offsets.items()}


def _world_points(actors, cues, base):
    points = []
    joint_radii = {name: 0.105 if name == "head" else
                   (0.035 if name in ("left_foot", "right_foot") else 0.045)
                   for name in base}
    feature_radii = {"nose": 0.027, "left_eye": 0.016, "right_eye": 0.016}
    for frame_index in range(FRAME_COUNT):
        cue = _cue_for_frame(cues, frame_index)
        time_s = frame_index / FPS
        for actor in actors:
            acting_cue = cue if cue["actor_id"] == actor["id"] else None
            joints, envelope = _pose(actor, acting_cue, frame_index, base)
            pitch = 0.0
            if acting_cue is not None and acting_cue["gesture"] == "nod":
                peak = math.radians(7 if acting_cue["variation"] == "soft" else 14)
                pitch = peak * envelope
            for name, point in joints.items():
                points.append((point, joint_radii[name], f"{actor['id']}:{name}"))
            for name, point in _face_points(joints["head"], pitch).items():
                points.append((point, feature_radii[name], f"{actor['id']}:{name}"))
            for start, end in dance_motion.BONE_EDGES:
                points.append((joints[start], 0.024, f"{actor['id']}:{start}-{end}:start"))
                points.append((joints[end], 0.024, f"{actor['id']}:{start}-{end}:end"))
    return points


def _material(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material


def _add_sphere(name, radius, material, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def _build_actor(actor, index, base, material, face_material):
    joint_objects = {}
    for name in base:
        radius = 0.105 if name == "head" else (0.035 if name in ("left_foot", "right_foot") else 0.045)
        joint_objects[name] = _add_sphere(f"{actor['id']}_{name}", radius, material)

    bones = {}
    for start, end in dance_motion.BONE_EDGES:
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.024, depth=1.0)
        obj = bpy.context.object
        obj.name = f"{actor['id']}_{start}_{end}"
        obj.data.materials.append(material)
        bones[(start, end)] = obj

    feature_objects = {
        "nose": _add_sphere(f"{actor['id']}_nose", 0.027, face_material, 12, 8),
        "left_eye": _add_sphere(f"{actor['id']}_left_eye", 0.016, face_material, 12, 8),
        "right_eye": _add_sphere(f"{actor['id']}_right_eye", 0.016, face_material, 12, 8),
    }
    return {"actor": actor, "index": index, "material": material,
            "joint_objects": joint_objects, "bones": bones, "feature_objects": feature_objects}


def _set_actor_pose(rig, joints, pitch):
    joint_objects = rig["joint_objects"]
    for name, obj in joint_objects.items():
        obj.location = joints[name]
    for (start, end), obj in rig["bones"].items():
        direction = joints[end] - joints[start]
        obj.location = (joints[start] + joints[end]) * 0.5
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        obj.scale.z = direction.length
    for name, point in _face_points(joints["head"], pitch).items():
        rig["feature_objects"][name].location = point


def _setup_scene(output):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = "WORLD"
    scene.world.color = (0.055, 0.070, 0.095)
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = FPS

    floor_material = _material("stage_floor", (0.16, 0.19, 0.24, 1.0))
    bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.object
    floor.name = "stage_floor"
    floor.data.materials.append(floor_material)

    bpy.ops.object.camera_add(location=(0.0, -7.0, 2.15))
    camera = bpy.context.object
    target = Vector((0.0, 0.0, 0.96))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.4
    scene.camera = camera
    scene.render.filepath = str(output / "000.png")
    bpy.context.view_layer.update()
    return scene, camera


def _check_camera_bounds(scene, camera, points, actors):
    bpy.context.view_layer.update()
    margin = 0.035
    left_actor = min(actors, key=lambda actor: actor["x_m"])
    right_actor = max(actors, key=lambda actor: actor["x_m"])
    left_x = world_to_camera_view(
        scene, camera, Vector((left_actor["x_m"], left_actor["y_m"], left_actor["z_m"] + 1.0))
    ).x
    right_x = world_to_camera_view(
        scene, camera, Vector((right_actor["x_m"], right_actor["y_m"], right_actor["z_m"] + 1.0))
    ).x
    if not left_x < right_x:
        raise ValueError("camera reverses semantic screen ordering")
    view_width = camera.data.ortho_scale
    view_height = view_width / (scene.render.resolution_x / scene.render.resolution_y)
    for point, radius, label in points:
        projected = world_to_camera_view(scene, camera, point)
        margin_x = margin + radius / view_width
        margin_y = margin + radius / view_height
        if not (margin_x <= projected.x <= 1.0 - margin_x and
                margin_y <= projected.y <= 1.0 - margin_y and projected.z > 0):
            raise ValueError(f"actor mesh bounds outside camera at {label}")


def render_plan(plan_path, output_path):
    plan_bytes = Path(plan_path).read_bytes()
    plan = validate_plan(json.loads(plan_bytes))
    output = Path(output_path).expanduser().resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite existing output directory: {output}")
    output.mkdir(parents=True)

    base = _base_joints()
    scene, camera = _setup_scene(output)
    rigs = []
    for index, actor in enumerate(plan["actors"]):
        color = COLORS[index]
        rigs.append(_build_actor(actor, index, base,
                                 _material(f"actor_{index}_material", color),
                                 _material(f"actor_{index}_face", EYE_COLOR)))
    all_points = _world_points(plan["actors"], plan["cues"], base)
    _check_camera_bounds(scene, camera, all_points, plan["actors"])

    frames = []
    for frame_index in range(FRAME_COUNT):
        time_s = frame_index / FPS
        cue = _cue_for_frame(plan["cues"], frame_index)
        frame_actors = []
        for rig in rigs:
            actor = rig["actor"]
            acting_cue = cue if cue["actor_id"] == actor["id"] else None
            joints, envelope = _pose(actor, acting_cue, frame_index, base)
            pitch = 0.0
            if acting_cue is not None and acting_cue["gesture"] == "nod":
                peak = math.radians(7 if acting_cue["variation"] == "soft" else 14)
                pitch = peak * envelope
            _set_actor_pose(rig, joints, pitch)
            frame_actors.append({"id": actor["id"], "intended_joints_world_m": joints})
        bpy.context.view_layer.update()
        for actor_record, rig in zip(frame_actors, rigs):
            actor_record["joints_world_m"] = {
                name: [float(v) for v in obj.matrix_world.translation]
                for name, obj in rig["joint_objects"].items()
            }
            actor_record["intended_joints_world_m"] = {
                name: [float(v) for v in point]
                for name, point in actor_record["intended_joints_world_m"].items()
            }
        scene.render.filepath = str(output / f"{frame_index:03d}.png")
        bpy.ops.render.render(write_still=True)
        frames.append({"frame_index": frame_index, "time_s": time_s,
                       "active_cue": dict(cue), "actors": frame_actors})

    scene_metadata = {
        "engine": scene.render.engine,
        "resolution_px": [WIDTH, HEIGHT],
        "fps": FPS,
        "frame_count": FRAME_COUNT,
        "duration_s": DURATION_S,
        "camera": {
            "projection": "orthographic",
            "location_world_m": [float(v) for v in camera.location],
            "target_world_m": [0.0, 0.0, 0.96],
            "ortho_scale_m": float(camera.data.ortho_scale),
            "actor_bounds_checked": True,
            "screen_right_world_direction": "+x",
            "actor_screen_order_checked": True,
        },
        "bone_edges": dance_motion.BONE_EDGES,
        "source_motion": "dance_motion.generate('restrained').frames[8]",
        "motion_scope": "Static staging with bounded wave/nod gestures; no root translation.",
    }
    receipt = {
        "kind": "actor_staging_render",
        "scene_revision": plan["scene_revision"],
        "scope": plan["scope"],
        "technical_limit": SCOPE,
        "source_plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "render": scene_metadata,
        "frames": frames,
    }
    (output / "motion.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender -b --python experiments/actor_staging_render.py -- plan.json output_dir")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 2:
        raise SystemExit("usage: blender -b --python experiments/actor_staging_render.py -- plan.json output_dir")
    render_plan(args[0], args[1])


if __name__ == "__main__":
    main()

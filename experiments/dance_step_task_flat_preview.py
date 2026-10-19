"""Render a verified local step-task result as a flat 2D motion preview.

This is a front-projected illustrative proxy built from the compiled joint
tracks. It is not a skinned character, anime-quality artwork, or avatar
execution.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

from harness2.dance_step_task import compile_task, verify_task
from experiments.dance_step_task_cases import CASES


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_IN = ROOT / "evidence/dance-step-task-model-v1.json"
EVIDENCE_OUT = ROOT / "evidence/dance-step-task-flat-v2.json"
OUTPUT_DIR = Path("/Users/adom/Development/hermes-testing/runs/harness2-step-task-flat-v2")
CASE_ID = "offset_return_to_mark_with_endpoint_direction"
MODEL_NAME = "hermes-lab-qwen3-8b:latest"
WIDTH, HEIGHT = 640, 420
FPS = 20
ANIMATION_FRAMES = 80
TOTAL_SAMPLES = 81
SCALE_PX_PER_M = 160.0
ORIGIN_X_PX = 320.0
GROUND_Y_PX = 370.0
EXPECTED_PYTHON = Path(
    "/Users/adom/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
)

PALETTE = {
    "background": "#fbf4e8",
    "panel": "#fffaf1",
    "ink": "#252b3a",
    "muted": "#697184",
    "lane": "#d9d1c3",
    "target": "#158b88",
    "root": "#e28a42",
    "hair": "#44304d",
    "skin": "#efbd99",
    "shirt": "#e77562",
    "shirt_light": "#f39a7e",
    "pants": "#354b70",
    "shoe": "#242b3b",
    "white": "#fffdf8",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _font(size: int) -> ImageFont.ImageFont:
    # Pillow's bundled default font keeps this script asset-free and portable.
    return ImageFont.load_default(size=size)


def _project(point: list[float], start_x_m: float) -> tuple[int, int]:
    world_x = start_x_m + point[0]
    return (round(ORIGIN_X_PX + world_x * SCALE_PX_PER_M),
            round(GROUND_Y_PX - point[2] * SCALE_PX_PER_M))


def _dashed_line(draw: ImageDraw.ImageDraw, xy, fill, width=2, dash=7, gap=5) -> None:
    (x1, y1), (x2, y2) = xy
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    offset = 0.0
    while offset < length:
        end = min(offset + dash, length)
        draw.line((round(x1 + ux * offset), round(y1 + uy * offset),
                   round(x1 + ux * end), round(y1 + uy * end)),
                  fill=fill, width=width)
        offset += dash + gap


def _draw_limb(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]],
               color: str, width: int) -> None:
    draw.line(points, fill=PALETTE["ink"], width=width + 4, joint="curve")
    draw.line(points, fill=color, width=width, joint="curve")
    radius = max(3, width // 2)
    for x, y in points[1:-1]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=color, outline=PALETTE["ink"], width=2)


def _draw_scene(joints: dict, task: dict, frame_index: int,
                world_root_mm: float, target_x_mm: int, output_path: Path,
                start_x_m: float) -> dict:
    image = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["background"])
    draw = ImageDraw.Draw(image)
    title_font, small_font = _font(16), _font(12)

    # Backdrop and timeline.
    draw.rounded_rectangle((18, 16, 622, 54), radius=10, fill=PALETTE["panel"])
    draw.text((30, 27), "FLAT 2D STEP PREVIEW", fill=PALETTE["ink"], font=title_font)
    draw.text((390, 29), f"frame {frame_index:02d}/80   {frame_index / FPS:0.2f}s",
              fill=PALETTE["muted"], font=small_font)
    draw.line((31, 64, 609, 64), fill=PALETTE["lane"], width=3)
    progress_x = round(31 + (578 * frame_index / ANIMATION_FRAMES))
    draw.ellipse((progress_x - 4, 60, progress_x + 4, 68), fill=PALETTE["target"])

    lo, hi = task["root_bounds_mm"]
    lane_y = 394

    def x_pixel(world_x_mm: float) -> int:
        return round(ORIGIN_X_PX + (world_x_mm / 1000.0) * SCALE_PX_PER_M)

    lane_left, lane_right = x_pixel(lo), x_pixel(hi)
    draw.line((lane_left, lane_y, lane_right, lane_y), fill=PALETTE["lane"], width=9)
    draw.line((lane_left, lane_y - 8, lane_left, lane_y + 8), fill=PALETTE["ink"], width=2)
    draw.line((lane_right, lane_y - 8, lane_right, lane_y + 8), fill=PALETTE["ink"], width=2)
    target_x = x_pixel(target_x_mm)
    _dashed_line(draw, ((target_x, 78), (target_x, lane_y - 12)), PALETTE["target"], width=2)
    draw.polygon(((target_x - 6, 76), (target_x + 6, 76), (target_x, 84)),
                 fill=PALETTE["target"])
    draw.text((max(16, min(570, target_x + 24)), 112), "TARGET", fill=PALETTE["target"], font=small_font)
    draw.text((lane_left - 16, 404), f"{lo}", fill=PALETTE["muted"], font=small_font)
    draw.text((lane_right - 18, 404), f"{hi} mm", fill=PALETTE["muted"], font=small_font)

    projected = {name: _project(point, start_x_m) for name, point in joints.items()}
    # Construct a simple original front-view figure from the exact projected
    # joint coordinates. All limb centerlines terminate at their compiled joints.
    for side in ("left", "right"):
        _draw_limb(draw, [projected[f"{side}_hip"], projected[f"{side}_knee"],
                          projected[f"{side}_ankle"]], PALETTE["pants"], 8)
        _draw_limb(draw, [projected[f"{side}_ankle"], projected[f"{side}_foot"]],
                   PALETTE["shoe"], 7)

    left_shoulder = projected["left_shoulder"]
    right_shoulder = projected["right_shoulder"]
    right_hip = projected["right_hip"]
    left_hip = projected["left_hip"]
    torso = [left_shoulder, right_shoulder,
             (right_hip[0] + 3, right_hip[1] + 3),
             (left_hip[0] - 3, left_hip[1] + 3)]
    draw.polygon(torso, fill=PALETTE["shirt"], outline=PALETTE["ink"], width=3)
    draw.line((left_shoulder[0] + 4, left_shoulder[1] + 4,
               right_shoulder[0] - 4, right_shoulder[1] + 4),
              fill=PALETTE["shirt_light"], width=3)
    draw.line((left_hip[0], left_hip[1], right_hip[0], right_hip[1]),
              fill=PALETTE["ink"], width=3)
    draw.line((projected["head"], ((left_shoulder[0] + right_shoulder[0]) // 2,
                                    (left_shoulder[1] + right_shoulder[1]) // 2 + 2)),
              fill=PALETTE["skin"], width=7)

    for side in ("left", "right"):
        _draw_limb(draw, [projected[f"{side}_shoulder"], projected[f"{side}_elbow"],
                          projected[f"{side}_wrist"]], PALETTE["skin"], 6)

    hx, hy = projected["head"]
    head_box = (hx - 15, hy - 17, hx + 15, hy + 18)
    draw.ellipse(head_box, fill=PALETTE["skin"], outline=PALETTE["ink"], width=2)
    draw.pieslice((hx - 17, hy - 20, hx + 17, hy + 13), 180, 360,
                  fill=PALETTE["hair"], outline=PALETTE["ink"], width=2)
    draw.polygon(((hx - 16, hy - 2), (hx - 7, hy - 7), (hx - 3, hy + 1),
                  (hx + 3, hy - 6), (hx + 9, hy + 1), (hx + 16, hy - 3),
                  (hx + 13, hy + 9), (hx - 13, hy + 9)),
                 fill=PALETTE["hair"], outline=PALETTE["ink"])
    draw.ellipse((hx - 7, hy + 3, hx - 5, hy + 5), fill=PALETTE["ink"])
    draw.ellipse((hx + 5, hy + 3, hx + 7, hy + 5), fill=PALETTE["ink"])
    draw.arc((hx - 4, hy + 5, hx + 4, hy + 12), 10, 165, fill=PALETTE["ink"], width=1)

    root_pixel = projected["pelvis"]
    draw.ellipse((root_pixel[0] - 5, lane_y - 5, root_pixel[0] + 5, lane_y + 5),
                 fill=PALETTE["root"], outline=PALETTE["ink"], width=1)
    draw.text((24, 78), f"root x = {world_root_mm:+0.0f} mm",
              fill=PALETTE["ink"], font=small_font)
    image.save(output_path, format="PNG", optimize=True)
    return {
        "frame": frame_index,
        "time_seconds": frame_index / FPS,
        "world_root_x_mm": world_root_mm,
        "pelvis_pixel": [root_pixel[0], root_pixel[1]],
        "root_marker_pixel": [root_pixel[0], lane_y],
        "target_marker_x_pixel": target_x,
        "joint_pixels": {name: [point[0], point[1]] for name, point in projected.items()},
    }


def _select_accepted_attempt(evidence: dict, case: dict) -> tuple[dict, dict, int]:
    if evidence.get("complete") is not True or evidence.get("paid_provider_calls") != 0:
        raise ValueError("model evidence must be complete with zero paid calls")
    matches = [result for result in evidence["results"]
               if result.get("case_id") == CASE_ID and result.get("model") == MODEL_NAME]
    if len(matches) != 1:
        raise ValueError("expected exactly one Qwen result for the selected case")
    result = matches[0]
    accepted = [(index, evidence["calls"][index]) for index in result["call_indices"]
                if evidence["calls"][index].get("accepted") is True]
    if not accepted or result.get("final_accepted") is not True:
        raise ValueError("selected model result has no accepted final attempt")
    call_index, call = accepted[0]
    if call.get("attempt") != 1 or result.get("first_accepted") is not False:
        raise ValueError("expected the explicitly identified repaired attempt 1")
    if not case["feasible"]:
        raise ValueError("selected task must be host-feasible")
    return result, call, call_index


def _render_video(frame_dir: Path, video_path: Path) -> tuple[dict, str]:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required for this preview")
    media_dir = Path("/private/tmp")
    media_dir.mkdir(parents=True, exist_ok=True)
    descriptor, log_name = tempfile.mkstemp(prefix="harness2-step-task-flat-v2-",
                                            suffix=".log", dir=media_dir)
    os.close(descriptor)
    log_path = Path(log_name)
    log_parts = []
    encode = [ffmpeg, "-hide_banner", "-y", "-loglevel", "info", "-framerate", str(FPS),
              "-i", str(frame_dir / "frame_%03d.png"), "-frames:v", str(ANIMATION_FRAMES),
              "-t", "4", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
              "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path)]
    try:
        encoded = subprocess.run(encode, capture_output=True, text=True, check=False, timeout=30)
        log_parts.append("COMMAND: " + json.dumps(encode) + "\n" + encoded.stdout + encoded.stderr)
        if encoded.returncode != 0:
            raise RuntimeError(f"ffmpeg exited with {encoded.returncode}; see {log_path}")
        probe_cmd = [ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames,duration",
                     "-of", "json", str(video_path)]
        probed = subprocess.run(probe_cmd, capture_output=True, text=True, check=False, timeout=10)
        log_parts.append("COMMAND: " + json.dumps(probe_cmd) + "\n" + probed.stdout + probed.stderr)
        if probed.returncode != 0:
            raise RuntimeError(f"ffprobe exited with {probed.returncode}; see {log_path}")
        probe = json.loads(probed.stdout)
        streams = probe.get("streams", [])
        if len(streams) != 1:
            raise RuntimeError("ffprobe did not find exactly one video stream")
        stream = streams[0]
        if (stream.get("width") != WIDTH or stream.get("height") != HEIGHT
                or stream.get("r_frame_rate") != f"{FPS}/1"
                or int(stream.get("nb_read_frames", -1)) != ANIMATION_FRAMES
                or not math.isclose(float(stream.get("duration", 0)), 4.0, abs_tol=0.02)):
            raise RuntimeError("encoded preview does not match requested 640x420, 20fps, 4s")
        log_path.write_text("\n\n".join(log_parts))
        return stream, str(log_path)
    except Exception:
        log_path.write_text("\n\n".join(log_parts))
        raise


def main() -> None:
    if Path(sys.executable).resolve() != EXPECTED_PYTHON.resolve():
        raise RuntimeError(f"run with the bundled Python interpreter at {EXPECTED_PYTHON}")
    if EVIDENCE_OUT.exists():
        raise FileExistsError(f"refusing to overwrite {EVIDENCE_OUT}")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"refusing to overwrite {OUTPUT_DIR}")
    evidence_bytes = EVIDENCE_IN.read_bytes()
    source_evidence = json.loads(evidence_bytes)
    frozen_hashes = source_evidence.get("sources")
    if type(frozen_hashes) is not dict or not frozen_hashes:
        raise ValueError("model evidence is missing source hashes")
    for relative, expected in frozen_hashes.items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"frozen source hash mismatch: {relative}")
    fixture_by_id = {case["id"]: case for case in CASES}
    frozen_cases = {case["id"]: case for case in source_evidence.get("cases", [])}
    if frozen_cases != fixture_by_id:
        raise ValueError("current case fixture differs from the frozen model evidence")
    case = fixture_by_id.get(CASE_ID)
    if case is None:
        raise ValueError("selected fixture case is missing")
    result_row, call_row, call_index = _select_accepted_attempt(source_evidence, case)

    compiled = compile_task(call_row["content"], case["task"])
    checks = verify_task(compiled, case["task"])
    if (compiled["receipt"] != call_row.get("receipt")
            or compiled["placement"] != call_row.get("placement")
            or [[move, variation] for move, variation in
                [(row["id"], row["variation"]) for row in compiled["local"]["sequence"]["move_plan"]]]
            != call_row.get("moves")):
        raise ValueError("recompiled result differs from accepted model evidence")

    sequence = compiled["local"]["sequence"]
    start_x_m = case["task"]["start_x_mm"] / 1000.0
    world_roots = [case["task"]["start_x_mm"] + frame["joints"]["pelvis"][0] * 1000
                   for frame in sequence["frames"]]
    lo, hi = case["task"]["root_bounds_mm"]
    if any(value < lo - 1e-7 or value > hi + 1e-7 for value in world_roots):
        raise ValueError("recompiled root trajectory leaves approved world lane")
    final_world_x = world_roots[-1]
    if not math.isclose(final_world_x, case["task"]["target_x_mm"], abs_tol=1e-7):
        raise ValueError("recompiled world endpoint misses target")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    frame_dir = OUTPUT_DIR / "frames"
    frame_dir.mkdir()
    projections = []
    for index, frame in enumerate(sequence["frames"]):
        projected_root = _project(frame["joints"]["pelvis"], start_x_m)
        world_x = case["task"]["start_x_mm"] + frame["joints"]["pelvis"][0] * 1000
        out = (frame_dir / f"frame_{index:03d}.png" if index < ANIMATION_FRAMES
               else OUTPUT_DIR / "endpoint.png")
        projection = _draw_scene(frame["joints"], case["task"], index,
                                 world_x, case["task"]["target_x_mm"], out, start_x_m)
        if projection["pelvis_pixel"] != [projected_root[0], projected_root[1]]:
            raise AssertionError("logged root projection differs from draw projection")
        projections.append(projection)

    video_path = OUTPUT_DIR / "preview.mp4"
    probe, media_log_path = _render_video(frame_dir, video_path)
    receipt = {
        "task_receipt": compiled["receipt"],
        "local_receipt": compiled["local"]["receipt"],
        "placement": compiled["placement"],
        "checks": checks,
    }
    report = {
        "complete": True,
        "renderer_sha256": _sha256(Path(__file__)),
        "video_sha256": _sha256(video_path),
        "endpoint_sha256": _sha256(OUTPUT_DIR / "endpoint.png"),
        "scope": "Flat front-projected 2D proxy from a locally compiled step plan; no skinning, art-quality, balance, or avatar-execution claim.",
        "paid_provider_calls": 0,
        "model_evidence_path": str(EVIDENCE_IN.relative_to(ROOT)),
        "model_evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "frozen_source_hashes": frozen_hashes,
        "selected_model_result": {
            "model": call_row["model"],
            "case_id": call_row["case_id"],
            "call_index": call_index,
            "attempt": call_row["attempt"],
            "accepted": call_row["accepted"],
            "first_attempt_accepted": result_row["first_accepted"],
            "final_result_accepted": result_row["final_accepted"],
            "raw_content": call_row["content"],
        },
        "task": case["task"],
        "request": case["request"],
        "compiled_receipt": receipt,
        "render": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "compiled_sample_count": TOTAL_SAMPLES,
            "video_frame_count": ANIMATION_FRAMES,
            "video_duration_seconds": 4.0,
            "scale_px_per_m": SCALE_PX_PER_M,
            "origin_x_px": ORIGIN_X_PX,
            "ground_y_px": GROUND_Y_PX,
            "world_start_x_m_offset": start_x_m,
            "world_root_min_x_mm": min(world_roots),
            "world_root_max_x_mm": max(world_roots),
            "world_final_x_mm": final_world_x,
            "target_x_mm": case["task"]["target_x_mm"],
            "video": str(video_path),
            "endpoint_png": str(OUTPUT_DIR / "endpoint.png"),
            "ffprobe": probe,
            "media_log_path_outside_git": media_log_path,
            "projection_coordinates": projections,
        },
    }
    _write_json(EVIDENCE_OUT, report)
    print(json.dumps({"evidence": str(EVIDENCE_OUT), "video": str(video_path),
                      "frames": ANIMATION_FRAMES, "samples": TOTAL_SAMPLES,
                      "paid_provider_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()

"""Render the first brief-correct local Qwen motif plans as a flat comparison.

The two original front-projected figures are proxies made from verified joint
tracks. They are not skinned characters, anime artwork, or avatar execution.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from harness2.dance_motif_score import compile_intent, verify_score
from experiments.dance_motif_cases import CASES, score_intent


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_IN = ROOT / "evidence/dance-motif-model-v1.json"
EVIDENCE_OUT = ROOT / "evidence/dance-motif-preview-v1.json"
OUTPUT_DIR = Path("/Users/adom/Development/hermes-testing/runs/harness2-dance-motif-v1")
MODEL_NAME = "hermes-lab-qwen3-8b:latest"
WIDTH, HEIGHT = 800, 520
FPS = 20
VIDEO_FRAMES = 320
TOTAL_SAMPLES = 321
SCALE_PX_PER_M = 160.0
BASELINE_Y = 460.0
PANEL_CENTERS = (205.0, 595.0)
EXPECTED_PYTHON = Path(
    "/Users/adom/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
)

PALETTE = {
    "background": "#fbf4e8",
    "panel": "#fffaf1",
    "ink": "#252b3a",
    "muted": "#697184",
    "line": "#d9d1c3",
    "active": "#158b88",
    "skin": "#efbd99",
    "hair": "#44304d",
    "pants": "#354b70",
    "shoe": "#242b3b",
    "sway": "#e77562",
    "pulse": "#5a8fbd",
    "highlight": "#f0c96a",
    "soft": "#158b88",
    "clear": "#d66a3a",
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
    return ImageFont.load_default(size=size)


def _project(point: list[float], center_x: float) -> tuple[int, int]:
    return (round(center_x + point[0] * SCALE_PX_PER_M),
            round(BASELINE_Y - point[2] * SCALE_PX_PER_M))


def _verify_projection_geometry(sequences: list[dict]) -> dict:
    """Check all projected source joints against text, panel, and footer bounds."""
    if len(sequences) != 2:
        raise ValueError("two verified sequences are required")
    panels = ((18, 111, 392, 500), (408, 111, 782, 500))
    label_bottom = 154
    marker_top, marker_bottom = 485, 493
    minimum_head_label_gap = math.inf
    minimum_art_label_gap = math.inf
    minimum_geometry_panel_margin = math.inf
    minimum_foot_marker_gap = math.inf
    sample_count = 0
    for actor_index, (sequence, center) in enumerate(zip(sequences, PANEL_CENTERS)):
        frames = sequence.get("frames")
        if type(frames) is not list or len(frames) != TOTAL_SAMPLES:
            raise ValueError("geometry preflight requires all 321 compiled samples")
        panel_left, panel_top, panel_right, panel_bottom = panels[actor_index]
        for frame in frames:
            pixels = {name: _project(point, center)
                      for name, point in frame["joints"].items()}
            hx, hy = pixels["head"]
            head_top = hy - 20
            minimum_head_label_gap = min(minimum_head_label_gap, head_top - label_bottom)
            for name, (x, y) in pixels.items():
                x_margin = 17 if name == "head" else 7
                top_margin = 20 if name == "head" else 7
                bottom_margin = 18 if name == "head" else 7
                minimum_art_label_gap = min(
                    minimum_art_label_gap, y - top_margin - label_bottom)
                minimum_geometry_panel_margin = min(
                    minimum_geometry_panel_margin,
                    x - x_margin - panel_left,
                    panel_right - (x + x_margin),
                    y - top_margin - panel_top,
                    panel_bottom - (y + bottom_margin),
                )
            foot_bottom = max(pixels["left_foot"][1], pixels["right_foot"][1]) + 7
            minimum_foot_marker_gap = min(minimum_foot_marker_gap, marker_top - foot_bottom)
            minimum_geometry_panel_margin = min(
                minimum_geometry_panel_margin,
                marker_top - panel_top,
                panel_bottom - marker_bottom,
            )
            sample_count += 1
    if minimum_head_label_gap <= 0:
        raise ValueError("head artwork collides with title/detail labels")
    if minimum_art_label_gap <= 0:
        raise ValueError("projected character artwork collides with title/detail labels")
    if minimum_geometry_panel_margin <= 0:
        raise ValueError("projected character or ground marker leaves its panel")
    if minimum_foot_marker_gap <= 0:
        raise ValueError("feet collide with the ground marker")
    return {
        "samples_checked": sample_count,
        "head_to_label_clearance_px_min": minimum_head_label_gap,
        "all_art_to_label_clearance_px_min": minimum_art_label_gap,
        "drawn_geometry_to_panel_edge_px_min": minimum_geometry_panel_margin,
        "foot_to_ground_marker_clearance_px_min": minimum_foot_marker_gap,
    }


def _draw_limb(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]],
               color: str, width: int) -> None:
    draw.line(points, fill=PALETTE["ink"], width=width + 4, joint="curve")
    draw.line(points, fill=color, width=width, joint="curve")
    radius = max(3, width // 2)
    for x, y in points[1:-1]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=color, outline=PALETTE["ink"], width=2)


def _draw_actor(draw: ImageDraw.ImageDraw, joints: dict, center_x: float,
                shirt: str) -> dict[str, list[int]]:
    projected = {name: _project(point, center_x) for name, point in joints.items()}
    for side in ("left", "right"):
        _draw_limb(draw, [projected[f"{side}_hip"], projected[f"{side}_knee"],
                          projected[f"{side}_ankle"]], PALETTE["pants"], 9)
        _draw_limb(draw, [projected[f"{side}_ankle"], projected[f"{side}_foot"]],
                   PALETTE["shoe"], 7)

    left_shoulder, right_shoulder = projected["left_shoulder"], projected["right_shoulder"]
    left_hip, right_hip = projected["left_hip"], projected["right_hip"]
    torso = [left_shoulder, right_shoulder,
             (right_hip[0] + 3, right_hip[1] + 3),
             (left_hip[0] - 3, left_hip[1] + 3)]
    draw.polygon(torso, fill=shirt, outline=PALETTE["ink"], width=3)
    draw.line((left_shoulder[0] + 4, left_shoulder[1] + 4,
               right_shoulder[0] - 4, right_shoulder[1] + 4),
              fill=PALETTE["white"], width=3)
    draw.line((left_hip[0], left_hip[1], right_hip[0], right_hip[1]),
              fill=PALETTE["ink"], width=3)
    draw.line((projected["head"], ((left_shoulder[0] + right_shoulder[0]) // 2,
                                    (left_shoulder[1] + right_shoulder[1]) // 2 + 2)),
              fill=PALETTE["skin"], width=7)
    for side in ("left", "right"):
        _draw_limb(draw, [projected[f"{side}_shoulder"], projected[f"{side}_elbow"],
                          projected[f"{side}_wrist"]], PALETTE["skin"], 7)

    hx, hy = projected["head"]
    draw.ellipse((hx - 15, hy - 17, hx + 15, hy + 18),
                 fill=PALETTE["skin"], outline=PALETTE["ink"], width=2)
    draw.pieslice((hx - 17, hy - 20, hx + 17, hy + 13), 180, 360,
                  fill=PALETTE["hair"], outline=PALETTE["ink"], width=2)
    draw.polygon(((hx - 16, hy - 2), (hx - 7, hy - 7), (hx - 3, hy + 1),
                  (hx + 3, hy - 6), (hx + 9, hy + 1), (hx + 16, hy - 3),
                  (hx + 13, hy + 9), (hx - 13, hy + 9)),
                 fill=PALETTE["hair"], outline=PALETTE["ink"])
    draw.ellipse((hx - 7, hy + 3, hx - 5, hy + 5), fill=PALETTE["ink"])
    draw.ellipse((hx + 5, hy + 3, hx + 7, hy + 5), fill=PALETTE["ink"])
    draw.arc((hx - 4, hy + 5, hx + 4, hy + 12), 10, 165,
             fill=PALETTE["ink"], width=1)
    return {name: [point[0], point[1]] for name, point in projected.items()}


def _frame_state(intent: dict, frame_index: int) -> dict:
    move_index = min(frame_index // 20, 15)
    section_index = move_index // 4
    local_move = move_index % 4
    section_motif = intent["motif"] if section_index != 2 else (
        "pulse" if intent["motif"] == "sway" else "sway")
    move_id = ("rise", section_motif, section_motif, "settle")[local_move]
    progress_beats = 2.0 if frame_index == TOTAL_SAMPLES - 1 else (frame_index % 20) / 10.0
    if frame_index == TOTAL_SAMPLES - 1:
        move_index = 15
        section_index = 3
        local_move = 3
        section_motif = intent["motif"]
        move_id = "settle"
    return {
        "move_index": move_index,
        "section_index": section_index,
        "section_label": ("A", "A", "B", "A")[section_index],
        "move_id": move_id,
        "accent": intent["accents"][section_index],
        "move_progress_beats": progress_beats,
    }


def _draw_frame(sequences: list[dict], intents: list[dict], frame_index: int,
                output_path: Path) -> dict:
    image = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["background"])
    draw = ImageDraw.Draw(image)
    title, body, small = _font(16), _font(13), _font(11)
    time_seconds = frame_index / FPS
    draw.rounded_rectangle((14, 12, WIDTH - 14, 47), radius=9, fill=PALETTE["panel"])
    draw.text((27, 22), "FLAT 2D MOTIF PREVIEW", fill=PALETTE["ink"], font=title)
    draw.text((WIDTH - 148, 24), f"{time_seconds:05.2f}s / 16.00s",
              fill=PALETTE["muted"], font=small)

    timeline_left, timeline_right = 24, WIDTH - 24
    timeline_y = 66
    draw.line((timeline_left, timeline_y, timeline_right, timeline_y),
              fill=PALETTE["line"], width=4)
    progress_x = round(timeline_left + (timeline_right - timeline_left) *
                       min(frame_index, VIDEO_FRAMES) / VIDEO_FRAMES)
    draw.ellipse((progress_x - 4, timeline_y - 4, progress_x + 4, timeline_y + 4),
                 fill=PALETTE["active"])
    for i, label in enumerate(("A", "A", "B", "A")):
        x1 = timeline_left + (timeline_right - timeline_left) * i / 4
        x2 = timeline_left + (timeline_right - timeline_left) * (i + 1) / 4
        selected = _frame_state(intents[0], frame_index)["section_index"] == i
        box = (round(x1 + 2), 77, round(x2 - 2), 96)
        draw.rounded_rectangle(box, radius=6,
                               fill=PALETTE["highlight"] if selected else PALETTE["panel"],
                               outline=PALETTE["line"], width=1)
        draw.text(((box[0] + box[2]) // 2 - 4, 82), label,
                  fill=PALETTE["ink"], font=body)
    draw.text((24, 104), "SECTION", fill=PALETTE["muted"], font=small)

    actor_logs = []
    state_by_actor = []
    for index, (sequence, intent, center, label) in enumerate(
            zip(sequences, intents, PANEL_CENTERS, ("SWAY PLAN", "PULSE PLAN"))):
        state = _frame_state(intent, frame_index)
        state_by_actor.append(state)
        panel = (18 + index * 390, 111, 392 + index * 390, 500)
        draw.rounded_rectangle(panel, radius=10, fill=PALETTE["panel"],
                               outline=PALETTE["line"], width=1)
        draw.text((panel[0] + 14, panel[1] + 10), label,
                  fill=PALETTE["ink"], font=body)
        accent_color = PALETTE[state["accent"]]
        # Accent words are labels; color is kept consistent across both panels.
        draw.text((panel[0] + 14, panel[1] + 30),
                  f"{state['section_label']}  {state['move_id']}  {state['accent']}  "
                  f"move {state['move_index'] + 1}/16",
                  fill=PALETTE["muted"], font=small)
        draw.text((panel[2] - 82, panel[1] + 30),
                  f"{state['move_progress_beats']:0.1f}/2 beats",
                  fill=accent_color, font=small)
        joints = sequence["frames"][frame_index]["joints"]
        pixels = _draw_actor(draw, joints, center, PALETTE[intent["motif"]])
        root = pixels["pelvis"]
        draw.ellipse((root[0] - 4, 485, root[0] + 4, 493),
                     fill=PALETTE["active"], outline=PALETTE["ink"], width=1)
        actor_logs.append(pixels)

    image.save(output_path, format="PNG", optimize=True)
    return {
        "sample_index": frame_index,
        "time_seconds": time_seconds,
        "section_labels": [state["section_label"] for state in state_by_actor],
        "current_moves": [state["move_id"] for state in state_by_actor],
        "current_accents": [state["accent"] for state in state_by_actor],
        "move_progress_beats": [state["move_progress_beats"] for state in state_by_actor],
        "actors": [
            {"motif": intents[i]["motif"], "joint_pixels": actor_logs[i]}
            for i in range(2)
        ],
    }


def _find_correct_calls(evidence: dict) -> list[dict]:
    if evidence.get("complete") is not True:
        raise ValueError("model evidence must be complete")
    paid = evidence.get("paid_provider_calls", evidence.get("provider_calls_paid", 0))
    if paid != 0:
        raise ValueError("expected zero paid provider calls")
    frozen_cases = evidence.get("cases")
    if frozen_cases != CASES:
        raise ValueError("model evidence fixture differs from the frozen motif cases")
    calls = evidence.get("calls")
    if type(calls) is not list:
        raise ValueError("model evidence has no raw calls list")

    selected = []
    for wanted_motif in ("sway", "pulse"):
        match = None
        for case in CASES:
            if case["expected"]["motif"] != wanted_motif:
                continue
            for index, call in enumerate(calls):
                if (call.get("model") != MODEL_NAME or call.get("case_id") != case["id"]
                        or call.get("condition") != "compact"
                        or call.get("compiled") is not True
                        or call.get("finish_reason") != "stop"
                        or call.get("brief_correct") is not True):
                    continue
                compiled = compile_intent(call.get("content"))
                checks = verify_score(compiled)
                if score_intent(compiled["intent"], case):
                    raise ValueError("report marks a brief-inconsistent call brief-correct")
                if compiled["intent"] != case["expected"]:
                    raise ValueError("compiled intent differs from the brief's hidden check")
                if call.get("intent") != compiled["intent"]:
                    raise ValueError("recompiled intent differs from recorded call intent")
                if call.get("motion_receipt") != compiled["receipt"]:
                    raise ValueError("recompiled receipt differs from recorded motion receipt")
                if (checks.get("frame_count") != TOTAL_SAMPLES
                        or checks.get("section_labels") != ["A", "A", "B", "A"]):
                    raise ValueError("compiled score has unexpected sample count or section labels")
                match = {"case": case, "call": call, "call_index": index,
                         "compiled": compiled}
                break
            if match is not None:
                break
        if match is None:
            raise ValueError(f"no brief-correct local Qwen call for {wanted_motif}")
        selected.append(match)
    if selected[0]["case"]["id"] == selected[1]["case"]["id"]:
        raise ValueError("sway and pulse selections must come from separate briefs")
    return selected


def _render_video(frame_dir: Path, video_path: Path) -> tuple[dict, str]:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required for this preview")
    log_dir = Path("/private/tmp")
    log_dir.mkdir(parents=True, exist_ok=True)
    descriptor, log_name = tempfile.mkstemp(prefix="harness2-dance-motif-v1-",
                                            suffix=".log", dir=log_dir)
    os.close(descriptor)
    log_path = Path(log_name)
    log_parts = []
    encode = [ffmpeg, "-hide_banner", "-y", "-loglevel", "info", "-framerate", str(FPS),
              "-i", str(frame_dir / "frame_%03d.png"), "-frames:v", str(VIDEO_FRAMES),
              "-t", "16", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
              "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path)]
    try:
        encoded = subprocess.run(encode, capture_output=True, text=True,
                                 check=False, timeout=60)
        log_parts.append("COMMAND: " + json.dumps(encode) + "\n" + encoded.stdout + encoded.stderr)
        if encoded.returncode != 0:
            raise RuntimeError(f"ffmpeg exited with {encoded.returncode}; see {log_path}")
        probe_cmd = [ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames,duration",
                     "-of", "json", str(video_path)]
        probed = subprocess.run(probe_cmd, capture_output=True, text=True,
                                check=False, timeout=15)
        log_parts.append("COMMAND: " + json.dumps(probe_cmd) + "\n" + probed.stdout + probed.stderr)
        if probed.returncode != 0:
            raise RuntimeError(f"ffprobe exited with {probed.returncode}; see {log_path}")
        streams = json.loads(probed.stdout).get("streams", [])
        if len(streams) != 1:
            raise RuntimeError("ffprobe did not find exactly one video stream")
        stream = streams[0]
        if (stream.get("width") != WIDTH or stream.get("height") != HEIGHT
                or stream.get("r_frame_rate") != f"{FPS}/1"
                or int(stream.get("nb_read_frames", -1)) != VIDEO_FRAMES
                or not math.isclose(float(stream.get("duration", 0)), 16.0, abs_tol=0.03)):
            raise RuntimeError("encoded preview does not match requested 800x520, 20fps, 16s")
        log_path.write_text("\n\n".join(log_parts))
        return stream, str(log_path)
    except Exception:
        log_path.write_text("\n\n".join(log_parts))
        raise


def main() -> None:
    if Path(__import__("sys").executable).resolve() != EXPECTED_PYTHON.resolve():
        raise RuntimeError(f"run with the bundled Python interpreter at {EXPECTED_PYTHON}")
    if EVIDENCE_OUT.exists():
        raise FileExistsError(f"refusing to overwrite {EVIDENCE_OUT}")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"refusing to overwrite {OUTPUT_DIR}")
    evidence_bytes = EVIDENCE_IN.read_bytes()
    source_evidence = json.loads(evidence_bytes)
    source_hashes = source_evidence.get("sources")
    if type(source_hashes) is not dict or not source_hashes:
        raise ValueError("model evidence is missing source hashes")
    for relative, expected in source_hashes.items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"frozen source hash mismatch: {relative}")

    selected = _find_correct_calls(source_evidence)
    intents, sequences, receipts = [], [], []
    for chosen in selected:
        compiled = chosen["compiled"]
        checks = verify_score(compiled)
        sequence = compiled["sequence"]
        if (len(compiled["sequence"]["frames"]) != TOTAL_SAMPLES
                or checks.get("frame_count") != TOTAL_SAMPLES
                or checks.get("duration_seconds") != 16.0
                or sequence.get("fps") != FPS or sequence.get("beats") != 32
                or sequence.get("duration_seconds") != 16.0
                or checks.get("section_labels") != ["A", "A", "B", "A"]):
            raise ValueError("verified score does not contain the expected 321 samples")
        intents.append(compiled["intent"])
        sequences.append(compiled["sequence"])
        receipts.append(compiled["receipt"])
    projection_geometry = _verify_projection_geometry(sequences)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    frame_dir = OUTPUT_DIR / "frames"
    frame_dir.mkdir()
    projection_log = []
    for frame_index in range(TOTAL_SAMPLES):
        target = (frame_dir / f"frame_{frame_index:03d}.png" if frame_index < VIDEO_FRAMES
                  else OUTPUT_DIR / "endpoint.png")
        projection_log.append(_draw_frame(sequences, intents, frame_index, target))

    video_path = OUTPUT_DIR / "preview.mp4"
    probe, media_log_path = _render_video(frame_dir, video_path)
    report = {
        "complete": True,
        "renderer_sha256": _sha256(Path(__file__)),
        "video_sha256": _sha256(video_path),
        "endpoint_sha256": _sha256(OUTPUT_DIR / "endpoint.png"),
        "scope": "Flat front-projected 2D proxies from verified local procedural joint tracks; no skinning, finished-art, taste, or avatar-execution claim.",
        "provider_calls_during_render": 0,
        "model_evidence_path": str(EVIDENCE_IN.relative_to(ROOT)),
        "model_evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "frozen_source_hashes": source_hashes,
        "compiler_sha256": _sha256(ROOT / "harness2/dance_motif_score.py"),
        "fixture_sha256": _sha256(ROOT / "experiments/dance_motif_cases.py"),
        "selected_calls": [
            {"model": chosen["call"]["model"], "case_id": chosen["case"]["id"],
             "call_index": chosen["call_index"], "attempt": chosen["call"].get("attempt"),
             "brief_correct": chosen["call"].get("brief_correct"),
             "raw_content": chosen["call"]["content"],
             "intent": chosen["compiled"]["intent"],
             "compiled_receipt": chosen["compiled"]["receipt"]}
            for chosen in selected
        ],
        "render": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "compiled_sample_count_per_actor": TOTAL_SAMPLES,
            "video_frame_count": VIDEO_FRAMES,
            "video_duration_seconds": 16.0,
            "scale_px_per_m": SCALE_PX_PER_M,
            "panel_centers_px": list(PANEL_CENTERS),
            "baseline_y_px": BASELINE_Y,
            "projection_geometry_preflight": projection_geometry,
            "section_labels": ["A", "A", "B", "A"],
            "video": str(video_path),
            "endpoint_png": str(OUTPUT_DIR / "endpoint.png"),
            "ffprobe": probe,
            "media_log_path_outside_git": media_log_path,
            "projected_joint_pixels_for_all_321_samples": projection_log,
        },
    }
    _write_json(EVIDENCE_OUT, report)
    print(json.dumps({"evidence": str(EVIDENCE_OUT), "video": str(video_path),
                      "frames": VIDEO_FRAMES, "samples": TOTAL_SAMPLES,
                      "provider_calls_during_render": 0}, sort_keys=True))


if __name__ == "__main__":
    main()

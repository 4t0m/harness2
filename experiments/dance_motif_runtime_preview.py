"""Render the recorded motif-runtime playback samples as flat 2D proxies.

This is a finite recording of the probe's sample log, not live playback,
skinning, finished anime art, a taste judgment, or avatar execution.
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
import time

from PIL import Image, ImageDraw, ImageFont

from experiments.dance_motif_preview import (
    BASELINE_Y as HELPER_BASELINE_Y,
    PANEL_CENTERS as HELPER_PANEL_CENTERS,
    PALETTE,
    SCALE_PX_PER_M as HELPER_SCALE_PX_PER_M,
    _draw_actor,
)
from experiments.dance_motif_runtime_cases import CASES, score_response
from harness2.dance_motif_score import compile_intent, verify_score


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_IN = ROOT / "evidence/dance-motif-runtime-v1.json"
EVIDENCE_OUT = ROOT / "evidence/dance-motif-runtime-preview-v1.json"
OUTPUT_DIR = Path("/Users/adom/Development/hermes-testing/runs/harness2-motif-runtime-v1")
CHECKER_PATH = ROOT / "experiments/dance_motif_runtime_check.py"
HELPER_PATH = ROOT / "experiments/dance_motif_preview.py"
RUNTIME_PATH = ROOT / "harness2/dance_motif_runtime.py"
WIDTH, HEIGHT = 800, 550
FPS = 20
VIDEO_SAMPLES = 140
TOTAL_SAMPLES = 141
PANEL_CENTERS = (205.0, 595.0)
PANEL_RECTS = ((18, 118, 392, 500), (408, 118, 782, 500))
TIMELINE_LEFT, TIMELINE_RIGHT = 24, 776
TIMELINE_MS = 7000
EXPECTED_PYTHON = Path(
    "/Users/adom/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
)

MODEL_LABELS = {
    "gemma4:e2b": "E2B",
    "hermes-lab-qwen3-8b:latest": "QWEN3 8B",
}
MODEL_COLORS = {
    "gemma4:e2b": PALETTE["sway"],
    "hermes-lab-qwen3-8b:latest": PALETTE["pulse"],
}
EVENT_COLORS = {
    "request": "#be8b22",
    "queued": "#be8b22",
    "delivery": PALETTE["muted"],
    "switch": PALETTE["active"],
    "interrupt": "#bd4f4f",
    "late": PALETTE["muted"],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _frame_sha256(frame: dict) -> str:
    payload = json.dumps(frame, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _font(size: int) -> ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _relative(run: dict, at_ms: int) -> int:
    return int(at_ms - run["playback_epoch_ms"])


def _event(run: dict, kind: str, role: str | None = None) -> dict | None:
    return next((event for event in run["events"]
                 if event.get("kind") == kind and
                 (role is None or event.get("role") == role)), None)


def _run_events(run: dict) -> dict:
    replacement_request = _event(run, "request", "replacement")
    replacement_delivery = _event(run, "delivery", "replacement")
    interrupt = _event(run, "interrupt")
    late_delivery = _event(run, "delivery", "delayed_after_stop")
    if any(item is None for item in
           (replacement_request, replacement_delivery, interrupt, late_delivery)):
        raise ValueError("run is missing a replacement, interrupt, or late-delivery event")
    result = replacement_delivery.get("result", {})
    return {
        "replacement_request": replacement_request,
        "replacement_delivery": replacement_delivery,
        "replacement_switch_ms": result.get("switch_at_ms"),
        "replacement_delivery_status": result.get("status"),
        "interrupt": interrupt,
        "late_delivery": late_delivery,
    }


def _status_for_sample(run: dict, sample: dict, calls_by_hash: dict, events: dict) -> dict:
    now_ms = sample["now_ms"]
    role = calls_by_hash.get(sample.get("score_sha256"), "unresolved")
    if role == "unresolved":
        raise ValueError("sample score hash does not map to an admitted local source")
    status = sample.get("status")
    if status == "frozen":
        current = f"FROZEN / {role.upper()}"
    elif status in ("playing", "holding_end"):
        if (events["replacement_delivery_status"] == "queued"
                and now_ms >= events["replacement_delivery"]["at_ms"]
                and now_ms < events["replacement_switch_ms"]):
            current = "PLAY / INITIAL + REPL QUEUED"
        elif (events["replacement_switch_ms"] is not None
              and now_ms >= events["replacement_switch_ms"]):
            current = "PLAY / REPLACEMENT"
        else:
            current = f"{status.upper()} / INITIAL"
    else:
        current = str(status).upper()

    late = events["late_delivery"]
    if now_ms >= late["at_ms"]:
        late_status = late.get("result", {}).get("status", "delivery status missing")
        late_label = f"late {late_status}"
    else:
        late_request = _event(run, "request", "delayed_after_stop")
        late_label = "late response pending" if late_request and now_ms >= late_request["at_ms"] else "late not requested"
    return {"role": role, "status": status, "current_label": current,
            "late_label": late_label}


def _timeline_x(relative_ms: int) -> int:
    clamped = max(0, min(TIMELINE_MS, relative_ms))
    return round(TIMELINE_LEFT + (TIMELINE_RIGHT - TIMELINE_LEFT) *
                 clamped / TIMELINE_MS)


def _timeline_events(run: dict) -> list[dict]:
    meta = _run_events(run)
    switch_ms = meta["replacement_switch_ms"]
    delivery_status = meta["replacement_delivery_status"]
    delivery_kind = "queued" if delivery_status == "queued" else "delivery"
    points = [
        ("request", meta["replacement_request"]["at_ms"], "replacement request"),
        (delivery_kind, meta["replacement_delivery"]["at_ms"],
         "replacement queued" if delivery_status == "queued" else f"delivery {delivery_status}"),
    ]
    if type(switch_ms) is int:
        points.append(("switch", switch_ms, "replacement switch"))
    points.append(("interrupt", meta["interrupt"]["at_ms"], "stop"))
    late_status = meta["late_delivery"].get("result", {}).get("status", "status_missing")
    points.append(("late", meta["late_delivery"]["at_ms"], f"late {late_status}"))
    return [{"kind": kind, "at_ms": at_ms, "label": label,
             "relative_ms": _relative(run, at_ms)} for kind, at_ms, label in points]


def _draw_frame(runs: list[dict], samples: list[dict], calls_by_hashes: list[dict],
                event_maps: list[dict], sample_index: int, output: Path) -> dict:
    image = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["background"])
    draw = ImageDraw.Draw(image)
    title_font, body_font, small_font = _font(15), _font(12), _font(10)
    draw.rounded_rectangle((14, 10, WIDTH - 14, 37), radius=8, fill=PALETTE["panel"])
    draw.text((25, 17), "MOTIF RUNTIME / RECORDED SAMPLE PLAYBACK",
              fill=PALETTE["ink"], font=title_font)
    draw.text((WIDTH - 120, 19), "2D FLAT PROXY", fill=PALETTE["muted"], font=small_font)

    axis_y = 57
    draw.line((TIMELINE_LEFT, axis_y, TIMELINE_RIGHT, axis_y),
              fill=PALETTE["line"], width=3)
    for second in range(8):
        x = _timeline_x(second * 1000)
        draw.line((x, axis_y - 4, x, axis_y + 5), fill=PALETTE["ink"], width=1)
        draw.text((x - 2, 41), str(second), fill=PALETTE["muted"], font=small_font)
    draw.text((TIMELINE_RIGHT + 3, 41), "s", fill=PALETTE["muted"], font=small_font)

    event_rows = []
    event_label_parts = []
    for run_index, (run, row_y) in enumerate(zip(runs, (63, 71))):
        label = MODEL_LABELS[run["model"]]
        events = _timeline_events(run)
        event_rows.append(events)
        row_index = 0 if run["model"] == "gemma4:e2b" else 1
        marker_y = row_y + row_index * 2
        for event in events:
            x = _timeline_x(event["relative_ms"])
            color = EVENT_COLORS[event["kind"]]
            draw.line((x, marker_y - 2, x, marker_y + 3), fill=color, width=2)
        sample_rel = _relative(run, samples[run_index]["sample"]["now_ms"])
        playhead_x = _timeline_x(sample_rel)
        draw.ellipse((playhead_x - 3, axis_y - 3, playhead_x + 3, axis_y + 3),
                     fill=MODEL_COLORS[run["model"]], outline=PALETTE["ink"], width=1)
        values = " ".join(
            f"{item['label']} {_relative(run, item['at_ms']) / 1000:0.2f}"
            for item in events
        )
        event_label_parts.append((label, values))
    for y, (label, values) in zip((80, 94), event_label_parts):
        draw.text((24, y), f"{label}: {values}", fill=PALETTE["muted"], font=small_font)

    actors = []
    for actor_index, (run, sample_row, calls_by_hash, event_meta) in enumerate(
            zip(runs, samples, calls_by_hashes, event_maps)):
        runtime_sample = sample_row["sample"]
        frame = runtime_sample["frame"]
        actual_ms = runtime_sample["now_ms"]
        runtime_status = _status_for_sample(run, runtime_sample, calls_by_hash, event_meta)
        x1, y1, x2, y2 = PANEL_RECTS[actor_index]
        draw.rounded_rectangle((x1, y1, x2, y2), radius=10,
                               fill=PALETTE["panel"], outline=PALETTE["line"], width=1)
        color = MODEL_COLORS[run["model"]]
        draw.text((x1 + 14, 125),
                  f"{MODEL_LABELS[run['model']]} / {run['model']}",
                  fill=color, font=body_font)
        draw.text((x1 + 14, 145), runtime_status["current_label"],
                  fill=PALETTE["ink"], font=small_font)
        draw.text((x1 + 14, 162), runtime_status["late_label"],
                  fill=PALETTE["muted"], font=small_font)

        projected = _draw_actor(draw, frame["joints"], PANEL_CENTERS[actor_index], color)
        root_x = projected["pelvis"][0]
        draw.line((x1 + 25, 486, x2 - 25, 486), fill=PALETTE["line"], width=2)
        draw.ellipse((root_x - 4, 482, root_x + 4, 490),
                     fill=PALETTE["active"], outline=PALETTE["ink"], width=1)
        actors.append({
            "model": run["model"],
            "status": runtime_status,
            "actual_now_ms": actual_ms,
            "relative_to_playback_epoch_ms": _relative(run, actual_ms),
            "target_relative_ms": sample_row["target_relative_ms"],
            "lateness_ms": sample_row["lateness_ms"],
            "source_frame_index": runtime_sample["source_frame_index"],
            "score_sha256": runtime_sample["score_sha256"],
            "source_frame_sha256": _frame_sha256(frame),
            "projected_joint_pixels": projected,
        })

    draw.text((24, 508), f"sample {sample_index + 1:03d}/{TOTAL_SAMPLES}  /  20 fps",
              fill=PALETTE["ink"], font=body_font)
    draw.text((246, 508),
              f"E2B t={actors[0]['relative_to_playback_epoch_ms'] / 1000:0.2f}s"
              f"  late={actors[0]['lateness_ms']:+d}ms",
              fill=MODEL_COLORS["gemma4:e2b"], font=small_font)
    draw.text((495, 508),
              f"Qwen t={actors[1]['relative_to_playback_epoch_ms'] / 1000:0.2f}s"
              f"  late={actors[1]['lateness_ms']:+d}ms",
              fill=MODEL_COLORS["hermes-lab-qwen3-8b:latest"], font=small_font)
    draw.text((24, 528), "Finite samples from the saved runtime log; no live viewer or persistent playback.",
              fill=PALETTE["muted"], font=small_font)
    image.save(output, format="PNG", optimize=True)
    return {
        "sample_index": sample_index,
        "actors": actors,
        "event_markers": event_rows,
    }


def _validate_report(data: dict) -> tuple[list[dict], list[dict], dict]:
    if data.get("complete") is not True:
        raise ValueError("runtime model evidence is incomplete")
    if data.get("provider_calls_paid") != 0:
        raise ValueError("runtime evidence reports unexpected paid provider calls")
    source_hashes = data.get("sources")
    if type(source_hashes) is not dict or not source_hashes:
        raise ValueError("runtime evidence is missing frozen source hashes")
    for relative, expected_hash in source_hashes.items():
        source = ROOT / relative
        if not source.is_file() or _sha256(source) != expected_hash:
            raise ValueError(f"frozen runtime source hash mismatch: {relative}")
    if data.get("cases") != CASES:
        raise ValueError("runtime evidence uses different scenario fixtures")
    if data.get("playback_observation_ms") != 7000 or data.get("sample_period_ms") != 50:
        raise ValueError("runtime observation does not match the requested 7-second 20fps window")

    calls = data.get("calls")
    if type(calls) is not list or len(calls) != 6:
        raise ValueError("runtime evidence must contain six recorded model calls")
    call_compilations = {}
    for call in calls:
        if call.get("finish_reason") != "stop" or call.get("error"):
            raise ValueError("runtime report contains an incomplete model response")
        case = next((item for item in CASES if item["id"] == call.get("case_id")), None)
        if case is None or call.get("role") not in ("initial", "replacement", "delayed_after_stop"):
            raise ValueError("runtime report contains an unknown case/role")
        if call.get("user") != case[call["role"]]["request"]:
            raise ValueError("recorded model prompt differs from the frozen case request")
        compiled = compile_intent(call["content"])
        verify_score(compiled)
        violations = score_response(call["content"], case[call["role"]]["expected_intent"])
        if (call.get("brief_violations") != violations
                or call.get("brief_correct") is not (not violations)):
            raise ValueError("saved offline brief score differs from replay")
        call_compilations[(call["case_id"], call["role"])] = compiled

    models = {run.get("model") for run in data.get("runs", [])}
    if models != set(MODEL_LABELS) or len(data.get("runs", [])) != 2:
        raise ValueError("runtime evidence must have one E2B run and one Qwen run")
    runs = [next(run for run in data["runs"] if run["model"] == model)
            for model in MODEL_LABELS]
    for run in runs:
        if run.get("complete") is not True or len(run.get("samples", [])) != TOTAL_SAMPLES:
            raise ValueError("each runtime run must include 141 samples")
        event_meta = _run_events(run)
        case = next((item for item in CASES if item["id"] == run.get("case_id")), None)
        if case is None:
            raise ValueError("runtime run references an unknown fixture")
        role_calls = {role: call_compilations[(run["case_id"], role)]
                      for role in ("initial", "replacement", "delayed_after_stop")}
        score_roles = {compiled["receipt"]["sequence_sha256"]: role
                       for role, compiled in role_calls.items()}
        report_calls = {call["role"]: call for call in calls
                        if call["case_id"] == run["case_id"]}
        for role in ("initial", "replacement"):
            delivery = report_calls[role].get("delivery", {})
            if delivery.get("score_sha256") != role_calls[role]["receipt"]["sequence_sha256"]:
                raise ValueError("delivery score hash differs from replayed compiler receipt")
        if run["initial_state"].get("status") not in ("playing", "holding_end"):
            raise ValueError("runtime did not begin in an active playback state")
        frozen_frame = next((event.get("sample", {}).get("frame")
                             for event in run["events"] if event.get("kind") == "interrupt"), None)
        if frozen_frame is None:
            raise ValueError("runtime run has no captured interrupt pose")
        frozen_hash = _frame_sha256(frozen_frame)
        switch_at_ms = event_meta["replacement_switch_ms"]
        if type(switch_at_ms) is not int:
            raise ValueError("replacement event lacks an effective timestamp")
        for sample_row in run["samples"]:
            sample = sample_row["sample"]
            frame = sample["frame"]
            score_hash = sample.get("score_sha256")
            if score_hash not in score_roles:
                raise ValueError("sample references an unrecognized accepted score")
            role = "replacement" if sample["now_ms"] >= switch_at_ms else "initial"
            if score_roles[score_hash] != role:
                raise ValueError("sample score does not match event-timestamp playback phase")
            source_index = sample.get("source_frame_index")
            if sample.get("status") == "frozen":
                if _frame_sha256(frame) != frozen_hash:
                    raise ValueError("frozen sample differs from the interrupt frame")
            else:
                if type(source_index) is not int or not 0 <= source_index <= 320:
                    raise ValueError("playing sample has invalid source frame index")
                source_frame = role_calls[role]["sequence"]["frames"][source_index]
                if frame != source_frame:
                    raise ValueError("sample frame differs from its compiled source frame")
        run["_score_roles"] = score_roles
        run["_role_compilations"] = role_calls
        run["_event_meta"] = event_meta
        run["_frozen_frame_sha256"] = frozen_hash
    return runs, calls, source_hashes


def _render_video(frame_dir: Path, video_path: Path) -> tuple[dict, str]:
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe are required for this preview")
    log_dir = Path("/private/tmp")
    log_dir.mkdir(parents=True, exist_ok=True)
    descriptor, log_name = tempfile.mkstemp(prefix="harness2-motif-runtime-v1-",
                                            suffix=".log", dir=log_dir)
    os.close(descriptor)
    log_path = Path(log_name)
    command_log = []
    encode = [ffmpeg, "-hide_banner", "-y", "-loglevel", "info", "-framerate", str(FPS),
              "-i", str(frame_dir / "frame_%03d.png"), "-frames:v", str(VIDEO_SAMPLES),
              "-t", "7", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
              "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path)]
    try:
        encoded = subprocess.run(encode, capture_output=True, text=True,
                                 check=False, timeout=45)
        command_log.append("COMMAND: " + json.dumps(encode) + "\n" + encoded.stdout + encoded.stderr)
        if encoded.returncode != 0:
            raise RuntimeError(f"ffmpeg exited with {encoded.returncode}; see {log_path}")
        probe_command = [ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
                         "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames,duration",
                         "-of", "json", str(video_path)]
        probed = subprocess.run(probe_command, capture_output=True, text=True,
                                 check=False, timeout=15)
        command_log.append("COMMAND: " + json.dumps(probe_command) + "\n" + probed.stdout + probed.stderr)
        if probed.returncode != 0:
            raise RuntimeError(f"ffprobe exited with {probed.returncode}; see {log_path}")
        streams = json.loads(probed.stdout).get("streams", [])
        if len(streams) != 1:
            raise RuntimeError("ffprobe did not find exactly one video stream")
        stream = streams[0]
        if (stream.get("width") != WIDTH or stream.get("height") != HEIGHT
                or stream.get("r_frame_rate") != f"{FPS}/1"
                or int(stream.get("nb_read_frames", -1)) != VIDEO_SAMPLES
                or not math.isclose(float(stream.get("duration", 0)), 7.0, abs_tol=0.03)):
            raise RuntimeError("preview does not match 800x550, 20 fps, 140 frames, 7 seconds")
        log_path.write_text("\n\n".join(command_log))
        return stream, str(log_path)
    except Exception:
        log_path.write_text("\n\n".join(command_log))
        raise


def main() -> None:
    import sys
    if Path(sys.executable).resolve() != EXPECTED_PYTHON.resolve():
        raise RuntimeError(f"run with the bundled Python interpreter at {EXPECTED_PYTHON}")
    if (HELPER_BASELINE_Y != 460.0 or HELPER_SCALE_PX_PER_M != 160.0
            or HELPER_PANEL_CENTERS != PANEL_CENTERS):
        raise ValueError("frozen character helper no longer matches the specified projection")
    if EVIDENCE_OUT.exists() or OUTPUT_DIR.exists():
        raise FileExistsError("refusing to overwrite existing preview output")
    evidence_bytes = EVIDENCE_IN.read_bytes()
    source = json.loads(evidence_bytes)
    runs, calls, source_hashes = _validate_report(source)
    run_samples = [run["samples"] for run in runs]
    calls_by_hashes = [run["_score_roles"] for run in runs]
    event_maps = [run["_event_meta"] for run in runs]

    render_started = time.monotonic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    frame_dir = OUTPUT_DIR / "frames"
    frame_dir.mkdir()
    projection_log = []
    for sample_index in range(VIDEO_SAMPLES):
        target = frame_dir / f"frame_{sample_index:03d}.png"
        projection_log.append(_draw_frame(
            runs, [items[sample_index] for items in run_samples], calls_by_hashes,
            event_maps, sample_index, target))
    endpoint_path = OUTPUT_DIR / "endpoint.png"
    endpoint_log = _draw_frame(
        runs, [items[VIDEO_SAMPLES] for items in run_samples], calls_by_hashes,
        event_maps, VIDEO_SAMPLES, endpoint_path)

    video_path = OUTPUT_DIR / "runtime-preview.mp4"
    ffprobe, media_log_path = _render_video(frame_dir, video_path)
    render_wall_seconds = time.monotonic() - render_started
    report = {
        "complete": True,
        "scope": "Finite 7-second recording rendered from saved 20fps runtime samples; no live viewer, persistent playback, skinning, finished anime art, aesthetic judgment, or avatar execution.",
        "provider_calls_during_render": 0,
        "runtime_evidence_path": str(EVIDENCE_IN.relative_to(ROOT)),
        "runtime_evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        "source_hashes": source_hashes,
        "runtime_checker_path": str(CHECKER_PATH.relative_to(ROOT)),
        "runtime_checker_sha256": _sha256(CHECKER_PATH),
        "runtime_path": str(RUNTIME_PATH.relative_to(ROOT)),
        "runtime_sha256": _sha256(RUNTIME_PATH),
        "renderer_sha256": _sha256(Path(__file__)),
        "helper_path": str(HELPER_PATH.relative_to(ROOT)),
        "helper_sha256": _sha256(HELPER_PATH),
        "case_ids": [run["case_id"] for run in runs],
        "models": [run["model"] for run in runs],
        "recorded_provider_call_count": len(calls),
        "render_wall_seconds": render_wall_seconds,
        "selection": "E2B and Qwen runs selected by their recorded model identifiers; no response was substituted.",
        "model_calls": [
            {"index": index, "model": call["model"], "case_id": call["case_id"],
             "role": call["role"], "finish_reason": call["finish_reason"],
             "brief_correct": call["brief_correct"],
             "compiled_sequence_sha256": compile_intent(call["content"])["receipt"]["sequence_sha256"]}
            for index, call in enumerate(calls)
        ],
        "media": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "video_frames": VIDEO_SAMPLES,
            "duration_seconds": 7.0,
            "terminal_sample_png": str(endpoint_path),
            "terminal_sample_sha256": _sha256(endpoint_path),
            "video": str(video_path),
            "video_sha256": _sha256(video_path),
            "ffprobe": ffprobe,
            "media_log_outside_git": media_log_path,
            "sample_period_ms": source["sample_period_ms"],
            "playback_observation_ms": source["playback_observation_ms"],
            "finite_wall_clock_capture": [
                {"case_id": run["case_id"],
                 "first_sample_at_ms": run["samples"][0]["sample"]["now_ms"],
                 "last_sample_at_ms": run["samples"][-1]["sample"]["now_ms"],
                 "sample_count": len(run["samples"]),
                 "max_lateness_ms": max(row["lateness_ms"] for row in run["samples"])}
                for run in runs
            ],
            "events_by_run": [
                {"case_id": run["case_id"], "playback_epoch_ms": run["playback_epoch_ms"],
                 "timeline_events": _timeline_events(run),
                 "replacement_delivery_status": run["_event_meta"]["replacement_delivery_status"],
                 "late_delivery_status": run["_event_meta"]["late_delivery"].get("result", {}).get("status")}
                for run in runs
            ],
            "sampled_joint_projection_log": projection_log,
            "terminal_sample_projection_log": endpoint_log,
        },
    }
    _write_json(EVIDENCE_OUT, report)
    print(json.dumps({"evidence": str(EVIDENCE_OUT), "video": str(video_path),
                      "video_frames": VIDEO_SAMPLES, "terminal_sample": True,
                      "provider_calls_during_render": 0}, sort_keys=True))


if __name__ == "__main__":
    main()

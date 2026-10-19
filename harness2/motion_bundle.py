"""Portable technical motion reference bundle; no H3 compatibility claim."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Callable

from . import dance_motion
from .dance_edit import preservation_checks

ASSETS = ("tracks.json", "original.json", "comparison.mp4")
MANIFEST = "manifest.json"
SCHEMA_VERSION = 1
VIDEO_EXPECTED = {"width": 512, "height": 320, "frame_count": 40,
                  "fps": 10, "duration_seconds": 4.0}
Probe = Callable[[Path], dict]


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: dict) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read_json(path: Path) -> dict:
    def reject_constant(_value):
        raise ValueError("nonfinite JSON")
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream, object_pairs_hook=_unique_pairs,
                          parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def probe_video(path: Path) -> dict:
    """Read actual stream metadata with a 10-second ffprobe deadline."""
    run = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames,width,height,avg_frame_rate,duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True,
        timeout=10,
    )
    streams = json.loads(run.stdout).get("streams")
    if not isinstance(streams, list) or len(streams) != 1:
        raise ValueError("comparison video must have one video stream")
    stream = streams[0]
    return {"width": int(stream["width"]), "height": int(stream["height"]),
            "frame_count": int(stream["nb_read_frames"]),
            "fps": str(stream["avg_frame_rate"]),
            "duration_seconds": float(stream["duration"])}


def _check_video(metadata: dict) -> dict:
    if not isinstance(metadata, dict) or set(metadata) != set(VIDEO_EXPECTED):
        raise ValueError("incomplete video metadata")
    try:
        rate = Fraction(metadata["fps"])
        exact = (type(metadata["width"]) is int and metadata["width"] == 512
                 and type(metadata["height"]) is int and metadata["height"] == 320
                 and type(metadata["frame_count"]) is int and metadata["frame_count"] == 40
                 and rate == 10
                 and type(metadata["duration_seconds"]) in (int, float)
                 and abs(metadata["duration_seconds"] - 4.0) <= 0.001)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        exact = False
    if not exact:
        raise ValueError("comparison video must be 512x320, 10 fps, 40 frames, 4 seconds")
    return metadata


def _check_timing(sequence: dict) -> None:
    if not isinstance(sequence, dict):
        raise ValueError("motion sequence must be an object")
    expected = {"bpm": dance_motion.BPM, "fps": dance_motion.FPS,
                "beats": dance_motion.BEATS, "duration_seconds": dance_motion.DURATION}
    if any(type(sequence.get(key)) is not type(value) or sequence[key] != value
           for key, value in expected.items()):
        raise ValueError("motion timing differs from authoritative prototype")


def _check_motion(tracks: dict, original: dict) -> tuple[dict, dict]:
    if set(tracks) != {"labels", "sequences"} or not isinstance(tracks["sequences"], list) \
            or len(tracks["sequences"]) != 2 or not isinstance(tracks["labels"], list) \
            or len(tracks["labels"]) != 2 or tracks["labels"][0] != "original":
        raise ValueError("tracks must contain an original and edited sequence")
    source, edited = tracks["sequences"]
    if original != source:
        raise ValueError("original.json differs from first track sequence")
    for sequence in (source, edited):
        _check_timing(sequence)
        dance_motion.validate(sequence)
    checks = preservation_checks(source, edited)
    if not all(checks.values()):
        raise ValueError("edited track changed protected motion data")
    if source == edited:
        raise ValueError("edited track contains no edit")
    return source, edited


def _assets(folder: Path) -> dict:
    result = {}
    for name in ASSETS:
        path = folder / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or linked asset: {name}")
        result[name] = {"sha256": _hash(path), "size_bytes": path.stat().st_size}
    return result


def _inspect(folder: Path, probe: Probe) -> tuple[dict, dict, dict, dict]:
    assets = _assets(folder)
    tracks = _read_json(folder / "tracks.json")
    original = _read_json(folder / "original.json")
    source, edited = _check_motion(tracks, original)
    video = _check_video(probe(folder / "comparison.mp4"))
    return assets, video, source, edited


def build_bundle(source_dir: Path, destination: Path, *, probe: Probe = probe_video) -> dict:
    """Copy validated inputs into a fresh folder and write a checked manifest."""
    source_dir, destination = Path(source_dir), Path(destination)
    if source_dir.is_symlink() or not source_dir.is_dir() or destination.exists() \
            or source_dir.resolve() == destination.resolve():
        raise ValueError("source must be a directory and destination must be fresh and distinct")
    assets, video, source, edited = _inspect(source_dir, probe)
    destination.mkdir(parents=True, exist_ok=False)
    for name in ASSETS:
        shutil.copyfile(source_dir / name, destination / name)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "scope": "Portable technical stick-figure motion reference; no H3 compatibility, biomechanics, or style claim.",
        "assets": assets,
        "track_labels": ["original", "edited"],
        "motion": {"coordinate_system": "world x=lateral, y=forward, z=up; meters",
                   "source_fps": 20, "source_frame_count": 81,
                   "endpoint_inclusive": True, "beats": 8, "bpm": 120,
                   "edit_bounds_beats": [2, 6],
                   "original_sequence_sha256": _json_digest(source),
                   "edited_sequence_sha256": _json_digest(edited)},
        "video": video,
        "renderer_context": "Technical stick-figure comparison from the procedural motion prototype; original and edited tracks shown side by side.",
    }
    (destination / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verify_bundle(destination, probe=probe)
    return manifest


def verify_bundle(folder: Path, *, probe: Probe = probe_video) -> dict:
    """Verify copied bytes, motion invariants, and actual video against fixed rules."""
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir() or (folder / MANIFEST).is_symlink():
        raise ValueError("bundle directory or manifest unavailable")
    manifest = _read_json(folder / MANIFEST)
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != SCHEMA_VERSION \
            or not isinstance(manifest.get("assets"), dict) or set(manifest["assets"]) != set(ASSETS):
        raise ValueError("invalid bundle manifest schema or asset set")
    assets, video, source, edited = _inspect(folder, probe)
    if manifest["assets"] != assets:
        raise ValueError("bundle asset hash or size mismatch")
    if manifest.get("track_labels") != ["original", "edited"]:
        raise ValueError("bundle track labels differ")
    motion = manifest.get("motion")
    if not isinstance(motion, dict) or motion.get("coordinate_system") != "world x=lateral, y=forward, z=up; meters" \
            or motion.get("source_fps") != 20 or motion.get("source_frame_count") != 81 \
            or motion.get("endpoint_inclusive") is not True or motion.get("edit_bounds_beats") != [2, 6] \
            or motion.get("beats") != 8 or motion.get("bpm") != 120 \
            or motion.get("original_sequence_sha256") != _json_digest(source) \
            or motion.get("edited_sequence_sha256") != _json_digest(edited):
        raise ValueError("bundle motion manifest differs from checked tracks")
    if manifest.get("video") != video:
        raise ValueError("bundle video metadata differs from actual stream")
    return {"valid": True, "schema_version": SCHEMA_VERSION,
            "assets": assets, "motion_preserved": True, "video": video}

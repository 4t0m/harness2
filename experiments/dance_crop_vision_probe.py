"""Single-actor crop treatment on the frozen dance-vision images.

Prepare twelve 256x320 crops for independent review, then run at most 24
local vision calls. This reuses the baseline fixture and tests an interface
change; it is not held-out visual quality or dance synthesis evidence.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import time

from experiments.dance_visual_probe import (
    MODELS, NATIVE_KEYS, OPTIONS, _hash, _model_metadata, _ollama_call, _unique_pairs,
)

SOURCE_IMAGES = Path("/Users/adom/Development/hermes-testing/runs/harness2-dance-vision-v1/images")
SOURCE_HASHES = {
    "frame05-normal": "ab499bc52ce8a3da0bd60d4e40856c54898f32959d48e4c01644ffa2b4f8541c",
    "frame05-flip": "c12545043766629ac3e5aa768368d5c460980f7753432c43004ccc663d84d205",
    "frame20-normal": "ebb4223dcff241e0d1a1b8d136d34e1687a6936610c147af7ffac48bf2311ef4",
    "frame20-flip": "2995e08ddcdd429acc889824c02ebf6b7624730a065b95fdb6d94d189652b3d6",
    "frame35-normal": "73bb9190ae4b7b7ec26b3d8ac676c74f75e2270fba32e61c7d7b9167fb2fc950",
    "frame35-flip": "9c1d0f1d287c7b16af149855876f9d705ea9007fcf8740f133fb611b00104267",
}
PAIR_EXPECTED = {"frame05-normal": "same", "frame05-flip": "same",
                 "frame20-normal": "right", "frame20-flip": "left",
                 "frame35-normal": "same", "frame35-flip": "same"}
SCHEMA = {"type": "object", "required": ["hands_pose"], "additionalProperties": False,
          "properties": {"hands_pose": {"type": "string", "enum": ["narrow", "wide", "unclear"]}}}
SYSTEM = (
    "For this one stick figure, are the arms/hands hanging relatively close down beside "
    "the torso (narrow), or held diagonally outward well away from the torso (wide)? "
    "Judge pose only. Return exactly one JSON object with hands_pose set to narrow, wide, or unclear."
)
USER = "Classify the pose of the single stick figure in this image."
MAX_CALLS = 24
SEED = 20261020
_VERSION = re.compile(r"[1-9][0-9]*\Z")


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"invalid PNG: {path.name}")
    return struct.unpack(">II", header[16:24])


def _side_expected(case_id: str, side: str) -> str:
    winner = PAIR_EXPECTED[case_id]
    return "narrow" if winner == side else "wide"


def _crop(source: Path, output: Path, side: str) -> None:
    left = 0 if side == "left" else 256
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", str(source),
                    "-vf", f"crop=256:320:{left}:0", "-frames:v", "1",
                    "-compression_level", "9", str(output)],
                   check=True, timeout=15, capture_output=True)
    if _png_size(output) != (256, 320):
        raise ValueError("crop dimensions differ from native half-frame")


def _order() -> dict[str, list[str]]:
    ids = [f"{case_id}-{side}" for case_id in SOURCE_HASHES for side in ("left", "right")]
    random.Random(SEED).shuffle(ids)
    return {MODELS[0]: ids, MODELS[1]: list(reversed(ids))}


def prepare(version: int, *, runs_root: Path = Path("runs")) -> Path:
    """Make a fresh crop packet without contacting the model endpoint."""
    if type(version) is not int or version < 1:
        raise ValueError("positive integer version required")
    for case_id, expected_hash in SOURCE_HASHES.items():
        source = SOURCE_IMAGES / f"{case_id}.png"
        if source.is_symlink() or not source.is_file() or _hash(source) != expected_hash \
                or _png_size(source) != (512, 320):
            raise ValueError(f"frozen source image changed: {case_id}")
    work = Path(runs_root) / f"harness2-dance-crop-vision-v{version}"
    work.mkdir(parents=True, exist_ok=False)
    images = work / "images"
    images.mkdir()
    crops = []
    for case_id, source_hash in SOURCE_HASHES.items():
        source = SOURCE_IMAGES / f"{case_id}.png"
        for side in ("left", "right"):
            crop_id = f"{case_id}-{side}"
            output = images / f"{crop_id}.png"
            _crop(source, output, side)
            crops.append({"crop_id": crop_id, "pair_case_id": case_id,
                          "source_image_sha256": source_hash, "source_side": side,
                          "crop_box_xywh": [0 if side == "left" else 256, 0, 256, 320],
                          "image": f"images/{output.name}", "image_sha256": _hash(output),
                          "image_bytes": output.stat().st_size,
                          "expected_host_only": _side_expected(case_id, side)})
    manifest = {"status": "prepared_for_crop_and_oracle_review",
                "scope": "Reused-fixture single-actor pose interface treatment; not held-out quality",
                "source_images": str(SOURCE_IMAGES), "source_hashes": SOURCE_HASHES,
                "models": list(MODELS), "crops": crops, "pair_expected_host_only": PAIR_EXPECTED,
                "order_seed": SEED, "order_by_model": _order(),
                "system_prompt": SYSTEM, "user_prompt": USER, "schema": SCHEMA,
                "options": OPTIONS, "think": False, "max_calls": MAX_CALLS,
                "transport_timeout_seconds": 35, "hard_deadline_seconds": 40,
                "api_cost_usd": None, "local_hardware_cost": "unmeasured"}
    (work / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return work


def _verdict(content: str, expected: str) -> dict:
    if not isinstance(content, str) or len(content.encode("utf-8")) > 4096:
        return {"strict_json": False, "semantic_correct": False,
                "reason": "nontext or oversized content"}
    def reject_constant(_value):
        raise ValueError("nonfinite JSON")
    try:
        value = json.loads(content, object_pairs_hook=_unique_pairs,
                           parse_constant=reject_constant)
    except (ValueError, TypeError, RecursionError):
        return {"strict_json": False, "semantic_correct": False,
                "reason": "not one strict JSON object"}
    if not isinstance(value, dict) or set(value) != {"hands_pose"} \
            or type(value["hands_pose"]) is not str \
            or value["hands_pose"] not in ("narrow", "wide", "unclear"):
        return {"strict_json": False, "semantic_correct": False,
                "reason": "invalid hands_pose field"}
    answer = value["hands_pose"]
    return {"strict_json": True, "semantic_correct": answer == expected,
            "answer": answer, "reason": "correct" if answer == expected else "semantic mismatch"}


def derive_pair(left: str, right: str) -> str:
    """Host comparison of two strict per-actor classifications."""
    if left not in ("narrow", "wide", "unclear") or right not in ("narrow", "wide", "unclear"):
        raise ValueError("pair requires two catalog classifications")
    if "unclear" in (left, right):
        return "unclear"
    if left == right:
        return "same"
    return "left" if left == "narrow" else "right"


def _read_packet(work: Path) -> dict:
    manifest_path = work / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("prepared crop manifest unavailable")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "prepared_for_crop_and_oracle_review" \
            or manifest.get("source_hashes") != SOURCE_HASHES \
            or manifest.get("pair_expected_host_only") != PAIR_EXPECTED \
            or manifest.get("models") != list(MODELS) or manifest.get("schema") != SCHEMA \
            or manifest.get("options") != OPTIONS or manifest.get("system_prompt") != SYSTEM \
            or manifest.get("user_prompt") != USER or manifest.get("max_calls") != MAX_CALLS \
            or manifest.get("order_seed") != SEED or manifest.get("order_by_model") != _order() \
            or not isinstance(manifest.get("crops"), list) or len(manifest["crops"]) != 12:
        raise ValueError("crop packet differs from frozen treatment")
    expected_ids = {f"{case_id}-{side}" for case_id in SOURCE_HASHES for side in ("left", "right")}
    if {row.get("crop_id") for row in manifest["crops"]} != expected_ids:
        raise ValueError("crop set changed")
    for row in manifest["crops"]:
        crop_id, case_id, side = row["crop_id"], row["pair_case_id"], row["source_side"]
        image = work / "images" / f"{crop_id}.png"
        if case_id not in SOURCE_HASHES or side not in ("left", "right") \
                or crop_id != f"{case_id}-{side}" or row.get("source_image_sha256") != SOURCE_HASHES[case_id] \
                or row.get("crop_box_xywh") != [0 if side == "left" else 256, 0, 256, 320] \
                or row.get("image") != f"images/{crop_id}.png" or image.is_symlink() \
                or not image.is_file() or _png_size(image) != (256, 320) \
                or row.get("image_sha256") != _hash(image) \
                or row.get("expected_host_only") != _side_expected(case_id, side):
            raise ValueError("prepared crop or host answer changed")
    return manifest


def run(version: int, *, runs_root: Path = Path("runs")) -> Path:
    """Run at most 24 calls, preserving raw replies and every attempted crop."""
    if type(version) is not int or version < 1:
        raise ValueError("positive integer version required")
    work = Path(runs_root) / f"harness2-dance-crop-vision-v{version}"
    manifest = _read_packet(work)
    metadata = _model_metadata()
    with (work / "model-metadata.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(metadata, indent=2) + "\n")
    by_id = {row["crop_id"]: row for row in manifest["crops"]}
    order = [(model, crop_id) for model in MODELS for crop_id in manifest["order_by_model"][model]]
    completed = []
    rows = []
    consecutive_failures = 0
    with (work / "receipts.jsonl").open("x", encoding="utf-8") as receipts:
        for model, crop_id in order:
            if len(completed) >= MAX_CALLS or consecutive_failures >= 2:
                break
            crop = by_id[crop_id]
            image_bytes = (work / crop["image"]).read_bytes()
            body = {"model": model, "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER,
                 "images": [base64.b64encode(image_bytes).decode("ascii")]},
            ], "stream": False, "think": False, "format": SCHEMA,
                    "options": OPTIONS, "keep_alive": "2m"}
            row = {"model_requested": model, "model_digest": metadata[model]["digest"],
                   "crop_id": crop_id, "pair_case_id": crop["pair_case_id"],
                   "source_side": crop["source_side"], "source_image_sha256": crop["source_image_sha256"],
                   "image_sha256": crop["image_sha256"], "image_bytes": len(image_bytes),
                   "system_prompt": SYSTEM, "user_prompt": USER, "schema": SCHEMA,
                   "request_options": OPTIONS, "think": False,
                   "expected_host_only": crop["expected_host_only"],
                   "transport_timeout_seconds": 35, "hard_deadline_seconds": 40,
                   "api_cost_usd": None, "local_hardware_cost": "unmeasured"}
            started = time.monotonic()
            try:
                raw = _ollama_call(body)
                row["raw_response"] = raw
                row["model_served"] = raw.get("model")
                row["done_reason"] = raw.get("done_reason")
                row["thinking_present"] = bool(raw.get("message", {}).get("thinking"))
                row.update({key: raw.get(key) for key in NATIVE_KEYS})
                if raw.get("done_reason") == "stop":
                    row.update(_verdict(raw.get("message", {}).get("content"), crop["expected_host_only"]))
                else:
                    row.update(strict_json=False, semantic_correct=False,
                               reason="incomplete native response")
                consecutive_failures = 0
            except Exception as exc:
                row.update(transport_error_type=type(exc).__name__, strict_json=False,
                           semantic_correct=False, reason="transport or native protocol failure")
                consecutive_failures += 1
            finally:
                row["wall_seconds"] = time.monotonic() - started
                receipts.write(json.dumps(row, ensure_ascii=False) + "\n")
                receipts.flush()
                os.fsync(receipts.fileno())
                rows.append(row)
                completed.append((model, crop_id))
    pairs = []
    for model in MODELS:
        for case_id, expected in PAIR_EXPECTED.items():
            by_side = {row["source_side"]: row for row in rows
                       if row["model_requested"] == model and row["pair_case_id"] == case_id}
            left, right = by_side.get("left"), by_side.get("right")
            if left and right and left.get("strict_json") and right.get("strict_json"):
                answer = derive_pair(left["answer"], right["answer"])
                status = "derived"
            else:
                answer, status = None, "incomplete_or_invalid_side"
            pairs.append({"model": model, "pair_case_id": case_id,
                          "left_crop_id": f"{case_id}-left", "right_crop_id": f"{case_id}-right",
                          "left_answer": left.get("answer") if left else None,
                          "right_answer": right.get("answer") if right else None,
                          "derived_pair": answer, "expected_host_only": expected,
                          "semantic_correct": answer == expected if answer is not None else False,
                          "status": status})
    with (work / "pairs.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(pairs, indent=2) + "\n")
    summary = {"attempted": len(completed), "max_calls": MAX_CALLS,
               "stopped_after_transport_failures": consecutive_failures >= 2,
               "unattempted": [{"model": model, "crop_id": crop_id}
                               for model, crop_id in order[len(completed):]],
               "receipts": "receipts.jsonl", "pairs": "pairs.json",
               "api_cost_usd": None, "local_hardware_cost": "unmeasured"}
    with (work / "summary.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(summary, indent=2) + "\n")
    return work


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    parser.add_argument("--version", required=True, type=str)
    parser.add_argument("--runs-root", type=Path,
                        default=Path("/Users/adom/Development/hermes-testing/runs"))
    args = parser.parse_args()
    if not _VERSION.fullmatch(args.version):
        parser.error("version must be a positive integer")
    work = (prepare if args.phase == "prepare" else run)(int(args.version), runs_root=args.runs_root)
    print(work)


if __name__ == "__main__":
    main()

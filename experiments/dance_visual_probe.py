"""Prepare, then run a bounded local vision check on an existing comparison video.

This measures geometric hand-position classification, not dance quality. The
prepare phase makes six inspectable PNGs and makes no model calls. Run only
after an independent reviewer has checked the images and host-only labels.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import time
from urllib.request import Request, urlopen

SOURCE_VIDEO = Path("/Users/adom/Development/hermes-testing/runs/harness2-dance-model-edit-v1/comparison.mp4")
SOURCE_SHA256 = "fae23a8b9cd88af9084ecdf50f18e7e89a4ee83a382e62d0ccfed727834a3d44"
MODELS = ("gemma4:e2b", "gemma4:e4b")
CASES = (
    ("frame05-normal", 5, False, "same"),
    ("frame05-flip", 5, True, "same"),
    ("frame20-normal", 20, False, "right"),
    ("frame20-flip", 20, True, "left"),
    ("frame35-normal", 35, False, "same"),
    ("frame35-flip", 35, True, "same"),
)
SYSTEM = (
    "Compare the two stick figures geometrically. Which figure's hands are closer to that "
    "figure's own torso: the figure on the image's left, the figure on the image's right, "
    "both about the same, or unclear? Ignore color, absolute screen position, and artistic "
    "appeal. Return exactly one JSON object with inward_hands set to left, right, same, or unclear."
)
USER = "Inspect this single image. Compare each figure's hands with its own torso."
SCHEMA = {"type": "object", "required": ["inward_hands"], "additionalProperties": False,
          "properties": {"inward_hands": {"type": "string",
                                          "enum": ["left", "right", "same", "unclear"]}}}
OPTIONS = {"num_ctx": 4096, "num_predict": 64, "temperature": 0}
API_URL = "http://127.0.0.1:11434/api/chat"
TAGS_URL = "http://127.0.0.1:11434/api/tags"
NATIVE_KEYS = ("total_duration", "load_duration", "prompt_eval_count",
               "prompt_eval_duration", "eval_count", "eval_duration")
MAX_CALLS = 12
MAX_BYTES = 1_048_576
_VERSION = re.compile(r"[1-9][0-9]*\Z")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_order(model_index: int) -> list[str]:
    order = [case[0] for case in CASES]
    random.Random(20261019 + model_index).shuffle(order)
    return order


def _extract_frame(video: Path, output: Path, frame_index: int, flip: bool) -> None:
    selection = f"select=eq(n\\,{frame_index})"
    filters = selection + (",hflip" if flip else "")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", str(video),
                    "-vf", filters, "-vsync", "0", "-frames:v", "1",
                    "-compression_level", "9", str(output)],
                   check=True, timeout=15, capture_output=True)
    if not output.is_file() or not output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"frame {frame_index} did not decode to PNG")


def prepare(version: int, *, runs_root: Path = Path("runs")) -> Path:
    """Create a fresh inspected-input packet; this never contacts Ollama."""
    if type(version) is not int or version < 1:
        raise ValueError("positive integer version required")
    if not SOURCE_VIDEO.is_file() or _hash(SOURCE_VIDEO) != SOURCE_SHA256:
        raise ValueError("frozen comparison video is missing or changed")
    work = Path(runs_root) / f"harness2-dance-vision-v{version}"
    work.mkdir(parents=True, exist_ok=False)
    images = work / "images"
    images.mkdir()
    cases = []
    for case_id, frame_index, flip, expected in CASES:
        image = images / f"{case_id}.png"
        _extract_frame(SOURCE_VIDEO, image, frame_index, flip)
        cases.append({"case_id": case_id, "source_frame_index": frame_index,
                      "horizontal_flip": flip, "image": f"images/{image.name}",
                      "image_sha256": _hash(image), "image_bytes": image.stat().st_size,
                      "expected_host_only": expected})
    manifest = {"status": "prepared_for_image_and_oracle_review",
                "scope": "Local geometric vision pilot; no dance synthesis or taste assessment",
                "source_video": str(SOURCE_VIDEO), "source_video_sha256": SOURCE_SHA256,
                "models": list(MODELS), "cases": cases,
                "order_by_model": {model: _case_order(index) for index, model in enumerate(MODELS)},
                "system_prompt": SYSTEM, "user_prompt": USER, "schema": SCHEMA,
                "options": OPTIONS, "think": False, "max_calls": MAX_CALLS,
                "transport_timeout_seconds": 35, "hard_deadline_seconds": 40,
                "api_cost_usd": None, "local_hardware_cost": "unmeasured"}
    (work / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return work


def _unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _verdict(content: str, expected: str) -> dict:
    if not isinstance(content, str) or len(content.encode("utf-8")) > 4096:
        return {"strict_json": False, "semantic_correct": False, "reason": "nontext or oversized content"}
    try:
        value = json.loads(content, object_pairs_hook=_unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    except (ValueError, TypeError, RecursionError):
        return {"strict_json": False, "semantic_correct": False, "reason": "not one strict JSON object"}
    if not isinstance(value, dict) or set(value) != {"inward_hands"} \
            or type(value["inward_hands"]) is not str or value["inward_hands"] not in SCHEMA["properties"]["inward_hands"]["enum"]:
        return {"strict_json": False, "semantic_correct": False, "reason": "invalid inward_hands field"}
    correct = value["inward_hands"] == expected
    return {"strict_json": True, "semantic_correct": correct,
            "answer": value["inward_hands"], "reason": "correct" if correct else "semantic mismatch"}


def _deadline(_signum, _frame):
    raise TimeoutError("40-second hard call deadline")


def _ollama_call(body: dict) -> dict:
    previous = signal.signal(signal.SIGALRM, _deadline)
    signal.setitimer(signal.ITIMER_REAL, 40)
    try:
        request = Request(API_URL, data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=35) as response:
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("oversized Ollama response")
        raw = json.loads(data)
        if not isinstance(raw, dict):
            raise ValueError("invalid Ollama response")
        return raw
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _model_metadata() -> dict:
    """Keep only requested model identities and native digests."""
    with urlopen(TAGS_URL, timeout=5) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("oversized Ollama model metadata")
    tags = json.loads(data)
    models = tags.get("models")
    if not isinstance(models, list):
        raise ValueError("invalid Ollama model metadata")
    selected = {}
    for name in MODELS:
        item = next((entry for entry in models
                     if isinstance(entry, dict) and entry.get("name") == name), None)
        if not isinstance(item, dict) or not isinstance(item.get("digest"), str):
            raise ValueError(f"requested local model unavailable: {name}")
        selected[name] = {key: item.get(key) for key in ("name", "digest", "modified_at", "size")}
    return selected


def _read_packet(work: Path) -> dict:
    manifest_path = work / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("prepared manifest unavailable")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "prepared_for_image_and_oracle_review" \
            or manifest.get("source_video_sha256") != SOURCE_SHA256 \
            or manifest.get("models") != list(MODELS) or manifest.get("max_calls") != MAX_CALLS \
            or manifest.get("system_prompt") != SYSTEM or manifest.get("user_prompt") != USER \
            or manifest.get("schema") != SCHEMA or manifest.get("options") != OPTIONS \
            or len(manifest.get("cases", [])) != len(CASES):
        raise ValueError("prepared packet differs from frozen pilot")
    for row, (case_id, index, flip, expected) in zip(manifest["cases"], CASES):
        path = work / "images" / f"{case_id}.png"
        if (row.get("case_id"), row.get("source_frame_index"), row.get("horizontal_flip"),
            row.get("expected_host_only")) != (case_id, index, flip, expected) \
                or row.get("image") != f"images/{case_id}.png" or path.is_symlink() \
                or not path.is_file() or row.get("image_sha256") != _hash(path):
            raise ValueError("prepared image or host answer changed")
    if manifest.get("order_by_model") != {m: _case_order(i) for i, m in enumerate(MODELS)}:
        raise ValueError("case order changed")
    return manifest


def run(version: int, *, runs_root: Path = Path("runs")) -> Path:
    """Run no more than 12 local calls; append one durable receipt per attempt."""
    if type(version) is not int or version < 1:
        raise ValueError("positive integer version required")
    work = Path(runs_root) / f"harness2-dance-vision-v{version}"
    manifest = _read_packet(work)
    model_metadata = _model_metadata()
    with (work / "model-metadata.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(model_metadata, indent=2) + "\n")
    by_id = {row["case_id"]: row for row in manifest["cases"]}
    order = [(model, case_id) for model in MODELS for case_id in manifest["order_by_model"][model]]
    receipts_path = work / "receipts.jsonl"
    consecutive_transport_failures = 0
    completed = []
    with receipts_path.open("x", encoding="utf-8") as receipts:
        for model, case_id in order:
            if len(completed) >= MAX_CALLS or consecutive_transport_failures >= 2:
                break
            case = by_id[case_id]
            image = work / case["image"]
            image_bytes = image.read_bytes()
            body = {"model": model, "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER,
                 "images": [base64.b64encode(image_bytes).decode("ascii")]},
            ], "stream": False, "think": False, "format": SCHEMA,
                    "options": OPTIONS, "keep_alive": "2m"}
            row = {"model_requested": model, "case_id": case_id, "system_prompt": SYSTEM,
                   "model_digest": model_metadata[model]["digest"],
                   "user_prompt": USER, "image_sha256": case["image_sha256"],
                   "image_bytes": len(image_bytes), "expected_host_only": case["expected_host_only"],
                   "request_options": OPTIONS, "schema": SCHEMA, "think": False,
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
                    row.update(_verdict(raw.get("message", {}).get("content"), case["expected_host_only"]))
                else:
                    row.update(strict_json=False, semantic_correct=False, reason="incomplete native response")
                consecutive_transport_failures = 0
            except Exception as exc:
                row.update(transport_error_type=type(exc).__name__, strict_json=False,
                           semantic_correct=False, reason="transport or native protocol failure")
                consecutive_transport_failures += 1
            finally:
                row["wall_seconds"] = time.monotonic() - started
                receipts.write(json.dumps(row, ensure_ascii=False) + "\n")
                receipts.flush()
                os.fsync(receipts.fileno())
                completed.append((model, case_id))
    summary = {"attempted": len(completed), "max_calls": MAX_CALLS,
               "stopped_after_transport_failures": consecutive_transport_failures >= 2,
               "unattempted": [{"model": model, "case_id": case_id}
                               for model, case_id in order[len(completed):]],
               "receipts": receipts_path.name, "api_cost_usd": None,
               "local_hardware_cost": "unmeasured"}
    with (work / "summary.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(summary, indent=2) + "\n")
    return work


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    parser.add_argument("--version", required=True, type=str)
    parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    args = parser.parse_args()
    if not _VERSION.fullmatch(args.version):
        parser.error("version must be a positive integer")
    work = (prepare if args.phase == "prepare" else run)(int(args.version), runs_root=args.runs_root)
    print(work)


if __name__ == "__main__":
    main()

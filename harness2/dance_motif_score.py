"""Strict AABA score over the frozen planted phrase shelf.

This is a technical motif grammar, not authentic choreography or avatar motion.
"""

from __future__ import annotations

import copy
import hashlib
import json

from . import dance_phrases

MOTIFS = ("sway", "pulse")
ACCENTS = ("soft", "clear")
SECTION_LABELS = ("A", "A", "B", "A")
MAX_INPUT_BYTES = 4096


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(_value):
    raise ValueError("nonfinite JSON number")


def _parse(raw: str) -> dict:
    if type(raw) is not str:
        raise ValueError("score must be JSON text")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError as exc:
        raise ValueError("score must be UTF-8 text") from exc
    if size > MAX_INPUT_BYTES:
        raise ValueError("score exceeds byte bound")
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("score must be strict JSON") from exc
    if type(value) is not dict:
        raise ValueError("score must be an object")
    return value


def _intent(motif: str, accents: list[str]) -> dict:
    if type(motif) is not str or motif not in MOTIFS:
        raise ValueError("unknown A motif")
    if (type(accents) is not list or len(accents) != 4 or any(
            type(accent) is not str or accent not in ACCENTS for accent in accents)):
        raise ValueError("four soft/clear section accents required")
    return {"motif": motif, "accents": accents[:]}


def _section_pairs(motif: str, accent: str) -> list[list[str]]:
    return [[move, accent] for move in ("rise", motif, motif, "settle")]


def _section_motifs(motif: str) -> tuple[str, ...]:
    opposite = "pulse" if motif == "sway" else "sway"
    return (motif, motif, opposite, motif)


def _assemble(sections: list[dict]) -> dict:
    if type(sections) is not list or len(sections) != 4:
        raise ValueError("four source sections required")
    frames = []
    for section_index, section in enumerate(sections):
        source = section["sequence"]["frames"]
        if section_index:
            prior = sections[section_index - 1]["sequence"]["frames"][-1]
            if prior["joints"] != source[0]["joints"] or prior["contacts"] != source[0]["contacts"]:
                raise ValueError("section seam pose/contact mismatch")
        for local, frame in enumerate(source):
            if section_index and local == 0:
                continue
            copied = copy.deepcopy(frame)
            copied["time"] = (section_index * 80 + local) / 20
            frames.append(copied)
    source_meta = sections[0]["sequence"]
    return {"kind": "procedural_dance_motif_score", "variant": "AABA",
            "bpm": 120, "fps": 20, "beats": 32, "duration_seconds": 16.0,
            "coordinate_system": source_meta["coordinate_system"],
            "bone_edges": copy.deepcopy(source_meta["bone_edges"]),
            "proportions_m": copy.deepcopy(source_meta["proportions_m"]),
            "segment_lengths_m": copy.deepcopy(source_meta["segment_lengths_m"]),
            "scope": "Planted technical motif score; no stepping, style authenticity, biomechanics, artistic quality or avatar-execution claim.",
            "frames": frames}


def _compile(intent: dict) -> dict:
    motifs = _section_motifs(intent["motif"])
    sections = [dance_phrases.compile_plan(json.dumps({"moves": _section_pairs(motif, accent)}))
                for motif, accent in zip(motifs, intent["accents"])]
    sequence = _assemble(sections)
    report = {"valid": True, "section_labels": list(SECTION_LABELS),
              "section_motifs": list(motifs), "section_frame_count": 81,
              "frame_count": 321, "fps": 20, "beats": 32,
              "duration_seconds": 16.0, "seam_count": 3,
              "sections_valid": all(dance_phrases.validate_compilation(section)["valid"]
                                    for section in sections)}
    receipt = {"intent_sha256": _digest(intent),
               "catalog_sha256": _digest(dance_phrases.CATALOG),
               "section_sha256": [_digest(section) for section in sections],
               "sequence_sha256": _digest(sequence), "validation": report}
    return {"intent": intent, "sections": sections, "sequence": sequence,
            "receipt": receipt}


def compile_intent(raw: str) -> dict:
    """Compile {motif, accents} into four 8-beat sections and 321 frames."""
    value = _parse(raw)
    if set(value) != {"motif", "accents"}:
        raise ValueError("intent requires exactly motif and accents")
    return _compile(_intent(value["motif"], value["accents"]))


def compile_expanded(raw: str) -> dict:
    """Accept only the same AABA grammar as 16 explicit move/variation pairs."""
    value = _parse(raw)
    if set(value) != {"moves"}:
        raise ValueError("expanded score requires exactly moves")
    moves = value["moves"]
    if type(moves) is not list or len(moves) != 16:
        raise ValueError("expanded score requires 16 moves")
    for pair in moves:
        if (type(pair) is not list or len(pair) != 2 or
                any(type(item) is not str for item in pair)):
            raise ValueError("each expanded move must be [id, variation]")
    motif = moves[1][0]
    if motif not in MOTIFS:
        raise ValueError("unknown A motif")
    accents = [moves[index * 4][1] for index in range(4)]
    intent = _intent(motif, accents)
    expected = [pair for section_motif, accent in zip(_section_motifs(motif), accents)
                for pair in _section_pairs(section_motif, accent)]
    if moves != expected:
        raise ValueError("expanded moves violate uniform-accent AABA grammar")
    return _compile(intent)


def verify_score(result: dict) -> dict:
    """Rebuild from intent; revalidate sections, seams, full frames and receipt."""
    if type(result) is not dict or set(result) != {"intent", "sections", "sequence", "receipt"}:
        raise ValueError("incomplete motif score")
    supplied = result["intent"]
    if type(supplied) is not dict or set(supplied) != {"motif", "accents"}:
        raise ValueError("invalid score intent")
    intent = _intent(supplied["motif"], supplied["accents"])
    if result["intent"] != intent:
        raise ValueError("score intent mismatch")
    sections = result["sections"]
    if type(sections) is not list or len(sections) != 4:
        raise ValueError("four source sections required")
    for section in sections:
        dance_phrases.validate_compilation(section)
    canonical = _compile(intent)
    if _digest(sections) != _digest(canonical["sections"]):
        raise ValueError("sections differ from frozen motif grammar")
    if (_digest(result["sequence"]) != _digest(_assemble(sections)) or
            _digest(result["sequence"]) != _digest(canonical["sequence"])):
        raise ValueError("score sequence differs from source sections")
    if _digest(result["receipt"]) != _digest(canonical["receipt"]):
        raise ValueError("score receipt mismatch")
    return canonical["receipt"]["validation"]

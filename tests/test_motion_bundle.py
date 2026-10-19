"""Offline bundle and verifier checks using tiny video bytes and an injected probe."""

import json
from pathlib import Path
import tempfile
import unittest

from harness2 import dance_motion
from harness2.dance_edit import edit_arms
from harness2.motion_bundle import build_bundle, verify_bundle

VIDEO = {"width": 512, "height": 320, "frame_count": 40,
         "fps": "10/1", "duration_seconds": 4.0}


def fake_probe(_path):
    return dict(VIDEO)


def fixture(folder):
    folder.mkdir()
    original = dance_motion.generate("restrained")
    edited = edit_arms(original, '{"operation":"accent_arms","strength":"clear"}')["sequence"]
    (folder / "original.json").write_text(json.dumps(original) + "\n")
    (folder / "tracks.json").write_text(json.dumps({"labels": ["original", "model-selected arm accent"],
                                                    "sequences": [original, edited]}) + "\n")
    (folder / "comparison.mp4").write_bytes(b"fake video bytes for injected probe")
    return original, edited


class MotionBundleTests(unittest.TestCase):
    def test_build_and_independent_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            fixture(source)
            bundle = root / "reference"
            manifest = build_bundle(source, bundle, probe=fake_probe)
            self.assertEqual(set(manifest["assets"]), {"tracks.json", "original.json", "comparison.mp4"})
            self.assertEqual(manifest["track_labels"], ["original", "edited"])
            self.assertEqual(manifest["motion"]["source_frame_count"], 81)
            self.assertEqual(manifest["motion"]["edit_bounds_beats"], [2, 6])
            self.assertTrue(manifest["motion"]["endpoint_inclusive"])
            self.assertIn("technical stick-figure", manifest["scope"].lower())
            self.assertTrue(verify_bundle(bundle, probe=fake_probe)["valid"])
            for name in ("tracks.json", "original.json", "comparison.mp4"):
                self.assertEqual((source / name).read_bytes(), (bundle / name).read_bytes())
            with self.assertRaises(ValueError):
                build_bundle(source, bundle, probe=fake_probe)
            with self.assertRaises(ValueError):
                build_bundle(source, source, probe=fake_probe)

    def test_video_metadata_must_match_fixed_stream_even_with_valid_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            fixture(source)
            bad_probe = lambda _: dict(VIDEO, frame_count=39)
            with self.assertRaisesRegex(ValueError, "40 frames"):
                build_bundle(source, root / "bad", probe=bad_probe)
            bundle = root / "reference"
            build_bundle(source, bundle, probe=fake_probe)
            with self.assertRaisesRegex(ValueError, "40 frames"):
                verify_bundle(bundle, probe=bad_probe)

    def test_hash_tamper_and_motion_corruption_are_independently_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            fixture(source)
            bundle = root / "reference"
            build_bundle(source, bundle, probe=fake_probe)
            (bundle / "comparison.mp4").write_bytes(b"tampered bytes")
            with self.assertRaisesRegex(ValueError, "asset hash"):
                verify_bundle(bundle, probe=fake_probe)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            original, _ = fixture(source)
            bundle = root / "reference"
            build_bundle(source, bundle, probe=fake_probe)
            tracks_path = bundle / "tracks.json"
            tracks = json.loads(tracks_path.read_text())
            tracks["sequences"][1] = dance_motion.generate("broad")  # valid, but changes protected motion
            tracks_path.write_text(json.dumps(tracks) + "\n")
            manifest_path = bundle / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            from harness2.motion_bundle import _hash, _json_digest
            manifest["assets"]["tracks.json"] = {"sha256": _hash(tracks_path),
                                                     "size_bytes": tracks_path.stat().st_size}
            manifest["motion"]["edited_sequence_sha256"] = _json_digest(tracks["sequences"][1])
            manifest_path.write_text(json.dumps(manifest) + "\n")
            self.assertEqual(tracks["sequences"][0], original)
            with self.assertRaisesRegex(ValueError, "protected motion"):
                verify_bundle(bundle, probe=fake_probe)

    def test_original_copy_must_match_first_track(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            fixture(source)
            original_path = source / "original.json"
            original = json.loads(original_path.read_text())
            original["scope"] = "changed metadata"
            original_path.write_text(json.dumps(original) + "\n")
            with self.assertRaisesRegex(ValueError, "original.json differs"):
                build_bundle(source, root / "reference", probe=fake_probe)


if __name__ == "__main__":
    unittest.main()

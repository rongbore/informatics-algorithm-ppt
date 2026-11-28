"""Tests for the compiled-alignment renderer helpers."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_lesson_v2_4 as renderer


class CompiledRendererTests(unittest.TestCase):
    def test_caption_wrapping_preserves_spaces(self):
        blocks = renderer.wrap_caption("C++ uses dp[i] and dp[i-1]", 12, 2)
        self.assertTrue(blocks)
        self.assertIn("dp[i]", "\n".join(blocks))
        self.assertIn("dp[i-1]", "\n".join(blocks))

    def test_subtitle_is_suppressed_during_thinking(self):
        visible = renderer.subtract_intervals(0.0, 5.0, [(1.0, 2.0), (3.0, 4.0)])
        self.assertEqual(visible, [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0)])

    def test_alignment_report_requires_review_gate(self):
        report = {
            "schema_version": "2.4.1",
            "auto_approved": False,
            "manual_review_required": True,
            "slides": [{"slide": 1}],
        }
        self.assertEqual(list(renderer.validate_alignment_report(report)), [1])
        report["auto_approved"] = True
        with self.assertRaises(ValueError):
            renderer.validate_alignment_report(report)

    def test_alignment_report_rejects_duplicate_slides(self):
        report = {
            "schema_version": "2.4.1",
            "auto_approved": False,
            "manual_review_required": True,
            "slides": [{"slide": 1}, {"slide": 1}],
        }
        with self.assertRaises(ValueError):
            renderer.validate_alignment_report(report)


    def test_render_inputs_accept_exact_source_fingerprints(self):
        import hashlib
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slides, audio, timings = root / "slides", root / "audio", root / "timings"
            for folder in (slides, audio, timings):
                folder.mkdir()
            payloads = {
                slides / "slide_001.png": b"slide-png",
                audio / "slide_001.mp3": b"audio-mp3",
                timings / "slide_001.json": b'{"slide":1}',
            }
            for path, data in payloads.items():
                path.write_bytes(data)
            digest = lambda data: hashlib.sha256(data).hexdigest()
            slide_map = {1: {"slide_image_sha256": digest(b"slide-png")}}
            fingerprints = {
                "audio_sha256": {"1": digest(b"audio-mp3")},
                "timing_sha256": {"1": digest(b'{"slide":1}')},
            }
            self.assertTrue(renderer.validate_render_inputs(
                slide_map, slides, audio, timings, fingerprints
            ))

    def test_render_inputs_reject_replaced_slide_image(self):
        import hashlib
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slides, audio, timings = root / "slides", root / "audio", root / "timings"
            for folder in (slides, audio, timings):
                folder.mkdir()
            (slides / "slide_001.png").write_bytes(b"new-slide-image")
            (audio / "slide_001.mp3").write_bytes(b"audio")
            (timings / "slide_001.json").write_bytes(b"timing")
            digest = lambda data: hashlib.sha256(data).hexdigest()
            slide_map = {1: {"slide_image_sha256": digest(b"original-slide-image")}}
            fingerprints = {
                "audio_sha256": {"1": digest(b"audio")},
                "timing_sha256": {"1": digest(b"timing")},
            }
            with self.assertRaisesRegex(ValueError, "slide image fingerprint mismatch"):
                renderer.validate_render_inputs(
                    slide_map, slides, audio, timings, fingerprints
                )

    def test_render_inputs_reject_stale_audio_and_timing_hashes(self):
        import hashlib
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slides, audio, timings = root / "slides", root / "audio", root / "timings"
            for folder in (slides, audio, timings):
                folder.mkdir()
            (slides / "slide_001.png").write_bytes(b"slide")
            (audio / "slide_001.mp3").write_bytes(b"changed-audio")
            (timings / "slide_001.json").write_bytes(b"changed-timing")
            digest = lambda data: hashlib.sha256(data).hexdigest()
            slide_map = {1: {"slide_image_sha256": digest(b"slide")}}
            fingerprints = {
                "audio_sha256": {"1": digest(b"original-audio")},
                "timing_sha256": {"1": digest(b"original-timing")},
            }
            with self.assertRaisesRegex(ValueError, "audio fingerprint mismatch"):
                renderer.validate_render_inputs(
                    slide_map, slides, audio, timings, fingerprints
                )


    def test_storyboard_rejects_unknown_region_ids(self):
        import json
        import tempfile

        slide_map = {1: {"regions": [{"region_id": "s001_r01"}]}}
        storyboard = {
            "schema_version": "2.6.0",
            "slides": [{
                "slide": 1,
                "shots": [{
                    "shot_type": "close_up",
                    "region_ids": ["s001_missing"],
                    "camera_motion": "none",
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "storyboard.json"
            path.write_text(json.dumps(storyboard), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown regions"):
                renderer.load_storyboard(path, slide_map)

    def test_storyboard_closeup_uses_verified_region_geometry(self):
        import json
        import tempfile

        slide_map = {1: {"regions": [{"region_id": "s001_r01"}]}}
        storyboard = {
            "schema_version": "2.6.0",
            "slides": [{
                "slide": 1,
                "shots": [{
                    "shot_type": "close_up",
                    "region_ids": ["s001_r01"],
                    "camera_motion": "none",
                    "render_status": "supported_by_current_renderer",
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "storyboard.json"
            path.write_text(json.dumps(storyboard), encoding="utf-8")
            plans = renderer.load_storyboard(path, slide_map)
        row = {"regions": [{
            "region_id": "s001_r01",
            "bbox": [0.40, 0.35, 0.20, 0.12],
        }]}
        crop = renderer.camera_crop(plans[1], row, 1920, 948, 0, 0, 1920, 948)
        self.assertIsNotNone(crop)
        self.assertEqual(crop["region_id"], "s001_r01")
        self.assertGreater(crop["zoom_x"], 1.0)
        self.assertLessEqual(crop["x"] + crop["width"], 1920)
        self.assertLessEqual(crop["y"] + crop["height"], 948)

    def test_focus_box_is_transformed_into_closeup_crop(self):
        crop = {
            "x": 400, "y": 200, "width": 1200, "height": 600,
            "zoom_x": 1.6, "zoom_y": 1.58,
        }
        transformed = renderer.transform_box_for_crop(
            500, 250, 200, 100, crop, 1920, 948
        )
        self.assertEqual(transformed, (160, 79, 320, 158))
        outside = renderer.transform_box_for_crop(
            10, 10, 50, 50, crop, 1920, 948
        )
        self.assertIsNone(outside)

    def test_storyboard_rejects_duplicate_slide_entries(self):
        import json
        import tempfile

        storyboard = {
            "schema_version": "2.6.0",
            "slides": [
                {"slide": 1, "shots": [{"shot_type": "establishing", "region_ids": []}]},
                {"slide": 1, "shots": [{"shot_type": "establishing", "region_ids": []}]},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "storyboard.json"
            path.write_text(json.dumps(storyboard), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate slide"):
                renderer.load_storyboard(path, {1: {"regions": []}})



if __name__ == "__main__":
    unittest.main()

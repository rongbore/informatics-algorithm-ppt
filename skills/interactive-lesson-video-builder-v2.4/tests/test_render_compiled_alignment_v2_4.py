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


if __name__ == "__main__":
    unittest.main()

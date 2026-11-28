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


if __name__ == "__main__":
    unittest.main()

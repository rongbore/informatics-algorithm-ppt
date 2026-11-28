"""Offline tests for the V2.4 renderer's pure timing helpers."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_lesson_v2_4_alpha3 as renderer


class RendererHelperTests(unittest.TestCase):
    def test_srt_time_format(self):
        self.assertEqual(renderer.srt_time(61.234), "00:01:01,234")

    def test_only_thinking_pauses_are_hidden(self):
        timing = {
            "pauses": [
                {"start": 1.0, "end": 2.0, "kind": "thinking_prompt"},
                {"start": 3.0, "end": 4.0, "kind": "slide_end"},
            ]
        }
        self.assertEqual(renderer.thinking_intervals(timing), [(1.0, 2.0)])

    def test_subtract_multiple_thinking_intervals(self):
        self.assertEqual(
            renderer.subtract_intervals(0.0, 5.0, [(1.0, 2.0), (3.0, 4.0)]),
            [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0)],
        )

    def test_subtitles_are_suppressed_during_thinking(self):
        timing = {
            "speech_events": [
                {"text": "这是一段字幕测试内容", "start": 0.0, "end": 4.0}
            ],
            "pauses": [
                {"start": 1.0, "end": 2.0, "kind": "thinking_prompt"}
            ],
        }
        config = {
            "disable_during_thinking": True,
            "max_chars_per_line": 16,
            "max_lines": 2,
        }
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "slide_001.srt"
            cues = renderer.make_srt(timing, target, config)
            self.assertEqual(
                [(round(start, 2), round(end, 2)) for start, end, _ in cues],
                [(0.0, 1.0), (2.0, 4.0)],
            )
            self.assertTrue(target.read_text(encoding="utf-8-sig").strip())

    def test_v24_config_is_versioned_and_1080p(self):
        config_path = Path(__file__).resolve().parents[1] / "config" / "video_ux_v2_4.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["version"], "2.4.0-alpha.3")
        self.assertEqual(
            (config["resolution"]["width"], config["resolution"]["height"]),
            (1920, 1080),
        )
        self.assertEqual(config["quality_control"]["never_auto_approve_full_course"], True)


if __name__ == "__main__":
    unittest.main()

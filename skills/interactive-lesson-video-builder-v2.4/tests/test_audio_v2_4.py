"""Offline tests for the V2.4 event-driven TTS planning helpers."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_audio_v2_4 as audio


class AudioPlanningTests(unittest.TestCase):
    def test_empty_narration_has_no_phrases(self):
        self.assertEqual(audio.split_phrases("   "), [])

    def test_long_sentences_split_at_sentence_boundaries(self):
        phrases = audio.split_phrases(
            "这是一段足够长的第一句话，用来验证分句。第二句也足够长，用来验证。"
        )
        self.assertEqual(len(phrases), 2)
        self.assertTrue(phrases[0].endswith("。"))
        self.assertTrue(phrases[1].endswith("。"))

    def test_punctuation_pause_policy(self):
        cfg = {
            "pause_after_question_ms": 700,
            "pause_after_sentence_ms": 520,
            "pause_after_comma_ms": 260,
            "pause_after_paragraph_ms": 850,
        }
        self.assertEqual(audio.punctuation_pause_ms("为什么？", cfg), 700)
        self.assertEqual(audio.punctuation_pause_ms("完成。", cfg), 520)
        self.assertEqual(audio.punctuation_pause_ms("例如，", cfg), 260)
        self.assertEqual(audio.punctuation_pause_ms("继续", cfg), 850)

    def test_explicit_difficulty_uses_v24_pacing_table(self):
        event = {"type": "thinking_prompt", "text": "解释代码为什么这样写？", "difficulty": "D4"}
        pacing = {"thinking_seconds_by_difficulty": {"D1": 6, "D2": 8, "D3": 10, "D4": 15, "D5": 20}}
        seconds, rationale = audio.thinking_seconds(event, pacing)
        self.assertEqual(seconds, 15.0)
        self.assertIn("explicit difficulty", rationale)

    def test_explicit_thinking_seconds_override_difficulty(self):
        event = {"text": "请先思考", "difficulty": "D1", "thinking_seconds": 13}
        seconds, rationale = audio.thinking_seconds(event, {})
        self.assertEqual(seconds, 13.0)
        self.assertEqual(rationale, "explicit thinking_seconds")

    def test_legacy_pause_after_seconds_is_preserved(self):
        event = {"text": "旧版事件", "pause_after_seconds": 7}
        seconds, rationale = audio.thinking_seconds(event, {})
        self.assertEqual(seconds, 7.0)
        self.assertEqual(rationale, "legacy/explicit pause_after_seconds")


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

audio = load_module("audio_v23", ROOT / "scripts" / "generate_audio_v2_3.py")
render = load_module("render_v23", ROOT / "scripts" / "render_lesson_v2_3.py")

class V23SkillTests(unittest.TestCase):
    def test_config_is_valid_and_1080p(self):
        cfg = json.loads((ROOT / "config" / "video_ux_v2_3.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["resolution"]["width"], 1920)
        self.assertEqual(cfg["resolution"]["height"], 1080)
        self.assertEqual(cfg["countdown"]["mode"], "numeric_only")

    def test_difficulty_mapping(self):
        pacing = {"thinking_seconds_by_difficulty": {"D1": 6, "D2": 8, "D3": 10, "D4": 15, "D5": 20}}
        self.assertEqual(audio.thinking_seconds({"difficulty": "D4"}, pacing)[0], 15)
        self.assertEqual(audio.thinking_seconds({"thinking_seconds": 12}, pacing)[0], 12)
        self.assertEqual(audio.thinking_seconds({"pause_after_seconds": 9}, pacing)[0], 9)

    def test_legacy_v22_prompt_uses_explicit_pause(self):
        pacing = {"thinking_seconds_by_difficulty": {"D1": 6, "D2": 8, "D3": 10, "D4": 15, "D5": 20}}
        event = {"type": "thinking_prompt", "text": "请推导递归查询过程。", "pause_after_seconds": 10}
        self.assertEqual(audio.thinking_seconds(event, pacing)[0], 10)

    def test_difficulty_inference(self):
        self.assertEqual(audio.infer_difficulty({"text": "请分析代码递归和状态转移过程。"})[0], "D4")
        self.assertEqual(audio.infer_difficulty({"text": "请说出 lowbit 的定义。"})[0], "D1")

    def test_phrase_split(self):
        phrases = audio.split_phrases("先观察根节点。再分析左右区间。")
        self.assertGreaterEqual(len(phrases), 1)
        self.assertTrue(all(p.strip() for p in phrases))

    def test_subtitles_suppressed_during_thinking(self):
        intervals = render.thinking_intervals({
            "pauses": [{"kind": "thinking_prompt", "start": 4, "end": 14},
                       {"kind": "slide_end", "start": 15, "end": 20}]
        })
        self.assertEqual(intervals, [(4.0, 14.0)])

if __name__ == "__main__":
    unittest.main()

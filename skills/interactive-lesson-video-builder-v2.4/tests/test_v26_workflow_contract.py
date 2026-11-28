import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class V26WorkflowContractTests(unittest.TestCase):
    def test_engine_schema_version_is_preserved(self):
        config = json.loads((ROOT / "config/video_ux_v2_4.json").read_text(encoding="utf-8"))
        self.assertEqual(config["version"], "2.4.0-alpha.3")
        self.assertEqual(config["delivery_mode"], "single_upload_full_course")
        self.assertEqual(config["teacher_voice"]["voice"], "zh-CN-YunjianNeural")
        self.assertEqual(config["focus"]["min_confidence"], 0.90)
        self.assertTrue(config["quality_control"]["automatic_full_course_render"])
        self.assertFalse(config["quality_control"]["manual_pilot_review"])

    def test_runner_contains_all_deterministic_stages(self):
        runner = (ROOT / "scripts/run_video_builder_v2_6.ps1").read_text(encoding="utf-8")
        for token in ("ValidateSet(\"Prepare\",\"Render\")", "generate_audio_v2_4.py",
                      "prepare_alignment_inputs_v2_4.py", "finalize_alignment_plan_v2_4.py",
                      "compile_alignment_v2_4.py", "render_lesson_v2_4.py",
                      "validate_full_video_v2_4.py", "--storyboard", "lesson_video_production_package.zip", "narration_script.txt", "measured_timeline.csv", "INCOMPLETE"):
            self.assertIn(token, runner)

    def test_storyboard_prompt_exists_and_active_skill_uses_runner(self):
        self.assertTrue((ROOT / "prompts/storyboard_compiler_v2_6.md").is_file())
        active = (ROOT.parent / "interactive-lesson-video-builder/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("run_video_builder_v2_6.ps1", active)
        self.assertIn("storyboard_compiler_v2_6.md", active)

if __name__ == "__main__":
    unittest.main()

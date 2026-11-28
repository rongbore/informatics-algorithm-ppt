import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(ROOT))
import local_sherpa_tts_v31 as local_tts


class LocalSherpaTtsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.model = self.root / "model.onnx"
        self.tokens = self.root / "tokens.txt"
        self.lexicon = self.root / "lexicon.txt"
        for path in (self.model, self.tokens, self.lexicon):
            path.write_text("placeholder", encoding="utf-8")
        self.rules = []
        for name in ("phone.fst", "date.fst", "number.fst"):
            path = self.root / name
            path.write_text("placeholder", encoding="utf-8")
            self.rules.append(str(path))
        self.old_env = {
            key: os.environ.get(key)
            for key in (
                "SHERPA_TTS_MODEL", "SHERPA_TTS_TOKENS",
                "SHERPA_TTS_LEXICON", "SHERPA_TTS_RULE_FSTS",
                "SHERPA_TTS_SPEAKER_ID", "SHERPA_TTS_THREADS",
            )
        }
        os.environ.update({
            "SHERPA_TTS_MODEL": str(self.model),
            "SHERPA_TTS_TOKENS": str(self.tokens),
            "SHERPA_TTS_LEXICON": str(self.lexicon),
        })
        os.environ.pop("SHERPA_TTS_RULE_FSTS", None)

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def test_required_path_rejects_missing_file(self):
        with self.assertRaisesRegex(RuntimeError, "not found"):
            local_tts._required_path("SHERPA_TTS_MODEL_MISSING")

    def test_local_adapter_auto_discovers_chinese_normalization_rules(self):
        captured = {}
        fake_audio = types.SimpleNamespace(samples=[0.0] * 2400, sample_rate=24000)

        class FakeEngine:
            def generate(self, text, generation):
                self.text = text
                return fake_audio

        def model_config(**kwargs):
            captured["model_config"] = kwargs
            return types.SimpleNamespace(**kwargs)

        def tts_config(**kwargs):
            captured["tts_config"] = kwargs
            return types.SimpleNamespace(validate=lambda: True, **kwargs)

        fake_sherpa = types.SimpleNamespace(
            OfflineTtsVitsModelConfig=model_config,
            OfflineTtsModelConfig=model_config,
            OfflineTtsConfig=tts_config,
            OfflineTts=lambda cfg: FakeEngine(),
            GenerationConfig=lambda: types.SimpleNamespace(),
        )

        def write(path, samples, samplerate, subtype):
            pathlib.Path(path).write_bytes(b"mock-wav-data")

        fake_soundfile = types.SimpleNamespace(write=write)
        with patch.dict(sys.modules, {"sherpa_onnx": fake_sherpa, "soundfile": fake_soundfile}):
            engine = local_tts.LocalSherpaTTS()
            output = self.root / "sample.wav"
            result = engine.synthesize_wav("并查集路径压缩。", output)
        self.assertEqual(captured["tts_config"]["rule_fsts"], ",".join(self.rules))
        self.assertEqual(result["provider"], "local_sherpa_onnx")
        self.assertTrue(output.exists())

    def test_explicit_rule_fst_setting_takes_precedence(self):
        custom = str(self.root / "custom.fst")
        pathlib.Path(custom).write_text("placeholder", encoding="utf-8")
        os.environ["SHERPA_TTS_RULE_FSTS"] = custom
        captured = {}

        def model_config(**kwargs):
            return types.SimpleNamespace(**kwargs)

        def tts_config(**kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(validate=lambda: True, **kwargs)

        fake_sherpa = types.SimpleNamespace(
            OfflineTtsVitsModelConfig=model_config,
            OfflineTtsModelConfig=model_config,
            OfflineTtsConfig=tts_config,
            OfflineTts=lambda cfg: object(),
        )
        fake_soundfile = types.SimpleNamespace(write=lambda *args, **kwargs: None)
        with patch.dict(sys.modules, {"sherpa_onnx": fake_sherpa, "soundfile": fake_soundfile}):
            local_tts.LocalSherpaTTS()
        self.assertEqual(captured["rule_fsts"], custom)


if __name__ == "__main__":
    unittest.main()

"""Offline Mandarin TTS adapter powered by sherpa-onnx VITS."""
from __future__ import annotations
import os
from pathlib import Path

def _required_path(env_name: str) -> str:
    value = os.getenv(env_name, "").strip()
    if not value:
        raise RuntimeError(f"Local offline TTS requires {env_name}")
    path = Path(value).expanduser()
    if not path.is_file():
        raise RuntimeError(f"Local TTS model file not found: {env_name}={path}")
    return str(path)

class LocalSherpaTTS:
    def __init__(self):
        try:
            import sherpa_onnx
            import soundfile  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("Install local TTS dependencies: pip install sherpa-onnx soundfile") from exc
        self._soundfile = soundfile
        model = _required_path("SHERPA_TTS_MODEL")
        tokens = _required_path("SHERPA_TTS_TOKENS")
        lexicon = os.getenv("SHERPA_TTS_LEXICON", "").strip()
        rules = os.getenv("SHERPA_TTS_RULE_FSTS", "").strip()
        sid = int(os.getenv("SHERPA_TTS_SPEAKER_ID", "21"))
        threads = max(1, int(os.getenv("SHERPA_TTS_THREADS", "2")))
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=model, tokens=tokens, lexicon=lexicon
                ),
                num_threads=threads,
                provider="cpu",
            ),
            rule_fsts=rules,
        )
        if not cfg.validate():
            raise RuntimeError("sherpa-onnx model configuration failed validation")
        self.engine = sherpa_onnx.OfflineTts(cfg)
        self.sid = sid

    def synthesize_wav(self, text: str, out_path: str | Path, speed: float = 1.0) -> dict:
        import sherpa_onnx
        generation = sherpa_onnx.GenerationConfig()
        generation.sid = self.sid
        generation.speed = float(speed)
        generation.silence_scale = 0.2
        audio = self.engine.generate(text, generation)
        if len(audio.samples) == 0:
            raise RuntimeError("Local sherpa-onnx generated empty audio")
        destination = Path(out_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._soundfile.write(str(destination), audio.samples, samplerate=audio.sample_rate, subtype="PCM_16")
        return {"path": str(destination), "sample_rate": int(audio.sample_rate),
                "samples": len(audio.samples), "duration_seconds": len(audio.samples)/audio.sample_rate,
                "provider": "local_sherpa_onnx"}

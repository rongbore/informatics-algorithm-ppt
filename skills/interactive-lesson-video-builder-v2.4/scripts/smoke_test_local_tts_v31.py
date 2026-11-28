#!/usr/bin/env python3
"""Generate one short offline Mandarin sample and verify its WAV output.

This script only invokes the local sherpa-onnx engine. It has no Tencent/Azure/Edge
network path and is safe to run without cloud credentials.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import wave
from pathlib import Path

from local_sherpa_tts_v31 import LocalSherpaTTS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="local_tts_v31_smoke.wav")
    parser.add_argument(
        "--text",
        default="同学们好，今天我们学习并查集。首先理解集合合并与路径压缩的核心思想。",
    )
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    output = Path(args.output).expanduser().resolve()
    engine = LocalSherpaTTS()
    result = engine.synthesize_wav(args.text, output, speed=args.speed)

    with wave.open(str(output), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        sample_width = wav.getsampwidth()
    duration = frames / sample_rate if sample_rate else 0

    if output.stat().st_size < 1024 or duration <= 0:
        raise RuntimeError("Smoke test failed: WAV output is empty or has zero duration")
    if channels != 1:
        raise RuntimeError(f"Expected mono WAV output; got {channels} channels")
    if sample_width != 2:
        raise RuntimeError(f"Expected 16-bit PCM WAV output; got {sample_width * 8}-bit")
    report = {
        "status": "PASS",
        "provider": "local_sherpa_onnx",
        "cloud_api_used": False,
        "output": str(output),
        "text_characters": len(args.text),
        "duration_seconds": round(duration, 3),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bits": sample_width * 8,
        "bytes": output.stat().st_size,
        "synthesis": result,
        "manual_listening_review_required": True,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "provider": "local_sherpa_onnx",
                          "cloud_api_used": False, "error": str(exc)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        raise SystemExit(2)

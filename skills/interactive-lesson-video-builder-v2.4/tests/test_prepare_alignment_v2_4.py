"""Tests for machine-prepared alignment contexts."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_alignment_inputs_v2_4 as prepare
from compile_alignment_v2_4 import canonical_digest


class PrepareAlignmentContextTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        timings = root / "timings"
        audio = root / "audio"
        timings.mkdir()
        audio.mkdir()
        (audio / "slide_001.mp3").write_bytes(b"fake-audio")
        timing = {
            "schema_version": "2.4.1",
            "slide": 1,
            "duration_seconds": 1.2,
            "speech_events": [{
                "event_id": "s001_e01", "phrase_index": 0, "type": "narration",
                "text": "讲解公式。", "start": 0.0, "end": 1.0,
            }],
            "pauses": [{
                "event_id": None, "kind": "slide_end", "start": 1.0, "end": 1.2,
            }],
        }
        (timings / "slide_001.json").write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8")
        regions = {
            "schema_version": "2.4.1",
            "source_pptx_sha256": "pptx-hash",
            "slides": [{
                "slide": 1,
                "slide_image_sha256": "image-hash",
                "regions": [{
                    "region_id": "s001_sh10", "kind": "knowledge",
                    "label": "公式", "text": "dp[i]", "bbox": [0.1, 0.1, 0.3, 0.2],
                    "mapping_eligible": True, "geometry_status": "source_verified",
                    "geometry_source": "pptx_native",
                }],
            }],
        }
        narration = {
            "slides": [{
                "slide": 1,
                "events": [{
                    "event_id": "s001_e01", "type": "narration", "text": "讲解公式。",
                }],
            }],
        }
        return regions, narration, timings, audio

    def test_context_contains_machine_hashes_and_exact_phrases(self):
        with tempfile.TemporaryDirectory() as directory:
            regions, narration, timings, audio = self.fixture(directory)
            with patch.object(prepare, "probe_duration", return_value=1.2):
                context = prepare.prepare_context(regions, narration, timings, audio)
            expected_id = dict(context)
            actual_id = expected_id.pop("context_id")
            self.assertEqual(actual_id, canonical_digest(expected_id))
            self.assertEqual(context["slides"][0]["phrases"][0]["phrase_text"], "讲解公式。")
            self.assertEqual(context["slides"][0]["phrases"][0]["phrase_index"], 0)
            self.assertIn("1", context["audio_sha256"])
            self.assertIn("1", context["timing_sha256"])

    def test_context_rejects_timing_for_different_narration(self):
        with tempfile.TemporaryDirectory() as directory:
            regions, narration, timings, audio = self.fixture(directory)
            narration["slides"][0]["events"][0]["text"] = "已经修改的句子。"
            with patch.object(prepare, "probe_duration", return_value=1.2):
                with self.assertRaises(ValueError):
                    prepare.prepare_context(regions, narration, timings, audio)


if __name__ == "__main__":
    unittest.main()

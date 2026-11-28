"""Regression tests for source-bound visual/speech/timeline compilation."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compile_alignment_v2_4 as compiler


def fixture(directory, phrase_one_targets=None, first_confidence=0.98):
    root = Path(directory)
    timing_dir, audio_dir = root / "timings", root / "audio"
    timing_dir.mkdir()
    audio_dir.mkdir()
    audio_path = audio_dir / "slide_001.mp3"
    audio_path.write_bytes(b"fixture audio bytes")

    regions = [
        {"region_id": "s001_sh10", "slide": 1, "shape_id": 10,
         "shape_name": "Formula", "shape_type": "TEXT_BOX", "kind": "knowledge",
         "label": "公式", "text": "dp[i] = dp[i-1] + a[i]",
         "bbox": [0.1, 0.1, 0.4, 0.15], "geometry_source": "pptx_native",
         "geometry_status": "source_verified", "mapping_eligible": True},
        {"region_id": "s001_sh11", "slide": 1, "shape_id": 11,
         "shape_name": "Code", "shape_type": "TEXT_BOX", "kind": "code",
         "label": "代码", "text": "cout << dp[n];",
         "bbox": [0.1, 0.3, 0.4, 0.15], "geometry_source": "pptx_native",
         "geometry_status": "source_verified", "mapping_eligible": True},
        {"region_id": "s001_sh12_duplicate", "slide": 1, "shape_id": 10,
         "shape_name": "Formula duplicate", "shape_type": "TEXT_BOX", "kind": "knowledge",
         "label": "公式重复", "text": "dp[i] = dp[i-1] + a[i]",
         "bbox": [0.1, 0.1, 0.4, 0.15], "geometry_source": "pptx_native",
         "geometry_status": "source_verified", "mapping_eligible": True},
    ]
    manifest = {
        "schema_version": "2.4.1", "source_pptx_name": "fixture.pptx",
        "source_pptx_sha256": "pptx-hash",
        "slide_size_emu": {"width": 1000, "height": 1000},
        "slide_count": 1, "slide_image_sha256": {},
        "slides": [{"slide": 1, "slide_image": None,
                    "slide_image_sha256": None, "regions": regions}],
    }
    first_text = "先看这个公式和代码。" if phrase_one_targets and len(phrase_one_targets) > 1 else "先看这个公式。"
    narration = {
        "schema_version": "2.4.0",
        "slides": [{"slide": 1, "events": [
            {"event_id": "s001_e01", "type": "narration", "text": first_text},
            {"event_id": "s001_e02", "type": "narration", "text": "最后输出代码结果。"},
        ]}],
    }
    timing = {
        "schema_version": "2.4.1", "slide": 1, "duration_seconds": 3.0,
        "speech_events": [
            {"event_id": "s001_e01", "phrase_index": 0, "type": "narration",
             "text": first_text, "start": 0.0, "end": 1.0},
            {"event_id": "s001_e02", "phrase_index": 0, "type": "narration",
             "text": "最后输出代码结果。", "start": 1.5, "end": 2.5},
        ],
        "pauses": [
            {"event_id": "s001_e01", "kind": "natural", "start": 1.0, "end": 1.5},
            {"event_id": None, "kind": "slide_end", "start": 2.5, "end": 3.0},
        ],
    }
    timing_path = timing_dir / "slide_001.json"
    timing_path.write_text(json.dumps(timing, ensure_ascii=False), encoding="utf-8")

    target_ids = phrase_one_targets or ["s001_sh10"]
    evidence_one = []
    for region_id in target_ids:
        if region_id in ("s001_sh10", "s001_sh12_duplicate"):
            region_quote, speech_quote = "dp[i] = dp[i-1] + a[i]", "公式"
        else:
            region_quote, speech_quote = "cout << dp[n];", "代码"
        evidence_one.append({
            "region_id": region_id, "region_quote": region_quote,
            "speech_quote": speech_quote,
            "reasoning": "讲解短语明确指向该页对应的教学视觉区域。",
        })
    phrase_one = {
        "event_id": "s001_e01", "phrase_index": 0, "phrase_text": first_text,
        "status": "matched", "region_ids": target_ids,
        "mapping_basis": "semantic", "confidence": first_confidence,
        "verification": {"status": "confirmed", "reviewer_pass": "independent-review-pass-1"},
        "evidence": evidence_one,
    }
    phrase_two = {
        "event_id": "s001_e02", "phrase_index": 0,
        "phrase_text": "最后输出代码结果。", "status": "matched",
        "region_ids": ["s001_sh11"], "mapping_basis": "semantic",
        "confidence": 0.97,
        "verification": {"status": "confirmed", "reviewer_pass": "independent-review-pass-2"},
        "evidence": [{
            "region_id": "s001_sh11", "region_quote": "cout << dp[n];",
            "speech_quote": "代码结果", "reasoning": "讲解指向展示输出语句的代码区域。",
        }],
    }
    plan = {
        "schema_version": "2.4.1",
        "region_manifest_sha256": compiler.canonical_digest(manifest),
        "narration_sha256": compiler.canonical_digest(narration),
        "timing_sha256": {"1": compiler.sha256_file(timing_path)},
        "audio_sha256": {"1": compiler.sha256_file(audio_path)},
        "slides": [{"slide": 1, "phrases": [phrase_one, phrase_two]}],
    }
    return manifest, narration, plan, timing_dir, audio_dir


class AlignmentCompilerTests(unittest.TestCase):
    def compile(self, data):
        manifest, narration, plan, timing_dir, audio_dir = data
        return compiler.compile_alignment(
            manifest, narration, plan, timing_dir, audio_dir,
            audio_durations={1: 3.0},
        )

    def test_compiles_exact_phrase_timestamps_and_source_regions(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.compile(fixture(directory))
            slide = result["slides"][0]
            self.assertEqual(result["matched_phrase_count"], 2)
            self.assertEqual(len(slide["regions"]), 2)
            self.assertEqual(slide["regions"][0]["intervals"][0]["start"], 0.0)
            self.assertEqual(slide["regions"][1]["intervals"][0]["start"], 1.5)

    def test_duplicate_geometry_is_consolidated(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.compile(fixture(directory, ["s001_sh10", "s001_sh12_duplicate"]))
            slide = result["slides"][0]
            formula = next(x for x in slide["regions"] if x["region_id"] == "s001_sh10")
            self.assertEqual(formula["aliases"], ["s001_sh12_duplicate"])
            self.assertEqual(len(formula["intervals"]), 1)
            self.assertEqual(slide["merged_duplicate_regions"], 1)

    def test_one_phrase_can_target_multiple_distinct_regions(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.compile(fixture(directory, ["s001_sh10", "s001_sh11"]))
            slide = result["slides"][0]
            first_phrase_regions = [
                region for region in slide["regions"]
                if any(interval["event_id"] == "s001_e01" for interval in region["intervals"])
            ]
            self.assertEqual(len(first_phrase_regions), 2)

    def test_low_confidence_match_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                self.compile(fixture(directory, first_confidence=0.75))

    def test_stale_region_manifest_fingerprint_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            data = list(fixture(directory))
            data[0]["slides"][0]["regions"][0]["bbox"][0] = 0.2
            with self.assertRaises(ValueError):
                self.compile(tuple(data))

    def test_phrase_text_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            data = list(fixture(directory))
            data[2]["slides"][0]["phrases"][0]["phrase_text"] = "改过的句子"
            with self.assertRaises(ValueError):
                self.compile(tuple(data))

    def test_timing_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            data = list(fixture(directory))
            data[2]["timing_sha256"]["1"] = "stale"
            with self.assertRaises(ValueError):
                self.compile(tuple(data))

    def test_unverified_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            data = list(fixture(directory))
            data[2]["slides"][0]["phrases"][0]["verification"]["status"] = "needs_review"
            with self.assertRaises(ValueError):
                self.compile(tuple(data))

    def test_missing_phrase_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            data = list(fixture(directory))
            data[2]["slides"][0]["phrases"].pop()
            with self.assertRaises(ValueError):
                self.compile(tuple(data))

    def test_unmatched_phrase_is_reported_without_a_focus_box(self):
        with tempfile.TemporaryDirectory() as directory:
            data = list(fixture(directory))
            row = data[2]["slides"][0]["phrases"][0]
            row.update(status="unmatched", region_ids=[], mapping_basis="unmatched",
                       evidence=[], confidence=0, reason="No reliable visual target")
            result = self.compile(tuple(data))
            self.assertEqual(result["unmatched_phrase_count"], 1)
            self.assertFalse(any(x["region_id"] == "s001_sh10" for x in result["slides"][0]["regions"]))


if __name__ == "__main__":
    unittest.main()

"""Tests for the machine-bound alignment decision finalizer."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import finalize_alignment_plan_v2_4 as finalizer
from compile_alignment_v2_4 import canonical_digest


def context():
    value = {
        "schema_version": "2.4.1",
        "region_manifest_sha256": "regions-sha",
        "narration_sha256": "narration-sha",
        "timing_sha256": {"1": "timing-sha"},
        "audio_sha256": {"1": "audio-sha"},
        "slides": [{
            "slide": 1,
            "regions": [{"region_id": "s001_sh10"}],
            "phrases": [{
                "event_id": "s001_e01",
                "phrase_index": 0,
                "phrase_text": "看这个公式。",
            }],
        }],
    }
    value["context_id"] = canonical_digest(value)
    return value


def decisions():
    return {
        "schema_version": "2.4.1",
        "context_id": context()["context_id"],
        "slides": [{
            "slide": 1,
            "phrases": [{
                "event_id": "s001_e01",
                "phrase_index": 0,
                "phrase_text": "看这个公式。",
                "status": "matched",
                "region_ids": ["s001_sh10"],
                "mapping_basis": "semantic",
                "confidence": 0.97,
                "verification": {"status": "confirmed", "planner_pass": "planner-pass", "reviewer_pass": "independent-pass"},
                "evidence": [{
                    "region_id": "s001_sh10",
                    "region_quote": "dp[i]",
                    "speech_quote": "公式",
                    "reasoning": "讲解短语指向递推公式区域。",
                }],
            }],
        }],
    }


class AlignmentFinalizerTests(unittest.TestCase):
    def test_fingerprints_are_copied_from_machine_context(self):
        result = finalizer.finalize_plan(context(), decisions())
        self.assertEqual(result["region_manifest_sha256"], "regions-sha")
        self.assertEqual(result["timing_sha256"]["1"], "timing-sha")
        self.assertEqual(result["audio_sha256"]["1"], "audio-sha")
        self.assertEqual(
            result["decisions_sha256"],
            canonical_digest({
                "schema_version": result["schema_version"],
                "context_id": result["context_id"],
                "slides": result["slides"],
            }),
        )

    def test_context_id_mismatch_is_rejected(self):
        rows = decisions()
        rows["context_id"] = "different-context"
        with self.assertRaises(ValueError):
            finalizer.finalize_plan(context(), rows)

    def test_missing_phrase_decision_is_rejected(self):
        rows = decisions()
        rows["slides"][0]["phrases"].clear()
        with self.assertRaises(ValueError):
            finalizer.finalize_plan(context(), rows)

    def test_unknown_region_is_rejected(self):
        rows = decisions()
        rows["slides"][0]["phrases"][0]["region_ids"] = ["not-on-this-slide"]
        with self.assertRaises(ValueError):
            finalizer.finalize_plan(context(), rows)

    def test_unmatched_phrase_cannot_keep_focus_region(self):
        rows = decisions()
        rows["slides"][0]["phrases"][0].update(status="unmatched")
        with self.assertRaises(ValueError):
            finalizer.finalize_plan(context(), rows)


if __name__ == "__main__":
    unittest.main()

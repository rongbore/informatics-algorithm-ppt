"""Offline tests for V2.4 media QA contracts."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_full_video_v2_4 as qa


def good_report():
    return {
        "version": "2.4.0-alpha.3",
        "slide_count": 1,
        "total_duration_seconds": 3.0,
        "resolution": "1920x1080",
        "manual_review_required": True,
        "auto_approved": False,
        "slides": [
            {
                "slide": 1,
                "duration_seconds": 3.0,
                "subtitle_cues": 2,
                "matched_focus_regions": 1,
                "unmatched_focus_regions": 0,
                "merged_duplicate_focus_regions": 1,
                "focus_alignment": [
                    {
                        "region_index": 0,
                        "intervals": [
                            {"start": 0.0, "end": 1.0, "event_id": "a"}
                        ],
                    },
                    {
                        "region_index": 1,
                        "reason": "merged_duplicate_geometry",
                        "merged_into_region_index": 0,
                        "intervals": [],
                    },
                ],
            }
        ],
    }


class MediaQATests(unittest.TestCase):
    def test_read_srt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one.srt"
            path.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n第一句\n\n"
                "2\n00:00:02,000 --> 00:00:03,000\n第二句\n",
                encoding="utf-8",
            )
            cues = qa.read_srt(path)
            self.assertEqual(len(cues), 2)
            self.assertEqual(cues[1][:2], (2.0, 3.0))

    def test_report_requires_manual_review(self):
        report = good_report()
        summary = qa.validate_focus_report(report)
        self.assertEqual(summary["slide_ids"], [1])
        self.assertEqual(summary["merged_duplicate_focus_regions"], 1)
        report["auto_approved"] = True
        with self.assertRaises(ValueError):
            qa.validate_focus_report(report)

    def test_duplicate_spoken_phrase_focus_is_rejected(self):
        report = good_report()
        report["slides"][0]["focus_alignment"].append(
            {
                "region_index": 2,
                "intervals": [{"start": 1.1, "end": 1.5, "event_id": "a"}],
            }
        )
        with self.assertRaises(ValueError):
            qa.validate_focus_report(report)

    def test_focus_intervals_must_fit_slide(self):
        report = good_report()
        report["slides"][0]["focus_alignment"][0]["intervals"][0]["end"] = 4.0
        with self.assertRaises(ValueError):
            qa.validate_focus_report(report)

    def test_speech_and_pause_timing_must_cover_audio(self):
        timing = {
            "slide": 1,
            "duration_seconds": 3.0,
            "speech_events": [
                {"start": 0.0, "end": 1.0, "event_id": "a"},
                {"start": 2.0, "end": 3.0, "event_id": "b"},
            ],
            "pauses": [
                {"start": 1.0, "end": 2.0, "kind": "thinking_prompt"}
            ],
        }
        cues = [(0.0, 1.0, "第一句"), (2.0, 3.0, "第二句")]
        result = qa.validate_timing_record(1, timing, 3.0, cues, 2)
        self.assertEqual(result["speech_events"], 2)

    def test_subtitle_cannot_overlap_thinking_pause(self):
        timing = {
            "slide": 1,
            "duration_seconds": 3.0,
            "speech_events": [
                {"start": 0.0, "end": 1.0, "event_id": "a"},
                {"start": 2.0, "end": 3.0, "event_id": "b"},
            ],
            "pauses": [
                {"start": 1.0, "end": 2.0, "kind": "thinking_prompt"}
            ],
        }
        cues = [(0.0, 1.0, "第一句"), (1.5, 2.5, "错误字幕")]
        with self.assertRaises(ValueError):
            qa.validate_timing_record(1, timing, 3.0, cues, 2)

    def test_one_phrase_can_focus_multiple_distinct_regions(self):
        report = good_report()
        first = report["slides"][0]["focus_alignment"][0]["intervals"][0]
        first.update(phrase_index=0, phrase_text="看公式")
        report["slides"][0]["focus_alignment"].append({
            "region_index": 2,
            "region_id": "code-region",
            "intervals": [{
                "start": 0.0, "end": 1.0, "event_id": "a",
                "phrase_index": 0, "phrase_text": "看公式"
            }],
        })
        result = qa.validate_focus_report(report)
        self.assertEqual(result["slides"][0]["slide"], 1)

    def test_same_phrase_cannot_be_duplicated_inside_one_region(self):
        report = good_report()
        first = report["slides"][0]["focus_alignment"][0]["intervals"][0]
        first.update(phrase_index=0, phrase_text="看公式")
        report["slides"][0]["focus_alignment"][0]["intervals"].append(dict(first))
        with self.assertRaises(ValueError):
            qa.validate_focus_report(report)

    def test_speech_pause_overlap_is_rejected(self):
        timing = {
            "slide": 1,
            "duration_seconds": 3.0,
            "speech_events": [{"start": 0.0, "end": 2.0, "event_id": "a"}],
            "pauses": [{"start": 1.0, "end": 3.0, "kind": "thinking_prompt"}],
        }
        with self.assertRaises(ValueError):
            qa.validate_timing_record(1, timing, 3.0, [(0.0, 1.0, "字幕")], 1)


if __name__ == "__main__":
    unittest.main()

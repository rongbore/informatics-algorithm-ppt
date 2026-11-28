"""Offline tests for V2.4 phrase-timed focus alignment."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import align_focus_v2_4 as focus


def sample(repeat=False):
    narration_events = [
        {"event_id": "a", "type": "narration", "text": "这是一个完整的测试语句。"}
    ]
    if repeat:
        narration_events.append(dict(narration_events[0], event_id="b"))

    narration_slide = {"slide": 1, "events": narration_events}
    speech_events = [
        dict(event, start=float(index * 2), end=float(index * 2 + 1))
        for index, event in enumerate(narration_events)
    ]
    timing = {
        "slide": 1,
        "duration_seconds": float(len(narration_events)) * 2,
        "speech_events": speech_events,
        "pauses": [
            {"start": float(index * 2 + 1), "end": float(index * 2 + 2), "kind": "natural"}
            for index in range(len(narration_events))
        ],
    }
    region = {
        "target_text": "这是一个完整的测试语句",
        "bbox": [0, 0, 0.4, 0.2],
        "shape_index": 6,
        "kind": "algorithm",
        "confidence": 1,
        "geometry_status": "matched",
    }
    item = {
        "slide": 1,
        "events": [dict(region, label="数据依据"), dict(region, label="图解数据")],
    }
    return item, narration_slide, timing


class FocusAlignmentTests(unittest.TestCase):
    def align(self, item, narration_slide, timing, anchors=None):
        return focus.align_slide(
            item, narration_slide, timing, timing["duration_seconds"], anchors or {}
        )

    def test_unique_literal_match_is_not_duplicated(self):
        item, narration_slide, timing = sample()
        rows = self.align(item, narration_slide, timing)
        self.assertEqual(rows[0]["mode"], "unique_literal_phrase")
        self.assertEqual(rows[1]["reason"], "merged_duplicate_geometry")
        self.assertEqual(len(rows[0]["intervals"]), 1)
        self.assertFalse(rows[1]["intervals"])

    def test_ambiguous_literal_match_is_rejected(self):
        item, narration_slide, timing = sample(repeat=True)
        rows = self.align(item, narration_slide, timing)
        self.assertTrue(all(not row["intervals"] for row in rows))

    def test_stale_timing_is_rejected(self):
        item, narration_slide, timing = sample()
        timing["speech_events"][0]["text"] = "wrong"
        with self.assertRaises(ValueError):
            self.align(item, narration_slide, timing)

    def test_pause_cannot_overlap_speech(self):
        item, narration_slide, timing = sample()
        timing["pauses"][0]["start"] = 0.5
        with self.assertRaises(ValueError):
            self.align(item, narration_slide, timing)

    def test_invalid_bbox_is_not_rendered(self):
        item, narration_slide, timing = sample()
        item["events"][0]["bbox"] = [0.9, 0, 0.4, 0.2]
        rows = self.align(item, narration_slide, timing)
        self.assertEqual(rows[0]["reason"], "invalid_or_unverified_geometry")
        self.assertFalse(rows[0]["intervals"])

    def test_operators_and_case_are_preserved(self):
        self.assertNotEqual(focus.norm("m+a"), focus.norm("M+a"))
        self.assertNotEqual(focus.norm("1.2"), focus.norm("12"))

    def test_reviewed_anchor_has_priority(self):
        item, narration_slide, timing = sample()
        rows = self.align(item, narration_slide, timing, {(1, 1): {"event_ids": ["a"]}})
        self.assertEqual(rows[0]["reason"], "merged_duplicate_geometry")
        self.assertEqual(rows[1]["mode"], "reviewable_event_anchor")

    def test_ratio_fields_never_trigger_focus(self):
        item, narration_slide, timing = sample()
        for event in item["events"]:
            event.update(
                target_text="Unrelated target",
                speech_start_ratio=0.2,
                speech_end_ratio=0.5,
            )
        rows = self.align(item, narration_slide, timing)
        self.assertFalse(any(row["intervals"] for row in rows))

    def test_duplicate_geometry_merges_distinct_anchored_phrases(self):
        item, narration_slide, timing = sample(repeat=True)
        anchors = {
            (1, 0): {"event_ids": ["a"]},
            (1, 1): {"event_ids": ["b"]},
        }
        rows = self.align(item, narration_slide, timing, anchors)
        self.assertEqual(len(rows[0]["intervals"]), 2)
        self.assertEqual(rows[0]["reason"], "merged_duplicate_geometry_intervals")
        self.assertEqual(rows[1]["reason"], "merged_duplicate_geometry")
        self.assertEqual(rows[1]["merged_into_region_index"], 0)
        self.assertFalse(rows[1]["intervals"])

    def test_different_shape_ids_are_not_merged(self):
        item, narration_slide, timing = sample(repeat=True)
        item["events"][1]["shape_index"] = 7
        anchors = {
            (1, 0): {"event_ids": ["a"]},
            (1, 1): {"event_ids": ["b"]},
        }
        rows = self.align(item, narration_slide, timing, anchors)
        self.assertEqual(len(rows[0]["intervals"]), 1)
        self.assertEqual(len(rows[1]["intervals"]), 1)
        self.assertNotIn("merged_into_region_index", rows[1])

    def test_source_fingerprint_is_enforced(self):
        item, narration_slide, _timing = sample()
        timeline = {"slides": [item]}
        narration = {"slides": [narration_slide]}
        plan = {
            "timeline_digest": focus.digest(timeline),
            "narration_digest": focus.digest(narration),
            "anchors": [],
        }
        focus.validate_sources(timeline, narration, plan)
        plan["narration_digest"] = "wrong"
        with self.assertRaises(ValueError):
            focus.validate_sources(timeline, narration, plan)


if __name__ == "__main__":
    unittest.main()

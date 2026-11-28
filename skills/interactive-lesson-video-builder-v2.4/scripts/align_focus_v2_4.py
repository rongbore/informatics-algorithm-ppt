"""Phrase-timed focus alignment. No ratio fallback and no network calls."""
import argparse
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(obj):
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def split_phrases(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    parts = [x.strip() for x in re.split(r"(?<=[。！？；：.!?;])", text) if x.strip()]
    result = []
    buf = ""
    for part in parts:
        if buf and len(buf) >= 12:
            result.append(buf)
            buf = part
        else:
            buf += part
    if buf:
        result.append(buf)
    return [x for x in result if len(x.strip()) >= 2]


def norm(value):
    # Preserve case and operators: M/m and +/− can have different meaning.
    value = unicodedata.normalize("NFC", str(value or "")).replace("−", "-").replace("－", "-")
    return re.sub(r"\s+", "", value)


def valid_bbox(event, min_confidence):
    bbox = event.get("bbox")
    try:
        return (
            isinstance(bbox, list)
            and len(bbox) == 4
            and all(isinstance(x, (int, float)) and math.isfinite(x) for x in bbox)
            and bbox[0] >= 0
            and bbox[1] >= 0
            and bbox[2] > 0
            and bbox[3] > 0
            and bbox[0] + bbox[2] <= 1.00002
            and bbox[1] + bbox[3] <= 1.00002
            and math.isfinite(float(event.get("confidence", 0)))
            and float(event.get("confidence", 0)) >= min_confidence
            and event.get("geometry_status") == "matched"
        )
    except (TypeError, ValueError):
        return False


def geometry_key(event):
    """Identity for duplicate region definitions; labels are intentionally excluded."""
    try:
        bbox = tuple(round(float(value), 6) for value in event["bbox"])
        if len(bbox) != 4:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return (
        event.get("shape_index"),
        event.get("kind"),
        norm(event.get("target_text")),
        bbox,
    )


def validate_sources(timeline, narration, plan):
    require(
        digest(timeline) == plan["timeline_digest"],
        "Timeline digest mismatch; review the anchor plan.",
    )
    require(
        digest(narration) == plan["narration_digest"],
        "Narration digest mismatch; compile the matching teaching plan.",
    )

    def index(doc):
        sequence = doc["slides"]
        result = {int(slide["slide"]): slide for slide in sequence}
        require(len(sequence) == len(result), "Duplicate slide number")
        return result

    timeline_by_slide, narration_by_slide = index(timeline), index(narration)
    require(
        set(timeline_by_slide) == set(narration_by_slide),
        "Timeline and narration page sets differ",
    )

    anchors = {}
    for anchor in plan["anchors"]:
        page = int(anchor["slide"])
        region_index = int(anchor["region_index"])
        require(
            page in timeline_by_slide
            and 0 <= region_index < len(timeline_by_slide[page].get("events", [])),
            "Unknown anchor region",
        )
        event = timeline_by_slide[page]["events"][region_index]
        event_ids = anchor["event_ids"]
        require(
            event["target_text"] == anchor["target_text"]
            and event["bbox"] == anchor["bbox"],
            "Anchor target/geometry changed",
        )
        by_id = {item["event_id"]: item for item in narration_by_slide[page]["events"]}
        require(
            bool(event_ids)
            and len(event_ids) == len(set(event_ids))
            and all(event_id in by_id for event_id in event_ids),
            "Invalid anchor event IDs",
        )
        require(
            [by_id[event_id]["text"] for event_id in event_ids] == anchor["evidence"],
            "Anchor evidence mismatch",
        )
        require((page, region_index) not in anchors, "Duplicate anchor")
        anchors[page, region_index] = anchor

    return timeline_by_slide, narration_by_slide, anchors


def validate_timing(narration_slide, timing, duration):
    page = int(narration_slide["slide"])
    require(int(timing["slide"]) == page, "Timing page mismatch")
    require(math.isfinite(duration) and duration > 0, "Invalid audio duration")
    require(
        abs(float(timing["duration_seconds"]) - duration) <= 0.10,
        "Timing/audio duration mismatch",
    )

    expected = []
    event_ids = set()
    for event in narration_slide["events"]:
        event_id = event["event_id"]
        require(event_id not in event_ids, "Duplicate narration event ID")
        event_ids.add(event_id)
        if event.get("type", "narration") == "pause":
            continue
        expected.extend(
            (event_id, event.get("type", "narration"), phrase)
            for phrase in split_phrases(event.get("text", ""))
        )

    speech = timing.get("speech_events", [])
    actual = [(event["event_id"], event["type"], event["text"]) for event in speech]
    require(actual == expected, f"Slide {page}: stale or mismatched speech timings")

    last_end = 0.0
    for event in speech:
        start, end = float(event["start"]), float(event["end"])
        require(
            math.isfinite(start)
            and math.isfinite(end)
            and start >= last_end - 0.002
            and start >= 0
            and end > start
            and end <= duration + 0.01,
            "Invalid speech interval",
        )
        last_end = end

    for pause in timing.get("pauses", []):
        start, end = float(pause["start"]), float(pause["end"])
        require(
            math.isfinite(start)
            and math.isfinite(end)
            and 0 <= start < end <= duration + 0.01,
            "Invalid pause interval",
        )
        require(
            not any(
                min(end, float(event["end"])) - max(start, float(event["start"])) > 0.002
                for event in speech
            ),
            "Speech overlaps pause",
        )

    return speech


def align_slide(item, narration_slide, timing, duration, anchors, min_confidence=0.45):
    speech = validate_timing(narration_slide, timing, duration)
    page = int(item["slide"])
    candidates = []
    audit = [
        {
            "region_index": index,
            "shape_index": event.get("shape_index"),
            "kind": event.get("kind"),
            "target_text": event.get("target_text"),
            "mode": "unmatched",
            "intervals": [],
        }
        for index, event in enumerate(item.get("events", []))
    ]

    for index, event in enumerate(item.get("events", [])):
        anchor = anchors.get((page, index))
        row = audit[index]
        if not valid_bbox(event, min_confidence):
            row["reason"] = "invalid_or_unverified_geometry"
            continue

        if anchor:
            matches = [
                i for i, phrase in enumerate(speech)
                if phrase["event_id"] in anchor["event_ids"]
            ]
            mode = "reviewable_event_anchor"
        else:
            target = norm(event.get("target_text"))
            matches = [
                i for i, phrase in enumerate(speech)
                if target and target in norm(phrase["text"])
            ]
            if len(target) < 8 or sum(char.isalnum() for char in target) < 6 or len(matches) != 1:
                row["reason"] = "no_unique_full_text_match"
                continue
            mode = "unique_literal_phrase"

        if not matches:
            row["reason"] = "anchor_has_no_spoken_phrase"
            continue
        candidates.append((0 if anchor else 1, index, matches, mode))

    # Reviewed anchors win. Identical region definitions share one rendered box,
    # while distinct spoken phrases can still contribute separate intervals.
    candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
    geometry_owner = {}
    chosen_phrases = {}

    for _priority, region_index, matches, mode in candidates:
        row = audit[region_index]
        event = item["events"][region_index]
        key = geometry_key(event)
        if key is None:
            owner_index = region_index
        else:
            owner_index = geometry_owner.setdefault(key, region_index)

        owner_row = audit[owner_index]
        is_duplicate_geometry = owner_index != region_index
        added = 0

        for phrase_index in matches:
            if phrase_index in chosen_phrases:
                continue
            phrase = speech[phrase_index]
            start = max(0.0, float(phrase["start"]))
            end = min(duration, float(phrase["end"]))
            if end - start < 0.08:
                continue
            chosen_phrases[phrase_index] = owner_index
            owner_row["intervals"].append(
                {
                    "start": start,
                    "end": end,
                    "event_id": phrase["event_id"],
                    "phrase": phrase["text"],
                }
            )
            added += 1

        if is_duplicate_geometry:
            row["mode"] = "merged_duplicate_geometry"
            row["reason"] = "merged_duplicate_geometry"
            row["merged_into_region_index"] = owner_index
            if added:
                owner_row["mode"] = "merged_duplicate_geometry"
                owner_row["reason"] = "merged_duplicate_geometry_intervals"
            continue

        if owner_row["intervals"]:
            owner_row["mode"] = mode if not owner_row.get("mode") else owner_row["mode"]
            owner_row["reason"] = (
                "one_region_per_phrase" if len(owner_row["intervals"]) < len(matches) else "matched"
            )
        else:
            owner_row["reason"] = "duplicate_or_competing_focus"

    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--narration", required=True)
    parser.add_argument("--anchor-plan", required=True)
    parser.add_argument("--timings", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--slides", nargs="+", type=int)
    args = parser.parse_args()

    timeline = load(args.timeline)
    narration = load(args.narration)
    anchor_plan = load(args.anchor_plan)
    timeline_by_slide, narration_by_slide, anchors = validate_sources(
        timeline, narration, anchor_plan
    )
    pages = args.slides or sorted(timeline_by_slide)
    require(
        len(pages) == len(set(pages)) and set(pages) <= set(timeline_by_slide),
        "Invalid page selection",
    )

    rows = []
    for page in pages:
        timing = load(Path(args.timings) / f"slide_{page:03d}.json")
        rows.append(
            {
                "slide": page,
                "regions": align_slide(
                    timeline_by_slide[page],
                    narration_by_slide[page],
                    timing,
                    float(timing["duration_seconds"]),
                    anchors,
                ),
            }
        )

    report = {
        "version": "2.4.0-alpha.3",
        "manual_review_required": True,
        "auto_approved": False,
        "audio_duration_independently_probed": False,
        "slides": rows,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Focus audit:", report_path)


if __name__ == "__main__":
    main()

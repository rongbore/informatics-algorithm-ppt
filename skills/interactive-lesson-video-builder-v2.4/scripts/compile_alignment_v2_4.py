"""Compile AI-proposed visual/speech mappings into source-verified time intervals."""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import unicodedata
from pathlib import Path

from generate_audio_v2_4 import split_phrases


ALLOWED_BASES = {
    "exact_text", "code_reference", "formula_reference",
    "diagram_reference", "semantic",
}
MATCHED_STATUSES = {"matched", "review_required", "unmatched"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def canonical_digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evidence_norm(value):
    return "".join(unicodedata.normalize("NFC", str(value or "")).split())


def probe_duration(path, ffprobe=None):
    ffprobe = ffprobe or shutil.which("ffprobe")
    require(bool(ffprobe), "FFprobe must be available on PATH")
    process = subprocess.run(
        [
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if process.returncode:
        raise RuntimeError(process.stderr[-3000:])
    duration = float(process.stdout.strip())
    require(math.isfinite(duration) and duration > 0, f"Invalid audio duration: {path}")
    return duration


def index_slides(document, name):
    slides = document.get("slides", [])
    result = {}
    for row in slides:
        number = int(row["slide"])
        require(number not in result, f"{name}: duplicate slide {number}")
        result[number] = row
    return result


def expected_phrases(narration_slide):
    rows = []
    event_ids = set()
    for index, event in enumerate(narration_slide.get("events", []), 1):
        event_id = str(event.get("event_id") or f"s{int(narration_slide['slide']):03d}_e{index:02d}")
        require(event_id not in event_ids, f"Slide {narration_slide['slide']}: duplicate event ID {event_id}")
        event_ids.add(event_id)
        kind = event.get("type", "narration")
        if kind == "pause":
            continue
        require(kind in ("narration", "thinking_prompt", "reveal", "summary"),
                f"Slide {narration_slide['slide']}: unsupported event type {kind}")
        for phrase_index, phrase in enumerate(split_phrases(event.get("text", ""))):
            rows.append({
                "event_id": event_id,
                "phrase_index": phrase_index,
                "type": kind,
                "text": phrase,
            })
    return rows


def validate_timing(narration_slide, timing, audio_duration):
    page = int(narration_slide["slide"])
    require(timing.get("schema_version") == "2.4.1",
            f"Slide {page}: timing schema must be 2.4.1; regenerate audio")
    require(int(timing["slide"]) == page, f"Slide {page}: timing file slide ID mismatch")
    recorded_duration = float(timing["duration_seconds"])
    require(
        math.isfinite(recorded_duration) and abs(recorded_duration - audio_duration) <= 0.15,
        f"Slide {page}: measured audio duration differs from timing JSON",
    )
    expected = expected_phrases(narration_slide)
    speech = timing.get("speech_events", [])
    require(len(speech) == len(expected), f"Slide {page}: narration phrase count differs from audio timing")
    actual = []
    phrase_counts = {}
    for event in speech:
        event_id = str(event["event_id"])
        require("phrase_index" in event, f"Slide {page}: phrase_index missing; regenerate V2.4.1 audio")
        phrase_index = int(event["phrase_index"])
        phrase_counts[event_id] = phrase_index + 1
        actual.append({
            "event_id": event_id,
            "phrase_index": phrase_index,
            "type": event.get("type", "narration"),
            "text": event.get("text", ""),
        })
    require(actual == expected, f"Slide {page}: stale timing or phrase text mismatch")

    intervals = []
    for event in speech:
        start, end = float(event["start"]), float(event["end"])
        require(
            math.isfinite(start) and math.isfinite(end)
            and 0 <= start < end <= audio_duration + 0.05,
            f"Slide {page}: invalid speech interval",
        )
        intervals.append((start, end, "speech"))
    for pause in timing.get("pauses", []):
        start, end = float(pause["start"]), float(pause["end"])
        require(
            math.isfinite(start) and math.isfinite(end)
            and 0 <= start < end <= audio_duration + 0.05,
            f"Slide {page}: invalid pause interval",
        )
        intervals.append((start, end, "pause"))
    intervals.sort(key=lambda row: (row[0], row[1]))
    last_end = 0.0
    for start, end, _kind in intervals:
        require(start >= last_end - 0.003, f"Slide {page}: speech and pause intervals overlap")
        require(start <= last_end + 0.15, f"Slide {page}: unexplained audio timeline gap")
        last_end = end
    require(abs(last_end - audio_duration) <= 0.20,
            f"Slide {page}: timing intervals do not cover the measured audio")
    return expected, speech


def region_geometry_key(region):
    text = region.get("text") or region.get("visual_description") or region.get("label") or ""
    return (
        str(region.get("kind", "knowledge")),
        evidence_norm(text),
        tuple(round(float(x), 7) for x in region["bbox"]),
    )


def validate_region(region, page):
    bbox = region.get("bbox")
    require(isinstance(bbox, list) and len(bbox) == 4, f"Slide {page}: invalid bbox")
    x, y, w, h = [float(value) for value in bbox]
    require(
        all(math.isfinite(value) for value in (x, y, w, h))
        and x >= 0 and y >= 0 and w > 0 and h > 0
        and x + w <= 1.00001 and y + h <= 1.00001,
        f"Slide {page}: bbox is outside normalized slide coordinates",
    )
    require(region.get("mapping_eligible") is True,
            f"Slide {page}: region {region.get('region_id')} is not verified for mapping")
    require(region.get("geometry_status") in ("source_verified", "vision_confirmed"),
            f"Slide {page}: region {region.get('region_id')} has unverified geometry")
    if region.get("geometry_source") == "vision_model":
        verification = region.get("verification", {})
        planner_pass = str(verification.get("planner_pass", "")).strip()
        reviewer_pass = str(verification.get("reviewer_pass", "")).strip()
        require(
            verification.get("status") == "confirmed"
            and planner_pass and reviewer_pass and planner_pass != reviewer_pass,
            f"Slide {page}: vision geometry lacks a distinct independent verification pass",
        )


def compile_alignment(region_manifest, narration, plan, timing_dir, audio_dir,
                      selected_slides=None, audio_durations=None):
    require(region_manifest.get("schema_version") == "2.4.1",
            "Unsupported region manifest schema")
    require(plan.get("schema_version") == "2.4.1",
            "Unsupported alignment plan schema")
    require(bool(str(plan.get("context_id", "")).strip()),
            "Alignment plan is missing its prepared context ID")
    require(
        plan.get("region_manifest_sha256") == canonical_digest(region_manifest),
        "Region manifest fingerprint mismatch",
    )
    require(
        plan.get("narration_sha256") == canonical_digest(narration),
        "Narration fingerprint mismatch",
    )

    region_slides = index_slides(region_manifest, "Region manifest")
    narration_slides = index_slides(narration, "Narration")
    plan_slides = index_slides(plan, "Alignment plan")
    require(set(region_slides) == set(narration_slides),
            "PPTX region and narration slide sets differ")
    pages = sorted(plan_slides)
    if selected_slides:
        selected = set(int(x) for x in selected_slides)
        require(selected <= set(plan_slides), "Requested slide is absent from alignment plan")
        pages = [page for page in pages if page in selected]
    require(bool(pages), "No slides selected for alignment compilation")

    timing_digests = plan.get("timing_sha256", {})
    audio_digests = plan.get("audio_sha256", {})
    output_slides = []
    total_phrases = matched_phrases = review_phrases = unmatched_phrases = 0
    global_timing_hashes, global_audio_hashes = {}, {}

    for page in pages:
        timing_path = Path(timing_dir) / f"slide_{page:03d}.json"
        audio_path = Path(audio_dir) / f"slide_{page:03d}.mp3"
        require(timing_path.is_file(), f"Slide {page}: timing JSON missing")
        require(audio_path.is_file(), f"Slide {page}: audio file missing")
        timing_hash, audio_hash = sha256_file(timing_path), sha256_file(audio_path)
        require(timing_digests.get(str(page)) == timing_hash,
                f"Slide {page}: timing file fingerprint mismatch")
        require(audio_digests.get(str(page)) == audio_hash,
                f"Slide {page}: audio file fingerprint mismatch")
        global_timing_hashes[str(page)] = timing_hash
        global_audio_hashes[str(page)] = audio_hash

        timing = load(timing_path)
        narration_slide = narration_slides[page]
        if audio_durations and page in audio_durations:
            duration = float(audio_durations[page])
        else:
            duration = probe_duration(audio_path)
        expected, speech = validate_timing(narration_slide, timing, duration)

        slide_manifest = region_slides[page]
        regions = slide_manifest.get("regions", [])
        region_by_id = {}
        for region in regions:
            region_id = str(region.get("region_id", ""))
            require(region_id and region_id not in region_by_id,
                    f"Slide {page}: missing or duplicate region ID")
            region_by_id[region_id] = region

        plan_phrases = plan_slides[page].get("phrases", [])
        plan_by_key = {}
        for row in plan_phrases:
            key = (str(row.get("event_id", "")), int(row.get("phrase_index", -1)))
            require(key not in plan_by_key, f"Slide {page}: duplicate phrase mapping {key}")
            plan_by_key[key] = row
        expected_keys = {(x["event_id"], x["phrase_index"]) for x in expected}
        require(set(plan_by_key) == expected_keys,
                f"Slide {page}: plan must account for every spoken phrase exactly once")

        canonical_regions, canonical_by_key, aliases = {}, {}, {}
        for region_id, region in region_by_id.items():
            if not region.get("mapping_eligible"):
                continue
            validate_region(region, page)
            key = region_geometry_key(region)
            if key not in canonical_by_key:
                canonical_id = region_id
                canonical_by_key[key] = canonical_id
                canonical_regions[canonical_id] = {
                    "region_id": canonical_id,
                    "aliases": [],
                    "bbox": region["bbox"],
                    "kind": region.get("kind", "knowledge"),
                    "label": region.get("label", region_id),
                    "text": region.get("text", ""),
                    "geometry_source": region.get("geometry_source"),
                    "geometry_status": region.get("geometry_status"),
                    "confidence": float(region.get("confidence", 1.0)),
                    "intervals": [],
                }
                aliases[region_id] = canonical_id
            else:
                canonical_id = canonical_by_key[key]
                aliases[region_id] = canonical_id
                canonical_regions[canonical_id]["aliases"].append(region_id)

        phrase_rows = []
        unmatched_rows, review_rows = [], []
        speech_by_key = {
            (str(row["event_id"]), int(row.get("phrase_index", 0))): row
            for row in speech
        }
        for expected_row in expected:
            key = (expected_row["event_id"], expected_row["phrase_index"])
            mapping = plan_by_key[key]
            require(mapping.get("phrase_text") == expected_row["text"],
                    f"Slide {page}: phrase text mismatch for {key}")
            status = mapping.get("status", "unmatched")
            require(status in MATCHED_STATUSES, f"Slide {page}: invalid mapping status {status}")
            region_ids = mapping.get("region_ids", [])
            require(isinstance(region_ids, list) and len(region_ids) == len(set(region_ids)),
                    f"Slide {page}: region_ids must be a unique list")
            confidence = float(mapping.get("confidence", 0))
            require(math.isfinite(confidence) and 0 <= confidence <= 1,
                    f"Slide {page}: invalid mapping confidence")

            if status == "matched":
                require(1 <= len(region_ids) <= 3,
                        f"Slide {page}: a matched phrase must target 1-3 visual regions")
                require(confidence >= 0.90,
                        f"Slide {page}: mapping confidence below 0.90 must be reviewed")
                require(mapping.get("mapping_basis") in ALLOWED_BASES,
                        f"Slide {page}: missing/invalid mapping basis")
                verification = mapping.get("verification", {})
                require(
                    verification.get("status") == "confirmed"
                    and str(verification.get("planner_pass", "")).strip()
                    and str(verification.get("reviewer_pass", "")).strip()
                    and str(verification.get("planner_pass", "")).strip()
                        != str(verification.get("reviewer_pass", "")).strip(),
                    f"Slide {page}: matched mapping lacks distinct planner and verifier passes",
                )
                evidence_rows = mapping.get("evidence", [])
                evidence_by_region = {x.get("region_id"): x for x in evidence_rows}
                require(
                    len(evidence_by_region) == len(evidence_rows)
                    and set(evidence_by_region) == set(region_ids),
                    f"Slide {page}: evidence must cover each target region exactly once",
                )
                for region_id in region_ids:
                    require(region_id in region_by_id,
                            f"Slide {page}: mapping references unknown region {region_id}")
                    region = region_by_id[region_id]
                    validate_region(region, page)
                    evidence = evidence_by_region.get(region_id)
                    require(evidence is not None,
                            f"Slide {page}: mapping lacks evidence for region {region_id}")
                    region_source = " ".join([
                        str(region.get("text", "")),
                        str(region.get("visual_description", "")),
                        str(region.get("label", "")),
                    ])
                    region_quote = str(evidence.get("region_quote", ""))
                    speech_quote = str(evidence.get("speech_quote", ""))
                    require(
                        evidence_norm(region_quote)
                        and evidence_norm(region_quote) in evidence_norm(region_source),
                        f"Slide {page}: region evidence quote is not source-grounded",
                    )
                    require(
                        evidence_norm(speech_quote)
                        and evidence_norm(speech_quote) in evidence_norm(expected_row["text"]),
                        f"Slide {page}: speech evidence quote is not source-grounded",
                    )
                    require(len(str(evidence.get("reasoning", "")).strip()) >= 12,
                            f"Slide {page}: evidence reasoning is too short")
                    canonical_id = aliases[region_id]
                    phrase_timing = speech_by_key[key]
                    canonical_regions[canonical_id]["intervals"].append({
                        "start": float(phrase_timing["start"]),
                        "end": float(phrase_timing["end"]),
                        "event_id": expected_row["event_id"],
                        "phrase_index": expected_row["phrase_index"],
                        "phrase_text": expected_row["text"],
                    })
                matched_phrases += 1
            elif status == "review_required":
                require(
                    all(region_id in region_by_id for region_id in region_ids),
                    f"Slide {page}: review candidate references unknown region",
                )
                review_phrases += 1
                review_rows.append({
                    "event_id": key[0], "phrase_index": key[1],
                    "phrase_text": expected_row["text"],
                    "candidate_region_ids": region_ids,
                    "reason": str(mapping.get("reason", "AI mapping requires review")),
                    "confidence": confidence,
                })
            else:
                require(not region_ids,
                        f"Slide {page}: unmatched phrase must not contain renderable region IDs")
                unmatched_phrases += 1
                unmatched_rows.append({
                    "event_id": key[0], "phrase_index": key[1],
                    "phrase_text": expected_row["text"],
                    "reason": str(mapping.get("reason", "No reliable visual target")),
                })
            phrase_rows.append({
                "event_id": key[0], "phrase_index": key[1],
                "phrase_text": expected_row["text"], "status": status,
                "region_ids": region_ids, "confidence": confidence,
            })
            total_phrases += 1

        output_regions = []
        for region in canonical_regions.values():
            intervals = sorted(region["intervals"], key=lambda x: (x["start"], x["end"]))
            deduped = []
            seen_intervals = set()
            for interval in intervals:
                interval_key = (
                    interval["event_id"], interval["phrase_index"],
                    round(interval["start"], 4), round(interval["end"], 4),
                )
                if interval_key in seen_intervals:
                    continue
                seen_intervals.add(interval_key)
                deduped.append(interval)
            if deduped:
                region["intervals"] = deduped
                output_regions.append(region)

        output_slides.append({
            "slide": page,
            "duration_seconds": round(duration, 3),
            "slide_image_sha256": slide_manifest.get("slide_image_sha256"),
            "regions": output_regions,
            "phrases": phrase_rows,
            "unmatched_phrases": unmatched_rows,
            "review_required_phrases": review_rows,
            "speech_events": speech,
            "pauses": timing.get("pauses", []),
            "merged_duplicate_regions": sum(len(x["aliases"]) for x in output_regions),
        })

    return {
        "version": "2.4.1-alpha.4",
        "schema_version": "2.4.1",
        "source_fingerprints": {
            "source_pptx_sha256": region_manifest["source_pptx_sha256"],
            "region_manifest_sha256": canonical_digest(region_manifest),
            "narration_sha256": canonical_digest(narration),
            "timing_sha256": global_timing_hashes,
            "audio_sha256": global_audio_hashes,
        },
        "slide_count": len(output_slides),
        "phrase_count": total_phrases,
        "matched_phrase_count": matched_phrases,
        "review_required_phrase_count": review_phrases,
        "unmatched_phrase_count": unmatched_phrases,
        "manual_review_required": True,
        "auto_approved": False,
        "slides": output_slides,
        "limitations": [
            "Semantic mapping is proposed by the AI planner and independently checked in a separate verification pass.",
            "Deterministic checks verify source IDs, evidence quotes, geometry, audio hashes, and measured timing; they cannot mathematically prove semantic correctness.",
            "Low-confidence or unsupported mappings are withheld from rendering and listed for review.",
            "Phrase-level timestamps are not word-level or phoneme-level forced alignment.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions", required=True)
    parser.add_argument("--narration", required=True)
    parser.add_argument("--alignment-plan", required=True)
    parser.add_argument("--timings-dir", required=True)
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--slides", nargs="*", type=int)
    args = parser.parse_args()

    result = compile_alignment(
        load(args.regions),
        load(args.narration),
        load(args.alignment_plan),
        args.timings_dir,
        args.audio_dir,
        selected_slides=args.slides,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Compiled {result['matched_phrase_count']}/{result['phrase_count']} phrases; "
        f"{result['review_required_phrase_count']} require review; "
        f"{result['unmatched_phrase_count']} have no visual target."
    )
    print(f"Alignment report: {output}")


if __name__ == "__main__":
    main()

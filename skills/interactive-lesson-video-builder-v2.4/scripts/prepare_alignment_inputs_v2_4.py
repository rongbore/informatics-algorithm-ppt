"""Prepare exact, hash-bound phrase and region context for the AI alignment planner."""
import argparse
import json
from pathlib import Path

from compile_alignment_v2_4 import (
    canonical_digest,
    load,
    probe_duration,
    sha256_file,
    validate_timing,
)


def prepare_context(region_manifest, narration, timing_dir, audio_dir, selected_slides=None):
    if region_manifest.get("schema_version") != "2.4.1":
        raise ValueError("Unsupported region manifest schema")
    region_slides = {int(row["slide"]): row for row in region_manifest.get("slides", [])}
    narration_slides = {int(row["slide"]): row for row in narration.get("slides", [])}
    if len(region_slides) != len(region_manifest.get("slides", [])):
        raise ValueError("Duplicate region-manifest slide IDs")
    if len(narration_slides) != len(narration.get("slides", [])):
        raise ValueError("Duplicate narration slide IDs")
    if set(region_slides) != set(narration_slides):
        raise ValueError("Region and narration slide sets differ")

    pages = sorted(region_slides)
    if selected_slides:
        selected = set(int(x) for x in selected_slides)
        if not selected <= set(pages):
            raise ValueError("Selected slide is absent from source files")
        pages = [page for page in pages if page in selected]

    context_slides = []
    timing_hashes, audio_hashes = {}, {}
    for page in pages:
        timing_path = Path(timing_dir) / f"slide_{page:03d}.json"
        audio_path = Path(audio_dir) / f"slide_{page:03d}.mp3"
        if not timing_path.is_file() or not audio_path.is_file():
            raise FileNotFoundError(f"Slide {page}: timing JSON or audio file missing")
        timing = load(timing_path)
        duration = probe_duration(audio_path)
        expected, speech = validate_timing(narration_slides[page], timing, duration)
        timing_hashes[str(page)] = sha256_file(timing_path)
        audio_hashes[str(page)] = sha256_file(audio_path)

        regions = []
        for region in region_slides[page].get("regions", []):
            regions.append({
                "region_id": region["region_id"],
                "kind": region.get("kind", "knowledge"),
                "label": region.get("label", ""),
                "text": region.get("text", ""),
                "visual_description": region.get("visual_description", ""),
                "bbox": region["bbox"],
                "mapping_eligible": bool(region.get("mapping_eligible")),
                "geometry_status": region.get("geometry_status"),
                "geometry_source": region.get("geometry_source"),
                "confidence": region.get("confidence", 1.0),
            })

        phrase_rows = []
        for expected_row, timing_row in zip(expected, speech):
            phrase_rows.append({
                "event_id": expected_row["event_id"],
                "phrase_index": expected_row["phrase_index"],
                "type": expected_row["type"],
                "phrase_text": expected_row["text"],
                "start": float(timing_row["start"]),
                "end": float(timing_row["end"]),
            })
        context_slides.append({
            "slide": page,
            "slide_image_sha256": region_slides[page].get("slide_image_sha256"),
            "regions": regions,
            "phrases": phrase_rows,
        })

    context = {
        "schema_version": "2.4.1",
        "region_manifest_sha256": canonical_digest(region_manifest),
        "narration_sha256": canonical_digest(narration),
        "timing_sha256": timing_hashes,
        "audio_sha256": audio_hashes,
        "slides": context_slides,
    }
    context["context_id"] = canonical_digest(context)
    return context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions", required=True)
    parser.add_argument("--narration", required=True)
    parser.add_argument("--timings-dir", required=True)
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--slides", nargs="*", type=int)
    args = parser.parse_args()

    context = prepare_context(
        load(args.regions), load(args.narration),
        args.timings_dir, args.audio_dir, args.slides,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {sum(len(row['phrases']) for row in context['slides'])} exact speech phrases")
    print(f"Context ID: {context['context_id']}")
    print(f"Context: {output}")


if __name__ == "__main__":
    main()

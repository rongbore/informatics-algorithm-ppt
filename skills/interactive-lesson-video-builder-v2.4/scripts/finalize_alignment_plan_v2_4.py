"""Attach machine-computed fingerprints to AI alignment decisions."""
import argparse
import json
from pathlib import Path

from compile_alignment_v2_4 import canonical_digest


def finalize_plan(context, decisions):
    if context.get("schema_version") != "2.4.1" or decisions.get("schema_version") != "2.4.1":
        raise ValueError("Unsupported alignment context/decision schema")
    context_payload = dict(context)
    supplied_context_id = context_payload.pop("context_id", None)
    if not supplied_context_id or supplied_context_id != canonical_digest(context_payload):
        raise ValueError("Prepared alignment context fingerprint is invalid")
    if decisions.get("context_id") != supplied_context_id:
        raise ValueError("Alignment decisions were generated for a different context")

    context_slides = {int(row["slide"]): row for row in context.get("slides", [])}
    decision_slides = {int(row["slide"]): row for row in decisions.get("slides", [])}
    if set(context_slides) != set(decision_slides):
        raise ValueError("Alignment decision slide set differs from prepared context")

    final_slides = []
    for page in sorted(context_slides):
        context_phrases = {
            (row["event_id"], int(row["phrase_index"])): row
            for row in context_slides[page].get("phrases", [])
        }
        decision_phrases = {}
        for row in decision_slides[page].get("phrases", []):
            key = (str(row.get("event_id", "")), int(row.get("phrase_index", -1)))
            if key in decision_phrases:
                raise ValueError(f"Slide {page}: duplicate phrase decision {key}")
            decision_phrases[key] = row
        if set(context_phrases) != set(decision_phrases):
            raise ValueError(f"Slide {page}: every measured phrase must be decided exactly once")

        region_ids = {
            region["region_id"] for region in context_slides[page].get("regions", [])
        }
        phrases = []
        for key, context_phrase in context_phrases.items():
            decision = decision_phrases[key]
            if decision.get("phrase_text") != context_phrase["phrase_text"]:
                raise ValueError(f"Slide {page}: phrase text changed for {key}")
            status = decision.get("status")
            if status not in ("matched", "review_required", "unmatched"):
                raise ValueError(f"Slide {page}: invalid mapping status")
            targets = decision.get("region_ids", [])
            if not isinstance(targets, list) or len(targets) != len(set(targets)):
                raise ValueError(f"Slide {page}: region_ids must be unique")
            if not set(targets) <= region_ids:
                raise ValueError(f"Slide {page}: decision references an unknown region")
            if status == "unmatched" and targets:
                raise ValueError(f"Slide {page}: unmatched phrase cannot have focus targets")
            if status == "matched" and not targets:
                raise ValueError(f"Slide {page}: matched phrase must have at least one target")
            row = dict(decision)
            row["event_id"] = key[0]
            row["phrase_index"] = key[1]
            phrases.append(row)
        final_slides.append({"slide": page, "phrases": phrases})

    decision_payload = {
        "schema_version": "2.4.1",
        "context_id": context["context_id"],
        "slides": final_slides,
    }
    return {
        "schema_version": "2.4.1",
        "context_id": context["context_id"],
        "decisions_sha256": canonical_digest(decision_payload),
        "region_manifest_sha256": context["region_manifest_sha256"],
        "narration_sha256": context["narration_sha256"],
        "timing_sha256": context["timing_sha256"],
        "audio_sha256": context["audio_sha256"],
        "slides": final_slides,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    context = json.loads(Path(args.context).read_text(encoding="utf-8-sig"))
    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8-sig"))
    plan = finalize_plan(context, decisions)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Finalized source-bound alignment plan: {output}")


if __name__ == "__main__":
    main()

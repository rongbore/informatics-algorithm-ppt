"""Extract source-grounded slide regions from a PowerPoint deck.

Native PowerPoint text/table geometry is authoritative. Image-only visual regions
may be added from a separately generated, slide-image-hash-bound vision plan.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

try:
    from pptx import Presentation
except ImportError as exc:
    raise RuntimeError("Install python-pptx from requirements-v2.4.txt") from exc


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_text(value):
    return " ".join(str(value or "").replace("\x0b", "\n").split()).strip()


def bbox_normalized(left, top, width, height, slide_width, slide_height):
    values = [left, top, width, height, slide_width, slide_height]
    if not all(isinstance(x, (int, float)) and math.isfinite(float(x)) for x in values):
        raise ValueError("Slide geometry contains non-finite values")
    if slide_width <= 0 or slide_height <= 0 or width <= 0 or height <= 0:
        raise ValueError("Slide or shape geometry is non-positive")
    x, y = left / slide_width, top / slide_height
    w, h = width / slide_width, height / slide_height
    if x < -1e-6 or y < -1e-6 or x + w > 1.00001 or y + h > 1.00001:
        raise ValueError("Shape lies outside slide bounds")
    return [round(max(0.0, x), 7), round(max(0.0, y), 7),
            round(min(w, 1.0 - max(0.0, x)), 7),
            round(min(h, 1.0 - max(0.0, y)), 7)]



def infer_kind(text):
    value = clean_text(text)
    if not value:
        return "knowledge"
    code_patterns = (
        r"#include\s*<", r"\busing\s+namespace\b", r"\bint\s+main\s*\(",
        r"\b(?:cout|cin|printf|scanf)\b", r"\b(?:for|while|if|return)\s*[\(;]",
        r"\bvector\s*<", r"[{};]",
    )
    if sum(bool(__import__("re").search(pattern, value)) for pattern in code_patterns) >= 2:
        return "code"
    if __import__("re").search(r"(?:dp|f|g)\s*\[|状态转移|递推|拓扑序|邻接表|树形DP|区间查询", value, __import__("re").I):
        return "algorithm"
    return "knowledge"

def shape_type_name(shape):
    value = getattr(shape, "shape_type", None)
    return getattr(value, "name", str(value))


def add_region(regions, slide_number, region_id, shape_id, name, shape_type,
               text, bbox, source="pptx_native", mapping_eligible=True,
               geometry_status="source_verified", extra=None):
    row = {
        "region_id": region_id,
        "slide": slide_number,
        "shape_id": shape_id,
        "shape_name": name,
        "shape_type": shape_type,
        "kind": "knowledge",
        "label": name or region_id,
        "text": clean_text(text),
        "bbox": bbox,
        "geometry_source": source,
        "geometry_status": geometry_status,
        "mapping_eligible": bool(mapping_eligible),
    }
    if extra:
        row.update(extra)
    regions.append(row)


def extract_regions(pptx_path, slides_dir=None, vision_plan_path=None):
    pptx_path = Path(pptx_path)
    if not pptx_path.is_file():
        raise FileNotFoundError(pptx_path)
    deck_hash = sha256_file(pptx_path)
    prs = Presentation(str(pptx_path))
    slide_width, slide_height = int(prs.slide_width), int(prs.slide_height)
    slides = []
    image_hashes = {}

    for slide_number, slide in enumerate(prs.slides, 1):
        regions = []
        image_name = f"slide_{slide_number:03d}.png"
        image_path = Path(slides_dir) / image_name if slides_dir else None
        image_hash = sha256_file(image_path) if image_path and image_path.is_file() else None
        if image_hash:
            image_hashes[str(slide_number)] = image_hash

        for shape in slide.shapes:
            shape_id = int(shape.shape_id)
            name = str(getattr(shape, "name", "") or "")
            shape_type = shape_type_name(shape)
            bbox = bbox_normalized(
                int(shape.left), int(shape.top), int(shape.width), int(shape.height),
                slide_width, slide_height
            )

            if getattr(shape, "has_table", False):
                table = shape.table
                y = int(shape.top)
                for row_index, row in enumerate(table.rows):
                    x = int(shape.left)
                    for col_index, cell in enumerate(row.cells):
                        cell_bbox = bbox_normalized(
                            x, y, int(table.columns[col_index].width), int(row.height),
                            slide_width, slide_height
                        )
                        cell_text = clean_text(cell.text)
                        if cell_text:
                            region_id = f"s{slide_number:03d}_sh{shape_id}_r{row_index}_c{col_index}"
                            add_region(
                                regions, slide_number, region_id, shape_id, name,
                                "TABLE_CELL", cell_text, cell_bbox,
                                extra={"row_index": row_index, "column_index": col_index}
                            )
                            regions[-1]["kind"] = infer_kind(cell_text)
                        x += int(table.columns[col_index].width)
                    y += int(row.height)
                continue

            text = clean_text(getattr(shape, "text", "")) if getattr(shape, "has_text_frame", False) else ""
            if text:
                add_region(
                    regions, slide_number, f"s{slide_number:03d}_sh{shape_id}",
                    shape_id, name, shape_type, text, bbox
                )
                regions[-1]["kind"] = infer_kind(text)
            else:
                # Preserve geometry for diagrams/images. A model must inspect the
                # rendered slide and create a hash-bound visual-region proposal.
                add_region(
                    regions, slide_number, f"s{slide_number:03d}_sh{shape_id}",
                    shape_id, name, shape_type, "", bbox,
                    mapping_eligible=False,
                    geometry_status="visual_review_required",
                    extra={"visual_description": ""}
                )

        slides.append({
            "slide": slide_number,
            "slide_image": image_name if image_hash else None,
            "slide_image_sha256": image_hash,
            "regions": regions,
        })

    manifest = {
        "schema_version": "2.4.1",
        "source_pptx_name": pptx_path.name,
        "source_pptx_sha256": deck_hash,
        "slide_size_emu": {"width": slide_width, "height": slide_height},
        "slide_count": len(slides),
        "slide_image_sha256": image_hashes,
        "slides": slides,
    }

    if vision_plan_path:
        vision = json.loads(Path(vision_plan_path).read_text(encoding="utf-8-sig"))
        if vision.get("source_pptx_sha256") != deck_hash:
            raise ValueError("Vision plan belongs to a different PPTX source")
        slide_index = {int(row["slide"]): row for row in slides}
        seen = {
            region["region_id"]
            for row in slides
            for region in row["regions"]
        }
        for proposal_slide in vision.get("slides", []):
            number = int(proposal_slide["slide"])
            if number not in slide_index:
                raise ValueError(f"Vision plan references unknown slide {number}")
            actual_hash = slide_index[number]["slide_image_sha256"]
            if not actual_hash or proposal_slide.get("slide_image_sha256") != actual_hash:
                raise ValueError(f"Slide {number}: vision proposal image hash mismatch")
            for proposal in proposal_slide.get("regions", []):
                region_id = str(proposal.get("region_id", "")).strip()
                if not region_id or region_id in seen:
                    raise ValueError(f"Slide {number}: missing or duplicate vision region ID")
                seen.add(region_id)
                bbox = proposal.get("bbox")
                if not isinstance(bbox, list) or len(bbox) != 4:
                    raise ValueError(f"Slide {number}: invalid vision bbox")
                x, y, w, h = [float(value) for value in bbox]
                if not all(math.isfinite(value) for value in (x, y, w, h)):
                    raise ValueError(f"Slide {number}: non-finite vision bbox")
                if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1.00001 or y + h > 1.00001:
                    raise ValueError(f"Slide {number}: vision bbox outside slide")
                confidence = float(proposal.get("confidence", 0))
                verification = proposal.get("verification", {})
                confirmed = (
                    confidence >= 0.90
                    and verification.get("status") == "confirmed"
                    and bool(str(verification.get("reviewer_pass", "")).strip())
                )
                add_region(
                    slide_index[number]["regions"], number, region_id, None,
                    str(proposal.get("label", region_id)), "VISION_REGION",
                    str(proposal.get("visual_description", "")),
                    [round(x, 7), round(y, 7), round(w, 7), round(h, 7)],
                    source="vision_model",
                    mapping_eligible=confirmed,
                    geometry_status="vision_confirmed" if confirmed else "vision_review_required",
                    extra={
                        "visual_description": clean_text(proposal.get("visual_description", "")),
                        "confidence": confidence,
                        "verification": verification,
                    },
                )
                slide_index[number]["regions"][-1]["kind"] = proposal.get("kind", "knowledge")

    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--slides-dir")
    parser.add_argument("--vision-plan")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = extract_regions(args.pptx, args.slides_dir, args.vision_plan)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {sum(len(x['regions']) for x in manifest['slides'])} regions from {manifest['slide_count']} slides")
    print(f"Manifest: {output}")


if __name__ == "__main__":
    main()

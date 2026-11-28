"""Tests for PPTX geometry extraction and image-hash-bound vision regions."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import extract_slide_regions_v2_4 as extractor


class SlideRegionExtractionTests(unittest.TestCase):
    def make_deck(self, path):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        box.text = "dp[i] = dp[i-1] + a[i]"
        table = slide.shapes.add_table(
            1, 2, Inches(1), Inches(3), Inches(4), Inches(1)
        ).table
        table.cell(0, 0).text = "左区间"
        table.cell(0, 1).text = "右区间"
        prs.save(path)
        return box.shape_id

    def test_extracts_text_and_table_cells_with_normalized_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            pptx = Path(directory) / "lesson.pptx"
            shape_id = self.make_deck(pptx)
            manifest = extractor.extract_regions(pptx)
            self.assertEqual(manifest["schema_version"], "2.4.1")
            regions = manifest["slides"][0]["regions"]
            text_region = next(x for x in regions if x["shape_id"] == shape_id)
            self.assertEqual(text_region["text"], "dp[i] = dp[i-1] + a[i]")
            self.assertAlmostEqual(text_region["bbox"][0], 1 / 13.333333, places=3)
            cells = [x for x in regions if x["shape_type"] == "TABLE_CELL"]
            self.assertEqual(len(cells), 2)
            self.assertEqual(cells[0]["text"], "左区间")
            self.assertTrue(all(x["mapping_eligible"] for x in cells))

    def test_vision_regions_require_matching_slide_hash_and_second_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pptx = root / "lesson.pptx"
            self.make_deck(pptx)
            slides_dir = root / "slides"
            slides_dir.mkdir()
            image = slides_dir / "slide_001.png"
            image.write_bytes(b"fake-slide-image-for-hash")
            deck_hash = extractor.sha256_file(pptx)
            image_hash = extractor.sha256_file(image)
            vision_path = root / "vision.json"
            vision_path.write_text(json.dumps({
                "source_pptx_sha256": deck_hash,
                "slides": [{
                    "slide": 1,
                    "slide_image_sha256": image_hash,
                    "regions": [{
                        "region_id": "s001_vision_01",
                        "bbox": [0.5, 0.5, 0.2, 0.2],
                        "kind": "algorithm",
                        "label": "图示步骤",
                        "visual_description": "图中箭头表示状态转移",
                        "confidence": 0.96,
                        "verification": {
                            "status": "confirmed",
                            "reviewer_pass": "independent-vision-review",
                        },
                    }],
                }],
            }, ensure_ascii=False), encoding="utf-8")
            manifest = extractor.extract_regions(pptx, slides_dir, vision_path)
            vision_region = next(
                x for x in manifest["slides"][0]["regions"]
                if x["region_id"] == "s001_vision_01"
            )
            self.assertTrue(vision_region["mapping_eligible"])
            self.assertEqual(vision_region["geometry_status"], "vision_confirmed")

    def test_stale_vision_image_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pptx = root / "lesson.pptx"
            self.make_deck(pptx)
            slides_dir = root / "slides"
            slides_dir.mkdir()
            (slides_dir / "slide_001.png").write_bytes(b"slide image")
            vision_path = root / "vision.json"
            vision_path.write_text(json.dumps({
                "source_pptx_sha256": extractor.sha256_file(pptx),
                "slides": [{
                    "slide": 1, "slide_image_sha256": "stale", "regions": [],
                }],
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                extractor.extract_regions(pptx, slides_dir, vision_path)

    def test_bbox_outside_slide_is_rejected(self):
        with self.assertRaises(ValueError):
            extractor.bbox_normalized(1000, 0, 100, 100, 1000, 1000)


if __name__ == "__main__":
    unittest.main()

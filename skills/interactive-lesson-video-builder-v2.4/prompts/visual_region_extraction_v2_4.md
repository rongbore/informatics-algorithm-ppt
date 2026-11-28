# V2.4.1 Visual Region Extraction Prompt

You are analyzing an algorithm-teaching slide deck. Use the rendered slide PNGs and the PPTX-native region manifest.

## Goal
Find visual regions that are not reliably represented by native PowerPoint text shapes: diagrams, graph nodes and edges, array cells, tree nodes, arrows, code blocks rendered as images, and other visual teaching objects.

## Non-negotiable constraints
- Never invent text, data, node labels, formulas, edges, or algorithm states.
- Every region must belong to the exact slide image supplied.
- Use normalized coordinates [x, y, width, height] relative to the full slide image, each in [0,1].
- Do not create a region that duplicates a native PPTX region unless the native geometry is demonstrably wrong.
- Do not use a single large bbox for unrelated visual objects.
- Preserve code and formula punctuation exactly when quoting it.
- If the region boundary is ambiguous, set confidence below 0.90 and mark it for review.
- A second independent visual pass must check the proposed bbox against the original slide image.

## Output
Return JSON only:
{
  "source_pptx_sha256": "<exact hash from manifest>",
  "slides": [{
    "slide": 1,
    "slide_image_sha256": "<exact hash from manifest>",
    "regions": [{
      "region_id": "s001_vision_01",
      "bbox": [0.1, 0.2, 0.3, 0.2],
      "kind": "knowledge|code|algorithm",
      "label": "short name",
      "visual_description": "literal, source-grounded description",
      "confidence": 0.95,
      "verification": {
        "status": "confirmed|needs_review",
        "reviewer_pass": "independent-vision-pass-1"
      }
    }]
  }]
}

Only use confirmed when the second pass agrees on both the region identity and all four bbox coordinates within 0.01 normalized units. Otherwise use needs_review.

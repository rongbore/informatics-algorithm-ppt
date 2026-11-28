---
name: interactive-lesson-video-builder-v2.4
version: 2.4.0-alpha.3
description: Build source-grounded algorithm teaching videos with verified phrase timing, duplicate-safe focus overlays, teaching-event compilation, and human-reviewed media QA.
---

# Interactive Lesson Video Builder V2.4

## Version boundary
V2.4 is developed in its own directory. Do not overwrite V2.2 or V2.3 scripts, configs, outputs, caches, or production artifacts. V2.4 alpha builds are not production-approved by default.

## Core pipeline
1. Inspect the supplied PPT/PPTX, slide text, speaker notes, diagrams, tables, and code.
2. Preserve source wording, numeric examples, code, formulas, slide order, and teacher intent.
3. Compile narration and teaching plans only when their source fingerprints match.
4. Generate phrase-level TTS timing from measured audio segments; do not claim word-level or phoneme-level alignment.
5. Align focus overlays to reviewed event anchors or a unique full-text phrase match. Never estimate focus time from slide-duration ratios.
6. Render subtitles from measured phrase boundaries and suppress them during intentional thinking silence.
7. Render only source-verified geometry. Exact duplicate region definitions must share one rendered region; distinct shape IDs remain independent.
8. Run static checks, unit tests, media-stream checks, and a five-slide pilot.
9. Require human review of instructional correctness, subtitle overlap, code legibility, narration pacing, and highlight placement.

## Focus alignment contract
- A region must have a valid normalized bbox, confidence above threshold, and geometry_status=matched.
- Anchor plans must match the exact timeline and narration SHA-256 digests.
- Anchored evidence must refer to existing narration events and preserve exact source text.
- At most one rendered focus region owns a given spoken phrase.
- Duplicate region definitions with identical shape_index, kind, normalized target_text, and bbox are merged into the first reviewed region; labels do not create additional geometry.
- Invalid, ambiguous, stale, or unverified regions remain unmatched. No ratio fallback is allowed.

## Algorithm animation honesty
A focus rectangle is not a data-structure simulation. Fenwick tree, segment tree, DFS, DP, graph traversal, and state transitions may be animated only from explicit, validated state sequences. Never infer state changes from narration alone.

## Quality gates
- V2.2 and V2.3 remain unchanged.
- Manual review is mandatory; QA must report manual_review_required=true and auto_approved=false.
- A successful FFmpeg process is not proof of teaching correctness or visual alignment.
- Full 80-slide rendering is blocked until the pilot is manually approved.

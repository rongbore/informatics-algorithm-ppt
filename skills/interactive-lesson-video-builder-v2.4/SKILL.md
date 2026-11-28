---
name: interactive-lesson-video-builder-v2.4
version: 2.4.1-alpha.4
description: Automatically align PowerPoint visual regions, event-driven narration, measured phrase timing, subtitles, and focus overlays with source fingerprints and fail-closed QA.
---

# Interactive Lesson Video Builder V2.4.1

## Purpose
Turn an existing PPTX lesson into a narrated, synchronized algorithm-teaching video. Automatically connect slide regions, spoken phrases, and measured audio time intervals. Preserve the original lesson's terminology, formulas, examples, C++ code, slide order, and teaching intent.

V2.2 and V2.3 assets remain available for compatibility. V2.4 is the active pipeline; do not overwrite earlier versioned files or production outputs.

## Required three-way alignment
Every rendered focus overlay must be backed by all three:
1. A source region ID and normalized bbox extracted from the exact PPTX or confirmed against the exact rendered slide image.
2. A narration event ID and phrase index whose text exactly matches the measured TTS timing record.
3. A start/end interval measured from the generated audio file by FFprobe.

Never infer focus time from slide-duration ratios, character counts, or guessed timestamps.

## Pipeline
1. Extract native text boxes and table-cell geometry from the original PPTX with scripts/extract_slide_regions_v2_4.py.
2. Associate the matching rendered slide PNGs and record their SHA-256 hashes.
3. For diagrams, graph nodes/edges, image-only formulas, and other non-text regions, use prompts/visual_region_extraction_v2_4.md. Re-run extraction with the image-hash-bound vision plan. Regions without a confirmed second visual pass remain ineligible for automatic focus.
4. Create narration events using stable, unique event IDs. Preserve source phrases; do not add unsupported facts or examples.
5. Generate TTS and measured phrase timings with scripts/generate_audio_v2_4.py. Each phrase timing record includes event_id, phrase_index, exact phrase text, start, and end.
6. Use prompts/alignment_planner_v2_4.md to map each measured phrase to zero, one, or multiple region IDs. Use prompts/alignment_verifier_v2_4.md as a separate second pass.
7. Compile the plan with scripts/compile_alignment_v2_4.py. It checks PPTX/region, narration, timing, and audio fingerprints; slide/event/phrase identity; source evidence quotes; normalized geometry; confidence; verification status; and interval integrity.
8. Render only the compiled report with scripts/render_lesson_v2_4.py. One phrase may map to several distinct regions; several phrases may map to one region. Duplicate physical geometry is consolidated.
9. Run scripts/validate_full_video_v2_4.py against the final MP4, all per-slide audio, timing JSON, and SRT files.
10. Render a five-slide pilot first. Inspect the actual video and audio before authorizing a full-course render.

## Automatic matching policy
- Native PowerPoint text and table-cell geometry is preferred over inferred coordinates.
- Vision-derived geometry is accepted only when tied to the exact slide image hash, confidence is at least 0.90, and a separate visual verification pass confirms the region and bbox.
- A phrase is automatically matched only when confidence is at least 0.90, a separate verification pass confirms the relationship, all region IDs exist on the same slide, and evidence quotes are exact source substrings.
- Low-confidence, ambiguous, stale, unsupported, or geometrically unverified mappings are withheld from rendering and listed as review_required or unmatched.
- A short transition sentence may correctly have no visual target. Do not force a highlight for every phrase.
- A single spoken phrase may point to multiple distinct visual regions when the phrase explicitly compares or operates on them.
- Exact duplicate region geometry is rendered once, with aliases recorded for audit.
- Any source hash mismatch invalidates the plan and requires regeneration.

## Audio and subtitle timing
- TTS is generated per phrase and actual segment durations are measured with FFprobe.
- Timings are phrase-level, not word-level or phoneme-level forced alignment.
- Subtitles are derived from phrase timing and hidden during intentional thinking pauses.
- Internal subtitle line splitting may distribute a phrase interval for readability; it must never be described as word-level synchronization.
- Thinking pauses and countdowns use explicit pause events and the configured D1-D5 policy.

## Algorithm animation
A focus box is not an algorithm simulation. Fenwick tree, segment tree, DFS, BFS, graph, DP, and state transitions may be animated only from explicit, validated state sequences with their own event IDs and geometry. Never infer a data-structure state transition from narration alone.

## Quality gates
- V2.2 and V2.3 assets remain preserved and are not overwritten by V2.4.
- No ratio-based focus timing fallback.
- No automatic rendering from stale or mismatched hashes.
- No automatic focus from ambiguous geometry or unverified visual proposals.
- QA always reports manual_review_required=true and auto_approved=false.
- A successful FFmpeg run or a passing machine QA report does not prove instructional correctness.
- Full-course rendering remains gated on a manually reviewed five-slide pilot.

See README.md for installation and execution commands.

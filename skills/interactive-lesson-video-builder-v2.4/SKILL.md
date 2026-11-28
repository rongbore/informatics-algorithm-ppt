---
name: interactive-lesson-video-builder.v2.4
version: 2.4.1-alpha.5
description: Source-audited engine for PowerPoint visual regions, phrase-level narration, measured audio timing, compiled alignment, rendering and media QA.
---

# Interactive Lesson Video Builder V2.4 Engine

V2.4 is the execution engine used by the active V2.5 agent-orchestrated Skill. V2.2 and V2.3 remain preserved for compatibility.

## Three-way alignment contract

Every rendered focus overlay must be backed by all three:
1. Visual source: exact PPTX SHA-256, slide-image SHA-256, slide number, stable region ID, normalized bbox, geometry source and verification status.
2. Speech source: narration event ID, phrase index, exact phrase text and TTS audio SHA-256.
3. Time source: actual measured start/end interval from the generated audio, timing JSON SHA-256 and FFprobe-probed duration.

All identifiers and fingerprints must agree. The renderer consumes only the compiled alignment report. Subtitle cues and focus overlays derive from the same measured phrase interval.

## Engine workflow

1. Export slide previews from PowerPoint using scripts/render_slides_v2_4.ps1.
2. Extract native text boxes and table-cell geometry using scripts/extract_slide_regions_v2_4.py.
3. Add image-only visual regions only from hash-bound vision proposals with a distinct verification pass.
4. Create narration events from source slide content and speaker notes using prompts/lesson_narration_compiler_v2_4.md. The Skill agent, not the user, authors this JSON unless the user explicitly supplies approved narration.
5. Generate per-phrase TTS and measured timings using scripts/generate_audio_v2_4.py.
6. Prepare exact, machine-hashed context using scripts/prepare_alignment_inputs_v2_4.py.
7. Run prompts/alignment_planner_v2_4.md, then independently run prompts/alignment_verifier_v2_4.md.
8. Finalize and compile with scripts/finalize_alignment_plan_v2_4.py and scripts/compile_alignment_v2_4.py.
9. Render only the compiled report with scripts/render_lesson_v2_4.py.
10. Validate media using scripts/validate_full_video_v2_4.py.

See README.md for commands and prompts. The Skill agent should execute these steps in sequence and should not make the user manually author intermediate JSON or copy prompts between stages.

## Matching and timing policy

- Prefer native PPTX geometry; bind all slide previews to image hashes.
- Vision geometry needs confidence >= 0.90 and independent visual confirmation.
- Phrase mapping needs confidence >= 0.90, independent verification and exact evidence substrings.
- Low-confidence, ambiguous, stale or unverified mappings are review_required/unmatched and are not rendered.
- Transition phrases may be unmatched; comparison phrases may target multiple distinct regions.
- Timing is phrase-level, not word-level or phoneme-level forced alignment.
- Never infer time from slide duration, character count, reading speed or guessed timestamps.
- Thinking pauses are explicit timeline intervals; subtitles must not overlap them.

## QA and release gates

- Recompute and compare slide-image, audio and timing-file SHA-256 values again immediately before rendering; refuse stale or mixed-source inputs.
- Check all source, region, narration, timing and audio fingerprints.
- Check interval coverage, non-overlap, geometry bounds, focus ownership, subtitles, stream metadata and full media decode.
- Machine QA must report manual_review_required=true and auto_approved=false.
- Render a five-slide pilot and require human review before full-course rendering.
- Never describe a successful machine QA run as proof of instructional correctness or final approval.

Algorithm state animation requires a separate validated state trace. A focus rectangle is not a data-structure simulation.

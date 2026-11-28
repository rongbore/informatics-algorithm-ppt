---
name: interactive-lesson-video-builder.v2.4
version: 2.4.1-alpha.6
description: Source-audited media engine for PowerPoint visual regions, phrase-level narration, measured timing, rendering and QA; orchestrated by V2.6 single-upload workflow.
---

# Interactive Lesson Video Builder V2.4 Engine

V2.4 is the deterministic execution engine used by the active V2.6 Skill. V2.2 and V2.3 remain preserved for compatibility.

## Engine workflow

1. Export every slide preview from PowerPoint using `scripts/render_slides_v2_4.ps1`.
2. Extract native text boxes and table-cell geometry using `scripts/extract_slide_regions_v2_4.py`.
3. Add image-only visual regions only from hash-bound vision proposals with an independent verification pass.
4. The Skill agent authors narration events and storyboard from the PPTX and speaker notes; the user does not prepare intermediate JSON.
5. Generate per-phrase TTS and measured timings using `scripts/generate_audio_v2_4.py`.
6. Prepare exact machine-hashed context using `scripts/prepare_alignment_inputs_v2_4.py`.
7. Run the alignment planner and independent verifier as separate passes.
8. Finalize and compile using `scripts/finalize_alignment_plan_v2_4.py` and `scripts/compile_alignment_v2_4.py`.
9. Render using `scripts/render_lesson_v2_4.py` from the compiled report only.
10. Validate media using `scripts/validate_full_video_v2_4.py`.

## Three-way alignment contract

Every rendered focus overlay must link:
- Visual: exact PPTX and slide-image hashes, slide number, stable region ID, normalized bbox, geometry source and verification status.
- Speech: narration event ID, phrase index, exact phrase and TTS audio hash.
- Time: actual measured start/end interval, timing JSON hash and FFprobe-probed duration.

Subtitles and focus overlays derive from the same measured phrase interval. All identifiers and hashes must agree.

## Automatic full-course behavior

- Generate a representative pilot internally using slides selected from the actual deck, not fixed slide numbers.
- Run deterministic pilot checks automatically; do not pause for user approval before the full draft render.
- If deterministic pilot checks pass, render every slide automatically.
- A low-confidence or ambiguous focus mapping is omitted while the original slide and narration remain in the full video; log it for review.
- A failed slide render/TTS operation is retried. If still unsuccessful, mark the package incomplete and do not claim a full video.
- Human semantic review remains required after generation; it is a quality sign-off, not a prerequisite to create the draft.

## Matching, timing and animation policy

- Native PPTX geometry is preferred; all slide previews are hash-bound.
- Vision geometry and phrase mapping require confidence >= 0.90 and independent verification.
- Low-confidence, ambiguous, stale or unverified mappings are not rendered.
- Timing is phrase-level, not word-level or phoneme-level forced alignment.
- Never infer time from slide duration, character count, reading speed or guessed timestamps.
- Algorithm-state animation requires a source-grounded state trace with validated initial state, every operation, before/after state, invariants and final state. A focus rectangle is not a data-structure simulation.
- If a valid state trace cannot be built, retain the original slide and narration; do not fabricate animation.

## QA and release

- Recompute slide-image, audio and timing-file SHA-256 values immediately before rendering.
- Check source fingerprints, phrase coverage, interval overlap, geometry bounds, subtitle intervals, focus ownership, stream metadata, full decode and audio/video duration alignment.
- Always report `manual_review_required=true` and `auto_approved=false`. Machine QA does not certify teaching correctness.

# Interactive Lesson Video Builder V2.4.1 — Alpha.4

V2.4.1 introduces an automatic, source-audited pipeline that connects PPTX visual regions, spoken narration phrases, and measured audio timestamps. V2.2 and V2.3 remain preserved in the repository for compatibility.

## What is automated

- Extract native PowerPoint text-box and table-cell geometry from the original PPTX.
- Bind rendered slide previews and vision-derived regions to SHA-256 image fingerprints.
- Generate per-phrase TTS audio and measured start/end times.
- Use an AI planner plus a separate verification pass to map each phrase to zero, one, or multiple visual region IDs.
- Compile the mapping only when source hashes, IDs, evidence quotes, geometry, confidence, and timing all validate.
- Render focus overlays from the compiled alignment report rather than manually authored ratio timelines.
- Consolidate duplicate geometry and allow one phrase to highlight multiple distinct regions.
- Validate final MP4 streams, duration, per-slide audio, timing JSON, SRT cues, and thinking-pause suppression.

Ambiguous or low-confidence matches are withheld from automatic rendering and listed for review. The pipeline does not claim word-level or phoneme-level forced alignment.

## Requirements

- Python 3.10+
- FFmpeg and FFprobe on PATH
- PowerPoint slide previews as PNG files named slide_001.png, slide_002.png, etc.
- edge-tts and python-pptx from the requirements file

Install:

    python -m pip install -r requirements-v2.4.txt

## Recommended directory layout

    input/
      lesson.pptx
    rendered/slides/
      slide_001.png
      slide_002.png
    build/v2_4/
    audio_v2_4/
      timings/
    subtitles_v2_4/
    video/
    qa_v2_4/

## Step 1 — Extract native PPTX regions

    python scripts/extract_slide_regions_v2_4.py --pptx input/lesson.pptx --slides-dir rendered/slides --output build/v2_4/regions_native.json

The extractor records shape IDs, table-cell IDs, exact source text, normalized bounding boxes, PPTX SHA-256, and slide-image hashes. Unsupported groups and image-only regions are not automatically eligible for focus.

## Step 2 — Add image-only visual regions when needed

Use prompts/visual_region_extraction_v2_4.md with the rendered slide previews and regions_native.json. The model returns a vision plan containing the exact PPTX hash and each slide-image hash.

    python scripts/extract_slide_regions_v2_4.py --pptx input/lesson.pptx --slides-dir rendered/slides --vision-plan build/v2_4/vision_regions.json --output build/v2_4/regions.json

A vision region is eligible only when confidence is at least 0.90, the slide image hash matches, and the independent visual pass confirms its identity and bbox.

## Step 3 — Generate narration audio and measured phrase timing

Prepare build/v2_4/narration_events_v2_4.json with unique event IDs and exact teacher-approved narration text.

    python scripts/generate_audio_v2_4.py --input build/v2_4/narration_events_v2_4.json --output audio_v2_4 --timings-output audio_v2_4/timings --config config/video_ux_v2_4.json

For all slides, add --all-slides after the pilot has been approved.

## Step 4 — Prepare a machine-hashed alignment context

Do not ask the AI model to calculate cryptographic hashes. Generate a context bundle that contains the exact slide regions, measured phrases, and machine-computed source fingerprints:

    python scripts/prepare_alignment_inputs_v2_4.py --regions build/v2_4/regions.json --narration build/v2_4/narration_events_v2_4.json --timings-dir audio_v2_4/timings --audio-dir audio_v2_4 --output build/v2_4/alignment_context.json

## Step 5 — Plan and independently verify visual/speech alignment

Use prompts/alignment_planner_v2_4.md with alignment_context.json and the matching slide previews. The planner returns alignment_decisions_draft.json. Then use prompts/alignment_verifier_v2_4.md as a separate second pass and save alignment_decisions_verified.json.

Finalize the decisions by copying the hashes from the prepared context and checking phrase coverage:

    python scripts/finalize_alignment_plan_v2_4.py --context build/v2_4/alignment_context.json --decisions build/v2_4/alignment_decisions_verified.json --output build/v2_4/alignment_plan.json

Every measured speech phrase must be represented exactly once in the plan. Use matched, review_required, or unmatched. Do not force a visual target for transition phrases.

## Step 6 — Compile and validate the three-way mapping

    python scripts/compile_alignment_v2_4.py --regions build/v2_4/regions.json --narration build/v2_4/narration_events_v2_4.json --alignment-plan build/v2_4/alignment_plan.json --timings-dir audio_v2_4/timings --audio-dir audio_v2_4 --output build/v2_4/compiled_alignment.json

This compiler verifies:
- exact PPTX/region and narration fingerprints;
- timing JSON and audio file fingerprints;
- slide IDs, event IDs, phrase indexes, and exact phrase text;
- source-grounded quotes on both the visual and spoken sides;
- normalized bbox bounds and region verification status;
- non-overlapping measured speech/pause timeline;
- confidence threshold and independent verification marker.

A single phrase can highlight several distinct regions. Duplicate physical regions are consolidated. Unmatched and review-required phrases are recorded but not drawn.

## Step 7 — Render from the compiled alignment

    python scripts/render_lesson_v2_4.py --slides rendered/slides --audio audio_v2_4 --speech-timings audio_v2_4/timings --alignment-report build/v2_4/compiled_alignment.json --output video/v2_4_pilot.mp4 --qa qa_v2_4_pilot --ux-config config/video_ux_v2_4.json --subtitle-dir subtitles_v2_4_pilot --only-slides 1 20 40 60 80

The renderer uses source-normalized bboxes and the exact phrase intervals from the compiled report. It does not recalculate timing from slide duration or narration length.

## Step 8 — Validate the final media

    python scripts/validate_full_video_v2_4.py --video video/v2_4_pilot.mp4 --qa-report qa_v2_4_pilot/qa_report_v2_4_alpha4.json --audio-dir audio_v2_4 --timings-dir audio_v2_4/timings --subtitle-dir subtitles_v2_4_pilot --output qa_v2_4_pilot/final_validation.json

Machine QA checks media streams, resolution, duration, full decode, phrase timing, subtitles, thinking pauses, duplicate geometry, and focus interval consistency. It does not certify semantic correctness or legibility.

## Install to the Windows Skill directory

From PowerShell:

    powershell -ExecutionPolicy Bypass -File .\install_v2_4.ps1

The installer backs up the existing Skill directory before copying V2.4.1 files to D:\Codex\skills\interactive-lesson-video-builder.

## Release gate

- Run a five-slide pilot first.
- Manually inspect code readability, formula/diagram focus boxes, subtitle line breaks, narration pacing, and actual frame timing.
- Only expand to the full deck after the pilot passes review.
- Keep manual_review_required=true and auto_approved=false.

# Interactive Lesson Video Builder V2.4 — Alpha.3

This is the isolated V2.4 development package. It does not replace the V2.3 Skill, its production outputs, or its caches.

## Included in this increment
- Phrase-level focus alignment with exact timeline/narration SHA-256 checks.
- Source-verified normalized bounding-box validation.
- Unique full-text matching or reviewed event anchors; no duration-ratio fallback.
- Duplicate region geometry consolidation so repeated labels cannot paint the same box twice.
- A V2.4 renderer using its own configuration and default output directories.
- Phrase-timed subtitles with suppression during intentional thinking pauses.
- Numeric-only countdown in the reserved subtitle band.
- Offline tests for focus alignment, duplicate geometry, timing helpers, and config integrity.

## Requirements
- Python 3.10+
- FFmpeg and FFprobe on PATH
- Source slide images named slide_001.png, slide_002.png, etc.
- Per-slide audio files and measured speech-timing JSON files
- Timeline, narration, and a matching reviewed anchor plan

The V2.4 focus engine and pure renderer helpers use only the Python standard library. Rendering requires FFmpeg/FFprobe.

## Run tests

From this directory:

    python -m compileall -q scripts tests
    python -m unittest discover -s tests -v

## Focus alignment CLI

    python scripts/align_focus_v2_4.py --timeline PATH --narration PATH --anchor-plan PATH --timings DIR --report PATH --slides 35

The renderer independently probes audio duration before alignment. The standalone audit CLI uses the duration recorded in the timing JSON and explicitly reports that it did not independently probe audio.

## Five-slide renderer pilot

    python scripts/render_lesson_v2_4_alpha3.py --slides PATH_TO_SLIDE_IMAGES --audio PATH_TO_AUDIO --speech-timings PATH_TO_TIMINGS --timeline PATH_TO_TIMELINE --narration PATH_TO_NARRATION --anchor-plan PATH_TO_ANCHOR_PLAN --output video/v2_4_pilot.mp4 --qa qa_v2_4_pilot --ux-config config/video_ux_v2_4.json --subtitle-dir subtitles_v2_4_pilot --only-slides 1 20 40 60 80

The renderer writes its QA report into the selected QA directory. Use V2.4-specific output paths; never point this command at V2.3 output or cache directories.

## Slide 35 duplicate-region finding

The supplied slide35-events.json contains two algorithm records with the same target_text, shape_index, and bbox, but different labels and overlapping ratio intervals. Those records describe one physical formula region. V2.4 consolidates exact duplicate geometry; it does not invent a second bbox for the numeric table. The table's highlight geometry must be extracted from the original PPTX and reviewed before it can be added as a separate region.

## Release status

Alpha.3 is a focused integration increment, not a full production release. The teaching-plan compiler, audio generation pipeline, full-video validation, and source archive integration still need to be completed and tested. Actual Edge TTS/FFmpeg rendering and frame-level visual review have not yet been completed. Human review remains mandatory.

# Interactive Lesson Video Builder V2.4 — Alpha.3

This is the isolated V2.4 development package. It does not replace the V2.3 Skill, its production outputs, or its caches.

## Included in this increment
- Event-driven TTS with measured phrase-level audio timing.
- Phrase-level focus alignment with exact timeline/narration SHA-256 checks.
- Source-verified normalized bounding-box validation.
- Unique full-text matching or reviewed event anchors; no duration-ratio fallback.
- Duplicate region geometry consolidation so repeated labels cannot paint the same box twice.
- A V2.4-only renderer and video UX config.
- Phrase-timed subtitles with suppression during intentional thinking pauses.
- Numeric-only countdown in the reserved subtitle band.
- Offline tests for audio planning, focus alignment, renderer timing helpers, and config integrity.

## Requirements
- Python 3.10+
- FFmpeg and FFprobe on PATH
- edge-tts installed in the active Python environment
- Source slide images named slide_001.png, slide_002.png, etc.
- V2.4 narration events, timeline, and reviewed anchor plan

Install TTS dependency:

    python -m pip install edge-tts

## Run tests

From this directory:

    python -m compileall -q scripts tests
    python -m unittest discover -s tests -v

## Generate audio and measured timing

Pilot slides (defaults to the five IDs in the V2.4 config):

    python scripts/generate_audio_v2_4.py --input build/narration_events_v2_4.json --output audio_v2_4 --timings-output audio_v2_4/timings --config config/video_ux_v2_4.json

Generate all slides only after the pilot is reviewed:

    python scripts/generate_audio_v2_4.py --input build/narration_events_v2_4.json --output audio_v2_4 --timings-output audio_v2_4/timings --config config/video_ux_v2_4.json --all-slides

The audio generator uses its own audio_v2_4/.cache directory. Do not point it to V2.3 audio or cache paths.

## Focus alignment CLI

    python scripts/align_focus_v2_4.py --timeline PATH --narration PATH --anchor-plan PATH --timings audio_v2_4/timings --report qa_v2_4/focus_report.json --slides 35

The renderer independently probes audio duration before alignment. The standalone audit CLI uses the duration recorded in the timing JSON and explicitly reports that it did not independently probe audio.

## Five-slide renderer pilot

    python scripts/render_lesson_v2_4_alpha3.py --slides PATH_TO_SLIDE_IMAGES --audio audio_v2_4 --speech-timings audio_v2_4/timings --timeline PATH_TO_TIMELINE --narration PATH_TO_NARRATION --anchor-plan PATH_TO_ANCHOR_PLAN --output video/v2_4_pilot.mp4 --qa qa_v2_4_pilot --ux-config config/video_ux_v2_4.json --subtitle-dir subtitles_v2_4_pilot --only-slides 1 20 40 60 80

The renderer writes its QA report into the selected QA directory. Use V2.4-specific output paths; never point this command at V2.3 output or cache directories.

## Full-video media QA

After rendering, validate the combined MP4, each source audio file, measured timing JSON, and generated SRT files:

    python scripts/validate_full_video_v2_4.py --video video/v2_4_pilot.mp4 --qa-report qa_v2_4_pilot/qa_report_v2_4_alpha3.json --audio-dir audio_v2_4 --timings-dir audio_v2_4/timings --subtitle-dir subtitles_v2_4_pilot --output qa_v2_4_pilot/final_validation.json

The validator checks the video/audio streams, resolution, total duration, complete media decode, per-slide audio/timing consistency, subtitle cue counts, and thinking-pause suppression. Use --skip-decode only when the full FFmpeg decode is intentionally deferred. A passing machine check is not a substitute for human visual review.

## Slide 35 duplicate-region finding

The supplied slide35-events.json contains two algorithm records with the same target_text, shape_index, and bbox, but different labels and overlapping ratio intervals. Those records describe one physical formula region. V2.4 consolidates exact duplicate geometry; it does not invent a second bbox for the numeric table. The table's highlight geometry must be extracted from the original PPTX and reviewed before it can be added as a separate region.

## Release status

Alpha.3 is a focused integration increment, not a full production release. The teaching-plan compiler, full-video validation, source archive integration, and actual Edge TTS/FFmpeg media render still need end-to-end validation. Human review remains mandatory.

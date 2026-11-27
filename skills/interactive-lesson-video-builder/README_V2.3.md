# Interactive Lesson Video Builder V2.3

## Changes
- Event-driven TTS reads slides[].events[] instead of flattening the slide into one text field.
- Thinking prompts create real silent audio intervals.
- Adaptive thinking time: D1 6s, D2 8s, D3 10s, D4 15s, D5 20s.
- Explicit knowledge-point pauses are 5s when knowledge_point_end=true.
- Slide-end pause defaults to 5s.
- Per-slide phrase timing JSON is generated from measured audio segments.
- Subtitles use phrase-level measured timestamps and are suppressed during thinking silence.
- Countdown is numeric-only in the reserved subtitle band; no central card.
- Highlight coordinates account for slide scaling and padding.
- QA reports technical checks and requires manual review.
- V2.2 scripts/config are not overwritten.

## Windows requirements
- Python 3.10+
- FFmpeg and FFprobe on PATH
- Existing project .venv
- edge-tts installed in that environment

Install dependency if needed:
powershell:
.\.venv\Scripts\python.exe -m pip install edge-tts

## Expected project layout
The Skill folder should contain .venv\Scripts\python.exe, scripts, config, narration events JSON, analysis\highlight_timeline.json and rendered\slides\slide_001.png etc.
Paths can be overridden in the pilot PowerShell script.

## Five-slide pilot
From the Skill root:
powershell -ExecutionPolicy Bypass -File .\scripts\run_v2_3_pilot.ps1

Override paths:
powershell -ExecutionPolicy Bypass -File .\scripts\run_v2_3_pilot.ps1 -Narration .\narration_events_v2_2.json -Timeline .\analysis\highlight_timeline.json -SlidesDir .\rendered\slides

## Full 80-slide audio
Only after the pilot is manually approved:
.\.venv\Scripts\python.exe scripts\generate_audio_v2_3.py --input .\narration_events_v2_2.json --output .\audio_v2_3 --timings-output .\audio_v2_3\timings --config .\config\video_ux_v2_3.json --all-slides

## Full render
.\.venv\Scripts\python.exe scripts\render_lesson_v2_3.py --slides .\rendered\slides --audio .\audio_v2_3 --speech-timings .\audio_v2_3\timings --timeline .\analysis\highlight_timeline.json --output .\video\v2_3_full_80slides.mp4 --qa .\qa_v2_3_full --ux-config .\config\video_ux_v2_3.json

## Known limits
- Subtitle timing is phrase-level, not word/phoneme forced alignment.
- TTS prosody depends on the selected voice; pacing cannot guarantee human-level emotional expression.
- Countdown is placed in the reserved bottom band; inspect actual font rendering and subtitle margins.
- Bboxes must be source-verified; the renderer corrects scale/padding but cannot infer exact geometry from text alone.
- Algorithm focus overlays are not full state simulation. True state animation needs verified state sequences and dedicated adapters.
- Automated QA cannot certify teaching correctness or all visual overlap. Human review is mandatory.

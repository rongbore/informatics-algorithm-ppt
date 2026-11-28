# Interactive Lesson Video Builder — V2.6 Single-Upload Full-Course Automation

V2.6 changes the user experience to **one PPTX upload → complete AI teaching-video draft**. The active Skill agent authors teaching content, narration, storyboard and alignment decisions; the V2.4.1 engine performs deterministic extraction, TTS timing, hash validation, rendering and media QA. V2.2/V2.3 compatibility assets remain preserved.

## User workflow

1. Upload one classroom `.pptx`.
2. Ask for an AI teaching video, or invoke this Skill.
3. The Skill infers language, learner level and a suitable teaching style from the deck. Default Chinese informatics lessons use energetic competition-coach narration.
4. The Skill generates the full deck automatically and returns the MP4 plus a ZIP of all editable production assets.

The user does not prepare slide images, narration JSON, region manifests, TTS audio, timing JSON, subtitles or command sequences.

## Automatic pipeline

1. Inspect source PPTX, notes, slide count, text, code, formulas, diagrams and exercises; hash the source.
2. Export every slide using PowerPoint COM on Windows and verify slide count/order/hash.
3. Extract native text/table geometry and add image-only regions only through hash-bound visual analysis and independent verification.
4. Author complete narration and stable event/phrase IDs from source content and speaker notes.
5. Generate storyboard and shot instructions; create algorithm-state animation only from an independently validated state trace.
6. Generate per-phrase neural TTS and measure actual durations with FFprobe.
7. Prepare machine-hashed alignment context; run planner and independent verifier; compile only exact verified visual/speech/time mappings.
8. Render a representative content-aware pilot internally, run deterministic checks, then automatically render the entire deck without waiting for user approval.
9. Render focus overlays and subtitles from the compiled alignment report only.
10. Run full media QA and package MP4, narration, storyboard, SRT, measured timeline, alignment audit and QA report.

Ambiguous focus matches are omitted, not guessed. The source slide and narration remain in the video. If a required slide cannot be rendered or narrated after bounded retries, the run is marked incomplete rather than falsely reported as complete.

## Prerequisites

- Windows with Microsoft PowerPoint installed for source-faithful PPTX slide export.
- Python 3.10+, FFmpeg and FFprobe on PATH.
- Install Python dependencies with `python -m pip install -r requirements-v2.4.txt`.
- Network access for configured Edge neural TTS.
- Sufficient local disk space for per-slide audio, previews and final MP4.

At startup, check these prerequisites. Never claim an output exists unless it was actually generated and validated. If a prerequisite is absent, report the exact blocker and remediation.

## Three-way alignment

Every focus event must link:
- visual source: PPTX hash, slide-image hash, slide, region ID, normalized bbox and verification status;
- speech source: narration event ID, phrase index, exact phrase and audio hash;
- time source: measured phrase start/end, timing JSON hash and FFprobe duration.

Subtitles and focus overlays derive from the same measured interval. No character-count timing, slide-duration ratios or guessed timestamps.

## Automatic pilot and human review

The five-slide pilot is an **internal automatic gate**, not a user-interaction gate. Select representative slides by content (opening, concept, code/formula, worked example and exercise/recap). If deterministic checks pass, render the complete course automatically.

Every delivery still reports `manual_review_required=true` and `auto_approved=false`: machine QA cannot certify pedagogical correctness, formula accuracy, code semantics, voice quality or visual legibility. This does not prevent generation of the full draft.

## Algorithm animation safeguards

For DFS/BFS, union-find, DP, trees and graphs, animation is allowed only when a source-grounded state trace contains initial state, every operation, before/after state, invariants and final state, and passes an independent validator. Otherwise retain the original slide with narration and verified focus; never invent state transitions.

## Output

- Full-course MP4 and merged SRT.
- Readable narration script (`narration_script.txt`) and narration event JSON.
- Measured speech/pause timeline (`measured_timeline.csv`).
- Storyboard JSON/CSV.
- Per-phrase timing JSON/CSV and audio assets.
- Source manifest, visual-region manifest and alignment audit.
- Machine QA report and human review checklist.
- One ZIP containing the complete production package.

## One-command production runner

The user uploads one PPTX. The Skill agent internally authors narration, storyboard and verified alignment decisions, then invokes the PowerShell runner twice inside the same orchestration request:

**Prepare phase** (agent-authored narration JSON is an internal artifact):

    powershell -ExecutionPolicy Bypass -File scripts/run_video_builder_v2_6.ps1 -Phase Prepare -Pptx input/lesson.pptx -OutputDir output/lesson -NarrationJson output/lesson/narration_events.json

The Prepare phase exports every slide with PowerPoint, extracts native regions, synthesizes per-phrase TTS, measures timing and creates the machine-hashed alignment context. The Skill agent then reads that context and slide previews, performs planner/verifier passes, and writes alignment decisions plus storyboard JSON.

**Render phase** (all JSON paths are generated internally by the Skill agent):

    powershell -ExecutionPolicy Bypass -File scripts/run_video_builder_v2_6.ps1 -Phase Render -Pptx input/lesson.pptx -OutputDir output/lesson -AlignmentDecisions output/lesson/alignment_decisions_verified.json -StoryboardJson output/lesson/storyboard.json

The Render phase compiles the alignment, renders and validates a content-aware internal pilot, renders the full deck, validates the final MP4, merges SRT captions, exports `narration_script.txt` and `measured_timeline.csv`, and creates `lesson_video_production_package.zip`. Any terminating failure writes a delivery manifest with `status=INCOMPLETE`; the runner must never present a partial file as a completed course. The two phases are invisible implementation details; the user is not asked to perform them.

**Storyboard rendering in V2.7:** the renderer consumes the storyboard JSON. It can produce a verified static close-up/extreme-close-up crop around an exact region ID, subtle slow push-in/pan on slides without active focus overlays, subtitles/countdowns, and a short fade-to-black for `short_dissolve`. The first shot is the rendered primary shot for each slide; additional shots remain storyboard-only until event-timed multi-shot rendering is implemented. Dynamic algorithm simulations still require a validated state trace. Never promise unsupported effects.

## Engine commands and implementation

The validated scripts and detailed engine command reference remain in this directory:
- `scripts/render_slides_v2_4.ps1`
- `scripts/extract_slide_regions_v2_4.py`
- `scripts/generate_audio_v2_4.py`
- `scripts/prepare_alignment_inputs_v2_4.py`
- `scripts/finalize_alignment_plan_v2_4.py`
- `scripts/compile_alignment_v2_4.py`
- `scripts/render_lesson_v2_4.py`
- `scripts/validate_full_video_v2_4.py`
- `scripts/run_video_builder_v2_6.ps1`
- `prompts/storyboard_compiler_v2_6.md`

The Skill agent orchestrates the semantic planning and verification steps between these deterministic tools. V2.2/V2.3 remain untouched.

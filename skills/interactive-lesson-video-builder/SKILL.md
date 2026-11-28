---
name: interactive-lesson-video-builder
version: 2.5.0-alpha.1
description: Agent-orchestrated teaching-video pipeline that automatically builds narration, visual-region mapping, measured phrase timing, synchronized focus/subtitles, rendering and fail-closed QA. V2.2/V2.3 compatibility assets are retained.
---

# Interactive Lesson Video Builder — Active Skill

Use V2.4.1 as the validated media engine and V2.5 orchestration contract as the active end-to-end workflow. Implementations live in `../interactive-lesson-video-builder-v2.4/`; V2.2 and V2.3 assets remain preserved and must never be overwritten.

## User-facing behavior: one request, end-to-end execution

When the user supplies a PPTX and asks for a teaching video, do not ask them to manually prepare narration JSON, region IDs, alignment decisions, timing files, subtitles, or command sequences. The Skill agent must create these artifacts itself, using the source deck, speaker notes, and the prompts in the versioned package.

Ask only for information that is genuinely missing and cannot be inferred (for example, the target audience or required language). Use the configured Chinese teaching defaults otherwise. Preserve the source lesson's order, facts, examples, formulas, C++ code, and teacher intent.

## Agent-orchestrated pipeline

1. **Inspect source:** inventory slide count, aspect ratio, text, speaker notes, code, formulas, diagrams, tables, teaching questions, and exercise difficulty. Create a source manifest and SHA-256 fingerprint.
2. **Render previews:** on Windows with PowerPoint, export every slide to PNG at the original aspect ratio. Bind each preview to its slide number and image SHA-256.
3. **Extract visual regions:** run the V2.4 native PPTX extractor. Create stable region IDs for text boxes and table cells. For image-only diagrams, graph structures, charts, and formula images, use the visual-region prompt with the exact slide preview; include only hash-bound proposals that pass a distinct visual verification pass.
4. **Author narration:** use `prompts/lesson_narration_compiler_v2_4.md` to create narration events directly from slide content and speaker notes. Split long explanations into natural, teachable phrases. Give each event a stable unique ID and each phrase a deterministic index. Include teaching transitions, examples, recap, and student thinking prompts only when supported by the lesson. Save the JSON; do not ask the user to write it.
5. **Generate voice:** synthesize each phrase with the configured TTS voice. Measure actual audio segment durations with FFprobe and write phrase-level timing records. Never estimate duration from character count, reading speed, slide duration, or a model-generated timestamp.
6. **Build alignment context:** run `prepare_alignment_inputs_v2_4.py` to generate exact region/phrase records and machine-computed hashes. The model must never invent or calculate hashes.
7. **Map and verify:** use the alignment planner to map each phrase to zero, one, or several source region IDs. Then run the independent verifier as a separate pass. A transition phrase may be unmatched. A comparison phrase may target multiple regions. Preserve all rejected candidates and reasons for audit.
8. **Finalize and compile:** run the finalizer and compiler. The compiler is the authority: only exact source IDs, evidence quotes, verified geometry, measured phrase timings, matching fingerprints, confidence >= 0.90, and distinct planner/verifier passes may become rendered focus events.
9. **Render:** render subtitles and focus overlays from the compiled report only. Use the measured phrase intervals; do not independently recreate a second timeline. Keep subtitles out of intentional thinking pauses. Keep numeric countdowns in their reserved non-overlapping band.
10. **QA:** validate MP4 video/audio streams, full decode, audio durations, timing coverage, subtitle intervals, pause suppression, focus interval consistency, and geometry. Produce a machine-readable alignment audit and final QA report.
11. **Pilot gate:** render a representative five-slide pilot (opening, concept, code/formula, worked example, exercise/recap where available). Require frame-by-frame human review for teaching correctness, legibility, highlight placement, narration pacing, and subtitle overlap before full-course rendering.

## Three-way alignment contract (non-negotiable)

Every visible focus event must have one auditable record linking:
- **Visual:** source PPTX SHA-256, slide-image SHA-256, slide number, stable region ID, normalized bbox, geometry source, verification status.
- **Speech:** narration event ID, phrase index, exact phrase text, source slide, and TTS audio file SHA-256.
- **Time:** measured start/end seconds from the actual audio segment, timing JSON SHA-256, and FFprobe-probed media duration.

All three must share the same slide, event, phrase, and source context. Renderer input is the compiled alignment report, never a freehand timeline. Subtitles use the same speech interval; focus overlays use the corresponding verified visual mapping. Store source IDs in the QA report so any rendered rectangle can be traced back to the source PPTX and spoken phrase.

## Fail-closed rules

- No guessed timestamps, slide-duration ratios, character-count timing, nearest-text fallback, or fuzzy matching promoted directly to render.
- No stale source/audio/timing/slide-image hashes.
- No unverified or unsupported geometry.
- No automatic focus for ambiguous matches or confidence below 0.90.
- No fabricated narration facts, examples, code behavior, or algorithm states.
- No algorithm-state animation unless a separate validated state trace supplies every state and transition.
- If a check fails, stop the affected slide, retain diagnostic output, and regenerate only from the changed source. Do not silently downgrade to a weaker alignment method.
- Machine QA passing does not mean semantic correctness. Always set `manual_review_required=true` and `auto_approved=false`.

## Output package

Produce, at minimum:
- source manifest and slide previews;
- native/verified visual-region manifest;
- narration event JSON;
- per-phrase audio and measured timing JSON;
- alignment context, draft decisions, independent verification, finalized plan;
- compiled alignment report;
- rendered MP4 and SRT subtitles;
- alignment audit and final media QA report;
- a concise pilot review checklist and unresolved-item list.

## Version isolation

V2.2 and V2.3 scripts, outputs, caches, and historical artifacts remain intact. V2.4 is the validated alignment/render/QA engine. V2.5 changes orchestration and workflow behavior; it must not silently replace the underlying engine or weaken its checks.

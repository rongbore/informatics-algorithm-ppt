---
name: interactive-lesson-video-builder
version: 2.3.0
description: Build source-grounded Chinese algorithm teaching videos from PPT/PPTX with event-driven narration, adaptive thinking pauses, phrase-timed subtitles, focus highlights and QA.
---

# Interactive Lesson Video Builder

## Purpose
Convert a supplied PPT/PPTX and lesson materials into a paced teaching video. Preserve source terminology, examples, C++ code, formulas and instructional sequence. Never invent algorithm states, code output, data values or slide content.

## V2.3 workflow
1. Inspect PPT/PPTX, slide text, speaker notes, code, formulas and visual layout.
2. Create narration events using templates/narration_event.schema.json.
3. Separate narration, thinking_prompt, reveal, summary and pause events.
4. Assign thinking difficulty: D1=6s, D2=8s, D3=10s, D4=15s, D5=20s. Explicit thinking_seconds or pause_after_seconds takes precedence. If absent, classify the reasoning burden and record the reason.
5. Generate TTS per phrase and write measured phrase boundaries to one timing JSON per slide.
6. Generate subtitles from measured phrase timing. Hide subtitles during intentional thinking silence. This is phrase-level timing, not word/phoneme forced alignment.
7. Render 1920x1080 with a reserved subtitle band. Preserve slide aspect ratio and apply the same scale/padding transform to highlight bboxes.
8. Render a numeric-only countdown in the reserved bottom band during thinking silence. Never render a central thinking card or large opaque overlay over slide content.
9. Run QA. Manually inspect the five-slide pilot before rendering the full deck.

## Teaching defaults
Default sequence: concept → explanation → worked reasoning → code/algorithm focus → guided question → silent thinking → reveal → recap.
- Knowledge-point pause: 5s when knowledge_point_end is true.
- Slide-end pause: 5s by default, configurable per slide.
- Thinking duration: D1 6s, D2 8s, D3 10s, D4 15s, D5 20s.
- Do not pause mechanically after every sentence.
- Countdown is positioned at the right side of the reserved subtitle band.

## Event types
- narration: spoken explanation.
- thinking_prompt: spoken question followed by silent thinking time.
- reveal: spoken answer or worked solution.
- summary: spoken recap.
- pause: explicit silence without speech.

Thinking duration precedence: thinking_seconds → pause_after_seconds → difficulty map → D3 fallback. Existing V2.2 pause_after_seconds is retained for compatibility.

## Highlight model
Each focus event may contain kind (knowledge/code/algorithm), target_text, bbox=[x,y,width,height] normalized relative to the original slide image, optional confidence, line_count and label. Only use bboxes verified against the PPT. Text match alone does not prove geometric accuracy.

## Algorithm animation honesty
The V2.3 renderer synchronizes focus overlays with narration. It does not infer a correct Fenwick tree, segment tree, DFS or DP state machine from arbitrary prose. Full state animation requires explicit verified state sequences and a dedicated visualization adapter. Never label a static highlight as a true algorithm simulation.

## Quality gates
- Preserve V2.2 files; use V2.3 versioned filenames.
- Validate slide IDs, audio, timing JSON and timeline coverage.
- Check output stream, 1080p resolution, audio presence and duration.
- Manually review subtitle overlap, code legibility, highlight alignment and instructional correctness.
- Never auto-approve a full 80-slide render solely because FFmpeg exited successfully.

See README_V2.3.md for Windows installation and execution.

---
name: interactive-lesson-video-builder
version: 2.4.1-alpha.4
description: Latest unified Skill for PPTX visual-region extraction, event-driven narration, measured phrase timing, automatic alignment, video rendering and QA. V2.2 and V2.3 compatibility assets are retained.
---

# Interactive Lesson Video Builder — Latest

Use V2.4.1 Alpha.4 as the active pipeline. The versioned implementation is maintained in:

- ../interactive-lesson-video-builder-v2.4/SKILL.md
- ../interactive-lesson-video-builder-v2.4/README.md

V2.2 and V2.3 assets remain in this directory and are preserved for compatibility. Do not overwrite or delete them when upgrading.

## Mandatory workflow
1. Extract PPTX-native visual regions and source geometry.
2. Bind slide previews to image hashes and add verified vision regions for image-only diagrams.
3. Generate event-driven narration with stable event IDs.
4. Generate per-phrase TTS and measure actual audio intervals.
5. Create an AI visual/speech mapping plan and run a separate verification pass.
6. Compile the mapping with exact source, narration, timing and audio fingerprints.
7. Render only the compiled alignment report.
8. Run media QA and inspect a five-slide pilot before full-course rendering.

Never use slide-duration ratios or guessed timestamps. Unverified or ambiguous visual matches are withheld. A phrase may map to multiple distinct regions. Duplicate geometry is consolidated. Manual review remains mandatory; never auto-approve a full course.

# Interactive Lesson Video Builder V2.4 — Alpha.3

This is the isolated V2.4 development package. It does not replace the V2.3 Skill or its production outputs.

## Included in this increment
- Phrase-level focus alignment with exact timeline/narration digest checks.
- Source-verified normalized bounding-box validation.
- Unique full-text matching or reviewed event anchors; no duration-ratio fallback.
- Duplicate region geometry consolidation so repeated labels cannot paint the same box twice.
- Offline unit tests for timing integrity, ambiguity, geometry, anchor priority, and digest mismatch.

## Run tests

From this directory:

    python -m unittest discover -s tests -v

Python 3.10+ is recommended. The focus engine has no third-party runtime dependencies.

## Focus alignment CLI

    python scripts/align_focus_v2_4.py --timeline PATH --narration PATH --anchor-plan PATH --timings DIR --report PATH --slides 35

The renderer must pass an independently probed audio duration to align_slide. The standalone audit CLI currently uses the duration recorded in the timing JSON and explicitly reports that it did not independently probe the audio.

## Slide 35 duplicate-region finding

The supplied slide35-events.json contains two algorithm records with the same target_text, shape_index, and bbox, but different labels and overlapping ratio intervals. Those records describe one physical formula region, not two independent boxes. V2.4 consolidates exact duplicate geometry; it does not invent a second bbox for the numeric table. The table's highlight geometry must be extracted from the original PPTX and reviewed before it can be added as a separate region.

## Release status

Alpha.3 is a focused integration increment, not a full production release. The complete V2.4 source archive, compiler, renderer, audio generation, and media QA must all be integrated and tested before a release candidate is declared. Human review remains mandatory.

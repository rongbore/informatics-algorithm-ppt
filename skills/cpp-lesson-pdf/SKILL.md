---
name: cpp-lesson-pdf
description: Generate Chinese C++ competitive programming lesson handouts as A4 PDF using the reference topology-sorting handout's XeLaTeX typography, color palette, code highlighting, diagrams and lesson/problem structure.
---

# C++ Lesson PDF Skill

## Trigger
Use for Chinese C++ lesson handouts, algorithm explanations, classroom exercises, and homework PDFs when the user requests this template style.

## Inputs
Ask for the topic, knowledge points, full problem statements, sample I/O, constraints and optional reference code. If a source PDF is provided, inspect all relevant pages and preserve the actual problem statement. Never fabricate constraints, samples or judge acceptance.

## Workflow
1. Read `references/PROMPT.md` and the sample `templates/main.tex`.
2. Preserve the lesson's two-section structure: `一、知识点讲解` then `二、课堂练习`.
3. Replace content in `templates/main.tex`, keeping `lesson-style.sty` and `diagram-styles.tex` intact.
4. Use XeLaTeX, run `scripts/build.sh` (Linux/macOS) or `scripts/build.ps1` (Windows).
5. Render every PDF page to images and inspect text overflow, code line numbers, diagram correctness and font availability.
6. Compare representative pages against the reference PDF, especially the first page, analysis/code pages, and table-heavy pages. Iterate until the style is consistent.
7. Provide the compiled PDF and optionally the edited source files.

## Requirements
- A4 portrait, white, Song font, title #22598D, section headings #18766E, analysis headings #B4661D.
- Main title ~24pt, major section ~14.3pt, subsection 12pt, body ~10.9pt, code ~9pt.
- C++ code uses a white bordered listing, line numbers, and editor-style syntax colors.
- Each exercise: problem statement, input/output, examples, constraints, summary, stepwise reasoning, sample derivation, key code modules, complexity, complete C++ solution.
- Avoid adding covers, dates, institutions or logos unless requested.
- If the original Fandol fonts are unavailable, configure a local Song-style font and disclose that the result is a visual approximation.

## Validation
Run PDF info check, visually render all pages, inspect compilation warnings, and test the C++ reference solution with samples when possible. A successful PDF compilation alone does not prove layout fidelity or algorithm correctness.


## Mandatory core comments in solution code
Every complete C++ solution printed in a lesson PDF MUST include concise, accurate Chinese core comments, not merely an explanation outside the code.
- Explain the meaning of non-obvious key variables, DP states, and data structures.
- Explain important initialization choices and their relation to the problem.
- Place comments adjacent to core transitions, algorithm decisions, loops, and data-structure updates; explain **why** the step is necessary.
- Annotate significant boundary cases, unreachable states, overflow/modulo handling, and path reconstruction when applicable.
- Explain what the final answer represents near the output.
- Avoid mechanical line-by-line narration and excessive comments on obvious syntax; typically 5–12 meaningful comments for a medium-length solution, adjusted to complexity.
- Comments must match the implemented algorithm exactly. Preserve the user's algorithm and variable names unless fixing a disclosed error.
- Use Chinese UTF-8 source comments and verify that the PDF listing renders them without missing glyphs or broken spacing.
- If using LaTeX listings, configure a Unicode-compatible code renderer or appropriate CJK handling; if it cannot display Chinese comments reliably, switch the rendering approach rather than silently deleting comments.
- Before delivery, inspect the rendered PDF and verify that **each** exercise's full reference solution contains visible Chinese core comments.

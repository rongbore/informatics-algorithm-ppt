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

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
5. Render every PDF page to images and inspect text overflow, confirm **C++ code has no line numbers or reserved numbering gutter**, diagram correctness and font availability.
6. Compare representative pages against the reference PDF, especially the first page, analysis/code pages, and table-heavy pages. Iterate until the style is consistent.
7. Provide the compiled PDF and optionally the edited source files.

## Requirements
- A4 portrait, white, Song font, title #22598D, section headings #18766E, analysis headings #B4661D.
- Main title ~24pt, major section ~14.3pt, subsection 12pt, body ~10.9pt, code ~9pt.
- C++ code uses a white bordered listing with **no line numbers**, no numbering gutter, and editor-style syntax colors.
- Each exercise: problem statement, input/output, examples, constraints, summary, stepwise reasoning, sample derivation, key code modules, complexity, complete C++ solution.
- Avoid adding covers, dates, institutions or logos unless requested.
- If the original Fandol fonts are unavailable, configure a local Song-style font and disclose that the result is a visual approximation.

## Validation
Run PDF info check, visually render all pages, inspect compilation warnings, and test the C++ reference solution with samples when possible. A successful PDF compilation alone does not prove layout fidelity or algorithm correctness.


## v1.3 mandatory reasoning and visual derivation upgrade

Read `references/DEEP-REASONING-STEPS.md` and `references/VISUAL-DERIVATION-STANDARD.md` before generating any nontrivial C++ algorithm handout. In every exercise, explain **what each state means and when it becomes final**, why each loop bound and guard exists, and how each candidate transition is computed. Generate a reproducible chain **initial state → current choice → arithmetic and validity decision → updated state → final state → counterexample when applicable**.

Use the smallest meaningful diagram/table for syntax exercises; for DP/tree/backpack/graph exercises include input provenance, old and new state snapshots, rejected candidates with reasons, a numeric transition table, and a mapping to the complete annotated C++ solution. Distinguish source-test samples from fabricated-for-teaching illustrative data. Never invent state changes.

For the tree-knapsack example described in the user's `解析.pdf`, run `python scripts/trace_dp_merge.py --markdown output/merge-trace.md` to verify candidate `j/k` updates and the forward-order bug. This is for in-place 0/1 child merge; do not assert that all DP implementations must use descending order. All numeric visuals must be checked, and PDFs must still pass text extraction and page rendering review.

Project-level Web Codex installations use `.agents/skills/cpp-lesson-pdf/` as the canonical v1.3 copy. The files in this legacy directory are maintained for local installation compatibility.


## v1.3.1 graph visualization workflow

Read `references/TOPOSORT-TRACE-WORKFLOW.md` when generating topological-sort lessons. Run `scripts/trace_toposort.py --markdown output/toposort-trace.md --latex output/toposort-tables.tex` to produce per-step queue/indegree updates and verified LaTeX tables. Do not confuse FIFO order with lexicographically smallest topo sort. On a cycle, explicitly state that a complete ordering is impossible. Preserve source/sample provenance and complete C++ solutions with Chinese comments.

The canonical Codex Web project-level Skill is `.agents/skills/cpp-lesson-pdf/`; this legacy directory retains a compatible copy of the graph-tracing data, script and documentation.


## v1.3.2 用户明确指定的代码页规则（高优先级）

- 最终学生 PDF 中**删除“排版说明”板块**，不添加源码引入方式、代码颜色、行号显示、编译/渲染过程等制作元说明。代码标题后直接进入代码框。
- C++ 代码块左侧和右侧都不显示行号，不保留空白编号 gutter。
- 保留正常 C++ 编辑器语法高亮、等宽字体、中文核心注释、白底浅灰蓝边框和完整源码。
- `templates/lesson-style.sty` 必须使用 `numbers=none`；禁止 `numbers=left/right`。
- 这些要求覆盖历史参考 PDF 曾经使用行号的做法。

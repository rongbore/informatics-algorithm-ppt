# cpp-lesson-pdf

中文 C++ 信息学课堂讲义 PDF 模板包（基于上传的《拓扑排序课堂讲义.pdf》样式分析）。

## 文件说明
- `SKILL.md`：AI Skill 使用说明
- `references/PROMPT.md`：内容与视觉生成提示词
- `templates/main.tex`：可编辑 XeLaTeX 示例讲义
- `templates/lesson-style.sty`：排版与代码样式
- `templates/diagram-styles.tex`：算法图解样式
- `scripts/build.sh`：Linux/macOS 编译
- `scripts/build.ps1`：Windows PowerShell 编译
- `examples/sample.pdf`：已编译的示例 PDF

## 编译
安装支持 XeLaTeX、ctex、xeCJK、TikZ、listings、tcolorbox 的 TeX Live 或 MiKTeX。

Linux/macOS：`bash scripts/build.sh`

Windows PowerShell：`powershell -ExecutionPolicy Bypass -File scripts/build.ps1`

生成 PDF：`output/main.pdf`。

## 字体兼容
原文件内嵌 FandolSong 字体。本模板通过 TeX Live 的 Fandol 字体路径加载，当前 Linux 环境可用。Windows 如果 TeX Live 安装目录不同，修改 `templates/lesson-style.sty` 中的 `Path=`；或者将其改为系统可用的中文宋体。请勿把原 PDF 内嵌字体直接抽取并传播。

## 复刻范围
该模板复刻主要字体、字号层级、颜色、章节逻辑、代码框和图形语言。示例 PDF 是新内容的排版演示，并非原 15 页逐页重制，也未完成像素级一致性认证。

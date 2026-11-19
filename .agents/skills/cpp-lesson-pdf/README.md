# cpp-lesson-pdf v1.2 — 逆向复刻增强版

针对用户上传的《拓扑排序课堂讲义.pdf》（15 页）进行了真实字体/矢量测量，并升级为可安装的 C++ 信息学 PDF Agent Skill。

## 本次升级

- `references/REVERSE-ENGINEERING.md`：从真实 PDF 中测得版心、字体、字号、颜色、代码框参数以及逐页结构。
- `references/reference-metrics.json`：自动提取的逐页字体和矢量统计（不包含原 PDF）。
- `references/MASTER-PROMPT.md`：可复制使用的统一母版提示词。
- `references/PDF-STYLE-GUIDE.md`：四种浅色说明框、样例双栏、图、公式、代码规范。
- `references/CODE-COMMENT-RULES.md`：每道练习必须有完整 C++ 代码和关键中文注释。
- `templates/lesson-style.sty`：真实浅色编辑器代码框使用 minted + tcolorbox，支持 UTF-8 中文注释；拒绝 `<MINTED>` 占位符。
- `scripts/validate.py`：A4、代码可见性、中文注释、代码样例和包完整性检验。
- `scripts/analyze_reference.py`：支持从后续参考 PDF 提取页面/色彩/文字统计。
- `scripts/build.sh` / `scripts/build.ps1`：强制至少两遍 XeLaTeX，检查占位符。

## 网页版 Codex（GitHub 项目级 Skill）

本目录位于 `.agents/skills/cpp-lesson-pdf/`，供 GitHub 仓库关联的 Codex 项目工作区使用。合并到 `main` 后，创建或刷新基于此仓库的 Codex 工作环境，确保 `SKILL.md` 可被发现。在 Codex 中可尝试 `$cpp-lesson-pdf` 调用；若工作环境未发现此 Skill，检查检出分支与项目配置。

GitHub 上的项目级安装**不会自动同步**到 Windows D 盘或 ChatGPT 插件目录。

## Windows 本地独立安装

可以将 `cpp-lesson-pdf/` 复制到 `D:\Codex\skills\cpp-lesson-pdf` 作为自定义备份目录，或运行安装脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\cpp-lesson-pdf\scripts\install.ps1
```

请根据具体 Codex 客户端支持的用户级 Skill 目录完成加载；仅复制到 D 盘并不保证客户端自动扫描到该目录。

## 编译演示

需 TeX Live 或 MiKTeX（XeLaTeX / ctex / minted / TikZ / tcolorbox）、Python Pygments（含 latexminted）、可用宋体类 CJK 字体。

Linux/macOS：`bash scripts/build.sh`

Windows：`powershell -ExecutionPolicy Bypass -File scripts/build.ps1`

成功后输出到 `output/main.pdf`；可执行 `python scripts/validate.py --pdf output/main.pdf --check-demo-code`。

**注意**：部分 minted 版本首次编译会产生 `<MINTED>` 占位符，第二遍通常才解析真正代码。本模板已加入强制检查，不能仅凭编译退出码判定成功。

## 可复用场景

- C++ 基础语法：知识点 + 课堂 5 题 + 每题完整代码与注释
- 图论与动态规划：算法图、表格、推导、复杂度及参考解
- 家庭作业详解：原题保真、逐题讲解、代码编辑器风格

## 对原 PDF 的复刻边界

本包复刻字体层级、颜色、版心、组件和教学逻辑，不宣称像素级完全一致（未获得原始 XeLaTeX 源码）。包中不包含原 PDF 或字体文件，便于管理版权及环境兼容。

示例 PDF 可以由 `templates/main.tex` 编译生成；仓库只提交可复现源码，不包含生成的二进制 PDF。

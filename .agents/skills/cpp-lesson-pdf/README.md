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


## v1.3：解题步骤与数据推演增强

新增 `references/DEEP-REASONING-STEPS.md`（八步教学法）和 `references/VISUAL-DERIVATION-STANDARD.md`（按算法分类的可视化表格标准）。

运行校验示例：

```bash
python3 scripts/trace_dp_merge.py --markdown output/tree-knapsack-trace.md
python3 scripts/validate.py --check-demo-code
```

示例数据文件：`examples/derivations/tree_knapsack_merge.json`。它来自用户上传《解析.pdf》第 3 页的**教学构造数据**，不是官方题目样例；另有 `tree_knapsack_visual.tex` 可嵌入使用 TikZ 和 LaTeX 的讲义。

最重要的验收条件：每道复杂算法题都必须交代状态定义、执行时机、循环与合法性条件、候选公式、逐步表格、错误反例与完整 C++ 代码。推导表需要能被数据或脚本复算，不允许仅凭图形生成器编造数值。

## v1.3.1：拓扑排序逐步图解与程序验算

在 v1.3 树形背包数值推演基础上，新增 Kahn 拓扑排序的**全步骤状态轨迹**：依赖图、初始入度、每次出队、每条有向边的入度更新、新增入队节点、完整队列变化、拓扑序和环检测。

源文件：`scripts/trace_toposort.py`、`examples/derivations/toposort_cases.json`、`examples/derivations/toposort_visual.tex`。

```bash
python3 scripts/trace_toposort.py --markdown output/toposort-trace.md --latex output/toposort-tables.tex
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

这两份推导演示数据都是课堂构造数据，**不属于题库官方样例**；生成 LaTeX 依赖 XeLaTeX/longtable，仍需 PDF 逐页视觉检查。


## v1.3.2：代码页去行号与移除排版说明

- 完整 C++ 代码继续使用编辑器风格语法高亮和中文核心注释，但代码左侧/右侧不显示行号，不预留编号 gutter。
- 删除学生讲义中的“排版说明”板块及源码引入、配色/行号说明等制作元信息；代码标题后直接显示代码。
- minted 不启用 `linenos`；listings 使用 `numbers=none`。
- `scripts/validate.py` 新增样式与 PDF 内容检查，回归测试锁定该排版要求。

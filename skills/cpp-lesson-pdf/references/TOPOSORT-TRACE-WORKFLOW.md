# 拓扑排序可复算推导：教学工作流（v1.3.1）

## 不变的语义与限制

本示例采用 **Kahn 算法 + FIFO 队列**；初始零入度节点按编号从小到大入队；每个出队节点按邻接表中边的输入先后处理后继，与 `examples/code/toposort_demo.cpp` 一致。它不等同于**字典序最小**拓扑排序（后者通常需要小根堆）。如果有多个合法拓扑序，不得把演示输出说成唯一答案。

输入在 `examples/derivations/toposort_cases.json`，明确标注为**教学示意数据，不是题库原样例**。包含一个 DAG（合流与多条可用分支）和一个含环图（仍可能先处理一部分节点）。

## 从数据到图表（杜绝虚构中间状态）

```bash
python3 scripts/trace_toposort.py \
  --data examples/derivations/toposort_cases.json \
  --markdown output/toposort-trace.md \
  --latex output/toposort-tables.tex
```

生成的 Markdown 和 XeLaTeX 长表来自**同一次**状态计算，字段包括：

| 字段 | 教学含义 |
|---|---|
| `initial_indegree` | 建图后各顶点入度，含重复边的累计 |
| `initial_queue` | 初始可处理顶点及先后顺序 |
| `steps[].queue_before` | 当前弹出节点前的实际队列 |
| `steps[].processed` | 当前出队顶点 |
| `steps[].updates` | 按邻接表顺序记录每一条边导致的入度变化、是否入队 |
| `steps[].queue_after` | 本轮结束后队列真实状态 |
| `steps[].indegree_after` | 每一步的完整入度数组快照 |
| `steps[].order_after` | 已输出的部分拓扑序 |
| `cycle` / `remaining` | 停止时是否仍有无法处理的节点及其编号 |

让学生自己计算：第 1 轮处理顶点 1 后，2 和 3 入度变为 0，因此队列变为 [2,3]；处理顶点 2 后，4 尚有一条入边，不能入队；处理顶点 3 后，4 和 6 才能入队。图、表、代码必须表达同样的过程。

## 在讲义中复用

在加载 `lesson-style.sty` 的 XeLaTeX 主文档中使用：

```latex
% main.tex 位于 templates/ 下，预先运行生成脚本
\input{../examples/derivations/toposort_visual.tex}
\input{../output/toposort-tables.tex}
```

`toposort_visual.tex` 用 TikZ 表示同一张 DAG，右侧状态表由脚本生成，不要手工重新输入中间数值。脚本长表包含分页续表头，需要母版加载 `longtable`。

## 检查与安全

1. 输入无向边不适用。所有节点必须在 1..n 内；自环会触发有环结论。
2. 相同的有向边如果输入两次，入度也增加两次，处理时按出现次数减少。
3. 有环时不能把部分已出队的顶点称作完整拓扑序；应输出“未处理完”及剩余入度节点。
4. 对于图论题原有样例，要先标注来源并校验原题输入，再用脚本导出推导，不得把本构造数据标注为题库官方样例。
5. 运行 `python3 -m unittest discover -s tests -p 'test_trace_toposort.py' -v`；测试包括实际 C++17 编译和输入/输出对照。
6. 长表虽然可跨页，但 TikZ 图仍需在 PDF 中逐页目检节点、边、字号与分页，不得仅凭校验脚本声称视觉无误。

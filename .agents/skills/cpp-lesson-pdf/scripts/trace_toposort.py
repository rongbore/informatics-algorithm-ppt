#!/usr/bin/env python3
"""Generate reproducible, step-by-step Kahn topological-sort traces.

Queue is FIFO, initial zeros are scanned 1..n, and adjacency order follows
edge input order, matching examples/code/toposort_demo.cpp.
The bundled examples are explicitly illustrative, not official judge samples.
"""
import argparse
from collections import deque
import json
from pathlib import Path


def trace_toposort(n, edges):
    if type(n) is not int or n < 1 or n > 10000:
        raise ValueError("n must be an integer between 1 and 10000")
    if len(edges) > 100000:
        raise ValueError("too many edges for a teaching trace")
    g = [[] for _ in range(n + 1)]
    indegree = [0] * (n + 1)
    for i, edge in enumerate(edges):
        if (not isinstance(edge, (list, tuple)) or len(edge) != 2
                or any(type(x) is not int or not 1 <= x <= n for x in edge)):
            raise ValueError(f"invalid directed edge at index {i}: {edge!r}")
        u, v = edge
        g[u].append(v)
        indegree[v] += 1

    initial_degrees = indegree[1:].copy()
    queue = deque(i for i in range(1, n + 1) if indegree[i] == 0)
    initial_queue = list(queue)
    order = []
    steps = []

    while queue:
        before = list(queue)
        u = queue.popleft()
        order.append(u)
        updates = []
        for v in g[u]:
            previous = indegree[v]
            indegree[v] -= 1
            newly_ready = indegree[v] == 0
            if newly_ready:
                queue.append(v)
            updates.append({
                "edge": [u, v],
                "before": previous,
                "after": indegree[v],
                "enqueued": newly_ready,
            })
        steps.append({
            "step": len(steps) + 1,
            "processed": u,
            "queue_before": before,
            "queue_after": list(queue),
            "updates": updates,
            "indegree_after": indegree[1:].copy(),
            "order_after": order.copy(),
        })
    cyclic = len(order) != n
    return {
        "n": n,
        "edges": edges,
        "initial_indegree": initial_degrees,
        "initial_queue": initial_queue,
        "steps": steps,
        "order": order,
        "cycle": cyclic,
        "remaining": [i for i in range(1, n + 1) if indegree[i] > 0],
    }


def verify_case(case):
    result = trace_toposort(case["n"], case["edges"])
    required = {
        "expected_initial_indegree": result["initial_indegree"],
        "expected_initial_queue": result["initial_queue"],
        "expected_queue_after": [s["queue_after"] for s in result["steps"]],
        "expected_order": result["order"],
        "expected_cycle": result["cycle"],
    }
    for field, value in required.items():
        if field not in case or case[field] != value:
            raise ValueError(
                f'{case.get("id", "unnamed")}: {field} mismatch; '
                f"expected recorded={case.get(field)!r}, computed={value!r}"
            )
    if not result["cycle"]:
        pos = {node: i for i, node in enumerate(result["order"])}
        for u, v in result["edges"]:
            if pos[u] >= pos[v]:
                raise ValueError(f"invalid topological order: {u}->{v}")
    return result


def as_cell(values):
    return "[" + ", ".join(str(x) for x in values) + "]"


def to_markdown(case, result, provenance):
    out = [
        f'## {case.get("title", case.get("id", "未命名示例"))}', "",
        f"数据性质：{provenance}", "",
        "图的有向边：" + ("、".join(f"{u}→{v}" for u, v in result["edges"]) or "无边"),
        "",
        f"初始各节点入度（节点 1 至 {result['n']}）：{as_cell(result['initial_indegree'])}",
        f"初始队列：{as_cell(result['initial_queue'])}", "",
        "| 步骤 | 队列（处理前） | 出队节点 | 被处理边与入度变化 | 队列（处理后） | 已输出序列 |",
        "|---:|---|---:|---|---|---|",
    ]
    for s in result["steps"]:
        changes = "；".join(
            f"{u}→{v}: {a['before']}→{a['after']}" + ("（入队）" if a["enqueued"] else "")
            for a in s["updates"] for u, v in [a["edge"]]
        ) or "无出边"
        out.append(
            f'| {s["step"]} | {as_cell(s["queue_before"])} | {s["processed"]} | '
            f'{changes} | {as_cell(s["queue_after"])} | {as_cell(s["order_after"])} |'
        )
    if not result["steps"]:
        out.append("| 0 | [] | — | 初始无入度为零的顶点 | [] | [] |")
    out += ["", "**最终判定**："]
    if result["cycle"]:
        out.append(
            f'仅处理 {len(result["order"])}/{result["n"]} 个节点，'
            f'仍有正入度节点 {as_cell(result["remaining"])}；存在有向环，程序输出 `-1`。'
        )
    else:
        out.append(
            f'共处理 {result["n"]} 个节点，'
            f'得到一个合法拓扑序：`{" ".join(map(str, result["order"]))}`。'
        )
    out.extend(["", "注：当多个节点入度均为零，拓扑序不一定唯一；本记录遵循 C++ 示例的 FIFO 队列规则。", ""])
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--data", type=Path,
        default=Path(__file__).resolve().parents[1] / "examples/derivations/toposort_cases.json",
    )
    ap.add_argument("--markdown", type=Path, help="write reproducible Markdown trace")
    args = ap.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    if not data.get("provenance") or not data.get("cases"):
        raise ValueError("data must include provenance and cases")
    chunks = ["# 拓扑排序：程序验证的队列与入度推导", ""]
    for case in data["cases"]:
        chunks.append(to_markdown(case, verify_case(case), data["provenance"]))
    content = "\n".join(chunks)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(content, encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()

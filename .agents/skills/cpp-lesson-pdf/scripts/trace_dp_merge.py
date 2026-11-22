#!/usr/bin/env python3
"""Reproducible 0/1 in-place tree knapsack child-merge trace.
Values come from a pedagogical example, NOT the problem's official sample.
"""
import argparse
import json
from pathlib import Path

def merge(old, child, cost, capacity, descending=True):
    old_size, child_size = len(old) - 1, len(child) - 1
    dp = list(old) + [None] * max(0, capacity + 1 - len(old))
    rows = []
    limit = min(capacity, old_size + child_size)
    indices = range(limit, 0, -1) if descending else range(1, limit + 1)
    for j in indices:
        for k in range(1, min(j, child_size) + 1):
            left, previous = j - k, dp[j]
            if left > old_size:
                reason = "旧部分人数不足"
                new_value = previous
            elif dp[left] is None or child[k] is None:
                reason = "不可达"
                new_value = previous
            else:
                candidate = dp[left] + child[k] - cost
                reason = f"{dp[left]} + {child[k]} - {cost} = {candidate}"
                new_value = candidate if previous is None else max(previous, candidate)
                dp[j] = new_value
            rows.append((j, k, reason, previous, new_value))
    return dp, rows

def validate(data):
    demo = data["worked_example"]
    dp, rows = merge(demo["old"], demo["child"], demo["edge_cost"], demo["capacity"])
    assert dp == demo["expected_after"], f"演示数据校验失败: {dp}"
    ex = data["counterexample"]
    reverse, _ = merge(ex["old"], ex["child"], ex["edge_cost"], ex["capacity"], True)
    forward, _ = merge(ex["old"], ex["child"], ex["edge_cost"], ex["capacity"], False)
    assert reverse == ex["expected_descending"], f"倒序校验失败: {reverse}"
    assert forward == ex["expected_ascending"], f"正序反例校验失败: {forward}"
    return dp, rows, reverse, forward

def show(value):
    if value is None:
        return "-INF"
    return str(value)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1] / "examples/derivations/tree_knapsack_merge.json")
    parser.add_argument("--markdown", type=Path, help="保存 Markdown 推导表")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    dp, rows, reverse, forward = validate(data)
    lines = [
      "# 子树合并逐步推导（构造的教学示意数据，非正式测试样例）", "",
      "数据来源：用户提供《解析.pdf》第3页的专门示意数据。", "",
      "| j | k | 候选公式或跳过原因 | 旧值 | 新值 |",
      "|---:|---:|---|---:|---:|",
    ]
    for j, k, reason, before, after in rows:
        lines.append(f"| {j} | {k} | {reason} | {show(before)} | {show(after)} |")
    lines += [
      "", f"倒序合并的最终状态：`{dp}`", "",
      "## 为什么原地更新要倒序", "",
      f"倒序结果：`{reverse}`；错误的正序结果：`{forward}`。",
      "正序时，刚写入的 dp[1]=5 被再次当作旧状态使用，导致同一孩子收益被加两次。",
      "如果改为独立旧、新数组，遍历方向约束可能不同；不要将此反例误作所有 DP 的通用规则。",
      "", "校验：全部数值由同一转移规则计算，不是凭空填写。", ""
    ]
    text = "\n".join(lines)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()

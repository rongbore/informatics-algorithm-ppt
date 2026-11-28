"""Deterministic ordinary DSU trace generator and replay validator."""
import argparse
import json
from pathlib import Path


def generate_trace(n, operations):
    if type(n) is not int or not 1 <= n <= 100:
        raise ValueError("Trace supports 1..100 nodes")
    if not isinstance(operations, list) or len(operations) > 1000:
        raise ValueError("Invalid operation list")
    parent = list(range(n + 1))
    size = [0] + [1] * n
    steps = []

    def state():
        return {"parent": parent[1:].copy(), "size": size[1:].copy()}

    def record(kind, before, **details):
        steps.append({"index": len(steps), "kind": kind,
                      "operation_index": op_index, "before": before,
                      "after": state(), **details})

    def find(x):
        path = []
        root = x
        while parent[root] != root:
            path.append(root)
            root = parent[root]
        record("find_path", state(), node=x, root=root, path=path + [root])
        for v in reversed(path):
            if parent[v] != root:
                before = state()
                parent[v] = root
                record("compress", before, node=v, root=root)
        return root

    initial = state()
    for op_index, op in enumerate(operations):
        kind = op.get("kind")
        if kind not in ("find", "union", "same"):
            raise ValueError("Unsupported operation")
        nodes = [op.get("x")] if kind == "find" else [op.get("x"), op.get("y")]
        if any(type(v) is not int or not 1 <= v <= n for v in nodes):
            raise ValueError("Node out of range")
        a = find(nodes[0])
        if kind == "find":
            record("result", state(), root=a)
            continue
        b = find(nodes[1])
        if kind == "same":
            record("result", state(), same=a == b)
        elif a == b:
            record("already_connected", state(), root=a)
        else:
            if size[a] > size[b]:
                a, b = b, a
            before = state()
            parent[a] = b
            size[b] += size[a]
            size[a] = 0
            record("union", before, child=a, root=b)
    return {"schema_version": "2.9.0", "algorithm": "dsu_size_compression",
            "n": n, "operations": operations, "initial": initial,
            "steps": steps, "final": state()}


def validate_trace(trace):
    expected = generate_trace(trace["n"], trace["operations"])
    if trace != expected:
        raise ValueError("Trace differs from deterministic replay")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    trace = generate_trace(data["n"], data["operations"])
    validate_trace(trace)
    Path(args.output).write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

"""Render replay-validated ordinary DSU states as standalone SVG frames."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

from dsu_trace_v29 import validate_trace


def svg_frame(state, label, active=(), changed=()):
    parents, sizes = state["parent"], state["size"]
    n = len(parents)
    if not 1 <= n <= 24:
        raise ValueError("Teaching renderer supports 1..24 nodes for legibility")
    roots = [i for i in range(1, n+1) if parents[i-1] == i]
    children = {i: [] for i in range(1, n+1)}
    for i, p in enumerate(parents, 1):
        if i != p:
            children[p].append(i)
    # Allocate horizontal space by leaf count; vertical position is actual depth.
    positions = {}
    def leaves(v):
        return max(1, sum(leaves(c) for c in children[v]))
    total = sum(leaves(r) for r in roots)
    unit = 1080 / total
    def place(v, left, depth):
        span = leaves(v) * unit
        positions[v] = (left + span/2, depth)
        cursor = left
        for c in children[v]:
            place(c, cursor, depth+1)
            cursor += leaves(c)*unit
    left = 100
    for r in roots:
        place(r, left, 0)
        left += leaves(r)*unit
    max_depth = max(d for x,d in positions.values())
    dy = min(104, 300/max(1,max_depth))
    radius = min(25, unit*.34, dy*.32)
    positions = {v:(x,145+d*dy) for v,(x,d) in positions.items()}
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">',
           '<rect width="1280" height="720" fill="#FAFAFA"/>',
           '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#3B5F98"/></marker></defs>',
           '<g font-family="sans-serif" fill="#263445">',
           '<text x="48" y="54" font-size="30" font-weight="bold">Disjoint Set Union</text>',
           f'<text x="48" y="92" font-size="23">{escape(label)}</text>']
    for v,p in enumerate(parents,1):
        if v == p:
            continue
        x,y = positions[v]; a,b = positions[p]
        length = math.hypot(a-x,b-y)
        ux,uy = (a-x)/length,(b-y)/length
        color = "#15803D" if v in changed else "#3B5F98"
        out.append(f'<line x1="{x+ux*radius:.2f}" y1="{y+uy*radius:.2f}" x2="{a-ux*(radius+7):.2f}" y2="{b-uy*(radius+7):.2f}" stroke="{color}" stroke-width="3" marker-end="url(#arrow)"/>')
    for v,(x,y) in positions.items():
        root = parents[v-1] == v
        fill = "#F6B849" if v in active else "#DCEDE2" if root else "#E8F4FB"
        out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{fill}" stroke="#234B6B" stroke-width="2"/>')
        out.append(f'<text x="{x:.2f}" y="{y+6:.2f}" text-anchor="middle" font-size="{min(18,radius):.2f}">{v}</text>')
        if root:
            out.append(f'<text x="{x:.2f}" y="{y-radius-8:.2f}" text-anchor="middle" font-size="14">size={sizes[v-1]}</text>')
    cell = min(72, 1120/n)
    for i,p in enumerate(parents,1):
        x = 80+(i-1)*cell
        fill = "#DCEDE2" if i in changed else "#E8F4FB"
        out.append(f'<rect x="{x:.2f}" y="530" width="{cell-2:.2f}" height="82" rx="4" fill="{fill}"/>')
        out.append(f'<text x="{x+cell/2:.2f}" y="553" text-anchor="middle" font-size="13">p[{i}]</text>')
        out.append(f'<text x="{x+cell/2:.2f}" y="591" text-anchor="middle" font-size="22">{p}</text>')
    out.append('<text x="80" y="659" font-size="18">Arrow: child to parent | Green edge: changed parent | Yellow: active node</text></g></svg>')
    return "\n".join(out)


def render_trace(trace, directory):
    validate_trace(trace)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    frames = []
    def save(state, label, active=(), changed=(), step=None):
        path = directory / f"frame_{len(frames):04d}.svg"
        data = svg_frame(state,label,active,changed).encode("utf-8")
        path.write_bytes(data)
        frames.append({"file":path.name,"sha256":hashlib.sha256(data).hexdigest(),
                       "step_index":step,"label":label})
    save(trace["initial"], "Initial state")
    for step in trace["steps"]:
        kind = step["kind"]
        active = step.get("path", [])
        changed = [i for i,(a,b) in enumerate(zip(step["before"]["parent"],step["after"]["parent"]),1) if a != b]
        if kind == "find_path":
            label = "Find path: " + " -> ".join(map(str,active))
        elif kind == "compress":
            label = f"Compress: {step['node']} -> {step['root']}"
        elif kind == "union":
            label = f"Union: {step['child']} -> {step['root']}"
        elif kind == "already_connected":
            label = f"Already connected: root {step['root']}"
        else:
            label = f"Same set: {step['same']}" if "same" in step else f"Root: {step['root']}"
        save(step["after"],label,active,changed,step["index"])
    manifest = {"schema_version":"2.9.0","frames":frames,
                "trace_sha256":hashlib.sha256(json.dumps(trace,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
                "source_verified":False,"speech_bound":False,"manual_review_required":True}
    (directory/"frames.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    render_trace(json.loads(Path(args.trace).read_text(encoding="utf-8-sig")), args.output_dir)


if __name__ == "__main__":
    main()

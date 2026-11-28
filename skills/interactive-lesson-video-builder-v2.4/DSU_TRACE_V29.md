# V2.9 ordinary DSU trace module

The trace generator supports 1-based ordinary disjoint-set union with union by size and path compression, and operations find, union, same. Equal-size merges attach the first root to the second. Size is stored only at roots; non-root size is zero. A source lesson using a different convention must not be represented as this exact execution.

Run:
    python scripts/dsu_trace_v29.py operations.json trace.json

Example input:
    {"n":4,"operations":[{"kind":"union","x":1,"y":2},{"kind":"union","x":3,"y":4},{"kind":"union","x":2,"y":4},{"kind":"find","x":1}]}

The output records the initial state, each find path, each actual compression, union, query result, and final state. Every step contains before/after parent and size arrays. Replay validation rejects modified traces. Tests independently check root-size and acyclicity invariants.

This module is not yet integrated with PPTX semantic extraction, speech timing or MP4 rendering. The caller must verify that the operation sequence, node numbering, tie-break convention and algorithm variant match the actual source slide and its narration. Do not substitute this ordinary DSU for weighted DSU or food-chain relations. Do not mark a trace as source-verified merely because replay succeeds.

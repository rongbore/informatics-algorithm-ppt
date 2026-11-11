# Trace protocol v1
A trace is a JSON object with `schemaVersion`, `algorithm`, `input`, `events`, and `expectedOutput`. Every event stores a complete snapshot so backward navigation is deterministic.

```json
{
  "schemaVersion": "1.0",
  "algorithm": "sliding-window-maximum",
  "input": {"values": [1,3,-1], "window": 2},
  "expectedOutput": [3,3],
  "events": [{"step":0,"action":"push","cursor":0,"windowStart":0,"queueIndices":[0],"output":[],"message":"加入下标 0","codeLine":null}]
}
```

## Required event fields
- `step`: consecutive nonnegative integer starting at 0
- `action`: `push|pop_back|pop_front|emit|inspect|finish` (extend with namespaced custom actions)
- `cursor`: current input index, integer
- `windowStart`: current visible window start, integer
- `queueIndices`: indices in monotonic queue, front to back
- `output`: emitted answer prefix
- `message`: nonempty Chinese explanation
- `codeLine`: positive integer or null

## Invariants for sliding-window-maximum
- `0 <= cursor < values.length`, `0 <= windowStart <= cursor`.
- Every queue index is unique, in strictly increasing index order, and inside `[windowStart,cursor]`.
- Queue values are strictly decreasing (equal values are removed on push).
- Output grows only on `emit`; emitted maximum is the queue-front value.
- Final output equals independent brute-force oracle.
- Event transitions must match action semantics; structural schema validation alone is not proof of semantic correctness.

For other algorithms define an algorithm-specific snapshot schema and an independent oracle. Avoid inventing execution events.

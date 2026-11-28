import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dsu_trace_v29 import generate_trace, validate_trace


class DsuTraceTests(unittest.TestCase):
    def test_path_compression_and_size(self):
        ops = [{"kind":"union","x":1,"y":2},
               {"kind":"union","x":3,"y":4},
               {"kind":"union","x":2,"y":4},
               {"kind":"find","x":1},
               {"kind":"same","x":1,"y":3}]
        trace = generate_trace(4, ops)
        self.assertTrue(validate_trace(trace))
        compression = [s for s in trace["steps"] if s["kind"] == "compress"]
        self.assertEqual(compression[0]["before"]["parent"], [2,4,4,4])
        self.assertEqual(compression[0]["after"]["parent"], [4,4,4,4])
        self.assertEqual(trace["final"]["size"], [0,0,0,4])
        self.assertTrue(trace["steps"][-1]["same"])

    def test_duplicate_union_does_not_change_size(self):
        trace = generate_trace(2, [{"kind":"union","x":1,"y":2}]*2)
        self.assertEqual(trace["final"]["size"], [0,2])
        self.assertEqual(trace["steps"][-1]["kind"], "already_connected")

    def test_disconnected_and_invalid(self):
        trace = generate_trace(2, [{"kind":"same","x":1,"y":2}])
        self.assertFalse(trace["steps"][-1]["same"])
        for op in [{"kind":"find","x":0}, {"kind":"union","x":1,"y":3}, {"kind":"unknown"}]:
            with self.assertRaises(ValueError):
                generate_trace(2,[op])

    def test_tampered_trace_rejected(self):
        trace = generate_trace(2,[{"kind":"union","x":1,"y":2}])
        bad = copy.deepcopy(trace)
        bad["steps"][-1]["after"]["parent"][0] = 1
        with self.assertRaises(ValueError):
            validate_trace(bad)

    def test_invariants_at_every_step(self):
        trace = generate_trace(8,[{"kind":"union","x":i,"y":i+1} for i in range(1,8)])
        for step in trace["steps"]:
            for state in (step["before"],step["after"]):
                parents = [0]+state["parent"]
                sizes = [0]+state["size"]
                counts = [0]*9
                for node in range(1,9):
                    seen = set()
                    while parents[node] != node:
                        self.assertNotIn(node,seen)
                        seen.add(node)
                        node = parents[node]
                    counts[node] += 1
                self.assertEqual(counts,sizes)

"""Regression checks: visualization state snapshots match Kahn's algorithm and C++ demo."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/trace_toposort.py"
DATA = ROOT / "examples/derivations/toposort_cases.json"

spec = importlib.util.spec_from_file_location("trace_toposort", SCRIPT)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class ToposortTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))
        cls.cases = {x["id"]: x for x in cls.data["cases"]}

    def test_dag_queue_and_state_history(self):
        result = trace.verify_case(self.cases["dag"])
        self.assertFalse(result["cycle"])
        self.assertEqual(result["order"], [1, 2, 3, 4, 6, 5])
        self.assertEqual(result["steps"][0]["queue_after"], [2, 3])
        self.assertEqual(result["steps"][2]["queue_after"], [4, 6])
        self.assertEqual(result["steps"][2]["indegree_after"], [0, 0, 0, 0, 1, 0])
        self.assertEqual(len(result["steps"]), 6)

    def test_partial_cycle_does_not_claim_full_toposort(self):
        result = trace.verify_case(self.cases["cycle"])
        self.assertTrue(result["cycle"])
        self.assertEqual(result["order"], [1])
        self.assertEqual(result["remaining"], [2, 3, 4])
        self.assertEqual(result["steps"][0]["updates"][0]["before"], 2)
        self.assertFalse(result["steps"][0]["updates"][0]["enqueued"])

    def test_multiple_valid_orders_follow_fifo_queue(self):
        result = trace.trace_toposort(3, [[1, 3], [2, 3]])
        self.assertEqual(result["order"], [1, 2, 3])
        self.assertFalse(result["cycle"])

    def test_duplicate_edges_count_as_distinct_dependencies(self):
        result = trace.trace_toposort(2, [[1, 2], [1, 2]])
        self.assertEqual(result["initial_indegree"], [0, 2])
        self.assertEqual(result["steps"][0]["queue_after"], [2])
        self.assertEqual(result["order"], [1, 2])

    def test_self_loop_prevents_topological_order(self):
        result = trace.trace_toposort(2, [[1, 1]])
        self.assertTrue(result["cycle"])
        self.assertEqual(result["order"], [2])
        self.assertEqual(result["remaining"], [1])

    def test_invalid_graph_rejected(self):
        for edges in ([[0, 1]], [[1, 4]], [[True, 1]], [[1]]):
            with self.subTest(edges=edges):
                with self.assertRaises(ValueError):
                    trace.trace_toposort(3, edges)
        with self.assertRaises(ValueError):
            trace.trace_toposort(0, [])

    def test_tampered_expected_states_rejected(self):
        example = dict(self.cases["dag"])
        example["expected_queue_after"] = [[]]
        with self.assertRaises(ValueError):
            trace.verify_case(example)

    def test_markdown_has_provenance_all_steps_and_cycle_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "toposort-trace.md"
            latex = Path(tmp) / "toposort-tables.tex"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--data", str(DATA),
                 "--markdown", str(dest), "--latex", str(latex)], check=True, capture_output=True,
                encoding="utf-8", text=True,
            )
            content = dest.read_text(encoding="utf-8")
            self.assertEqual(content + "\n", completed.stdout)
            self.assertIn("教学", content)
            self.assertIn("1→2: 1→0（入队）", content)
            self.assertIn("存在有向环", content)
            self.assertIn("拓扑序不一定唯一", content)
            tex = latex.read_text(encoding="utf-8")
            self.assertIn(r"\\begin{longtable}", tex)
            self.assertIn("1→2: 1→0", tex)
            self.assertIn(r"\\endfirsthead", tex)
            self.assertIn("存在环", tex)

    def test_legacy_sources_match_canonical(self):
        repository = ROOT.parents[2]
        legacy = repository / "skills" / "cpp-lesson-pdf"
        for relative in (
            "scripts/trace_toposort.py",
            "examples/derivations/toposort_cases.json",
            "examples/derivations/toposort_visual.tex",
            "references/TOPOSORT-TRACE-WORKFLOW.md",
        ):
            with self.subTest(relative=relative):
                self.assertEqual((ROOT / relative).read_bytes(),
                                 (legacy / relative).read_bytes())

    @unittest.skipUnless(shutil.which("g++"), "g++ not installed")
    def test_actual_cpp_demo_matches_trace(self):
        cpp = ROOT / "examples/code/toposort_demo.cpp"
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "topodemo"
            subprocess.run(["g++", "-std=c++17", "-O2", str(cpp),
                            "-o", str(executable)], check=True, capture_output=True)
            for example in self.data["cases"]:
                with self.subTest(case=example["id"]):
                    n, edges = example["n"], example["edges"]
                    given = "\n".join([f"{n} {len(edges)}"] +
                                      [f"{u} {v}" for u, v in edges]) + "\n"
                    output = subprocess.run([str(executable)], input=given,
                                            check=True, capture_output=True,
                                            text=True, encoding="utf-8").stdout.strip()
                    expected = "-1" if example["expected_cycle"] else " ".join(
                        str(x) for x in example["expected_order"]
                    )
                    self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()

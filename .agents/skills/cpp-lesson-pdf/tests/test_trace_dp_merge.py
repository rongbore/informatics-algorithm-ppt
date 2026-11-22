"""Regression checks for documented v1.3 tree-knapsack trace and Skill entrypoints."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]  # repository root: .agents/skills/cpp-lesson-pdf -> ../../..
SCRIPT = ROOT / "scripts" / "trace_dp_merge.py"
DATA = ROOT / "examples" / "derivations" / "tree_knapsack_merge.json"

spec = importlib.util.spec_from_file_location("trace_dp_merge", SCRIPT)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class TraceDpMergeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_documented_trace_and_counterexample(self):
        final, rows, descending, ascending = trace.validate(self.data)
        self.assertEqual(final, [0, 5, 8, 10, 13])
        self.assertEqual(len(rows), 7)
        self.assertEqual(descending, [0, 5, 7])
        self.assertEqual(ascending, [0, 5, 10])

    def test_connection_cost_paid_once_when_child_selected(self):
        final, rows = trace.merge([0, 2], [0, 5], 1, 2, descending=True)
        self.assertEqual(final, [0, 4, 6])

    def test_unreachable_state_not_used_in_combination(self):
        final, rows = trace.merge([0, None], [0, 5], 1, 2, descending=True)
        self.assertEqual(final, [0, 4, None])
        self.assertTrue(any("不可达" in row[2] for row in rows))

    def test_no_child_selection_keeps_previous_best(self):
        final, _ = trace.merge([0, 5, 8], [0, 4, 7], 2, 4, descending=True)
        self.assertEqual(final[:3], [0, 5, 8])

    def test_trace_markdown_is_created_and_contains_computations(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "trace.md"
            run = subprocess.run(
                [sys.executable, str(SCRIPT), "--data", str(DATA), "--markdown", str(output)],
                capture_output=True, text=True, encoding="utf-8", check=True,
            )
            txt = output.read_text(encoding="utf-8")
            self.assertIn("8 + 7 - 2 = 13", txt)
            self.assertIn("倒序合并", txt)
            self.assertIn("正序", txt)
            self.assertIn("教学示意", txt)

    def test_required_references_and_legacy_copy(self):
        required = (
            "SKILL.md",
            "references/DEEP-REASONING-STEPS.md",
            "references/VISUAL-DERIVATION-STANDARD.md",
            "scripts/trace_dp_merge.py",
            "examples/derivations/tree_knapsack_merge.json",
            "examples/derivations/tree_knapsack_visual.tex",
        )
        for name in required:
            self.assertTrue((ROOT / name).is_file(), name)
            legacy = REPO / "skills" / "cpp-lesson-pdf" / name
            self.assertTrue(legacy.is_file(), str(legacy))
        for name in required[1:]:
            self.assertEqual((ROOT / name).read_bytes(),
                             (REPO / "skills" / "cpp-lesson-pdf" / name).read_bytes(), name)
        entry = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("DEEP-REASONING-STEPS.md", entry)
        self.assertIn("VISUAL-DERIVATION-STANDARD.md", entry)


if __name__ == "__main__":
    unittest.main()

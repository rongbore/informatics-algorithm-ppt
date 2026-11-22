"""Regression tests for v1.3.2 clean code-page presentation."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
LEGACY = REPO / "skills" / "cpp-lesson-pdf"


class CodePresentationPolicyTests(unittest.TestCase):
    def test_canonical_minted_listing_has_no_line_number_options(self):
        style = (ROOT / "templates/lesson-style.sty").read_text(encoding="utf-8")
        match = re.search(r"minted options=\{([^}]*)\}", style)
        self.assertIsNotNone(match)
        self.assertNotIn("linenos", match.group(1))
        self.assertNotIn("numbersep", match.group(1))

    def test_legacy_listings_style_disables_numbers_and_gutter(self):
        style = (LEGACY / "templates/lesson-style.sty").read_text(encoding="utf-8")
        self.assertIn("numbers=none", style)
        self.assertNotIn("numbers=left", style)
        self.assertNotIn("numbers=right", style)
        self.assertNotIn("numberstyle=", style)
        self.assertNotIn("numbersep=", style)

    def test_no_layout_explanation_panel_in_student_template(self):
        template = (ROOT / "templates/main.tex").read_text(encoding="utf-8")
        self.assertNotIn("排版说明", template)
        prompt = (ROOT / "references/MASTER-PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("不得出现“排版说明”", prompt)
        self.assertIn("代码标题后直接进入代码框", prompt)

    def test_entrypoints_state_both_user_overrides(self):
        for path in (
            ROOT / "SKILL.md",
            ROOT / "references/CODE-COMMENT-RULES.md",
            ROOT / "references/QA-CHECKLIST.md",
            LEGACY / "SKILL.md",
            LEGACY / "references/PROMPT.md",
        ):
            with self.subTest(path=str(path)):
                text = path.read_text(encoding="utf-8")
                self.assertIn("不显示", text)
                self.assertIn("排版说明", text)


if __name__ == "__main__":
    unittest.main()

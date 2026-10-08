"""Keep welcome actions compact without changing the welcome flow."""
import ast
from pathlib import Path
import re
import unittest


class WelcomeActionLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "streamlit_app" / "fce_component.py").read_text(encoding="utf-8")

    def test_final_actions_wrap_instead_of_filling_fractional_columns(self):
        rule = re.search(r"\.ini-fce-final-actions\s*\{([^}]+)\}", self.source).group(1)
        self.assertIn("display: flex", rule)
        self.assertIn("flex-wrap: wrap", rule)
        self.assertIn("justify-content: center", rule)
        self.assertNotIn("grid-template-columns", rule)

    def test_buttons_fit_content_and_do_not_grow_on_mobile(self):
        self.assertIn("width: fit-content; max-width: 100%", self.source)
        self.assertIn(".ini-fce-overlay.is-mobile .ini-fce-final-actions .ini-fce-button { flex: 0 1 auto; }", self.source)

    def test_labels_and_navigation_are_preserved(self):
        ast.parse(self.source)
        for label in ("Replay", "Take Me to Introduction", "Take Me to New Chat"):
            self.assertIn(label, self.source)
        for action in ("replay", "go-introduction", "go-chat"):
            self.assertIn(f'data-action="{action}"', self.source)

    def test_replay_is_an_accessible_icon(self):
        self.assertIn('aria-label="Replay welcome" title="Replay welcome"', self.source)
        self.assertIn('class="ini-fce-button ini-fce-replay"', self.source)
        self.assertNotIn('data-action="replay">Replay</button>', self.source)

    def test_navigation_buttons_have_matching_dimensions(self):
        self.assertIn('.ini-fce-nav-action { width: 184px; height: 42px;', self.source)
        self.assertEqual(self.source.count('class="ini-fce-button ini-fce-nav-action'), 2)


if __name__ == "__main__":
    unittest.main()

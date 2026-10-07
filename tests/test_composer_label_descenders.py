"""Prevent Interrogate/Illustrate labels from clipping letter descenders."""
from pathlib import Path
import re
import unittest


class ComposerLabelDescenderTests(unittest.TestCase):
    def test_landing_and_active_composer_labels_have_vertical_room(self):
        source = (Path(__file__).resolve().parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        for position, size in (("top", 14), ("bottom", 12)):
            with self.subTest(position=position):
                pattern = rf"\.st-key-nc_{position}_interrogate[^{{]+p,.*?font-size: {size}px !important;.*?line-height: 1\.4 !important;"
                self.assertRegex(source, re.compile(pattern, re.S))
                for action in ("interrogate", "illustrate"):
                    self.assertIn(f'.st-key-nc_{position}_{action} button [data-testid="stMarkdownContainer"]', source)


if __name__ == "__main__":
    unittest.main()

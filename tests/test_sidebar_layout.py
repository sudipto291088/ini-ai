from pathlib import Path
import re
import unittest


class SidebarLayoutTests(unittest.TestCase):
    def test_sidebar_selectors_support_current_and_legacy_streamlit(self):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        self.assertNotRegex(source, r'\[data-testid="stSidebar"\]\[aria-expanded=')
        self.assertIn('[data-testid="stSidebar"]:is([aria-expanded="true"], [data-collapsed="false"])', source)
        self.assertIn('[data-testid="stSidebar"]:is([aria-expanded="false"], [data-collapsed="true"])', source)

    def test_desktop_sidebar_and_composer_share_the_same_width(self):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        self.assertIn('width: 288px !important;', source)
        self.assertIn('left: calc(50% + 144px);', source)
        self.assertIn('width: min(980px, calc(100vw - 320px));', source)


if __name__ == "__main__":
    unittest.main()

"""Keep v0.1.8's release surfaces and historical notes consistent."""
import ast
from datetime import date, timedelta
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


class ReleaseV018Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "streamlit_app/app.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_current_release_date_and_announcement_window(self):
        names = {"NEW_CHAT_UPDATE_VERSION", "NEW_CHAT_UPDATE_RELEASE_DATE", "NEW_CHAT_UPDATE_WINDOW_DAYS"}
        scope = {"date": date, "timedelta": timedelta}
        nodes = [n for n in self.tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id in names for t in n.targets)]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "release_constants", "exec"), scope)
        self.assertEqual(scope["NEW_CHAT_UPDATE_VERSION"], "v0.1.8")
        self.assertEqual(scope["NEW_CHAT_UPDATE_RELEASE_DATE"], date(2026, 10, 31))
        self.assertEqual(scope["NEW_CHAT_UPDATE_WINDOW_DAYS"], 7)

    def test_catalog_preserves_history_and_selects_new_release(self):
        catalog_node = next(n for n in ast.walk(self.tree) if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == "intro_releases" for t in n.targets))
        catalog = ast.literal_eval(catalog_node.value)
        self.assertEqual(len(catalog), 8)
        self.assertEqual(catalog["v0.1.8"]["date"], "October 31, 2026")
        self.assertEqual(catalog["v0.1.7"]["date"], "September 24, 2026")
        self.assertEqual(len(catalog["v0.1.8"]["items"]), 8)
        self.assertNotIn("v0.1.9", catalog)
        self.assertIn('intro_selected_release = "v0.1.8"', self.source)
        self.assertIn('if version == "v0.1.8":', self.source)
        self.assertIn('"v0.1.9",', self.source)

    def test_badge_and_notice_have_no_stale_current_version(self):
        self.assertIn('class="badge">v0.1.8', self.source)
        self.assertIn('"ini-new-chat-update-v018-"', self.source)
        notice = (ROOT / "streamlit_app/new_chat_update_component.py").read_text(encoding="utf-8")
        ast.parse(notice)
        self.assertIn('version: str = "v0.1.8"', notice)
        self.assertIn('NEW_CHAT_UPDATE_COMPONENT_VERSION = 26', notice)
        self.assertNotIn('v017', notice)

    def test_retrieval_user_agents_match_release(self):
        for source in ("arxiv", "crossref", "datacite", "doaj", "europe_pmc", "openalex",
                       "wikibooks", "wikidata", "wikipedia", "wikiversity"):
            with self.subTest(source=source):
                content = (ROOT / "api" / f"{source}_knowledge.py").read_text(encoding="utf-8")
                self.assertIn("InI.ai/0.1.8", content)
                self.assertNotIn("InI.ai/0.1.7", content)


if __name__ == "__main__":
    unittest.main()

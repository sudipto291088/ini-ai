from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from streamlit_app.privacy_page import PRIVACY_TEXT, show_public_privacy_page


class PrivacyPageTests(unittest.TestCase):
    def test_privacy_route_renders_without_login_or_storage(self):
        app = AppTest.from_string(
            "from streamlit_app.privacy_page import show_public_privacy_page\n"
            "import streamlit as st\n"
            "if show_public_privacy_page(): st.stop()\n"
            "raise RuntimeError('Private app must not run')\n"
        )
        app.query_params["page"] = "privacy"
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "InI.ai Privacy Policy")

    def test_other_routes_do_not_render_privacy(self):
        with patch("streamlit_app.privacy_page.st") as streamlit:
            streamlit.query_params.get.return_value = "chat"
            self.assertFalse(show_public_privacy_page())
            streamlit.title.assert_not_called()

    def test_both_entry_points_handle_privacy_before_auth(self):
        root = Path(__file__).parents[1]
        for filename in ("app.py", "auth_test_app.py"):
            text = (root / "streamlit_app" / filename).read_text(encoding="utf-8")
            self.assertLess(text.index("if show_public_privacy_page():"), text.index("require_google_account()"))

    def test_notice_discloses_processing_and_limits(self):
        for phrase in ("OpenAI", "Neon", "Legacy visitor mode", "not end-to-end encryption",
                       "no automatic conversation-expiry", "openid, email and profile",
                       "sudiptoini@gmail.com", "provider logs"):
            self.assertIn(phrase, PRIVACY_TEXT)

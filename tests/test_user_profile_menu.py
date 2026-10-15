from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
from streamlit_app.user_profile_menu import profile_identity, PROFILE_TRIGGER_CSS


class UserProfileMenuTests(unittest.TestCase):
    def test_profile_uses_regular_weight_with_larger_avatar(self):
        self.assertIn("font-weight:400", PROFILE_TRIGGER_CSS)
        self.assertIn("width:30px;height:30px", PROFILE_TRIGGER_CSS)
        self.assertNotIn("font-weight:650", PROFILE_TRIGGER_CSS)

    def test_signed_in_google_name_and_initials(self):
        self.assertEqual(profile_identity({"is_logged_in": True, "name": "Sudipto Bhadra"}),
                         ("Sudipto Bhadra", "SB"))
        self.assertEqual(profile_identity({"is_logged_in": True, "given_name": "Sudipto"}),
                         ("Sudipto", "S"))

    def test_missing_name_does_not_expose_or_parse_email(self):
        self.assertEqual(profile_identity({"is_logged_in": True, "email": "private@example.com"}),
                         ("User profile", "U"))
        self.assertEqual(profile_identity({"is_logged_in": False, "name": "Prior account"}),
                         ("User profile", "U"))

    def test_profile_name_is_plain_text_not_markdown(self):
        app = AppTest.from_string('''
import streamlit as st
from unittest.mock import patch
from streamlit_app.user_profile_menu import render_user_profile_menu
with patch("streamlit_app.user_profile_menu.st.user", {"is_logged_in": True, "name": "A [link](https://example.com)"}):
    render_user_profile_menu(can_sign_out=True, on_exit=lambda: None)
''').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.text[0].value, "A [link](https://example.com)")

    def app(self, signed_in=True):
        return AppTest.from_string(f'''
import streamlit as st
from streamlit_app.user_profile_menu import render_user_profile_menu
def exit_app():
    st.session_state["exit_called"] = True
with st.sidebar:
    render_user_profile_menu(can_sign_out={signed_in!r}, on_exit=exit_app)
''').run()

    def test_exit_app_uses_the_signout_callback(self):
        app = self.app()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.button(key="account_profile_exit").label, "Exit")
        app.button(key="account_profile_exit").click().run()
        self.assertTrue(app.session_state["exit_called"])

    def test_local_developer_cannot_trigger_account_logout(self):
        app = self.app(False)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.button(key="account_profile_exit").disabled)

    def test_profile_has_no_three_dots_and_keeps_red_shortcut(self):
        root = Path(__file__).resolve().parents[1]
        helper = (root / "streamlit_app/user_profile_menu.py").read_text()
        app = (root / "streamlit_app/app.py").read_text(encoding="utf-8-sig")
        self.assertNotIn("⋮", helper)
        self.assertNotIn('class="ini-sidebar-profile__chevron"', app)
        self.assertIn('key="account_signout"', app)
        self.assertIn('on_exit=sign_out', app)


if __name__ == "__main__":
    unittest.main()

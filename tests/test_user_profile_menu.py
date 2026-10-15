from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class UserProfileMenuTests(unittest.TestCase):
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
        self.assertEqual(app.button(key="account_profile_exit").label, "Exit app")
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

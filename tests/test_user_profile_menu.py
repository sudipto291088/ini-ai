from pathlib import Path
import ast
import importlib
import sys
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from streamlit_app.user_profile_menu import profile_identity, profile_header_html, PROFILE_TRIGGER_CSS


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
        header = profile_header_html("A [link](https://example.com)", "A", True)
        self.assertIn("A [link](https://example.com)", header)
        self.assertNotIn("<a ", header)
        self.assertIn("&lt;img", profile_header_html('<img src=x onerror="bad">', "A", True))

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

    def test_settings_opens_the_supplied_account_panel(self):
        app = AppTest.from_string('''
import streamlit as st
from streamlit_app.user_profile_menu import render_user_profile_menu
def settings():
    st.session_state["settings_opened"] = True
render_user_profile_menu(can_sign_out=True, on_exit=lambda: None, on_settings=settings)
''').run()
        self.assertFalse(app.button(key="account_profile_settings").disabled)
        app.button(key="account_profile_settings").click().run()
        self.assertTrue(app.session_state["settings_opened"])
        self.assertFalse(app.session_state["account_profile_menu"])

    def test_running_app_reloads_a_cached_legacy_profile_helper(self):
        from streamlit_app import user_profile_menu as helper
        source = (Path(__file__).resolve().parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        nodes = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "user_profile_menu" for target in node.targets
            ):
                nodes.append(node)
            elif isinstance(node, ast.If) and "PROFILE_MENU_VERSION" in ast.unparse(node.test):
                nodes.append(node)
            elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "render_user_profile_menu" for target in node.targets
            ):
                nodes.append(node)
        def legacy(*, can_sign_out, on_exit):
            raise AssertionError("The cached legacy renderer must be replaced")
        namespace = {"importlib": importlib}
        with patch.object(helper, "PROFILE_MENU_VERSION", 0), patch.object(helper, "render_user_profile_menu", legacy):
            exec(compile(ast.Module(body=nodes, type_ignores=[]), "profile_bootstrap", "exec"), namespace)
            self.assertGreaterEqual(namespace["user_profile_menu"].PROFILE_MENU_VERSION, 3)
            self.assertIn("on_settings", namespace["render_user_profile_menu"].__kwdefaults__)

    def test_bootstrap_imports_registered_module_when_package_attribute_is_stale(self):
        import streamlit_app
        from streamlit_app import user_profile_menu as helper
        source = (Path(__file__).resolve().parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8-sig")
        nodes = [node for node in ast.parse(source).body if (
            isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {
                "user_profile_menu", "render_user_profile_menu"
            } for target in node.targets)
        ) or (isinstance(node, ast.If) and "PROFILE_MENU_VERSION" in ast.unparse(node.test))]
        namespace = {"importlib": importlib}
        with patch.dict(sys.modules), patch.object(streamlit_app, "user_profile_menu", helper):
            sys.modules.pop("streamlit_app.user_profile_menu", None)
            exec(compile(ast.Module(body=nodes, type_ignores=[]), "profile_bootstrap", "exec"), namespace)
            self.assertIs(namespace["user_profile_menu"], sys.modules["streamlit_app.user_profile_menu"])
            self.assertIn("on_settings", namespace["render_user_profile_menu"].__kwdefaults__)

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

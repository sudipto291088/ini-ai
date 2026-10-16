import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from streamlit_app import account_data, account_settings, storage_sqlite as storage
from streamlit_app.account_identity import google_owner_id


class AccountDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        db = patch.object(storage, "DB_PATH", str(Path(self.temp.name) / "settings.db"))
        env = patch.dict(os.environ, {"INI_STORAGE_BACKEND": "sqlite"})
        db.start()
        env.start()
        self.addCleanup(db.stop)
        self.addCleanup(env.stop)
        storage.init_db()
        storage.save_session("B", "private-b", "Other account", "today", [{"content": "B-PRIVATE"}])
        storage.save_curriculum("B", "course-b", {"subject": "B-PRIVATE"})
        for i in range(61):
            storage.save_session("A", f"chat-a-{i}", f"Chat {i}", "today", [{"content": "Hello π"}])
        storage.save_curriculum("A", "course-a", {"subject": "Quantum computing"})

    def test_export_includes_every_owned_chat_and_no_other_accounts(self):
        data = account_data.export_conversations("A")
        result = json.loads(data)
        self.assertEqual(len(result["conversations"]), 61)
        self.assertEqual(len(result["subject_learning"]), 1)
        self.assertIn("π", data.decode())
        self.assertNotIn("B-PRIVATE", data.decode())
        self.assertEqual(account_data.conversation_summary("A"), {"conversations": 61, "curricula": 1})

    def test_delete_is_owner_scoped_and_covers_attached_curricula(self):
        account_data.delete_all_conversations("A")
        self.assertEqual(account_data.conversation_summary("A"), {"conversations": 0, "curricula": 0})
        self.assertEqual(account_data.conversation_summary("B"), {"conversations": 1, "curricula": 1})
        self.assertIsNotNone(storage.load_session("B", "private-b"))

    def test_failed_delete_rolls_back_the_whole_operation(self):
        with storage._conn() as c:
            c.execute("CREATE TRIGGER block_delete BEFORE DELETE ON learning_sessions BEGIN SELECT RAISE(ABORT, 'blocked'); END")
            c.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            account_data.delete_all_conversations("A")
        self.assertEqual(account_data.conversation_summary("A"), {"conversations": 61, "curricula": 1})

    def test_missing_owner_is_rejected_before_opening_storage(self):
        with patch.object(storage, "_conn") as connect:
            for function in (account_data.conversation_summary, account_data.export_conversations,
                             account_data.delete_all_conversations):
                with self.assertRaises(ValueError):
                    function("")
            connect.assert_not_called()


class SettingsAuthenticationTests(unittest.TestCase):
    def test_dialog_checks_validated_identity_and_expected_account(self):
        claims = {"is_logged_in": True, "iss": "https://accounts.google.com", "aud": "client",
                  "sub": "account-a", "email_verified": True, "exp": time.time() + 3600}
        owner = google_owner_id(claims, "client")
        secrets = {"auth": {"google": {"client_id": "client"}}}
        with patch.object(account_settings.st, "user", claims), patch.object(
            account_settings.st, "secrets", secrets
        ), patch.object(account_settings.st, "session_state", {"_authenticated_owner": owner}):
            self.assertEqual(account_settings._current_owner(owner), owner)
            self.assertIsNone(account_settings._current_owner("different-account"))
            claims["exp"] = time.time() - 1
            self.assertIsNone(account_settings._current_owner(owner))

    def test_delete_clears_active_chat_and_export_before_next_run(self):
        state = {"chat": {"private": "old"}, "_ini_settings_export": {"data": b"private"},
                 "_authenticated_owner": "A"}
        params = {"page": "chat", "chat_sid": "old"}
        with patch.object(account_settings.st, "session_state", state), patch.object(
            account_settings.st, "query_params", params
        ), patch.object(account_settings.st, "rerun") as rerun:
            account_settings._after_delete("A")
        self.assertNotIn("chat", state)
        self.assertNotIn("_ini_settings_export", state)
        self.assertEqual(state["visitor_id"], "A")
        self.assertEqual(params, {})
        rerun.assert_called_once()


SETTINGS_TEST_APP = '''
import streamlit as st
from unittest.mock import patch
from streamlit_app import account_settings as settings
def current_owner(expected=None):
    return None if st.session_state.get("expired") else "A"
def delete(owner):
    st.session_state["deleted_owner"] = owner
def exported(owner):
    st.session_state["exported_owner"] = owner
    return b'{"conversations": []}'
with patch.object(settings, "_current_owner", current_owner), patch.object(settings.st, "user", {
    "is_logged_in": True, "name": "Alex Morgan", "email": "alex@example.com"
}), patch.object(settings, "conversation_summary", return_value={"conversations": 3, "curricula": 1}), \\
     patch.object(settings, "delete_all_conversations", delete), patch.object(settings, "export_conversations", exported):
    settings.render_settings_content("A", on_deleted=lambda owner: st.session_state.update(deletion_done=True))
'''


class SettingsInterfaceTests(unittest.TestCase):
    def test_deletion_requires_exact_confirmation(self):
        app = AppTest.from_string(SETTINGS_TEST_APP).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.button(key="ini_settings_confirm_delete").disabled)
        app.text_input(key="ini_settings_delete_phrase").set_value("delete").run()
        self.assertTrue(app.button(key="ini_settings_confirm_delete").disabled)
        app.text_input(key="ini_settings_delete_phrase").set_value("DELETE").run()
        self.assertFalse(app.button(key="ini_settings_confirm_delete").disabled)
        app.button(key="ini_settings_confirm_delete").click().run()
        self.assertEqual(app.session_state["deleted_owner"], "A")
        self.assertTrue(app.session_state["deletion_done"])

    def test_export_is_prepared_for_current_account_only(self):
        app = AppTest.from_string(SETTINGS_TEST_APP).run()
        app.button(key="ini_settings_prepare").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["exported_owner"], "A")
        self.assertEqual(app.session_state["_ini_settings_export"]["owner"], "A")

    def test_expired_identity_blocks_dialog_actions(self):
        app = AppTest.from_string(SETTINGS_TEST_APP).run()
        app.session_state["expired"] = True
        app.run()
        self.assertEqual(len(app.error), 1)
        self.assertEqual(len(app.button), 0)

    def test_prepared_export_from_another_account_is_not_exposed(self):
        app = AppTest.from_string(SETTINGS_TEST_APP).run()
        app.session_state["_ini_settings_export"] = {"owner": "B", "data": b"B-PRIVATE"}
        app.run()
        self.assertEqual(len(app.get("download_button")), 0)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit_app.account_identity import bind_account_state, google_configured, google_owner_id
from streamlit_app import storage_sqlite as storage


class AccountIdentityTests(unittest.TestCase):
    def claims(self, subject="account-a"):
        return {"is_logged_in": True, "iss": "https://accounts.google.com", "aud": "client",
                "sub": subject, "email_verified": True, "exp": 2000}

    def test_owner_is_stable_and_distinct(self):
        a = google_owner_id(self.claims(), "client", now=1000)
        self.assertTrue(a.startswith("google-"))
        self.assertEqual(len(a), 71)
        self.assertNotEqual(a, google_owner_id(self.claims("account-b"), "client", now=1000))
        renamed = {**self.claims(), "email": "new@example.com", "name": "New name"}
        self.assertEqual(a, google_owner_id(renamed, "client", now=1000))

    def test_invalid_claims_fail_closed(self):
        for field, value in (("is_logged_in", False), ("iss", "attacker.example"),
                             ("aud", "other"), ("sub", ""), ("email_verified", False),
                             ("exp", 1000), ("exp", "nan"), ("exp", "inf"), ("exp", None)):
            with self.subTest(field=field, value=value):
                self.assertIsNone(google_owner_id({**self.claims(), field: value}, "client", now=1000))

    def test_multiple_audiences_require_authorized_party(self):
        claims = {**self.claims(), "aud": ["client", "other"]}
        self.assertIsNone(google_owner_id(claims, "client", now=1000))
        self.assertIsNotNone(google_owner_id({**claims, "azp": "client"}, "client", now=1000))

    def test_switch_clears_previous_conversation_but_same_account_preserves_it(self):
        state = {"visitor_id": "legacy-url", "messages": ["private"], "qc_state": {"subject": "A"}}
        bind_account_state(state, "google-owner-a")
        self.assertNotIn("messages", state)
        state["messages"] = ["account A"]
        bind_account_state(state, "google-owner-a")
        self.assertEqual(state["messages"], ["account A"])
        bind_account_state(state, "google-owner-b")
        self.assertNotIn("messages", state)

    def test_configuration_must_be_google_and_have_secure_redirect(self):
        config = {"auth": {"redirect_uri": "http://localhost:8501/oauth2callback",
            "cookie_secret": "a" * 64, "google": {"client_id": "client", "client_secret": "secret",
            "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration"}}}
        self.assertTrue(google_configured(config))
        self.assertFalse(google_configured({}))
        for redirect in ("http://public.example/oauth2callback", "https://example.com/other",
                         "https://example.com/oauth2callback?visitor=stolen"):
            config["auth"]["redirect_uri"] = redirect
            self.assertFalse(google_configured(config))

    def test_account_cannot_read_rename_delete_overwrite_or_claim_legacy_chats(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(storage, "DB_PATH", os.path.join(temp, "test.db")):
            storage.init_db()
            a = google_owner_id(self.claims(), "client", now=1000)
            b = google_owner_id(self.claims("account-b"), "client", now=1000)
            storage.save_session(a, "chat-a", "Private", "now", [{"content": "private"}])
            storage.save_session("legacy-url", "legacy", "Old", "now", [])
            self.assertIsNone(storage.load_session(b, "chat-a"))
            self.assertIsNone(storage.load_session(a, "legacy"))
            storage.rename_session(b, "chat-a", "Hijacked")
            storage.delete_session(b, "chat-a")
            storage.save_session(b, "chat-a", "Hijacked", "now", [])
            self.assertEqual(storage.load_session(a, "chat-a")["title"], "Private")
            storage.save_curriculum(a, "qc-a", {"subject": "Statistics"})
            self.assertIsNone(storage.load_curriculum(b, "qc-a"))
            storage.save_curriculum(b, "qc-a", {"subject": "Hijacked"})
            self.assertEqual(storage.load_curriculum(a, "qc-a")["subject"], "Statistics")

    def test_entrypoint_gates_before_database_and_does_not_trust_url_identity(self):
        source = Path("streamlit_app/app.py").read_text(encoding="utf-8")
        self.assertLess(source.index("visitor_id = require_google_account()"), source.index("init_db()"))
        self.assertNotIn('visitor_param = st.query_params.get("visitor")', source)
        self.assertNotIn('st.query_params["visitor"] =', source)
        self.assertNotIn('"visitor": st.session_state.visitor_id', source)


if __name__ == "__main__":
    unittest.main()

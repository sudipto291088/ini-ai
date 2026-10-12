"""Opt-in real PostgreSQL contract test; requires private INI_DATABASE_URL.

Uses random synthetic owners and IDs, never reads existing users' records.
"""
import os
import unittest
import uuid
from unittest.mock import patch
from streamlit_app import storage_sqlite as storage


@unittest.skipUnless(os.environ.get("INI_DATABASE_URL"), "Private PostgreSQL URL not configured")
class LivePostgresContractTests(unittest.TestCase):
    def test_persistence_and_owner_isolation(self):
        token = uuid.uuid4().hex
        owner, other = "test-A-" + token, "test-B-" + token
        sid, cid = "test-chat-" + token, "test-course-" + token
        with patch.dict(os.environ, {"INI_STORAGE_BACKEND": "postgres"}):
            storage.init_db()
            try:
                storage.save_session(owner, sid, "Statistics", "2026-10-12", [{"role": "user", "content": "test"}])
                storage.save_curriculum(owner, cid, {"subject": "Statistics", "understood": [0]})
                self.assertIsNone(storage.load_session(other, sid))
                self.assertIsNone(storage.load_curriculum(other, cid))
                storage.rename_session(other, sid, "stolen")
                storage.delete_session(other, sid)
                storage.save_session(other, sid, "stolen", "today", [])
                storage.save_curriculum(other, cid, {"subject": "stolen"})
                self.assertEqual(storage.load_session(owner, sid)["title"], "Statistics")
                self.assertEqual(storage.load_curriculum(owner, cid)["understood"], [0])
                # A fresh connection pool simulates application-process state loss.
                from streamlit_app.storage_postgres import _pool
                _pool(os.environ["INI_DATABASE_URL"]).close()
                _pool.cache_clear()
                self.assertEqual(storage.load_session(owner, sid)["messages"][0]["content"], "test")
                self.assertEqual(storage.load_curriculum(owner, cid)["understood"], [0])
            finally:
                storage.delete_session(owner, sid)
                with storage._conn() as c:
                    c.execute("DELETE FROM question_curricula WHERE visitor_id=? AND curriculum_id=?", (owner, cid))
                    c.commit()

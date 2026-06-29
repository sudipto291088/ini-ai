import os
import sqlite3
import tempfile
import unittest

from streamlit_app import storage_sqlite


class StoragePrivacyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = storage_sqlite.DB_PATH
        storage_sqlite.DB_PATH = os.path.join(
            self.temp_dir.name,
            "sessions.db",
        )

    def tearDown(self) -> None:
        storage_sqlite.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_visitors_cannot_access_or_modify_each_others_sessions(self) -> None:
        storage_sqlite.init_db()
        storage_sqlite.save_session(
            "visitor-A",
            "chat-a",
            "A chat",
            "2026-06-28",
            {"topic": "A"},
        )
        storage_sqlite.save_session(
            "visitor-B",
            "chat-b",
            "B chat",
            "2026-06-28",
            {"topic": "B"},
        )

        self.assertEqual(
            [row[0] for row in storage_sqlite.list_sessions("visitor-A")],
            ["chat-a"],
        )
        self.assertEqual(
            [row[0] for row in storage_sqlite.list_sessions("visitor-B")],
            ["chat-b"],
        )
        self.assertIsNone(storage_sqlite.load_session("visitor-B", "chat-a"))

        storage_sqlite.rename_session(
            "visitor-B",
            "chat-a",
            "Hijacked",
        )
        storage_sqlite.delete_session("visitor-B", "chat-a")
        storage_sqlite.save_session(
            "visitor-B",
            "chat-a",
            "Stolen",
            "2026-06-28",
            {},
        )

        owner_session = storage_sqlite.load_session("visitor-A", "chat-a")
        self.assertIsNotNone(owner_session)
        self.assertEqual(owner_session["title"], "A chat")
        self.assertIsNone(storage_sqlite.load_session("visitor-B", "chat-a"))

    def test_legacy_unowned_sessions_are_not_exposed(self) -> None:
        connection = sqlite3.connect(storage_sqlite.DB_PATH)
        try:
            connection.execute(
                """
                CREATE TABLE learning_sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    messages_json TEXT
                )
                """
            )
            connection.execute(
                """
                INSERT INTO learning_sessions
                    (session_id, title, created_at, updated_at, messages_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("legacy", "Legacy", "old", "old", "[]"),
            )
            connection.commit()
        finally:
            connection.close()

        storage_sqlite.init_db()

        self.assertEqual(storage_sqlite.list_sessions("visitor-A"), [])
        self.assertIsNone(storage_sqlite.load_session("visitor-A", "legacy"))


if __name__ == "__main__":
    unittest.main()

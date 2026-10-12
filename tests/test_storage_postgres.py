import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from streamlit_app import storage_sqlite as storage
from streamlit_app.storage_postgres import PostgresConnection, StorageUnavailable, connection, _pool


class PostgresStorageTests(unittest.TestCase):
    def test_pool_keeps_tls_verification_and_no_startup_options(self):
        _pool.cache_clear()
        driver = MagicMock()
        with patch.dict(sys.modules, {"psycopg_pool": driver}):
            _pool("private")
        kwargs = driver.ConnectionPool.call_args.kwargs
        self.assertEqual(kwargs["kwargs"]["sslmode"], "verify-full")
        self.assertNotIn("options", kwargs["kwargs"])
        self.assertEqual(kwargs["max_size"], 5)
        _pool.cache_clear()

    def test_timeouts_are_transaction_local_for_neon_pooling(self):
        pool = MagicMock()
        raw = pool.connection.return_value.__enter__.return_value
        with patch.dict(os.environ, {"INI_DATABASE_URL": "private"}), patch(
            "streamlit_app.storage_postgres._pool", return_value=pool
        ):
            with connection():
                pass
        self.assertEqual(raw.execute.call_args_list[0].args[0], "SET LOCAL statement_timeout = '15s'")
        self.assertEqual(raw.execute.call_args_list[1].args[0], "SET LOCAL lock_timeout = '10s'")

    def test_sql_parameters_are_bound_not_interpolated(self):
        raw = MagicMock()
        adapter = PostgresConnection(raw)
        params = ("owner' OR 1=1 --", "chat?")
        adapter.execute("SELECT title FROM learning_sessions WHERE visitor_id=? AND session_id=?", params)
        raw.execute.assert_called_once_with(
            "SELECT title FROM learning_sessions WHERE visitor_id=%s AND session_id=%s", params)

    def test_postgres_is_explicitly_opt_in(self):
        with patch.dict(os.environ, {"INI_STORAGE_BACKEND": "sqlite", "INI_DATABASE_URL": "private"}):
            self.assertFalse(storage._postgres_enabled())

    def test_missing_url_fails_closed(self):
        with patch.dict(os.environ, {"INI_DATABASE_URL": ""}):
            with self.assertRaises(StorageUnavailable):
                with connection():
                    self.fail("Should not reach database code")

    def test_provider_error_is_redacted_and_never_falls_back(self):
        with patch.dict(os.environ, {"INI_DATABASE_URL": "private"}), patch(
            "streamlit_app.storage_postgres._pool", side_effect=RuntimeError("password=SECRET")
        ):
            with self.assertRaises(StorageUnavailable) as caught:
                with connection():
                    pass
            self.assertNotIn("SECRET", str(caught.exception))

    def test_schema_uses_postgres_migration_not_pragma(self):
        raw = MagicMock()
        with patch.object(storage, "_conn") as factory:
            factory.return_value.__enter__.return_value = PostgresConnection(raw)
            storage._init_schema()
        statements = [call.args[0] for call in raw.execute.call_args_list]
        self.assertFalse(any("PRAGMA" in sql for sql in statements))
        self.assertTrue(any("ADD COLUMN IF NOT EXISTS visitor_id" in sql for sql in statements))

    def test_session_writes_preserve_existing_owner(self):
        raw = MagicMock()
        with patch.object(storage, "_conn") as factory:
            factory.return_value.__enter__.return_value = PostgresConnection(raw)
            storage.save_session("A", "chat", "title", "today", [])
        sql, params = raw.execute.call_args.args
        self.assertIn("WHERE learning_sessions.visitor_id=excluded.visitor_id", sql)
        self.assertEqual(params[:2], ("chat", "A"))

    def test_curriculum_writes_preserve_existing_owner(self):
        raw = MagicMock()
        with patch.object(storage, "_conn") as factory:
            factory.return_value.__enter__.return_value = PostgresConnection(raw)
            storage.save_curriculum("A", "course", {"subject": "Statistics"})
        sql, params = raw.execute.call_args.args
        self.assertIn("WHERE question_curricula.visitor_id=excluded.visitor_id", sql)
        self.assertEqual(params[:2], ("course", "A"))

    def test_all_session_mutations_and_reads_are_owner_scoped(self):
        for name, args in (
            ("load_session", ("B", "chat")),
            ("rename_session", ("B", "chat", "new")),
            ("delete_session", ("B", "chat")),
            ("cleanup_empty_sessions", ("B",)),
            ("load_curriculum", ("B", "course")),
        ):
            with self.subTest(name=name):
                raw = MagicMock()
                raw.execute.return_value.fetchone.return_value = None
                with patch.object(storage, "_conn") as factory:
                    factory.return_value.__enter__.return_value = PostgresConnection(raw)
                    getattr(storage, name)(*args)
                sql, params = raw.execute.call_args.args
                self.assertIn("visitor_id=%s", sql)
                self.assertEqual(params[2] if name == "rename_session" else params[0], "B")

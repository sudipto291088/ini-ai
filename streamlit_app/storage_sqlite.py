import os
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple

DB_PATH = os.environ.get(
    "INI_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ini_sessions.db"),
)


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        yield connection
    finally:
        connection.close()


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id TEXT PRIMARY KEY,
                visitor_id TEXT NOT NULL DEFAULT '',
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                messages_json TEXT
            )
            """
        )
        columns = {
            row[1]
            for row in c.execute("PRAGMA table_info(learning_sessions)").fetchall()
        }
        if "visitor_id" not in columns:
            c.execute(
                """
                ALTER TABLE learning_sessions
                ADD COLUMN visitor_id TEXT NOT NULL DEFAULT ''
                """
            )
        c.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_learning_sessions_visitor_updated
            ON learning_sessions (visitor_id, updated_at DESC)
            """
        )
        c.commit()


def save_session(
    visitor_id: str,
    session_id: str,
    title: str,
    created_at: str,
    messages: List[Dict[str, Any]],
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    payload = json.dumps(messages, ensure_ascii=False)

    with _conn() as c:
        c.execute(
            """
            INSERT INTO learning_sessions (
                session_id, visitor_id, title, created_at, updated_at, messages_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                title=excluded.title,
                updated_at=excluded.updated_at,
                messages_json=excluded.messages_json
            WHERE learning_sessions.visitor_id=excluded.visitor_id
            """,
            (session_id, visitor_id, title, created_at, now, payload),
        )
        c.commit()


def list_sessions(
    visitor_id: str,
    limit: int = 50,
) -> List[Tuple[str, str, str, str]]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT session_id, title, created_at, updated_at
            FROM learning_sessions
            WHERE visitor_id=?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (visitor_id, limit),
        ).fetchall()
    return rows


def load_session(visitor_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute(
            """
            SELECT session_id, title, created_at, updated_at, messages_json
            FROM learning_sessions
            WHERE visitor_id=? AND session_id=?
            """,
            (visitor_id, session_id),
        ).fetchone()

    if not row:
        return None

    sid, title, created_at, updated_at, messages_json = row
    msgs = json.loads(messages_json) if messages_json else []

    return {
        "session_id": sid,
        "title": title,
        "created": created_at,
        "updated": updated_at,
        "messages": msgs,
    }


def rename_session(visitor_id: str, session_id: str, new_title: str) -> None:
    clean_title = (new_title or "").strip()
    if not clean_title:
        return

    now = datetime.now().isoformat(timespec="seconds")

    with _conn() as c:
        c.execute(
            """
            UPDATE learning_sessions
            SET title=?, updated_at=?
            WHERE visitor_id=? AND session_id=?
            """,
            (clean_title, now, visitor_id, session_id),
        )
        c.commit()


def delete_session(visitor_id: str, session_id: str) -> None:
    with _conn() as c:
        c.execute(
            "DELETE FROM learning_sessions WHERE visitor_id=? AND session_id=?",
            (visitor_id, session_id),
        )
        c.commit()


def cleanup_empty_sessions(visitor_id: str) -> None:
    with _conn() as c:
        c.execute(
            """
            DELETE FROM learning_sessions
            WHERE visitor_id=?
              AND (title IS NULL OR title='' OR title='Learning Session')
              AND (messages_json IS NULL OR messages_json='[]')
            """,
            (visitor_id,),
        )
        c.commit()

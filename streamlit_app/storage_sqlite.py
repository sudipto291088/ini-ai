import os
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.environ.get(
    "INI_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ini_sessions.db"),
)


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                messages_json TEXT
            )
            """
        )
        c.commit()


def save_session(
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
            INSERT INTO learning_sessions (session_id, title, created_at, updated_at, messages_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                title=excluded.title,
                updated_at=excluded.updated_at,
                messages_json=excluded.messages_json
            """,
            (session_id, title, created_at, now, payload),
        )
        c.commit()


def list_sessions(limit: int = 50) -> List[Tuple[str, str, str, str]]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT session_id, title, created_at, updated_at
            FROM learning_sessions
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as c:
        row = c.execute(
            """
            SELECT session_id, title, created_at, updated_at, messages_json
            FROM learning_sessions
            WHERE session_id=?
            """,
            (session_id,),
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


def rename_session(session_id: str, new_title: str) -> None:
    clean_title = (new_title or "").strip()
    if not clean_title:
        return

    now = datetime.now().isoformat(timespec="seconds")

    with _conn() as c:
        c.execute(
            """
            UPDATE learning_sessions
            SET title=?, updated_at=?
            WHERE session_id=?
            """,
            (clean_title, now, session_id),
        )
        c.commit()


def delete_session(session_id: str) -> None:
    with _conn() as c:
        c.execute(
            "DELETE FROM learning_sessions WHERE session_id=?",
            (session_id,),
        )
        c.commit()


def cleanup_empty_sessions() -> None:
    with _conn() as c:
        c.execute(
            """
            DELETE FROM learning_sessions
            WHERE (title IS NULL OR title='' OR title='Learning Session')
              AND (messages_json IS NULL OR messages_json='[]')
            """
        )
        c.commit()
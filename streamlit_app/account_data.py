"""Owner-scoped account controls using the existing SQLite/PostgreSQL adapter."""
from datetime import datetime, timezone
import json

from streamlit_app import storage_sqlite as storage


def _require_data_owner(owner: str) -> None:
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("A conversation owner is required.")


def conversation_summary(owner: str) -> dict[str, int]:
    _require_data_owner(owner)
    with storage._conn() as c:
        sessions = c.execute(
            "SELECT COUNT(*) FROM learning_sessions WHERE visitor_id=?", (owner,)
        ).fetchone()[0]
        curricula = c.execute(
            "SELECT COUNT(*) FROM question_curricula WHERE visitor_id=?", (owner,)
        ).fetchone()[0]
    return {"conversations": sessions, "curricula": curricula}


def export_conversations(owner: str) -> bytes:
    """Export all of this owner's saved data, without a sidebar-sized limit."""
    _require_data_owner(owner)
    with storage._conn() as c:
        if not getattr(c, "postgres", False):
            c.execute("BEGIN")
        sessions = c.execute(
            """SELECT session_id, title, created_at, updated_at, messages_json
               FROM learning_sessions WHERE visitor_id=? ORDER BY updated_at DESC, session_id""",
            (owner,),
        ).fetchall()
        curricula = c.execute(
            """SELECT curriculum_id, subject, updated_at, curriculum_json
               FROM question_curricula WHERE visitor_id=? ORDER BY updated_at DESC, curriculum_id""",
            (owner,),
        ).fetchall()
    payload = {
        "format": "ini-conversations", "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conversations": [
            {"id": sid, "title": title, "created_at": created, "updated_at": updated,
             "messages": json.loads(messages) if messages else []}
            for sid, title, created, updated, messages in sessions
        ],
        "subject_learning": [
            {"id": cid, "subject": subject, "updated_at": updated, "state": json.loads(state)}
            for cid, subject, updated, state in curricula
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def delete_all_conversations(owner: str) -> None:
    """Delete only one owner's chats and curricula in a single transaction."""
    _require_data_owner(owner)
    with storage._conn() as c:
        c.execute("DELETE FROM question_curricula WHERE visitor_id=?", (owner,))
        c.execute("DELETE FROM learning_sessions WHERE visitor_id=?", (owner,))
        c.commit()

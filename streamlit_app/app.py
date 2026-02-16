import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st


# =========================
# Config
# =========================
DEFAULT_API_BASE = os.environ.get("INI_API_BASE", "http://127.0.0.1:8000")
DEV_MODE = os.environ.get("INI_DEV_MODE", "0") == "1"


# =========================
# Page Setup
# =========================
st.set_page_config(page_title="InI.ai", layout="wide")

CSS = """
<style>
:root{
  --bg:#0b0f19;
  --panel:#111827;
  --muted:#6b7280;
  --text:#0f172a;
  --card:#ffffff;
  --stroke:#e5e7eb;
  --soft:#f8fafc;
}
.badge{
  display:inline-block;
  padding: 2px 10px;
  border-radius:999px;
  font-size:12px;
  border:1px solid var(--stroke);
  background: var(--soft);
}
.muted{ color: var(--muted); }
.small{ font-size: 12px; }
.bigtitle{ font-size: 30px; font-weight: 700; margin: 0 0 12px 0; }
.sectiontitle{ font-size: 20px; font-weight: 700; margin: 18px 0 10px 0; }
.card{
  border: 1px solid var(--stroke);
  border-radius: 14px;
  background: var(--card);
  padding: 14px 16px;
  margin: 10px 0;
}
.chatmsg{
  border: 1px solid var(--stroke);
  border-radius: 14px;
  background: var(--card);
  padding: 12px 14px;
  margin: 10px 0;
}
.chatmeta{
  font-size: 12px;
  color: var(--muted);
  margin-top: 6px;
}
.uib{
  border: 1px solid var(--stroke);
  border-radius: 16px;
  background: var(--card);
  padding: 10px 12px;
}
.uib-row{
  display:flex;
  align-items:center;
  gap:10px;
}
.uib-actions{
  display:flex;
  align-items:center;
  gap:10px;
}
.iconbtn{
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid var(--stroke);
  background: var(--soft);
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight: 700;
}
.center-link{
  display:flex;
  justify-content:center;
  margin: 10px 0 0 0;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================
# Helpers
# =========================
def now_label() -> str:
    # Keep the nice day/time display at top
    return datetime.now().strftime("%a, %b %d • %I:%M %p")


def normalize_mojibake(s: str) -> str:
    # Fix common “â€” / â€™” artifacts without shortening content
    if not s:
        return s
    replacements = {
        "â€”": "—",
        "â€“": "–",
        "â€™": "’",
        "â€œ": "“",
        "â€": "”",
        "â€¦": "…",
        "Â·": "·",
        "Â": "",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def session_title_for_sidebar(sess: Dict[str, Any]) -> str:
    """Compact label like: RAG.Feb 15.2026"""
    first = (sess.get("last_prompt") or sess.get("title") or "Session").strip()
    kw = (first.split()[0] if first else "Session").strip().strip(".,:;!?").upper()
    created = sess.get("created") or datetime.now().strftime("%b %d.%Y")
    # created stored as "Feb 15.2026"
    return f"{kw}.{created}"


# =========================
# Session State
# =========================
if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE

if "page" not in st.session_state:
    st.session_state.page = "New Chat"

if "chat" not in st.session_state:
    st.session_state.chat = {"topic": "", "interrogate": None, "illustrate": None}

# Learning: multiple sessions
if "learning_sessions" not in st.session_state:
    st.session_state.learning_sessions: Dict[str, Dict[str, Any]] = {}

if "learning_active_id" not in st.session_state:
    st.session_state.learning_active_id: Optional[str] = None


def ensure_learning_session() -> str:
    if st.session_state.learning_active_id and st.session_state.learning_active_id in st.session_state.learning_sessions:
        return st.session_state.learning_active_id

    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {
        "created": datetime.now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
    }
    st.session_state.learning_active_id = sid
    return sid


def start_new_learning_session() -> str:
    """Always create a new learning session and make it active."""
    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {
        "created": datetime.now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
    }
    st.session_state.learning_active_id = sid
    return sid


# =========================
# API calls
# =========================
def post_json(path: str, payload: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
    url = f"{st.session_state.api_base}{path}"
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data


def fetch_study(topic: str, mode: str = "deep", continue_token: Optional[str] = None) -> Dict[str, Any]:
    payload = {"topic": topic, "mode": mode}
    if continue_token:
        payload["continue_token"] = continue_token
    return post_json("/study/ai", payload, timeout=180)


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.markdown("## InI.ai")
    st.markdown('<span class="badge">v0 • AI Tutor</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="muted small">🕒 {now_label()}</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown("### Navigation")
    # No radio buttons — use compact nav buttons
    nav1, nav2, nav3 = st.columns([1, 1, 1], gap="small")
    with nav1:
        go_chat = st.button("💬 New Chat", use_container_width=True)
    with nav2:
        go_learn = st.button("📚 My New Learning", use_container_width=True)
    with nav3:
        go_proj = st.button("🧩 New Project", use_container_width=True)

    # Clicking a nav item starts a fresh session for that area (ChatGPT-like)
    if go_chat:
        st.session_state.page = "New Chat"
        st.session_state.chat = {"topic": "", "interrogate": None, "illustrate": None}
    if go_proj:
        st.session_state.page = "New Project"
    if go_learn:
        st.session_state.page = "My New Learning"
        start_new_learning_session()

    if DEV_MODE:
        st.divider()
        with st.expander("API Settings (dev)", expanded=False):
            st.session_state.api_base = st.text_input("API base", st.session_state.api_base)

    if st.session_state.page == "My New Learning":
        st.divider()
        st.markdown("### Your Learning")

        sessions = list(st.session_state.learning_sessions.items())
        if sessions:
            # newest first
            sessions = sessions[::-1]
            labels = [session_title_for_sidebar(s) for _, s in sessions]
            ids = [sid for sid, _ in sessions]

            # default active = most recent
            if st.session_state.learning_active_id is None:
                st.session_state.learning_active_id = ids[0]

            # active id -> index
            try:
                active_idx = ids.index(st.session_state.learning_active_id)
            except ValueError:
                active_idx = 0
                st.session_state.learning_active_id = ids[0]

            picked = st.selectbox(
                "Sessions",
                options=list(range(len(labels))),
                index=active_idx,
                format_func=lambda i: labels[i],
                label_visibility="collapsed",
            )
            st.session_state.learning_active_id = ids[picked]
        else:
            st.markdown('<div class="muted small">No sessions yet.</div>', unsafe_allow_html=True)


# =========================
# Pages
# =========================
def page_new_chat() -> None:
    st.markdown('<div class="bigtitle">New Chat</div>', unsafe_allow_html=True)

    st.session_state.chat["topic"] = st.text_input(
        "Topic",
        value=st.session_state.chat.get("topic", ""),
        placeholder="Interrogate / Illustrate topic...",
        key="chat_topic_input",
    )

    st.info("Interrogate + Illustrate UI can be polished after My New Learning is solid.", icon="ℹ️")
    st.caption("v0 note: LLM is enabled for AI/ML; templates for other topics.")

    # (You said: we’ll polish New Chat later. Keep minimal for now.)


def render_learning_messages(sess: Dict[str, Any]) -> None:
    for msg in sess["messages"]:
        role = msg.get("role", "assistant")
        text = normalize_mojibake(msg.get("text", "")).strip()
        ts = msg.get("ts")

        if role == "user":
            st.markdown(
                f"""
                <div class="chatmsg">
                  <div><b>🧑 You</b></div>
                  <div>{text}</div>
                  <div class="chatmeta">{ts}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="chatmsg">
                  <div><b>🤖 InI</b></div>
                  <div>{text}</div>
                  <div class="chatmeta">{ts}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Continue block (centered), only if it truly has more
        if msg.get("incomplete") is True and msg.get("continue_token"):
            st.markdown('<div class="center-link">', unsafe_allow_html=True)
            if st.button("Continue", key=f"cont-{msg.get('id')}"):
                st.session_state._continue_from = msg.get("continue_token")
            st.markdown("</div>", unsafe_allow_html=True)


def page_my_new_learning() -> None:
    st.markdown('<div class="bigtitle">My New Learning</div>', unsafe_allow_html=True)
    st.caption("Ask about AI. Enter = Deep. Use ◎ for overview. Use ? to quiz.")

    sid = ensure_learning_session()
    sess = st.session_state.learning_sessions[sid]

    # show history
    render_learning_messages(sess)

    # UIB at bottom (ChatGPT-like). It naturally stays at bottom after first message.
    st.markdown('<div class="uib">', unsafe_allow_html=True)
    uib_cols = st.columns([7, 1, 1, 1], gap="small")
    with uib_cols[0]:
        user_text = st.text_input(
            "",
            value="",
            placeholder="Type your topic/question...",
            label_visibility="collapsed",
            key="learn_input",
        )
    with uib_cols[1]:
        overview = st.button("◎", help="High-level overview", key="btn_overview")
    with uib_cols[2]:
        quiz = st.button("?", help="Quiz me", key="btn_quiz")
    with uib_cols[3]:
        send = st.button("➤", help="Send (deep)", key="btn_send")
    st.markdown("</div>", unsafe_allow_html=True)

    mode = "deep"
    if overview:
        mode = "high"
    if quiz:
        mode = "quiz"

    # Optional: Continue from previous incomplete chunk
    continue_token = getattr(st.session_state, "_continue_from", None)
    if continue_token:
        # clear the continue token once used
        st.session_state._continue_from = None

    if (send or overview or quiz) and user_text.strip():
        ts = now_label()
        sess["messages"].append(
            {"id": f"u-{int(time.time())}", "role": "user", "text": user_text.strip(), "ts": ts}
        )
        sess["last_prompt"] = user_text.strip()

        try:
            resp = fetch_study(user_text.strip(), mode=mode, continue_token=continue_token)
            answer = normalize_mojibake(resp.get("answer", "")).strip() or "(No answer returned.)"
            incomplete = bool(resp.get("incomplete"))
            cont = resp.get("continue_token") or None

            sess["messages"].append(
                {
                    "id": f"a-{int(time.time())}",
                    "role": "assistant",
                    "text": answer,
                    "ts": now_label(),
                    "incomplete": incomplete,
                    "continue_token": cont,
                }
            )
            st.rerun()

        except Exception as e:
            sess["messages"].append(
                {
                    "id": f"e-{int(time.time())}",
                    "role": "assistant",
                    "text": f"Error calling API: {e}",
                    "ts": now_label(),
                    "incomplete": False,
                    "continue_token": None,
                }
            )
            st.rerun()


def page_new_project() -> None:
    st.markdown('<div class="bigtitle">New Project</div>', unsafe_allow_html=True)
    st.info("Coming soon in v1.", icon="🧩")


# =========================
# Router
# =========================
if st.session_state.page == "New Chat":
    page_new_chat()
elif st.session_state.page == "My New Learning":
    page_my_new_learning()
else:
    page_new_project()

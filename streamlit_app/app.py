import os
import time
import re
from datetime import datetime
from typing import Any, Dict, Optional, List

import requests
import streamlit as st

# Try autorefresh (for live clock). If not installed, app still runs.
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
except Exception:
    st_autorefresh = None


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
  --muted:#6b7280;
  --card:#ffffff;
  --stroke:#e5e7eb;
  --soft:#f8fafc;
  --soft2:#f3f4f6;
  --ink:#0f172a;
  --blue:#2563eb;
}

html, body, [class*="css"]  {
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
  color: var(--ink);
}

/* Keep content readable / centered */
.main .block-container{
  max-width: 980px;
  padding-top: 1.25rem;
}

/* --- Sidebar clock tile (your screenshot style) --- */
.clock_tile{
  width: 100%;
  border: 1px solid var(--stroke);
  border-radius: 14px;
  background: var(--card);
  padding: 10px 10px;
  margin: 10px 0 12px 0;
}

/* Centered single-line time */
.clock_center{
  display:flex;
  align-items:center;
  justify-content:center;
  gap: 8px;
  margin-top: 2px;
}
.clock_time{
  font-size: 36px;
  font-weight: 750;
  line-height: 1;
  letter-spacing: 0.5px;
}
.clock_ampm{
  font-size: 13px;
  font-weight: 650;
  color: var(--muted);
  margin-top: 12px; /* visually aligns with big digits */
}

.clock_row_bottom{
  display:flex;
  gap: 8px;
  margin-top: 10px;
}
.clock_box{
  flex:1;
  border: 1px solid var(--stroke);
  border-radius: 10px;
  background: var(--soft);
  padding: 6px 8px;
  text-align:center;
  font-size: 13px;
  font-weight: 650;
  color: var(--ink);
}

.badge{
  display:inline-block;
  padding: 3px 10px;
  border-radius:999px;
  font-size:12px;
  border:1px solid var(--stroke);
  background: var(--soft);
}

.small{ font-size: 12px; }
.bigtitle{ font-size: 30px; font-weight: 750; margin: 0 0 12px 0; }

/* --- Chat message rectangles --- */
.chatmsg{
  border: 1px solid var(--stroke);
  border-radius: 14px;
  background: var(--card);
  padding: 12px 14px;
  margin: 14px 0;   /* more separation between bubbles */
}
.chatheader{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
}
.chatrole{
  font-weight: 750;
}
.chatbody{
  margin-top: 4px;             /* slightly tighter */
  white-space: pre-wrap;       /* preserve bullets/newlines */
  line-height: 1.28;           /* tighter baseline; big gaps are fixed by compactor */
}
.chatmeta{
  font-size: 12px;
  color: var(--muted);
  margin-top: 8px;
  text-align: right;           /* timestamp bottom-right (UNCHANGED) */
}

/* --- UIB box --- */
.uib{
  border: 1px solid var(--stroke);
  border-radius: 16px;
  background: var(--card);
  padding: 10px 12px;
  margin-top: 10px;
}
.uib_hint{
  font-size: 12px;
  color: var(--muted);
  margin-top: 8px;
}

/* --- Sidebar: compact nav links (no big “1999 buttons”) --- */
.sidebar_section_title{
  font-size: 13px;
  font-weight: 750;
  color: var(--muted);
  margin-top: 8px;
  margin-bottom: 6px;
  text-transform: none;
}
.nav_links{
  display:flex;
  flex-direction:column;
  gap: 6px;
  margin-top: 6px;
}
a.navlink{
  display:flex;
  align-items:center;
  gap: 10px;
  text-decoration:none;
  border: 1px solid var(--stroke);
  background: var(--card);
  padding: 9px 10px;
  border-radius: 12px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 650;
}
a.navlink:hover{
  background: var(--soft);
  border-color: #d1d5db;
}
.navicon{
  width: 18px;
  text-align:center;
}

/* --- Learning sessions: compact like “TOPIC.Feb 15.2026” --- */
.session_links{
  display:flex;
  flex-direction:column;
  gap: 8px;
  margin-top: 8px;
}
a.sesslink{
  display:flex;
  align-items:center;
  gap: 10px;
  text-decoration:none;
  border: 1px solid var(--stroke);
  background: var(--soft);
  padding: 9px 10px;
  border-radius: 12px;
  color: var(--ink);
  font-size: 12px;
  font-weight: 650;
}
a.sesslink:hover{
  background: var(--soft2);
  border-color: #d1d5db;
}
.sessdot{
  width: 8px; height: 8px;
  border-radius: 999px;
  background: #9ca3af;
  flex: 0 0 auto;
}
.sessdot.active{ background: var(--blue); }

/* Sidebar padding */
div[data-testid="stSidebar"] .block-container{
  padding-top: 1rem;
}

/* Continue button: small, centered, NEVER wraps */
div.stButton > button{
  border-radius: 12px;
  padding: 6px 16px;
  font-weight: 650;
  white-space: nowrap !important;
  min-width: 120px;
  text-align: center;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================
# Helpers
# =========================
def now_label() -> str:
    return datetime.now().strftime("%a, %b %d • %I:%M %p")


def clock_parts() -> Dict[str, str]:
    now = datetime.now()
    t = now.strftime("%I:%M").lstrip("0") or now.strftime("%I:%M")
    return {
        "time": t,
        "ampm": now.strftime("%p"),
        "date": now.strftime("%m/%d"),
        "dow": now.strftime("%a"),
    }


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
        "â": "—",
        "â": "–",
        "â": "’",
        "â": "“",
        "â": "”",
        "â¦": "…",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def _compact_spacing_preserve_code(text: str) -> str:
    """
    Remove the "ugly huge gaps" without shortening content.
    - Preserves triple-backtick code blocks exactly.
    - Collapses whitespace-only blank lines.
    - Tightens list formatting even when bullets are indented (e.g., "  - item", "    • item").
    """
    if not isinstance(text, str) or not text:
        return text or ""

    # Normalize CRLF early
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split by fenced code blocks. Keep code parts verbatim.
    parts = text.split("```")
    out_parts: List[str] = []

    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Code block content stays verbatim
            out_parts.append(part)
            continue

        s = part

        # Trim trailing spaces at EOL (prevents phantom "blank lines")
        s = re.sub(r"[ \t]+\n", "\n", s)

        # Convert "blank lines that contain spaces/tabs" into true blank lines
        # e.g., "\n   \n" -> "\n\n"
        s = re.sub(r"\n[ \t]+\n", "\n\n", s)

        # Tighten blank lines before bullets (allow leading indentation)
        # "\n\n   - item" -> "\n   - item"
        s = re.sub(r"\n\s*\n(?=\s*[-*•]\s)", "\n", s)

        # Tighten blank lines before numbered items (allow leading indentation)
        # "\n\n   1. item" -> "\n   1. item"
        s = re.sub(r"\n\s*\n(?=\s*\d+\.\s)", "\n", s)

        # Global cap: collapse 3+ newlines (including whitespace-newlines) -> 2 newlines
        s = re.sub(r"(?:\n[ \t]*){3,}", "\n\n", s)

        out_parts.append(s)

    compacted = "```".join(out_parts)
    return compacted.strip()


def session_title_for_sidebar(sess: Dict[str, Any]) -> str:
    """Compact label like: RAG.Feb 15.2026"""
    first = (sess.get("last_prompt") or sess.get("title") or "Session").strip()
    kw = (first.split()[0] if first else "Session").strip().strip(".,:;!?").upper()
    created = sess.get("created") or datetime.now().strftime("%b %d.%Y")
    return f"{kw}.{created}"


def needs_continue_flag(msg: Dict[str, Any]) -> bool:
    """Continue should appear ONLY when model truly has more to say."""
    if msg.get("incomplete") is True:
        return True
    sr = (msg.get("stop_reason") or "").strip().lower()
    return sr == "max_output_tokens"


def _strip_duplicate_chunk_prefix(chunk: str) -> str:
    """
    Remove annoying repeated lead-ins that appear at chunk boundaries
    without deleting actual content.
    """
    lines = chunk.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)

    patterns = {
        "overview",
        "retr overview",
        "continuation",
        "continuation —",
        "continuation — numeric example (finish calculation)",
    }

    changed = True
    while changed and lines:
        changed = False
        first = lines[0].strip()
        first_clean = first.strip("•-*\"'“”‘’ ").lower()
        if first_clean in patterns:
            lines.pop(0)
            changed = True
            continue
        if first_clean.replace(":", "") in patterns and len(first_clean) <= 40:
            lines.pop(0)
            changed = True
            continue

    return "\n".join(lines).strip()


def _overlap_dedupe_append(existing: str, chunk: str, max_window: int = 1600) -> str:
    """
    Append chunk to existing while removing overlap duplication.
    Keeps answers long; only removes repeated boundary overlap.
    """
    existing = existing or ""
    chunk = chunk or ""
    if not chunk.strip():
        return existing

    ex = existing.rstrip()
    ch = _strip_duplicate_chunk_prefix(chunk).lstrip()
    if not ch:
        return ex

    tail = ex[-max_window:]
    head = ch[:max_window]

    best = 0
    max_k = min(len(tail), len(head))
    for k in range(80, max_k + 1):
        if tail[-k:] == head[:k]:
            best = k

    if best > 0:
        ch = ch[best:].lstrip()

    if ex:
        return (ex + "\n" + ch).strip()
    return ch.strip()


# =========================
# Session State
# =========================
if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE

if "page" not in st.session_state:
    st.session_state.page = "New Chat"

if "chat" not in st.session_state:
    st.session_state.chat = {"topic": "", "interrogate": None, "illustrate": None}

if "learning_sessions" not in st.session_state:
    st.session_state.learning_sessions: Dict[str, Dict[str, Any]] = {}

if "learning_active_id" not in st.session_state:
    st.session_state.learning_active_id: Optional[str] = None

if "_continue_msg_id" not in st.session_state:
    st.session_state._continue_msg_id = None

if "_last_page_param" not in st.session_state:
    st.session_state._last_page_param = None


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
    return r.json()


def fetch_study(
    topic: str,
    mode: str = "deep",
    previous_response_id: Optional[str] = None,
    continue_token: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"topic": topic, "mode": mode}
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id
    if continue_token:
        payload["continue_token"] = continue_token
    return post_json("/study/ai", payload, timeout=180)


# =========================
# URL / Query routing (clean nav links)
# =========================
qp = st.query_params
page_param = (qp.get("page") or "chat").lower()
learn_sid = qp.get("learn_sid")

param_to_page = {
    "chat": "New Chat",
    "learn": "My New Learning",
    "proj": "New Project",
}

if page_param in param_to_page:
    new_page = param_to_page[page_param]
    if new_page == "My New Learning":
        if (st.session_state._last_page_param != "learn") and (learn_sid is None):
            start_new_learning_session()
    st.session_state.page = new_page

st.session_state._last_page_param = page_param

if learn_sid and learn_sid in st.session_state.learning_sessions:
    st.session_state.learning_active_id = learn_sid


# =========================
# Sidebar
# =========================
with st.sidebar:
    # ============================================================
    # Live Clock (no page refresh)
    # - Prefer Streamlit-native fragment when available.
    # - Fallback to streamlit-autorefresh if installed.
    # ============================================================
    def _render_clock_tile():
        cp = clock_parts()
        st.markdown(
            f'''
            <div class="clock_tile">
              <div class="clock_center">
                <div class="clock_time">{cp["time"]}</div>
                <div class="clock_ampm">{cp["ampm"]}</div>
              </div>
              <div class="clock_row_bottom">
                <div class="clock_box">{cp["date"]}</div>
                <div class="clock_box">{cp["dow"]}</div>
              </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    if hasattr(st, "fragment"):
        @st.fragment(run_every="1s")  # type: ignore[arg-type]
        def _clock_fragment():
            _render_clock_tile()
        _clock_fragment()
    elif st_autorefresh is not None:
        st_autorefresh(interval=1000, key="ini_clock_tick")
        _render_clock_tile()
    else:
        _render_clock_tile()
        st.caption("Tip: install 'streamlit-autorefresh' to enable a live-updating clock.")

    st.markdown("## InI.ai")
    st.markdown('<span class="badge">v0 • AI Tutor</span>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar_section_title">Navigation</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="nav_links">
          <a class="navlink" href="?page=chat"><span class="navicon">💬</span><span>New Chat</span></a>
          <a class="navlink" href="?page=learn"><span class="navicon">📚</span><span>My New Learning</span></a>
          <a class="navlink" href="?page=proj"><span class="navicon">🧩</span><span>New Project</span></a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if DEV_MODE:
        st.markdown("<hr/>", unsafe_allow_html=True)
        with st.expander("API Settings (dev)", expanded=False):
            st.session_state.api_base = st.text_input("API base", st.session_state.api_base)

    if st.session_state.page == "My New Learning":
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar_section_title">Your Learning</div>', unsafe_allow_html=True)

        sessions_items = list(st.session_state.learning_sessions.items())[::-1]
        if sessions_items:
            st.markdown('<div class="session_links">', unsafe_allow_html=True)
            for sid, sess in sessions_items:
                label = session_title_for_sidebar(sess)
                active = (sid == st.session_state.learning_active_id)
                dot_cls = "sessdot active" if active else "sessdot"
                st.markdown(
                    f"""
                    <a class="sesslink" href="?page=learn&learn_sid={sid}">
                      <span class="{dot_cls}"></span>
                      <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{label}</span>
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="small" style="color:var(--muted);">No sessions yet.</div>', unsafe_allow_html=True)


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


def render_learning_messages(sess: Dict[str, Any]) -> None:
    for msg in sess["messages"]:
        role = msg.get("role", "assistant")
        raw_text = normalize_mojibake(msg.get("text", "")).strip()
        text = _compact_spacing_preserve_code(raw_text)
        ts = msg.get("ts") or ""

        if role == "user":
            st.markdown(
                f"""
                <div class="chatmsg">
                  <div class="chatheader">
                    <div class="chatrole">🧑 You</div>
                  </div>
                  <div class="chatbody">{text}</div>
                  <div class="chatmeta">{ts}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="chatmsg">
                  <div class="chatheader">
                    <div class="chatrole">🤖 InI</div>
                  </div>
                  <div class="chatbody">{text}</div>
                  <div class="chatmeta">{ts}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if needs_continue_flag(msg):
                c1, c2, c3 = st.columns([1, 0.45, 1])
                with c2:
                    clicked = st.button("Continue", key=f"cont-{msg.get('id')}")
                if clicked:
                    st.session_state._continue_msg_id = msg.get("id")
                    st.rerun()


def _continue_one_chunk(sess: Dict[str, Any], msg_id: str) -> None:
    idx = None
    for i, m in enumerate(sess["messages"]):
        if m.get("id") == msg_id:
            idx = i
            break
    if idx is None:
        return

    m = sess["messages"][idx]
    if m.get("role") != "assistant":
        return

    prompt = (m.get("prompt") or "").strip()
    mode = (m.get("mode") or "deep").strip()
    prev_id = m.get("response_id") or None
    legacy_token = m.get("continue_token") or None

    if not prompt:
        m["incomplete"] = False
        m["stop_reason"] = None
        return

    resp = fetch_study(prompt, mode=mode, previous_response_id=prev_id, continue_token=legacy_token)
    chunk_raw = normalize_mojibake(resp.get("answer", "") or "").strip()
    chunk = _compact_spacing_preserve_code(chunk_raw)

    if chunk:
        existing = (m.get("text") or "")
        m["text"] = _overlap_dedupe_append(existing, chunk)

    m["incomplete"] = bool(resp.get("incomplete"))
    m["stop_reason"] = resp.get("stop_reason") or None

    if resp.get("response_id"):
        m["response_id"] = resp.get("response_id")
    if resp.get("continue_token"):
        m["continue_token"] = resp.get("continue_token")

    m["ts"] = now_label()


def page_my_new_learning() -> None:
    st.markdown('<div class="bigtitle">My New Learning</div>', unsafe_allow_html=True)
    st.caption("Ask about AI. Enter = Deep. Use ◎ for overview. Use ? to quiz.")

    sid = ensure_learning_session()
    sess = st.session_state.learning_sessions[sid]

    if st.session_state._continue_msg_id:
        msg_id = st.session_state._continue_msg_id
        st.session_state._continue_msg_id = None
        try:
            _continue_one_chunk(sess, msg_id)
        except Exception as e:
            sess["messages"].append(
                {
                    "id": f"e-{int(time.time())}",
                    "role": "assistant",
                    "text": f"Error continuing: {e}",
                    "ts": now_label(),
                    "incomplete": False,
                    "stop_reason": None,
                }
            )
        st.rerun()

    render_learning_messages(sess)

    st.markdown('<div class="uib">', unsafe_allow_html=True)
    uib_cols = st.columns([8, 0.8, 0.8, 0.8], gap="small")
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

    st.markdown('<div class="uib_hint">➤ Deep (default) • ◎ Overview • ? Quiz</div>', unsafe_allow_html=True)

    mode = "deep"
    if overview:
        mode = "high"
    if quiz:
        mode = "quiz"

    if (send or overview or quiz) and user_text.strip():
        prompt = user_text.strip()

        sess["messages"].append(
            {"id": f"u-{int(time.time())}", "role": "user", "text": prompt, "ts": now_label()}
        )
        sess["last_prompt"] = prompt

        try:
            resp = fetch_study(prompt, mode=mode)
            answer_raw = normalize_mojibake(resp.get("answer", "") or "").strip()
            answer = _compact_spacing_preserve_code(answer_raw)
            if not answer:
                answer = "No answer generated."

            msg: Dict[str, Any] = {
                "id": f"a-{int(time.time())}",
                "role": "assistant",
                "text": answer,
                "ts": now_label(),
                "incomplete": bool(resp.get("incomplete")),
                "stop_reason": resp.get("stop_reason") or None,
                "prompt": prompt,
                "mode": mode,
            }

            if resp.get("response_id"):
                msg["response_id"] = resp.get("response_id")
            if resp.get("continue_token"):
                msg["continue_token"] = resp.get("continue_token")

            sess["messages"].append(msg)
            st.rerun()

        except Exception as e:
            sess["messages"].append(
                {
                    "id": f"e-{int(time.time())}",
                    "role": "assistant",
                    "text": f"Error calling API: {e}",
                    "ts": now_label(),
                    "incomplete": False,
                    "stop_reason": None,
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
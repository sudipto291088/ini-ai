import os
import time
import re
from datetime import datetime
from typing import Any, Dict, Optional

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
  --ink:#0f172a;

  --bubbleUser:#eef2ff;
  --bubbleAsst:#ffffff;

  --litOver:#e0e7ff;
  --litQuiz:#ede9fe;
}

html, body, [class*="css"]{
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif !important;
  color: var(--ink);
}
button, input, textarea, select, label, p, div, span{
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif !important;
}

.main .block-container{
  max-width: 980px;
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
}

/* --- Sidebar clock tile (keep as-is) --- */
.clock_tile{
  width: 100%;
  border: 1px solid var(--stroke);
  border-radius: 14px;
  background: var(--card);
  padding: 10px 10px;
  margin: 10px 0 12px 0;
}
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
  margin-top: 12px;
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

div[data-testid="stSidebar"] .block-container{
  padding-top: 1rem;
}

/* Prevent Continue wrapping into Con / tinu / e */
button[kind="secondary"]{
  min-width: 110px !important;
}

/* =========================
   UIB capsule (stable)
   ========================= */
.ini_uib_wrap{ margin-top: 18px; }
.ini_uib_outer{
  display:flex;
  justify-content:center;
  width:100%;
}
.ini_uib_capsule{
  width: min(920px, 100%);
  border: 1px solid var(--stroke);
  background: #fff;
  border-radius: 999px;
  padding: 10px 12px;
}

.ini_uib_capsule [data-testid="stHorizontalBlock"]{
  flex-wrap: nowrap !important;
  align-items:center !important;
}
.ini_uib_capsule [data-testid="column"]{
  min-width: 0 !important;
}

/* Text input styling */
.ini_uib_capsule div[data-testid="stTextInput"] input{
  border-radius: 999px !important;
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* Icon buttons inside capsule */
.ini_uib_capsule [data-testid="column"]:nth-child(2) button,
.ini_uib_capsule [data-testid="column"]:nth-child(3) button,
.ini_uib_capsule [data-testid="column"]:nth-child(4) button{
  border-radius: 999px !important;
  width: 40px !important;
  height: 40px !important;
  padding: 0 !important;
  border: 1px solid var(--stroke) !important;
  background: #fff !important;
  font-weight: 900 !important;
}

/* Lit state (applied via wrapper class) */
.ini_lit_over .ini_uib_capsule [data-testid="column"]:nth-child(2) button{
  background: var(--litOver) !important;
  border-color: #c7d2fe !important;
}
.ini_lit_quiz .ini_uib_capsule [data-testid="column"]:nth-child(3) button{
  background: var(--litQuiz) !important;
  border-color: #ddd6fe !important;
}

/* Hint under capsule (VERTICAL) */
.ini_hint{
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted);
  padding-left: 10px;
  display:flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  line-height: 1.2;
}
.ini_hint b{ color: var(--ink); }

/* Make chat look cleaner */
.stChatMessage{
  padding-top: 0.25rem !important;
  padding-bottom: 0.25rem !important;
}
.stChatMessage .stMarkdown{
  line-height: 1.38;
}

/* Responsive */
@media (max-width: 720px){
  .main .block-container{ padding-left: 1rem; padding-right: 1rem; }
  .ini_uib_capsule{ padding: 10px 10px; }
  .ini_uib_capsule [data-testid="stHorizontalBlock"]{
    flex-wrap: wrap !important;
    gap: 8px !important;
  }
  .ini_uib_capsule [data-testid="column"]:nth-child(1){
    flex: 1 1 100% !important;
  }
  .ini_uib_capsule [data-testid="column"]:nth-child(2),
  .ini_uib_capsule [data-testid="column"]:nth-child(3),
  .ini_uib_capsule [data-testid="column"]:nth-child(4){
    flex: 0 0 auto !important;
  }
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
    return {"time": t, "ampm": now.strftime("%p"), "date": now.strftime("%m/%d"), "dow": now.strftime("%a")}


def normalize_mojibake(s: str) -> str:
    if not s:
        return s
    replacements = {
        "â€”": "—", "â€“": "–", "â€™": "’", "â€œ": "“", "â€": "”", "â€¦": "…",
        "Â·": "·", "Â": "",
        "â": "—", "â": "–", "â": "’", "â": "“", "â": "”", "â¦": "…",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def normalize_whitespace_for_readability(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text or ""
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n[ \t]+\n", "\n\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"(?m)^\s*\d+\.\s*[A-Za-z]?\s*$\n?", "", s)
    return s.strip()


def session_title_for_sidebar(sess: Dict[str, Any]) -> str:
    first = (sess.get("last_prompt") or sess.get("title") or "Session").strip()
    kw = (first.split()[0] if first else "Session").strip().strip(".,:;!?").upper()
    created = sess.get("created") or datetime.now().strftime("%b %d.%Y")
    return f"{kw}.{created}"


def needs_continue_flag(msg: Dict[str, Any]) -> bool:
    if msg.get("incomplete") is True:
        return True
    sr = (msg.get("stop_reason") or "").strip().lower()
    return sr == "max_output_tokens"


def mode_label(mode: str) -> str:
    m = (mode or "").strip().lower()
    if m == "high":
        return "Overview"
    if m == "quiz":
        return "Quiz"
    return "Deep"


def _strip_duplicate_chunk_prefix(chunk: str) -> str:
    lines = chunk.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    bad_first_lines = {
        "definition",
        "definition / quick intuition",
        "overview",
        "quick intuition",
        "why rag matters / when to use it",
        "next steps",
    }
    changed = True
    while changed and lines:
        changed = False
        first = lines[0].strip().strip(":").lower()
        if first in bad_first_lines:
            lines.pop(0)
            changed = True
            while lines and not lines[0].strip():
                lines.pop(0)
    return "\n".join(lines).strip()


# (ALL YOUR IMPORTS AND CSS REMAIN EXACTLY AS THEY ARE ABOVE — unchanged)

# --- KEEP EVERYTHING ABOVE EXACTLY THE SAME ---
# I am only replacing the overlap logic block.

def _strip_duplicate_chunk_prefix(chunk: str) -> str:
    if not chunk:
        return chunk

    lines = chunk.splitlines()

    # Remove leading empty lines
    while lines and not lines[0].strip():
        lines.pop(0)

    # Remove common repeated structural headers
    bad_first_lines = {
        "definition",
        "definition —",
        "definition -",
        "overview",
        "introduction",
        "core mechanism",
        "why rag matters",
        "next steps",
    }

    changed = True
    while changed and lines:
        changed = False
        first = lines[0].strip().strip(":").lower()
        for bad in bad_first_lines:
            if first.startswith(bad):
                lines.pop(0)
                changed = True
                break
        while lines and not lines[0].strip():
            lines.pop(0)

    return "\n".join(lines).strip()


def _overlap_dedupe_append(existing: str, chunk: str, max_window: int = 2500) -> str:
    """
    Improved append logic:
    - Stronger overlap detection
    - Prevents duplicate numbered headings
    - Enforces clean spacing
    """

    if not existing:
        return chunk.strip()

    if not chunk.strip():
        return existing.strip()

    ex = existing.rstrip()
    ch = _strip_duplicate_chunk_prefix(chunk).lstrip()

    if not ch:
        return ex

    # Detect longest suffix-prefix overlap
    tail = ex[-max_window:]
    head = ch[:max_window]

    best_overlap = 0
    max_k = min(len(tail), len(head))

    for k in range(120, max_k + 1):  # higher threshold for stability
        if tail[-k:] == head[:k]:
            best_overlap = k

    if best_overlap > 0:
        ch = ch[best_overlap:].lstrip()

    # Remove repeated numbered headings like "1." restart
    last_lines = ex.splitlines()[-10:]
    for line in last_lines:
        clean = line.strip()
        if re.match(r"^\d+\.\s", clean):
            if ch.strip().startswith(clean):
                ch = ch[len(clean):].lstrip()

    return (ex + "\n\n" + ch).strip()


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
    st.session_state.learning_active_id = None

if "_continue_msg_id" not in st.session_state:
    st.session_state._continue_msg_id = None

if "_last_page_param" not in st.session_state:
    st.session_state._last_page_param = None

# UIB state
if "uib_text" not in st.session_state:
    st.session_state.uib_text = ""
if "uib_mode" not in st.session_state:
    st.session_state.uib_mode = "deep"  # deep|high|quiz

# Streamlit-safe clear flag
if "_uib_clear_next" not in st.session_state:
    st.session_state._uib_clear_next = False

# Send request flag (Enter / Arrow)
if "_uib_send_requested" not in st.session_state:
    st.session_state._uib_send_requested = False


def ensure_learning_session() -> str:
    if st.session_state.learning_active_id and st.session_state.learning_active_id in st.session_state.learning_sessions:
        return st.session_state.learning_active_id
    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {"created": datetime.now().strftime("%b %d.%Y"), "messages": [], "last_prompt": ""}
    st.session_state.learning_active_id = sid
    return sid


def start_new_learning_session() -> str:
    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {"created": datetime.now().strftime("%b %d.%Y"), "messages": [], "last_prompt": ""}
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
    continue_mode: bool = False,
    previous_answer: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Backend contract (v0):
      - topic: str
      - mode: deep|high|quiz
      - optional continuation:
          continue_mode: bool
          previous_answer: str
    """
    payload: Dict[str, Any] = {"topic": topic, "mode": mode}

    if continue_mode and previous_answer:
        payload["continue_mode"] = True
        payload["previous_answer"] = previous_answer

    return post_json("/study/ai", payload, timeout=180)


# =========================
# URL / Query routing
# =========================
qp = st.query_params
page_param = (qp.get("page") or "chat").lower()
learn_sid = qp.get("learn_sid")

param_to_page = {"chat": "New Chat", "learn": "My New Learning", "proj": "New Project"}

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
# Sidebar (DO NOT BREAK)
# =========================
with st.sidebar:
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

    st.markdown('<div class="small" style="color:var(--muted); font-weight:750; margin-top:10px;">Navigation</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="?page=chat">💬&nbsp;&nbsp;New Chat</a>
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="?page=learn">📚&nbsp;&nbsp;My New Learning</a>
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="?page=proj">🧩&nbsp;&nbsp;New Project</a>
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
        st.markdown('<div class="small" style="color:var(--muted); font-weight:750;">Your Learning</div>', unsafe_allow_html=True)

        sessions_items = list(st.session_state.learning_sessions.items())[::-1]
        if sessions_items:
            for sid, sess in sessions_items:
                label = session_title_for_sidebar(sess)
                active = (sid == st.session_state.learning_active_id)
                dot = "🔵" if active else "⚪"
                st.markdown(f"- {dot} [{label}](?page=learn&learn_sid={sid})")
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

    if not prompt:
        m["incomplete"] = False
        m["stop_reason"] = None
        return

    # New backend continuation contract:
    # send continue_mode + previous_answer (the current assistant text)
    resp = fetch_study(
        topic=prompt,
        mode=mode,
        continue_mode=True,
        previous_answer=m.get("text") or "",
    )

    chunk_raw = normalize_mojibake(resp.get("answer", "") or "")
    chunk = normalize_whitespace_for_readability(chunk_raw)

    if chunk.strip():
        existing = (m.get("text") or "")
        m["text"] = _overlap_dedupe_append(existing, chunk)

    m["incomplete"] = bool(resp.get("incomplete"))
    m["stop_reason"] = resp.get("stop_reason") or None
    m["ts"] = now_label()


def _mode_hint_text(mode: str) -> str:
    m = (mode or "deep").lower()
    if m == "high":
        return "Overview"
    if m == "quiz":
        return "Quiz"
    return "Deep (default)"


def _request_send() -> None:
    st.session_state._uib_send_requested = True


def _process_send(sess: Dict[str, Any]) -> None:
    prompt = (st.session_state.uib_text or "").strip()
    mode = (st.session_state.uib_mode or "deep").strip().lower()
    if mode not in {"deep", "high", "quiz"}:
        mode = "deep"

    if not prompt:
        return

    sess["messages"].append(
        {"id": f"u-{int(time.time())}", "role": "user", "text": prompt, "ts": now_label(), "mode_label": mode_label(mode)}
    )
    sess["last_prompt"] = prompt

    try:
        resp = fetch_study(prompt, mode=mode)
        answer = normalize_whitespace_for_readability(normalize_mojibake(resp.get("answer", "") or "")) or "No answer generated."
        sess["messages"].append(
            {
                "id": f"a-{int(time.time())}",
                "role": "assistant",
                "text": answer,
                "ts": now_label(),
                "incomplete": bool(resp.get("incomplete")),
                "stop_reason": resp.get("stop_reason") or None,
                "prompt": prompt,
                "mode": mode,
                # legacy fields retained (backend may not return them now, but keeping won't break session data)
                "response_id": resp.get("response_id"),
                "continue_token": resp.get("continue_token"),
            }
        )
    except Exception as e:
        sess["messages"].append({"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error calling API: {e}", "ts": now_label()})

    st.session_state._uib_clear_next = True
    st.rerun()


def _render_user_mode_hint(mode_lbl: str) -> None:
    # Vertical stacked hint UNDER user bubble (no HTML).
    # Icons are unicode so no leaking "keyboard_double_arrow_right".
    active = (mode_lbl or "Deep").strip()
    lines = [
        ("➤", "Deep (default)"),
        ("◎", "Overview"),
        ("?", "Quiz"),
    ]
    for ico, label in lines:
        if label.startswith(active):
            st.caption(f"**{ico} {label}**")
        else:
            st.caption(f"{ico} {label}")


def page_my_new_learning() -> None:
    st.markdown('<div class="bigtitle">My New Learning</div>', unsafe_allow_html=True)
    st.caption("Interactive AI tutor (v0): AI topics only. Deep is default; use Overview/Quiz when needed.")

    sid = ensure_learning_session()
    sess = st.session_state.learning_sessions[sid]

    # Handle Continue
    if st.session_state._continue_msg_id:
        msg_id = st.session_state._continue_msg_id
        st.session_state._continue_msg_id = None
        try:
            _continue_one_chunk(sess, msg_id)
        except Exception as e:
            sess["messages"].append({"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error continuing: {e}", "ts": now_label()})
        st.rerun()

    # Render chat using Streamlit-native chat (stable)
    for msg in sess["messages"]:
        role = msg.get("role", "assistant")
        ts = msg.get("ts") or ""
        text = normalize_whitespace_for_readability(normalize_mojibake(msg.get("text", "") or ""))

        if role == "user":
            with st.chat_message("user"):
                st.markdown(text)
                _render_user_mode_hint(msg.get("mode_label") or "Deep")
                st.markdown(f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>", unsafe_allow_html=True)
        else:
            with st.chat_message("assistant"):
                st.markdown(text)
                st.markdown(f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>", unsafe_allow_html=True)

                if needs_continue_flag(msg):
                    if st.button("Continue", key=f"cont-{msg.get('id')}"):
                        st.session_state._continue_msg_id = msg.get("id")
                        st.rerun()

    # Clear input BEFORE widget is created (Streamlit-safe)
    if st.session_state._uib_clear_next:
        st.session_state.uib_text = ""
        st.session_state._uib_clear_next = False

    # Lit classes
    lit_over = (st.session_state.uib_mode == "high")
    lit_quiz = (st.session_state.uib_mode == "quiz")
    wrap_classes = "ini_uib_wrap"
    if lit_over:
        wrap_classes += " ini_lit_over"
    if lit_quiz:
        wrap_classes += " ini_lit_quiz"

    st.markdown(f'<div class="{wrap_classes}">', unsafe_allow_html=True)
    st.markdown('<div class="ini_uib_outer">', unsafe_allow_html=True)
    st.markdown('<div class="ini_uib_capsule">', unsafe_allow_html=True)

    cols = st.columns([8.4, 0.65, 0.65, 0.65], gap="small")

    with cols[0]:
        st.text_input(
            "uib",
            key="uib_text",
            label_visibility="collapsed",
            placeholder="Type your topic/question...",
            on_change=_request_send,   # Enter triggers send request
        )

    with cols[1]:
        if st.button("◎", key="uib_over_btn"):
            st.session_state.uib_mode = "deep" if st.session_state.uib_mode == "high" else "high"
            st.rerun()

    with cols[2]:
        if st.button("?", key="uib_quiz_btn"):
            st.session_state.uib_mode = "deep" if st.session_state.uib_mode == "quiz" else "quiz"
            st.rerun()

    with cols[3]:
        if st.button("➤", key="uib_send_btn"):
            st.session_state._uib_send_requested = True
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # capsule
    st.markdown("</div>", unsafe_allow_html=True)  # outer

    st.markdown(
        f"""
        <div class="ini_hint">
          <div>• <b>{_mode_hint_text(st.session_state.uib_mode)}</b></div>
          <div>Enter or ➤ to send</div>
          <div>◎ / ? toggle mode</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)  # wrap end

    # Execute send AFTER widgets exist
    if st.session_state._uib_send_requested:
        st.session_state._uib_send_requested = False
        _process_send(sess)


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






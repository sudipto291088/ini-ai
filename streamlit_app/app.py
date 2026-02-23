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
  --soft2:#f3f4f6;
  --ink:#0f172a;

  --blue:#2563eb;
  --blueSoft:#e0e7ff;

  --purple:#7c3aed;
  --purpleSoft:#ede9fe;

  --bubbleUser:#eef2ff;
  --bubbleAsst:#ffffff;

  /* UIB */
  --uibMax: 820px;
  --uibPad: 120px;
  --uibHeight: 50px;
  --uibRadius: 999px;
  --uibIcon: 36px;
}

/* Fonts */
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
  padding-bottom: 7.2rem; /* room for fixed UIB */
}

/* --- Sidebar clock tile (keep as-is; do not break sidebar) --- */
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

/* --- Chat bubble styling --- */
.bubble{
  border: 1px solid var(--stroke);
  border-radius: 16px;
  padding: 10px 12px;
  box-shadow: 0 1px 0 rgba(0,0,0,0.02);
  background: var(--bubbleAsst);
}
.bubble.user{
  background: var(--bubbleUser);
}
.bubble .role{
  font-weight: 800;
  font-size: 13px;
  margin-bottom: 6px;
}
.bubble .body{
  font-size: 14px;
  line-height: 1.35;
}
.meta_right{
  font-size: 12px;
  color: var(--muted);
  text-align: right;
  margin-top: 4px;
}

/* Mode hint block (under user bubble, left aligned) */
.mode_hint_left{
  font-size: 11px;
  color: var(--muted);
  text-align: left;
  margin-top: 4px;
  line-height: 1.2;
}
.mode_hint_left .line{
  display:flex;
  align-items:center;
  gap: 8px;
  margin: 2px 0;
}
.mode_hint_left .ico{
  width: 18px;
  height: 18px;
  border-radius: 999px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size: 12px;
  border: 1px solid var(--stroke);
  background: #fff;
  opacity: 0.95;
}
.mode_hint_left .active{
  font-weight: 800;
  color: var(--ink);
}
.mode_hint_left .active .ico{
  border-color: #cbd5e1;
}

/* Sidebar */
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

div[data-testid="stSidebar"] .block-container{
  padding-top: 1rem;
}

/* =========================
   UIB (native, fixed bottom, icons INSIDE capsule)
   ========================= */
.ini-uib-wrap{
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 18px;
  width: min(var(--uibMax), calc(100vw - var(--uibPad)));
  z-index: 9999;
}

.ini-uib-shell{
  height: var(--uibHeight);
  border: 1px solid var(--stroke);
  background: #ffffff;
  border-radius: var(--uibRadius);
  display:flex;
  align-items:center;
  padding: 6px 10px;
  box-shadow: 0 1px 0 rgba(0,0,0,0.02);
}

.ini-uib-subhint{
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted);
  display:flex;
  gap: 14px;
  align-items:center;
  padding-left: 10px;
}

/* Remove widget chrome so the shell is the only capsule */
.ini-uib-shell div[data-testid="stTextInput"]{
  width: 100%;
}
.ini-uib-shell div[data-testid="stTextInput"] input{
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  background: transparent !important;
  font-size: 14px !important;
  padding: 10px 6px !important;
}
.ini-uib-shell div[data-testid="stTextInput"] > label{
  display:none !important;
}

/* Icon buttons become circles */
.ini-uib-shell .ini-icon-wrap div.stButton > button{
  width: var(--uibIcon) !important;
  height: var(--uibIcon) !important;
  border-radius: 999px !important;
  padding: 0 !important;
  border: 1px solid var(--stroke) !important;
  background: #ffffff !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  box-shadow: none !important;
  font-size: 16px !important;
  font-weight: 800 !important;
}
.ini-uib-shell .ini-icon-wrap div.stButton > button:hover{
  border-color: #cbd5e1 !important;
}

/* Lit states */
.ini-uib-shell .lit-overview div.stButton > button{
  background: var(--blueSoft) !important;
  border-color: #c7d2fe !important;
}
.ini-uib-shell .lit-quiz div.stButton > button{
  background: var(--purpleSoft) !important;
  border-color: #ddd6fe !important;
}

/* Send button a touch stronger */
.ini-uib-shell .ini-send-wrap div.stButton > button{
  border-color: #d1d5db !important;
}
.ini-uib-shell .ini-send-wrap div.stButton > button:hover{
  border-color: #9ca3af !important;
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


def tutor_suffix_for_v0_ai() -> str:
    return (
        "\n\n"
        "Tutor instructions (v0): Teach interactively for a beginner. "
        "Keep depth but stay cohesive. Use clear section headers. "
        "Include: (1) quick intuition, (2) a small example, "
        "(3) 2 check-questions, (4) next steps."
    )


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


def _overlap_dedupe_append(existing: str, chunk: str, max_window: int = 1800) -> str:
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

    return (ex + "\n\n" + ch).strip() if ex else ch.strip()


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

if "uib_mode" not in st.session_state:
    st.session_state.uib_mode = "deep"

if "_uib_submit" not in st.session_state:
    st.session_state._uib_submit = False

# IMPORTANT: we will clear the input on the *next* run, before widget instantiation
if "_uib_clear_next" not in st.session_state:
    st.session_state._uib_clear_next = False

# Widget key value can exist, but must be set BEFORE instantiation in a run
if "uib_text" not in st.session_state:
    st.session_state.uib_text = ""


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


def _render_mode_hint_block(active_mode: str) -> None:
    deep_active = active_mode == "Deep"
    ov_active = active_mode == "Overview"
    qz_active = active_mode == "Quiz"

    deep_cls = "active" if deep_active else ""
    ov_cls = "active" if ov_active else ""
    qz_cls = "active" if qz_active else ""

    st.markdown(
        f"""
        <div class="mode_hint_left">
          <div class="line {deep_cls}"><span class="ico">➤</span><span>Deep (default)</span></div>
          <div class="line {ov_cls}"><span class="ico">◎</span><span>Overview</span></div>
          <div class="line {qz_cls}"><span class="ico">?</span><span>Quiz</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_learning_messages(sess: Dict[str, Any]) -> None:
    for msg in sess["messages"]:
        role = msg.get("role", "assistant")
        ts = msg.get("ts") or ""
        text = normalize_whitespace_for_readability(normalize_mojibake(msg.get("text", "") or ""))

        if role == "user":
            left, right = st.columns([2.2, 7.8], gap="small")
            with right:
                st.markdown('<div class="bubble user">', unsafe_allow_html=True)
                st.markdown('<div class="role">You</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="body">{text}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                active_mode = (msg.get("mode_label") or "Deep").strip()
                _render_mode_hint_block(active_mode)

                # timestamp location preserved
                st.markdown(f'<div class="meta_right">{ts}</div>', unsafe_allow_html=True)

        else:
            left, right = st.columns([7.8, 2.2], gap="small")
            with left:
                st.markdown('<div class="bubble assistant">', unsafe_allow_html=True)
                st.markdown('<div class="role">InI</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="body">{text}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown(f'<div class="meta_right">{ts}</div>', unsafe_allow_html=True)

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

    chunk_raw = normalize_mojibake(resp.get("answer", "") or "")
    chunk = normalize_whitespace_for_readability(chunk_raw)

    if chunk.strip():
        existing = (m.get("text") or "")
        m["text"] = _overlap_dedupe_append(existing, chunk)

    m["incomplete"] = bool(resp.get("incomplete"))
    m["stop_reason"] = resp.get("stop_reason") or None

    if resp.get("response_id"):
        m["response_id"] = resp.get("response_id")
    if resp.get("continue_token"):
        m["continue_token"] = resp.get("continue_token")

    m["ts"] = now_label()


def _toggle_mode(new_mode: str) -> None:
    cur = st.session_state.uib_mode
    if new_mode == "high":
        st.session_state.uib_mode = "deep" if cur == "high" else "high"
    elif new_mode == "quiz":
        st.session_state.uib_mode = "deep" if cur == "quiz" else "quiz"
    else:
        st.session_state.uib_mode = "deep"


def _enter_submit() -> None:
    st.session_state._uib_submit = True


def _process_send(sess: Dict[str, Any], prompt: str, mode: str) -> None:
    sess["last_prompt"] = prompt
    sess["messages"].append(
        {
            "id": f"u-{int(time.time())}",
            "role": "user",
            "text": prompt,
            "ts": now_label(),
            "mode_label": mode_label(mode),
        }
    )

    prompt_to_send = prompt + tutor_suffix_for_v0_ai()

    resp = fetch_study(prompt_to_send, mode=mode)
    answer_raw = normalize_mojibake(resp.get("answer", "") or "")
    answer = normalize_whitespace_for_readability(answer_raw) or "No answer generated."

    msg: Dict[str, Any] = {
        "id": f"a-{int(time.time())}",
        "role": "assistant",
        "text": answer,
        "ts": now_label(),
        "incomplete": bool(resp.get("incomplete")),
        "stop_reason": resp.get("stop_reason") or None,
        "prompt": prompt_to_send,
        "mode": mode,
    }

    if resp.get("response_id"):
        msg["response_id"] = resp.get("response_id")
    if resp.get("continue_token"):
        msg["continue_token"] = resp.get("continue_token")

    sess["messages"].append(msg)


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

    # Render chat so far
    render_learning_messages(sess)

    # =========================
    # UIB: fixed bottom capsule (native widgets)
    # =========================

    # IMPORTANT: Clear input BEFORE the widget is instantiated in this run
    if st.session_state._uib_clear_next:
        st.session_state.uib_text = ""
        st.session_state._uib_clear_next = False

    cur_mode = st.session_state.uib_mode

    st.markdown('<div class="ini-uib-wrap"><div class="ini-uib-shell">', unsafe_allow_html=True)

    c_input, c_over, c_quiz, c_send = st.columns([12, 1.3, 1.3, 1.3], gap="small")

    with c_input:
        st.text_input(
            "",
            key="uib_text",
            placeholder="Type your topic/question...",
            label_visibility="collapsed",
            on_change=_enter_submit,
        )

    with c_over:
        lit = "lit-overview" if cur_mode == "high" else ""
        st.markdown(f'<div class="ini-icon-wrap {lit}">', unsafe_allow_html=True)
        if st.button("◎", key="uib_btn_overview", help="Overview (toggle)"):
            _toggle_mode("high")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c_quiz:
        lit = "lit-quiz" if cur_mode == "quiz" else ""
        st.markdown(f'<div class="ini-icon-wrap {lit}">', unsafe_allow_html=True)
        if st.button("?", key="uib_btn_quiz", help="Quiz (toggle)"):
            _toggle_mode("quiz")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with c_send:
        st.markdown('<div class="ini-icon-wrap ini-send-wrap">', unsafe_allow_html=True)
        send_clicked = st.button("➤", key="uib_btn_send", help="Send")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    mode_txt = "Deep (default)" if cur_mode == "deep" else ("Overview" if cur_mode == "high" else "Quiz")
    st.markdown(
        f"""
        <div class="ini-uib-subhint">
          <span>• <b>{mode_txt}</b></span>
          <span>Enter or ➤ to send • Icons toggle mode</span>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if send_clicked:
        st.session_state._uib_submit = True

    if st.session_state._uib_submit:
        st.session_state._uib_submit = False
        prompt = (st.session_state.uib_text or "").strip()
        if prompt:
            try:
                _process_send(sess, prompt, cur_mode)
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

            # Reset after sending (SAFE way)
            st.session_state._uib_clear_next = True
            st.session_state.uib_mode = "deep"
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
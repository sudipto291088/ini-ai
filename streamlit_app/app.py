import os
import time
import re
import secrets
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from pathlib import Path

import requests
import streamlit as st
from storage_sqlite import (
    init_db,
    save_session,
    list_sessions,
    load_session,
    delete_session,
    rename_session,
)
from time_utils import browser_local_now



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
st.set_page_config(page_title="InI.ai", layout="wide", initial_sidebar_state="expanded")

visitor_param = st.query_params.get("visitor")
if isinstance(visitor_param, list):
    visitor_param = visitor_param[-1] if visitor_param else ""

visitor_id = str(visitor_param or "").strip()
if not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", visitor_id):
    visitor_id = secrets.token_urlsafe(24)
    st.query_params["visitor"] = visitor_id

st.session_state.visitor_id = visitor_id

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

/* Material icons removed to prevent stray keyboard_double_arrow_right text rendering */

html, body{
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif !important;
  color: var(--ink);
}
button, input, textarea, select, label, p, div, a{
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif !important;
}

span{
  font-family: inherit;
}

/* Sidebar collapse icon: replace broken ligature text with a clean arrow */
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]{
  font-size: 0 !important;
  line-height: 1 !important;
  color: transparent !important;
  position: relative !important;
  display: inline-block !important;
  width: 1.5rem !important;
  height: 1.5rem !important;
}

[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"]::before{
  content: "❮" !important;
  font-size: 1.15rem !important;
  line-height: 1.5rem !important;
  color: rgba(49, 51, 63, 0.6) !important;
  position: absolute !important;
  inset: 0 !important;
  text-align: center !important;
}

[data-testid="stSidebarCollapseButton"]{
  min-width: 2rem !important;
  min-height: 2rem !important;
}

.main .block-container{
  max-width: 980px;
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
}

/* --- Sidebar clock tile --- */
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

/* Prevent Continue wrapping */
button[kind="secondary"]{
  min-width: 110px !important;
}

/* =========================
   UIB capsule (stable)
   ========================= */
.ini_uib_wrap{ margin-top: 120px; }
.ini_uib_outer{
  display:flex;
  justify-content:center;
  width:100%;
}
.ini_uib_capsule{
  width: min(980px, 100%);
  border: 1px solid var(--stroke);
  background: #fff;
  border-radius: 999px;
  padding: 14px 18px;
}
.ini_uib_capsule [data-testid="stHorizontalBlock"]{
  flex-wrap: nowrap !important;
  align-items:center !important;
}
.ini_uib_capsule [data-testid="column"]{
  min-width: 0 !important;
}
.ini_uib_capsule div[data-testid="stTextInput"] input{
  border-radius: 999px !important;
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}
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
.ini_lit_over .ini_uib_capsule [data-testid="column"]:nth-child(2) button{
  background: var(--litOver) !important;
  border-color: #c7d2fe !important;
}
.ini_lit_quiz .ini_uib_capsule [data-testid="column"]:nth-child(3) button{
  background: var(--litQuiz) !important;
  border-color: #ddd6fe !important;
}
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

.ini_session_row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:8px;
  margin: 2px 0 6px 0;
}

.ini_session_menu{
  position:relative;
  min-width:18px;
  text-align:right;
  opacity:0;
  transition:opacity 0.15s ease;
}

.ini_session_row:hover .ini_session_menu{
  opacity:1;
}

.ini_session_menu details{
  position:relative;
}

.ini_session_menu summary{
  list-style:none;
  cursor:pointer;
  color:#9aa0a6;
  font-size:18px;
  line-height:1;
  user-select:none;
}

.ini_session_menu summary::-webkit-details-marker{
  display:none;
}

.ini_session_dropdown{
  position:absolute;
  right:0;
  top:20px;
  min-width:90px;
  background:#fff;
  border:1px solid var(--stroke);
  border-radius:10px;
  box-shadow:0 8px 24px rgba(15,23,42,0.08);
  padding:6px 0;
  z-index:999;
}

.ini_session_dropdown a{
  display:block;
  padding:7px 10px;
  text-decoration:none !important;
  color:var(--ink) !important;
  font-size:13px;
}

.ini_session_dropdown a:hover{
  background:#f8fafc;
}

/* Make chat look cleaner */
.stChatMessage{
  padding-top: 0.25rem !important;
  padding-bottom: 0.25rem !important;
}
.stChatMessage .stMarkdown{
  line-height: 1.38;
}

/* Follow-up / session links */
.ini_plain_link{
  display:block;
  text-decoration:none !important;
  color: var(--ink) !important;
  text-align:left !important;
  margin: 6px 0;
  line-height: 1.55;
  border:none !important;
  outline:none !important;
  background:transparent !important;
  padding:0 !important;
  font-size: 0.95rem;
}
.ini_plain_link:hover{
  text-decoration:none !important;
}
.ini_sidebar_link{
  display:block;
  text-decoration:none !important;
  color: var(--ink) !important;
  text-align:left !important;
  padding: 6px 0;
  line-height: 1.4;
}
.ini_sidebar_link:hover{
  text-decoration:none !important;
}
.ini_popup_section{
  margin-top: 8px;
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

/* Preserve Streamlit material icon fonts */

/* Keep custom expander arrows */
.stExpander summary::before {
  content: "➤";
  display: inline-block;
  margin-right: 6px;
  font-size: 15px;
}

.stExpander details[open] > summary::before {
  content: "▼";
}


div[data-testid="stVerticalBlockBorderWrapper"]{
  background:#ffffff !important;
  border:1px solid #e5e7eb !important;
  border-radius:22px !important;
  padding:22px 26px !important;
  margin:18px 0 28px 0 !important;
  box-shadow:0 6px 22px rgba(15,23,42,0.08) !important;
  overflow:hidden !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] > div{
  background:#ffffff !important;
}

/* Interrogate question mini wrappers */
div.stButton > button {
  width:100% !important;
  text-align:left !important;
  justify-content:flex-start !important;
  white-space:normal !important;
  height:auto !important;
  line-height:1.45 !important;
  padding:12px 14px !important;
  margin:5px 0 !important;

  background:#ffffff !important;
  color:#111827 !important;
  border:1px solid #e5e7eb !important;
  border-radius:14px !important;
  box-shadow:0 1px 4px rgba(15,23,42,0.05) !important;
}

/* Hover polish */
div.stButton > button:hover {
  background:#f8fafc !important;
  border-color:#d1d5db !important;
}


</style>
"""

init_db()

st.markdown(CSS, unsafe_allow_html=True)

# Load external styles.css (safe addition)
try:
    css_path = Path(__file__).parent / "styles.css"

    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True,
            )
except Exception:
    pass




# =========================
# Helpers
# =========================
def _user_now() -> datetime:
    try:
        timezone_offset = st.context.timezone_offset
    except Exception:
        timezone_offset = None
    return browser_local_now(timezone_offset)


def now_label() -> str:
    return _user_now().strftime("%a, %b %d • %I:%M %p")


def new_msg_id(prefix: str) -> str:
    return f"{prefix}-{time.time_ns()}"


def clock_parts() -> Dict[str, str]:
    now = _user_now()
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
    created = sess.get("created") or _user_now().strftime("%b %d.%Y")
    return f"{kw}.{created}"


def needs_continue_flag(msg: Dict[str, Any]) -> bool:
    return bool(msg.get("incomplete"))


def mode_label(mode: str) -> str:
    m = (mode or "").strip().lower()
    if m == "high":
        return "Overview"
    if m == "quiz":
        return "Quiz"
    return "Deep"


def _strip_duplicate_chunk_prefix(chunk: str) -> str:
    if not chunk:
        return chunk

    lines = chunk.splitlines()

    while lines and not lines[0].strip():
        lines.pop(0)

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


def truncate_session_text(text: str, max_chars: int = 28) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) <= max_chars:
        return s
    return s[:max_chars].rstrip() + "..."


def _format_short_mmdd(created_at: str) -> str:
    s = (created_at or "").strip()
    if not s:
        return ""

    for fmt in ("%b %d.%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%m/%d")
        except Exception:
            pass

    return ""


def _query_href(**updates: Optional[str]) -> str:
    params: Dict[str, str] = {}
    for key, value in st.query_params.items():
        if isinstance(value, list):
            if value:
                params[key] = str(value[-1])
        elif value is not None:
            params[key] = str(value)

    for key, value in updates.items():
        if value is None or str(value).strip() == "":
            params.pop(key, None)
        else:
            params[key] = str(value)

    return "?" + urlencode(params)


def _private_href(**params: Optional[str]) -> str:
    values: Dict[str, str] = {
        "visitor": st.session_state.visitor_id,
    }
    for key, value in params.items():
        if value is not None and str(value).strip():
            values[key] = str(value)
    return "?" + urlencode(values)


def _reset_query_to_page(page: str) -> None:
    st.query_params.clear()
    st.query_params["visitor"] = st.session_state.visitor_id
    st.query_params["page"] = page


def _chat_popup_href(sid: str) -> str:
    return _query_href(popup_chat_sid=sid)


def _chat_root_href(sid: str) -> str:
    return _private_href(page="chat", chat_sid=sid)

def _chat_root_view_href(sid: str) -> str:
    return _private_href(page="chat", chat_sid=sid, chat_root="1")



def _chat_branch_href(sid: Optional[str], question: str) -> str:
    if sid:
        return _private_href(page="chat", chat_sid=sid, chat_q=question)
    return _private_href(page="chat", chat_q=question)


def _learn_session_href(sid: str) -> str:
    return _private_href(page="learn", learn_sid=sid)


def _learn_branch_href(sid: Optional[str], question: str) -> str:
    if sid:
        return _private_href(page="learn", learn_sid=sid, learn_q=question)
    return _private_href(page="learn", learn_q=question)


def _chat_rename_href(sid: str) -> str:
    return _private_href(
        page="chat",
        session_action="rename",
        session_sid=sid,
    )


def _chat_delete_href(sid: str) -> str:
    return _private_href(
        page="chat",
        session_action="delete",
        session_sid=sid,
    )


def _learn_rename_href(sid: str) -> str:
    return _private_href(
        page="learn",
        session_action="rename",
        session_sid=sid,
    )


def _learn_delete_href(sid: str) -> str:
    return _private_href(
        page="learn",
        session_action="delete",
        session_sid=sid,
    )



def clean_followup_text(text: str) -> str:
    s = (text or "").strip()

    # remove numbering already supplied by backend
    s = re.sub(r"^\(?\d+\)?[.)]?\s*", "", s)
    s = re.sub(r"^[•\-*]\s*", "", s)

    # remove wrapping quotes
    s = s.strip('"').strip("'")

    # collapse duplicate spaces
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def render_followup_links(
    page: str,
    followups: list[str],
    sid: Optional[str] = None,
    target: Optional[str] = None,
) -> None:
    cleaned: list[str] = []
    seen = set()

    for fu in followups or []:
        item = clean_followup_text(fu)
        key = re.sub(r"\s+", " ", item.lower()).strip()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)

    if not cleaned:
        return

    if target is None:
        target = "_blank" if page == "chat" else "_self"

    for idx, fu in enumerate(cleaned, start=1):
        if page == "chat":
            href = _chat_branch_href(sid, fu)
        else:
            href = _learn_branch_href(sid, fu)

        st.markdown(
            f'<a class="ini_plain_link" '
            f'href="{href}" '
            f'target="{target}" '
            f'style="display:block; cursor:pointer; color:#2563eb !important; margin:8px 0;">'
            f'{idx}. {fu} ↗'
            f'</a>',
            unsafe_allow_html=True,
        )


def render_followup_text(followups: list[str]) -> None:
    cleaned: list[str] = []
    seen = set()

    for fu in followups or []:
        item = clean_followup_text(fu)
        key = re.sub(r"\s+", " ", item.lower()).strip()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)

    if not cleaned:
        return

    st.markdown(
        "\n".join([f"{idx}. {item}" for idx, item in enumerate(cleaned, start=1)])
    )


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

if "_nc_continue_q" not in st.session_state:
    st.session_state._nc_continue_q = None

if "_nc_continue_loading_q" not in st.session_state:
    st.session_state._nc_continue_loading_q = None

if "_mnl_continue_loading_id" not in st.session_state:
    st.session_state._mnl_continue_loading_id = None

if "chat_direct_answer" not in st.session_state:
    st.session_state.chat_direct_answer = None

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions: Dict[str, Dict[str, Any]] = {}

if "chat_active_id" not in st.session_state:
    st.session_state.chat_active_id = None

if "chat_loaded_sid" not in st.session_state:
    st.session_state.chat_loaded_sid = None

if "chat_branch_history" not in st.session_state:
    st.session_state.chat_branch_history = []

if "chat_popup_sid" not in st.session_state:
    st.session_state.chat_popup_sid = None

if "chat_top_topic_input" not in st.session_state:
    st.session_state.chat_top_topic_input = ""

if "chat_bottom_topic_input" not in st.session_state:
    st.session_state.chat_bottom_topic_input = ""

if "chat_root_topic" not in st.session_state:
    st.session_state.chat_root_topic = ""

if "chat_root_interrogate" not in st.session_state:
    st.session_state.chat_root_interrogate = None

if "chat_root_illustrate" not in st.session_state:
    st.session_state.chat_root_illustrate = None

if "chat_root_intro" not in st.session_state:
    st.session_state.chat_root_intro = ""

if "chat_root_direct_answer" not in st.session_state:
    st.session_state.chat_root_direct_answer = None

if "chat_root_answers" not in st.session_state:
    st.session_state.chat_root_answers = {}

if "chat_root_followups" not in st.session_state:
    st.session_state.chat_root_followups = {}

if "chat_root_open_questions" not in st.session_state:
    st.session_state.chat_root_open_questions = set()

if "chat_root_visited_questions" not in st.session_state:
    st.session_state.chat_root_visited_questions = set()

if "chat_top_enter_submit" not in st.session_state:
    st.session_state.chat_top_enter_submit = False

if "chat_bottom_enter_submit" not in st.session_state:
    st.session_state.chat_bottom_enter_submit = False

if "chat_branch_answers" not in st.session_state:
    st.session_state.chat_branch_answers = []

# UIB state
if "uib_text" not in st.session_state:
    st.session_state.uib_text = ""
if "uib_mode" not in st.session_state:
    st.session_state.uib_mode = "deep"  # deep|high|quiz

if "_uib_send_requested" not in st.session_state:
    st.session_state._uib_send_requested = False

if "_mnl_pending_request" not in st.session_state:
    st.session_state._mnl_pending_request = None

if "_mnl_generating" not in st.session_state:
    st.session_state._mnl_generating = False

if "nc_started" not in st.session_state:
    st.session_state.nc_started = False

if "rename_session_sid" not in st.session_state:
    st.session_state.rename_session_sid = None

if "rename_session_page" not in st.session_state:
    st.session_state.rename_session_page = None


def ensure_learning_session() -> str:
    if (
        st.session_state.learning_active_id
        and st.session_state.learning_active_id in st.session_state.learning_sessions
    ):
        return st.session_state.learning_active_id

    sid = f"learn-{secrets.token_urlsafe(12)}"
    st.session_state.learning_sessions[sid] = {
        "created": _user_now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
        "_title_set": False,
    }
    st.session_state.learning_active_id = sid
    return sid


def start_new_learning_session() -> str:
    sid = f"learn-{secrets.token_urlsafe(12)}"
    st.session_state.learning_sessions[sid] = {
        "created": _user_now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
        "_title_set": False,
    }
    st.session_state.learning_active_id = sid
    return sid


def _persist_learning_session(sid: str, sess: Dict[str, Any]) -> None:
    created = sess.get("created") or _user_now().strftime("%b %d.%Y")

    default_titles = {"", "Learning Session", "Session", "New Session"}

    first_user_prompt = ""
    for m in sess.get("messages", []):
        if m.get("role") == "user":
            t = (m.get("text") or "").strip()
            if t:
                first_user_prompt = t
                break

    current_title = (sess.get("title") or "").strip()

    if not sess.get("_title_set", False):
        if (current_title in default_titles) and first_user_prompt:
            sess["title"] = first_user_prompt
            sess["_title_set"] = True
        elif current_title and (current_title not in default_titles):
            sess["_title_set"] = True

    title_to_save = (sess.get("title") or "Learning Session").strip()

    save_session(
        visitor_id=st.session_state.visitor_id,
        session_id=sid,
        title=title_to_save,
        created_at=created,
        messages=sess.get("messages", []),
    )


def _empty_new_chat_state() -> Dict[str, Any]:
    return {
        "topic": "",
        "interrogate": None,
        "illustrate": None,
        "chat_intro": "",
        "chat_answers": {},
        "chat_followups": {},
        "chat_open_questions": [],
        "chat_visited_questions": [],
        "chat_direct_answer": None,
        "chat_seed_done": "",
        "chat_branch_history": [],
        "chat_branch_answers": [],
    }


def _reset_new_chat_state() -> None:
    st.session_state.chat = {"topic": "", "interrogate": None, "illustrate": None}
    st.session_state.chat_intro = ""
    st.session_state.chat_answers = {}
    st.session_state.chat_followups = {}
    st.session_state.chat_open_questions = set()
    st.session_state.chat_visited_questions = set()
    st.session_state.chat_direct_answer = None
    st.session_state.chat_seed_done = ""
    st.session_state.chat_branch_history = []
    st.session_state.chat_branch_answers = []
    st.session_state.chat_top_topic_input = ""
    st.session_state.chat_bottom_topic_input = ""

    st.session_state.chat_root_topic = ""
    st.session_state.chat_root_interrogate = None
    st.session_state.chat_root_illustrate = None
    st.session_state.chat_root_intro = ""
    st.session_state.chat_root_direct_answer = None
    st.session_state.chat_root_answers = {}
    st.session_state.chat_root_followups = {}
    st.session_state.chat_root_open_questions = set()
    st.session_state.chat_root_visited_questions = set()
    st.session_state.nc_started = False

def _current_new_chat_payload() -> Dict[str, Any]:
    return {
        "topic": (st.session_state.chat.get("topic") or "").strip(),
        "interrogate": st.session_state.chat.get("interrogate"),
        "illustrate": st.session_state.chat.get("illustrate"),
        "chat_intro": st.session_state.chat_intro,
        "chat_answers": st.session_state.chat_answers,
        "chat_followups": st.session_state.chat_followups,
        "chat_open_questions": sorted(list(st.session_state.chat_open_questions)),
        "chat_visited_questions": sorted(list(st.session_state.chat_visited_questions)),
        "chat_direct_answer": st.session_state.chat_direct_answer,
        "chat_seed_done": st.session_state.chat_seed_done,
        "chat_branch_history": st.session_state.chat_branch_history,
        "chat_branch_answers": st.session_state.chat_branch_answers,

        "chat_root_topic": st.session_state.chat_root_topic,
        "chat_root_interrogate": st.session_state.chat_root_interrogate,
        "chat_root_illustrate": st.session_state.chat_root_illustrate,
        "chat_root_intro": st.session_state.chat_root_intro,
        "chat_root_direct_answer": st.session_state.chat_root_direct_answer,
        "chat_root_answers": st.session_state.chat_root_answers,
        "chat_root_followups": st.session_state.chat_root_followups,
        "chat_root_open_questions": sorted(list(st.session_state.chat_root_open_questions)),
        "chat_root_visited_questions": sorted(list(st.session_state.chat_root_visited_questions)),
    }


def _new_chat_title_from_payload(payload: Dict[str, Any]) -> str:
    root_topic = (payload.get("chat_root_topic") or "").strip()
    if root_topic:
        return root_topic

    topic = (payload.get("topic") or "").strip()
    if topic:
        return topic

    direct = payload.get("chat_direct_answer") or {}
    prompt = (direct.get("prompt") or "").strip() if isinstance(direct, dict) else ""
    if prompt:
        return prompt

    visited = payload.get("chat_visited_questions") or []
    if visited:
        return str(visited[0]).strip()

    return "New Chat Session"


def _persist_new_chat_session(sid: Optional[str] = None) -> str:
    payload = _current_new_chat_payload()

    has_meaningful_content = any([
        payload.get("topic"),
        payload.get("interrogate"),
        payload.get("illustrate"),
        payload.get("chat_intro"),
        payload.get("chat_answers"),
        payload.get("chat_direct_answer"),
    ])

    if not has_meaningful_content:
        return st.session_state.chat_active_id or st.session_state.chat_loaded_sid or ""

    if not sid:
        sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

    if not sid:
        sid = f"chat-{secrets.token_urlsafe(12)}"

    st.session_state.chat_active_id = sid
    st.session_state.chat_loaded_sid = sid

    created = _user_now().strftime("%b %d.%Y")
    existing = st.session_state.chat_sessions.get(sid, {})
    if existing.get("created"):
        created = existing["created"]

    title = _new_chat_title_from_payload(payload)

    st.session_state.chat_sessions[sid] = {
        "created": created,
        "title": title,
        "payload": payload,
    }

    save_session(
        visitor_id=st.session_state.visitor_id,
        session_id=sid,
        title=title,
        created_at=created,
        messages=payload,
    )
    return sid


def _load_new_chat_session(sid: str) -> bool:
    loaded = load_session(st.session_state.visitor_id, sid)
    if not loaded:
        return False

    payload = loaded.get("messages") or {}
    if not isinstance(payload, dict):
        return False

    st.session_state.chat_active_id = sid
    st.session_state.chat_loaded_sid = sid
    st.session_state.chat_sessions[sid] = {
        "created": loaded.get("created") or _user_now().strftime("%b %d.%Y"),
        "title": (loaded.get("title") or "New Chat Session"),
        "payload": payload,
    }

    st.session_state.chat = {
        "topic": payload.get("topic") or "",
        "interrogate": payload.get("interrogate"),
        "illustrate": payload.get("illustrate"),
    }
    st.session_state.chat_intro = payload.get("chat_intro") or ""
    st.session_state.chat_answers = payload.get("chat_answers") or {}
    st.session_state.chat_followups = payload.get("chat_followups") or {}
    st.session_state.chat_open_questions = set(payload.get("chat_open_questions") or [])
    st.session_state.chat_visited_questions = set(payload.get("chat_visited_questions") or [])
    st.session_state.chat_direct_answer = payload.get("chat_direct_answer")
    st.session_state.chat_seed_done = payload.get("chat_seed_done") or ""
    st.session_state.chat_branch_history = payload.get("chat_branch_history") or []
    st.session_state.chat_branch_answers = payload.get("chat_branch_answers") or []
    st.session_state.chat_top_topic_input = payload.get("topic") or ""
    st.session_state.chat_bottom_topic_input = ""
    st.session_state.chat_root_topic = payload.get("chat_root_topic") or payload.get("topic") or ""
    st.session_state.chat_root_interrogate = payload.get("chat_root_interrogate")
    st.session_state.chat_root_illustrate = payload.get("chat_root_illustrate")
    st.session_state.chat_root_intro = payload.get("chat_root_intro") or ""
    st.session_state.chat_root_direct_answer = payload.get("chat_root_direct_answer")
    st.session_state.chat_root_answers = payload.get("chat_root_answers") or {}
    st.session_state.chat_root_followups = payload.get("chat_root_followups") or {}
    st.session_state.chat_root_open_questions = set(payload.get("chat_root_open_questions") or [])
    st.session_state.chat_root_visited_questions = set(payload.get("chat_root_visited_questions") or [])

    st.session_state.nc_started = True
    return True


def _activate_root_view_from_loaded_session() -> None:
    st.session_state.chat["interrogate"] = st.session_state.chat_root_interrogate
    st.session_state.chat["illustrate"] = st.session_state.chat_root_illustrate
    st.session_state.chat_intro = st.session_state.chat_root_intro or ""
    st.session_state.chat_answers = dict(st.session_state.chat_root_answers or {})
    st.session_state.chat_followups = dict(st.session_state.chat_root_followups or {})
    st.session_state.chat_open_questions = set(st.session_state.chat_root_open_questions or [])
    st.session_state.chat_visited_questions = set(st.session_state.chat_root_visited_questions or [])
    st.session_state.chat_direct_answer = st.session_state.chat_root_direct_answer
    st.session_state.chat_seed_done = ""

def _sync_chat_root_snapshot() -> None:
    existing_root_interrogate = (
        st.session_state.chat_root_interrogate
        if isinstance(st.session_state.chat_root_interrogate, dict)
        else {}
    )
    existing_root_illustrate = (
        st.session_state.chat_root_illustrate
        if isinstance(st.session_state.chat_root_illustrate, dict)
        else {}
    )

    current_interrogate = st.session_state.chat.get("interrogate")
    current_illustrate = st.session_state.chat.get("illustrate")

    if isinstance(current_interrogate, dict):
        st.session_state.chat_root_interrogate = {
            **current_interrogate,
            "ts": existing_root_interrogate.get("ts") or now_label(),
        }
    else:
        st.session_state.chat_root_interrogate = current_interrogate

    if isinstance(current_illustrate, dict):
        st.session_state.chat_root_illustrate = {
            **current_illustrate,
            "ts": existing_root_illustrate.get("ts") or now_label(),
        }
    else:
        st.session_state.chat_root_illustrate = current_illustrate

    st.session_state.chat_root_intro = st.session_state.chat_intro or ""
    st.session_state.chat_root_direct_answer = st.session_state.chat_direct_answer
    st.session_state.chat_root_answers = dict(st.session_state.chat_answers or {})
    st.session_state.chat_root_followups = dict(st.session_state.chat_followups or {})
    st.session_state.chat_root_open_questions = set(st.session_state.chat_open_questions or [])
    st.session_state.chat_root_visited_questions = set(st.session_state.chat_visited_questions or [])



def _append_chat_branch(prompt: str, kind: str) -> None:
    p = (prompt or "").strip()
    k = (kind or "").strip().lower()

    # Only explicit CTA/FUQ-derived prompts should be stored in popup history.
    # Ordinary typed follow-up topics should not appear there.
    if not p or k not in {"fuq", "cta"}:
        return

    existing = st.session_state.chat_branch_history or []
    key = (p.lower(), k)
    seen = {
        (str(x.get("prompt", "")).strip().lower(), str(x.get("kind", "")).strip().lower())
        for x in existing
        if isinstance(x, dict)
    }

    if key not in seen:
        existing.append({"prompt": p, "kind": k})
        st.session_state.chat_branch_history = existing


def _collect_chat_popup_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    root_topic = (
        (payload.get("chat_root_topic") or "").strip()
        or (payload.get("topic") or "").strip()
        or "Root Topic"
    )

    history = payload.get("chat_branch_history") or []

    fuqs: list[str] = []
    ctas: list[str] = []

    for item in history:
        if not isinstance(item, dict):
            continue
        prompt = (item.get("prompt") or "").strip()
        kind = (item.get("kind") or "").strip().lower()
        if not prompt:
            continue
        if kind == "cta":
            ctas.append(prompt)
        elif kind == "fuq":
            fuqs.append(prompt)

    def _dedupe(seq: list[str]) -> list[str]:
        out = []
        seen = set()
        for x in seq:
            k = x.strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(x)
        return out

    return {
        "root_topic": root_topic,
        "fuqs": _dedupe(fuqs),
        "ctas": _dedupe(ctas),
    }


@st.dialog("Session Branches")
def _render_chat_session_popup() -> None:
    sid = st.session_state.chat_popup_sid
    if not sid:
        return

    loaded = load_session(st.session_state.visitor_id, sid)
    if not loaded:
        st.warning("Session could not be loaded.")
        return

    payload = loaded.get("messages") or {}
    if not isinstance(payload, dict):
        st.warning("Session payload is invalid.")
        return

    data = _collect_chat_popup_data(payload)
    root_topic = data["root_topic"]
    fuqs = data["fuqs"]
    ctas = data["ctas"]

    has_visible_bg = any([
        (st.session_state.get("chat") or {}).get("interrogate"),
        (st.session_state.get("chat") or {}).get("illustrate"),
        st.session_state.get("chat_direct_answer"),
        bool(st.session_state.get("chat_answers", {})),
    ])

    fuq_target = "_blank" if has_visible_bg else "_self"

    st.markdown(
        f'<a class="ini_plain_link" href="{_chat_root_view_href(sid)}" target="_self"><b>↠ {root_topic}</b></a>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    st.markdown("#### FUQs")
    if fuqs:
        html = ['<div class="ini_popup_section">']
        for item in fuqs:
            href = _chat_branch_href(sid, item)
            html.append(f'<a class="ini_plain_link" href="{href}" target="{fuq_target}">{item}</a>')
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.caption("No FUQs saved yet.")

    st.markdown("#### CTAs")
    if ctas:
        html = ['<div class="ini_popup_section">']
        for item in ctas:
            href = _chat_branch_href(sid, item)
            html.append(f'<a class="ini_plain_link" href="{href}" target="_blank">{item}</a>')
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.caption("No CTAs saved yet.")

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
    payload: Dict[str, Any] = {"topic": topic, "mode": mode}

    if continue_mode and previous_answer:
        payload["continue_mode"] = True
        payload["previous_answer"] = previous_answer

    return post_json("/study/ai", payload, timeout=180)


def fetch_interrogate(topic: str) -> Dict[str, Any]:
    return post_json("/interrogate", {"topic": topic}, timeout=240)


def fetch_illustrate(topic: str) -> Dict[str, Any]:
    return post_json("/illustrate", {"topic": topic}, timeout=240)


def fetch_study_full(topic: str, mode: str = "deep", max_rounds: int = 4) -> Dict[str, Any]:
    resp = fetch_study(topic, mode=mode)
    answer = normalize_whitespace_for_readability(
        normalize_mojibake(resp.get("answer", "") or "")
    )

    rounds = 0
    while rounds < max_rounds and (
        resp.get("incomplete") is True
        or (resp.get("stop_reason") or "").strip().lower() == "max_output_tokens"
    ):
        resp = fetch_study(
            topic,
            mode=mode,
            continue_mode=True,
            previous_answer=answer,
        )
        chunk = normalize_whitespace_for_readability(
            normalize_mojibake(resp.get("answer", "") or "")
        ).strip()

        if not chunk:
            break

        answer = (answer.rstrip() + "\n\n" + chunk).strip()
        rounds += 1

    return {
        "answer": answer,
        "incomplete": resp.get("incomplete"),
        "stop_reason": resp.get("stop_reason"),
        "followups": resp.get("followups") or [],
    }


def split_answer_and_embedded_followups(text: str) -> tuple[str, list[str]]:
    if not text:
        return "", []

    lines = text.splitlines()

    marker_patterns = [
        r"^suggested follow-ups?:?$",
        r"^suggested follow-up questions:?$",
    ]

    cta_header_patterns = [
        r"^if you want,?\s+i can\b.*:?\s*$",
        r"^if you'd like,?\s+i can\b.*:?\s*$",
        r"^next i can\b.*:?\s*$",
        r"^would you like\b.*:?\s*$",
        r"^do you want me to\b.*:?\s*$",
        r"^which part should i expand on\b.*:?\s*$",
        r"^should i\b.*:?\s*$",
    ]

    def _clean_fu_line(s: str) -> str:
        s = re.sub(r"^\(?\d+\)?[.)]?\s*", "", s)
        s = re.sub(r"^[-•*o]\s*", "", s)
        return s.strip()

    marker_idx = None
    for i, ln in enumerate(lines):
        s = re.sub(r"[*_`]+", "", (ln or "").strip()).lower()
        if any(re.match(p, s) for p in marker_patterns):
            marker_idx = i
            break

    followups: list[str] = []
    body_lines: list[str] = []

    if marker_idx is not None:
        body_lines = lines[:marker_idx]
        fu_lines = lines[marker_idx + 1:]

        for ln in fu_lines:
            s = _clean_fu_line((ln or "").strip())
            if s:
                followups.append(s)

        return "\n".join(body_lines).strip(), followups

    i = 0
    while i < len(lines):
        raw = lines[i]
        s = (raw or "").strip()
        low = s.lower()

        if any(re.match(p, low) for p in cta_header_patterns):
            body_lines.append("")
            i += 1

            while i < len(lines):
                next_raw = lines[i]
                next_s = (next_raw or "").strip()

                if not next_s:
                    break

                cleaned = _clean_fu_line(next_s)

                if any(re.match(p, cleaned.lower()) for p in cta_header_patterns):
                    i += 1
                    continue

                if cleaned and len(cleaned) >= 8 and not cleaned.endswith(":"):
                    followups.append(cleaned)

                i += 1

            while i < len(lines) and not (lines[i] or "").strip():
                i += 1
            continue

        body_lines.append(raw)
        i += 1

    seen = set()
    deduped = []
    for fu in followups:
        key = fu.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(fu)

    return "\n".join(body_lines).strip(), deduped


def normalize_clicked_followup_prompt(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return s

    lowered = s.lower()

    patterns = [
        r"^would you like\s+",
        r"^do you want\s+",
        r"^want\s+",
        r"^interested in\s+",
    ]

    for p in patterns:
        if re.match(p, lowered):
            s = re.sub(p, "", s, flags=re.IGNORECASE).strip()
            break

    replacements = [
        ("a short checklist", "Give me a short checklist"),
        ("a concise comparison", "Give me a concise comparison"),
        ("a compact example", "Give me a compact example"),
        ("a practical checklist", "Give me a practical checklist"),
        ("a short plan", "Give me a short plan"),
    ]

    low2 = s.lower()
    for old, new in replacements:
        if low2.startswith(old):
            s = new + s[len(old):]
            break

    s = s.rstrip(" ?")
    return s      




# =========================
# URL / Query routing
# =========================
qp = st.query_params
page_param = (qp.get("page") or "home").lower()
learn_sid = (qp.get("learn_sid") or "").strip()
chat_sid = (qp.get("chat_sid") or "").strip()
popup_chat_sid = (qp.get("popup_chat_sid") or "").strip()
chat_root = (qp.get("chat_root") or "").strip()
chat_q = (qp.get("chat_q") or "").strip()
learn_q = (qp.get("learn_q") or "").strip()
session_action = (qp.get("session_action") or "").strip().lower()
session_sid = (qp.get("session_sid") or "").strip()

param_to_page = {
    "home": "Home",
    "chat": "New Chat",
    "learn": "My New Learning",
    "proj": "New Project",
}

if page_param in param_to_page:
    new_page = param_to_page[page_param]
    st.session_state.page = new_page


previous_page_param = st.session_state.get("_last_page_param")

if (
    page_param == "chat"
    and not chat_sid
    and not chat_q
    and not popup_chat_sid
    and previous_page_param != "chat"
):
    _reset_new_chat_state()
    st.session_state.chat_active_id = None
    st.session_state.chat_loaded_sid = None

st.session_state._last_page_param = page_param

if popup_chat_sid:
    st.session_state.chat_popup_sid = popup_chat_sid
else:
    st.session_state.chat_popup_sid = None

if learn_sid:
    loaded = load_session(st.session_state.visitor_id, learn_sid)
    if loaded:
        st.session_state.learning_active_id = learn_sid
        st.session_state.learning_sessions[learn_sid] = {
            "created": loaded.get("created") or _user_now().strftime("%b %d.%Y"),
            "messages": loaded.get("messages") or [],
            "title": (loaded.get("title") or "Learning Session"),
            "last_prompt": "",
            "_title_set": (loaded.get("title") or "").strip() not in {"", "Learning Session", "Session", "New Session"},
        }

if chat_sid:
    if st.session_state.chat_loaded_sid != chat_sid:
        _load_new_chat_session(chat_sid)
    elif not st.session_state.chat.get("topic"):
        _load_new_chat_session(chat_sid)

if chat_sid and chat_root == "1":
    if st.session_state.chat_loaded_sid != chat_sid or (
        not st.session_state.chat_root_interrogate
        and not st.session_state.chat_root_illustrate
        and not st.session_state.chat_root_intro
        and not st.session_state.chat_root_answers
    ):
        _load_new_chat_session(chat_sid)
    _activate_root_view_from_loaded_session()

if session_action and session_sid:
    if session_action == "delete":
        delete_session(st.session_state.visitor_id, session_sid)

        if st.session_state.chat_active_id == session_sid:
            st.session_state.chat_active_id = None
            st.session_state.chat_loaded_sid = None

        if st.session_state.learning_active_id == session_sid:
            st.session_state.learning_active_id = None

        _reset_query_to_page(page_param)
        st.rerun()

    elif session_action == "rename":
        st.session_state.rename_session_sid = session_sid
        st.session_state.rename_session_page = page_param
        _reset_query_to_page(page_param)






# =========================
# Sidebar
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
    st.markdown('<span class="badge">v0.1.2 • AI Tutor</span>', unsafe_allow_html=True)

    st.markdown('<div class="small" style="color:var(--muted); font-weight:750; margin-top:10px;">Navigation</div>', unsafe_allow_html=True)
    intro_nav_href = _private_href(page="home")
    chat_nav_href = _private_href(page="chat")
    learn_nav_href = _private_href(page="learn")
    project_nav_href = _private_href(page="proj")
    st.markdown(
        f"""
        <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="{intro_nav_href}" target="_self">🏠&nbsp;&nbsp;Introduction</a>
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="{chat_nav_href}" target="_self">💬&nbsp;&nbsp;New Chat</a>
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="{learn_nav_href}" target="_self">📚&nbsp;&nbsp;My New Learning</a>
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="{project_nav_href}" target="_self">🧩&nbsp;&nbsp;New Project</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if DEV_MODE:
        st.markdown("<hr/>", unsafe_allow_html=True)
        with st.expander("API Settings (dev)", expanded=False):
            st.session_state.api_base = st.text_input("API base", st.session_state.api_base)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown('<div class="small" style="color:var(--muted); font-weight:750;">Your Chat</div>', unsafe_allow_html=True)

    chat_rows = [
        row
        for row in list_sessions(st.session_state.visitor_id, limit=30)
        if str(row[0]).startswith("chat-")
    ]
    if chat_rows:
        html = []
        for sid, title, created_at, updated_at in chat_rows:
            label = truncate_session_text((title or "New Chat Session").strip(), max_chars=28)
            mmdd = _format_short_mmdd(created_at or "")
            display = f"{label} {mmdd}".strip()

            html.append(f"""
            <div class="ini_session_row">
              <a class="ini_sidebar_link" href="{_chat_popup_href(sid)}" target="_self">{display}</a>
              <div class="ini_session_menu">
                <details>
                  <summary>⋯</summary>
                  <div class="ini_session_dropdown">
                    <a href="{_chat_rename_href(sid)}" target="_self">Rename</a>
                    <a href="{_chat_delete_href(sid)}" target="_self">Delete</a>
                  </div>
                </details>
              </div>
            </div>
            """)

        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.markdown('<div class="small" style="color:var(--muted);">No chat sessions yet.</div>', unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown('<div class="small" style="color:var(--muted); font-weight:750;">Your Learning</div>', unsafe_allow_html=True)


    rows = [
        row
        for row in list_sessions(st.session_state.visitor_id, limit=30)
        if str(row[0]).startswith("learn-")
    ]
    if rows:
        html = []
        for sid, title, created_at, updated_at in rows:
            label = truncate_session_text((title or "Learning Session").strip(), max_chars=28)
            mmdd = _format_short_mmdd(created_at or "")
            display = f"{label} {mmdd}".strip()

            html.append(f"""
            <div class="ini_session_row">
            <a class="ini_sidebar_link" href="{_learn_session_href(sid)}" target="_self">{display}</a>
            <div class="ini_session_menu">
                <details>
                <summary>⋯</summary>
                <div class="ini_session_dropdown">
                    <a href="{_learn_rename_href(sid)}" target="_self">Rename</a>
                    <a href="{_learn_delete_href(sid)}" target="_self">Delete</a>
                </div>
                </details>
            </div>
            </div>
            """)

        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.markdown('<div class="small" style="color:var(--muted);">No learning sessions yet.</div>', unsafe_allow_html=True)
@st.dialog("Rename Session")
def _render_rename_session_dialog() -> None:
    sid = st.session_state.rename_session_sid
    if not sid:
        return

    loaded = load_session(st.session_state.visitor_id, sid)
    current_title = ""
    if loaded:
        current_title = (loaded.get("title") or "").strip()

    new_title = st.text_input("Session name", value=current_title, key="rename_session_input")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save", key="rename_session_save_btn"):
            rename_session(
                st.session_state.visitor_id,
                sid,
                new_title.strip(),
            )
            st.session_state.rename_session_sid = None
            st.session_state.rename_session_page = None
            st.rerun()
    with c2:
        if st.button("Cancel", key="rename_session_cancel_btn"):
            st.session_state.rename_session_sid = None
            st.session_state.rename_session_page = None
            st.rerun()

if st.session_state.chat_popup_sid:
    _render_chat_session_popup()

if st.session_state.rename_session_sid:
    _render_rename_session_dialog()







# =========================
# Pages
# =========================

def page_home():
    st.markdown(
        """
# Welcome to InI.ai

### Interrogate n Illustrate

InI.ai is a Question Engine designed to help users learn through structured exploration rather than isolated answers.

The platform is actively being improved and updated on a regular basis.

---

## Currently Available

### New Chat

The primary learning experience.

**Interrogate**

- Generates an Introduction.
- Creates a structured Question Map.
- Organizes learning from Foundations to Advanced topics.
- Supported technical domains use LLM-generated Question Maps.
- Topics outside current LLM coverage use structured template-based Question Maps.

**Illustrate**

- Provides examples and applications for a topic.
- Helps understand where a concept is used in the real world.

**Recommended Topics**

- Artificial Intelligence
- Machine Learning
- Data Science
- Neural Networks
- Transformers
- Reinforcement Learning

---

## What's New in v0.1.2

InI now provides expanded Question Map coverage across:

- **Computer Science:** Algorithms, Operating Systems and Computer Architecture
- **Computer Hardware:** CPUs, GPUs, processors, AMD, Ryzen and multi-core architectures
- **Software and Cloud:** Docker and Kubernetes
- **Machine Learning and Statistics:** XGBoost, PCA, Bayesian Statistics, Time Series Forecasting and Gradient Descent

This release also improves recognition of short technical topics and preserves specific subjects such as Spatial AI and Constitutional AI throughout the learning experience.

---

### My New Learning

**Status: In active development**

This learning workspace is currently being refined. Its research modes, session continuity and overall learning experience will continue to improve in upcoming releases.

Current modes:

- Deep
- Overview
- Quiz

---

### Current Version

Version: v0.1.2

The platform is under active development and new features are being added regularly.

---

Enter a topic to begin your learning journey.
"""
    )

def page_new_chat() -> None:
    st.markdown('<div class="bigtitle">New Chat</div>', unsafe_allow_html=True)
    st.caption(
        "InI Question Engine (v0): Interrogate generates a progressive question ladder. "
        "Click a question to open or hide its answer."
    )

    if "chat_answers" not in st.session_state:
        st.session_state.chat_answers = {}
    if "chat_open_questions" not in st.session_state:
        st.session_state.chat_open_questions = set()
    if "chat_visited_questions" not in st.session_state:
        st.session_state.chat_visited_questions = set()
    if "chat_intro" not in st.session_state:
        st.session_state.chat_intro = ""
    if "chat_followups" not in st.session_state:
        st.session_state.chat_followups = {}
    if "chat_seed_done" not in st.session_state:
        st.session_state.chat_seed_done = ""

    if "chat_branch_answers" not in st.session_state:
        st.session_state.chat_branch_answers = []

    def _session_has_existing_root() -> bool:
        return any([
            st.session_state.chat_root_interrogate,
            st.session_state.chat_root_illustrate,
            st.session_state.chat_root_intro,
            st.session_state.chat_root_answers,
        ])

    def _append_interrogate_branch(topic_text: str, data: Dict[str, Any], intro: str) -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": "interrogate",
                "topic": topic_text,
                "interrogate": data,
                "intro": intro,
                "answers": {},
                "followups": {},
                "open_questions": [],
                "visited_questions": [],
                "ts": now_label(),
            }
        )
        # typed ordinary follow-up topic: keep in chat timeline only, not popup FUQ list
        pass

    def _append_illustrate_branch(topic_text: str, data: Dict[str, Any]) -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": "illustrate",
                "topic": topic_text,
                "illustrate": data,
                "ts": now_label(),
            }
        )
        # typed ordinary follow-up topic: keep in chat timeline only, not popup FUQ list
        pass
    
    def _append_direct_branch(topic_text: str, answer_payload: Dict[str, Any], kind: str = "fuq") -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": "direct",
                "topic": topic_text,
                "direct_answer": answer_payload,
                "ts": now_label(),
            }
        )
        # typed ordinary follow-up topic: keep in chat timeline only, not popup CTA/FUQ list
        pass


    def _append_nc_message(topic_text: str, answer_payload: Dict[str, Any], kind: str = "direct") -> None:
        st.session_state.chat_branch_answers.append(
            {
                "kind": kind,
                "topic": (topic_text or "").strip(),
                "direct_answer": answer_payload,
                "ts": now_label(),
            }
        )

    




    def _run_new_chat_direct_followup(topic_text: str) -> None:
        if not topic_text.strip():
            return
        try:
            current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid
            with st.spinner("Generating details... please wait."):
                resp = fetch_study(topic_text.strip(), mode="focused")
                answer = normalize_whitespace_for_readability(
                    normalize_mojibake(resp.get("answer", "") or "")
                ).strip() or "No answer generated."
                followups = resp.get("followups") or []

                st.session_state.chat_direct_answer = {
                    "prompt": topic_text.strip(),
                    "text": answer,
                    "incomplete": bool(resp.get("incomplete")),
                    "stop_reason": resp.get("stop_reason") or None,
                    "mode": "focused",
                    "followups": followups,
                    "ts": now_label()
                }
                _append_chat_branch(topic_text.strip(), "cta")
                _persist_new_chat_session(current_sid)
            st.rerun()
        except Exception as e:
            st.error(f"Error calling /study/ai: {e}")

    def _run_new_chat_branch_interrogate(topic_text: str) -> None:
        if not topic_text.strip():
            return

        current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

        with st.spinner("Generating question map... may take some time."):
            data = fetch_interrogate(topic_text.strip())
            intro_resp = fetch_study_full(topic_text.strip(), mode="high")
            intro = intro_resp.get("answer", "").strip()
            _append_interrogate_branch(topic_text.strip(), data, intro)
            _persist_new_chat_session(current_sid)

    def _run_new_chat_branch_illustrate(topic_text: str) -> None:
        if not topic_text.strip():
            return

        current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

        with st.spinner("Generating illustrations... please wait."):
            data = fetch_illustrate(topic_text.strip())
            _append_illustrate_branch(topic_text.strip(), data)
            _persist_new_chat_session(current_sid)

    def _render_branch_question_map(branch_idx: int, branch: Dict[str, Any]) -> None:

        
        data = branch.get("interrogate") or {}
        if not isinstance(data, dict) or not data.get("categories"):
            return

        with st.container():
            branch_ts = branch.get("ts") or now_label()

            intro = (branch.get("intro") or "").strip()
            if intro:
                clean_intro, intro_followups = split_answer_and_embedded_followups(intro)

                st.markdown("##### Introduction")
                st.markdown(clean_intro or intro)

                if intro_followups:
                    st.markdown("##### Suggested follow-ups")
                    render_followup_links("chat", intro_followups, st.session_state.chat_active_id)

            st.markdown("##### Question Map")

            branch_answers = branch.setdefault("answers", {})
            branch_followups = branch.setdefault("followups", {})
            branch_open_questions = set(branch.get("open_questions") or [])
            branch_visited_questions = set(branch.get("visited_questions") or [])

            hide_all = st.button(
                "Hide All Answers",
                key=f"branch_hide_all_answers_{branch_idx}"
            )
            if hide_all:
                branch_open_questions = set()
                

                branch["open_questions"] = []
                branch["visited_questions"] = sorted(list(branch_visited_questions))
                st.session_state.chat_branch_answers[branch_idx] = branch
                _persist_new_chat_session()
                st.rerun()

            cats = data.get("categories") or {}

            ladder = [
                ("Orientation", ["Orientation"]),
                ("Foundations", ["Foundations"]),
                ("Mechanisms", ["Mechanisms"]),
                ("Methods & Tools", ["Methods & Tools"]),
                ("Applications", ["Applications"]),
                ("Pitfalls", ["Pitfalls"]),
                ("Advanced / Future", ["Advanced / Future"]),
            ]

            for section, cat_keys in ladder:
                qs = []
                for ck in cat_keys:
                    items = cats.get(ck) or []
                    for it in items:
                        q = (it.get("question") or "").strip()
                        if q and q not in qs:
                            qs.append(q)

                if not qs:
                    continue

                open_section = st.toggle(
                    section,
                    value=(section == "Orientation"),
                    key=f"branch_{branch_idx}_sec_{section}",
                )

                if open_section:
                    for q in qs:
                        visited = q in branch_visited_questions
                        is_open = q in branch_open_questions
                        button_label = f"✓ {q}" if visited else q

                        if st.button(button_label, key=f"branch_{branch_idx}_q_{section}_{q}", type="secondary"):
                            branch_visited_questions.add(q)

                            if is_open:
                                branch_open_questions.discard(q)
                                branch["open_questions"] = sorted(list(branch_open_questions))
                                branch["visited_questions"] = sorted(list(branch_visited_questions))
                                st.session_state.chat_branch_answers[branch_idx] = branch
                                _persist_new_chat_session()
                                st.rerun()

                            if q in branch_answers:
                                branch_open_questions.add(q)
                                branch["open_questions"] = sorted(list(branch_open_questions))
                                branch["visited_questions"] = sorted(list(branch_visited_questions))
                                st.session_state.chat_branch_answers[branch_idx] = branch
                                _persist_new_chat_session()
                                st.rerun()

                            try:
                                with st.spinner("Generating details... please wait."):
                                    resp = fetch_study(q, mode="focused")
                                    answer = normalize_whitespace_for_readability(
                                        normalize_mojibake(resp.get("answer", "") or "")
                                    ).strip() or "No answer generated."

                                    branch_answers[q] = {
                                        "text": answer,
                                        "incomplete": bool(resp.get("incomplete")),
                                        "stop_reason": resp.get("stop_reason") or None,
                                        "prompt": q,
                                        "mode": "deep",
                                    }
                                    branch_followups[q] = resp.get("followups") or []
                                    branch_open_questions.add(q)
                                    branch["answers"] = branch_answers
                                    branch["followups"] = branch_followups
                                    branch["open_questions"] = sorted(list(branch_open_questions))
                                    branch["visited_questions"] = sorted(list(branch_visited_questions))
                                    st.session_state.chat_branch_answers[branch_idx] = branch
                                    _persist_new_chat_session()

                                st.rerun()

                            except Exception as e:
                                st.error(f"Error calling /study/ai: {e}")

                        if q in branch_open_questions:
                            answer_obj = branch_answers.get(q, {})
                            raw_answer = (
                                (answer_obj.get("text") or "").strip()
                                if isinstance(answer_obj, dict)
                                else str(answer_obj or "").strip()
                            )

                            if raw_answer:
                                clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

                                _render_nc_ai_bubble(
                                    "##### Answer\n\n" + (clean_answer or raw_answer),
                                    "",
                                )

                                followups = embedded_followups or branch_followups.get(q, [])
                                if followups:
                                    st.markdown("##### Suggested follow-ups")
                                    render_followup_links(
                                        "chat",
                                        followups,
                                        st.session_state.chat_active_id,
                                        target="_blank",
                                    )

                                is_incomplete = False
                                if isinstance(answer_obj, dict):
                                    is_incomplete = bool(answer_obj.get("incomplete"))

                                if is_incomplete:
                                    branch_continue_key = f"branch::{branch_idx}::{q}"

                                    if st.button("Continue", key=f"branch_{branch_idx}_cont_{section}_{q}"):
                                        st.session_state._nc_continue_loading_q = branch_continue_key
                                        st.rerun()

                                    if st.session_state._nc_continue_loading_q == branch_continue_key:
                                        st.markdown("⏳ **Continuing...**")

                                        previous_text = (answer_obj.get("text") or "").strip()
                                        mode = (answer_obj.get("mode") or "deep").strip()

                                        if previous_text:
                                            try:
                                                resp = fetch_study(
                                                    topic=q,
                                                    mode=mode,
                                                    continue_mode=True,
                                                    previous_answer=previous_text,
                                                )

                                                chunk = normalize_whitespace_for_readability(
                                                    normalize_mojibake(resp.get("answer", "") or "")
                                                ).strip()

                                                combined = (
                                                    previous_text.rstrip() + "\n\n" + chunk
                                                ).strip() if chunk else previous_text

                                                branch_answers[q] = {
                                                    "text": combined,
                                                    "incomplete": bool(resp.get("incomplete")),
                                                    "stop_reason": resp.get("stop_reason") or None,
                                                    "prompt": q,
                                                    "mode": mode,
                                                }

                                                if resp.get("followups"):
                                                    branch_followups[q] = resp.get("followups") or []

                                                branch["answers"] = branch_answers
                                                branch["followups"] = branch_followups
                                                st.session_state.chat_branch_answers[branch_idx] = branch
                                                _persist_new_chat_session()

                                            except Exception as e:
                                                st.error(f"Error continuing answer: {e}")

                                            finally:
                                                st.session_state._nc_continue_loading_q = None

                                            st.rerun()

                                st.markdown("---")

            st.markdown(
                f"<div style='margin-top:14px; text-align:right; color:#64748b; font-size:11px;'>{branch_ts}</div>",
                unsafe_allow_html=True,
            )

    def _render_nc_user_bubble(text: str, ts: str = "") -> None:
        prompt = (text or "").strip()
        if not prompt:
            return

        ts_html = ""
        if ts:
            ts_html = f"<div style='margin-top:6px; text-align:right; color:#64748b; font-size:11px;'>{ts}</div>"

        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-end; margin: 10px 0 14px 0;">
            <div style="
                max-width: 68%;
                background: #f3f4f6;
                color: #111827;
                border: 1px solid #e5e7eb;
                border-radius: 18px;
                padding: 10px 14px;
                line-height: 1.45;
                font-size: 14px;
                box-shadow: 0 1px 2px rgba(15,23,42,0.04);
            ">
                {prompt}
                {ts_html}
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )





    def _render_nc_ai_bubble(text: str, ts: str = "") -> None:
        body = (text or "").strip()
        if not body:
            return

        body = re.sub(r"<[^>]+>", "", body)

        # =========================
        # Highlight Engine
        # =========================

        def apply_highlights(s: str) -> str:

            # == highlighted text ==
            s = re.sub(
                r"==(.+?)==",
                r'<span style="background:#fef08a; padding:2px 5px; border-radius:6px; font-weight:600;">\1</span>',
                s,
                flags=re.DOTALL
            )

            # **important**
            s = re.sub(
                r"\*\*(.+?)\*\*",
                r'<span style="color:#111827; font-weight:800;">\1</span>',
                s,
                flags=re.DOTALL
            )

            # `inline code`
            s = re.sub(
                r"`(.+?)`",
                r'<span style="background:#f3f4f6; padding:2px 6px; border-radius:6px; font-family:monospace;">\1</span>',
                s,
                flags=re.DOTALL
            )

            return s

        body = apply_highlights(body)

        with st.container(border=True):
            
            st.markdown(
                """
                <style>
                .ini_ai_inner{
                    background:#ffffff;
                    border-radius:18px;
                    padding:14px 16px 10px 16px;
                    animation: fadeIn 0.18s ease;
                    line-height:1.65;
                }

                .ini_ai_inner ul,
                .ini_ai_inner ol{
                    padding-left:22px;
                }

                .ini_ai_inner li{
                    margin-bottom:6px;
                }

                @keyframes fadeIn{
                    from{
                        opacity:0;
                        transform:translateY(4px);
                    }
                    to{
                        opacity:1;
                        transform:translateY(0px);
                    }
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            st.markdown('<div class="ini_ai_inner">', unsafe_allow_html=True)

            st.markdown(body, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            if ts:
                st.markdown(
                    f"""
                    <div style="
                        margin-top:10px;
                        text-align:right;
                        color:#64748b;
                        font-size:11px;
                    ">
                        {ts}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )






    


    




    def _looks_like_live_local_query(text: str) -> bool:
        s = (text or "").strip().lower()
        markers = {
            "today", "current", "latest", "now",
            "gas", "petrol", "diesel", "water rate", "electricity rate",
            "price", "rate", "cost", "weather", "temperature",
            "maryland", "dc", "usa", "us", "near me", "local",
        }
        return any(m in s for m in markers)

    def _dedupe_followups(items: list[str]) -> list[str]:
        out: list[str] = []
        seen = set()
        for x in items or []:
            item = (x or "").strip()
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def _collect_active_nc_followups() -> list[str]:
        candidates: list[str] = []

        direct_payload = st.session_state.chat_direct_answer
        if isinstance(direct_payload, dict):
            candidates.extend(direct_payload.get("followups") or [])

        intro_text = (st.session_state.chat_intro or "").strip()
        if intro_text:
            _, intro_followups = split_answer_and_embedded_followups(intro_text)
            candidates.extend(intro_followups)

        for vals in (st.session_state.chat_followups or {}).values():
            if isinstance(vals, list):
                candidates.extend(vals)

        for item in st.session_state.chat_branch_answers or []:
            if not isinstance(item, dict):
                continue

            kind = (item.get("kind") or "").strip().lower()

            if kind == "direct":
                direct_payload = item.get("direct_answer") or {}
                if isinstance(direct_payload, dict):
                    candidates.extend(direct_payload.get("followups") or [])

            elif kind == "interrogate":
                intro = (item.get("intro") or "").strip()
                if intro:
                    _, intro_followups = split_answer_and_embedded_followups(intro)
                    candidates.extend(intro_followups)

                for vals in (item.get("followups") or {}).values():
                    if isinstance(vals, list):
                        candidates.extend(vals)

        return _dedupe_followups(candidates)

    def _resolve_typed_followup(prompt_text: str) -> str:
        raw = (prompt_text or "").strip()
        if not raw:
            return raw

        candidates = _collect_active_nc_followups()
        if not candidates:
            return raw

        # Numeric selection: "2" or "2."
        m = re.match(r"^\s*(\d+)\.?\s*$", raw)
        if m:
            idx = int(m.group(1))
            if 1 <= idx <= len(candidates):
                return candidates[idx - 1]

        raw_norm = re.sub(r"\s+", " ", raw.lower()).strip()

        # Partial/full text match
        if len(raw_norm) >= 4:
            for cand in candidates:
                cand_norm = re.sub(r"\s+", " ", cand.lower()).strip()
                if raw_norm == cand_norm or raw_norm in cand_norm or cand_norm in raw_norm:
                    return cand

        return raw

    def _run_new_chat_interrogate(topic_text: str) -> None:
        topic_text = _resolve_typed_followup(topic_text)

        if not topic_text.strip():
            return
        try:
            current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

            st.session_state.chat_popup_sid = None
            _reset_query_to_page("chat")

            with st.spinner("Generating question map... may take some time."):
                data = fetch_interrogate(topic_text.strip())
                st.session_state.chat["topic"] = topic_text.strip()

                if "chat_bottom_topic_input" in st.session_state:
                    del st.session_state["chat_bottom_topic_input"]

                has_existing_root = bool(
                    current_sid
                    and st.session_state.chat_loaded_sid == current_sid
                    and _session_has_existing_root()
                )

                # -------------------------------------------------
                # Intent-layer / direct-answer / conversational path
                # -------------------------------------------------
                if not (data.get("categories") or {}):
                    followups = data.get("followups") or []
                    intent_name = (data.get("intent") or "").strip().lower()
                    should_answer_direct = bool(data.get("should_answer_direct", False))

                    if should_answer_direct:
                        if _looks_like_live_local_query(topic_text):
                            reply = (
                                "I can recognize this as a direct factual query, but live or location-specific "
                                "rates need a current data source. In v0, ask me to explain the topic, or use a "
                                "fully sourced query once live data is connected."
                            )
                            followups = []
                            answer_incomplete = False
                            answer_stop_reason = None
                            mode_name = "focused"
                        else:
                            direct_resp = fetch_study_full(topic_text.strip(), mode="high")
                            reply = (direct_resp.get("answer") or "").strip() or "No answer generated."
                            followups = direct_resp.get("followups") or followups
                            answer_incomplete = bool(direct_resp.get("incomplete"))
                            answer_stop_reason = direct_resp.get("stop_reason") or None
                            mode_name = "high"
                    else:
                        reply = (data.get("reply") or "").strip() or "Send a topic to explore."
                        answer_incomplete = False
                        answer_stop_reason = None
                        mode_name = "focused"

                    show_followups = should_answer_direct and not _looks_like_live_local_query(topic_text)

                    direct_payload = {
                        "prompt": topic_text.strip(),
                        "text": reply,
                        "incomplete": answer_incomplete,
                        "stop_reason": answer_stop_reason,
                        "mode": mode_name,
                        "followups": followups,
                        "intent": intent_name,
                        "should_answer_direct": should_answer_direct,
                        "show_followups": show_followups,
                        "ts": now_label(),
                    }

                    if has_existing_root:
                        _append_nc_message(
                            topic_text.strip(),
                            direct_payload,
                            "direct",
                        )
                        _persist_new_chat_session(current_sid)
                        st.rerun()
                        return
                    


                    st.session_state.chat["topic"] = topic_text.strip()
                    st.session_state.chat_root_topic = topic_text.strip()
                    st.session_state.chat["interrogate"] = None
                    st.session_state.chat["illustrate"] = None
                    st.session_state.chat_intro = ""
                    st.session_state.chat_direct_answer = direct_payload

                    st.session_state.chat_answers = {}
                    st.session_state.chat_followups = {}
                    st.session_state.chat_open_questions = set()
                    st.session_state.chat_visited_questions = set()

                    st.session_state.chat_root_interrogate = None
                    st.session_state.chat_root_illustrate = None
                    st.session_state.chat_root_intro = ""
                    st.session_state.chat_root_direct_answer = direct_payload
                    st.session_state.chat_root_answers = {}
                    st.session_state.chat_root_followups = {}
                    st.session_state.chat_root_open_questions = set()
                    st.session_state.chat_root_visited_questions = set()

                    _persist_new_chat_session(current_sid)
                    st.rerun()
                    return

                # -------------------------------------------------
                # Real topic -> question-map path
                # -------------------------------------------------
                if has_existing_root:
                    intro_resp = fetch_study_full(topic_text.strip(), mode="high")
                    intro = intro_resp.get("answer", "").strip()
                    _append_interrogate_branch(topic_text.strip(), data, intro)
                    _persist_new_chat_session(current_sid)
                    st.rerun()
                    return

                st.session_state.chat["topic"] = topic_text.strip()
                st.session_state.chat_root_topic = topic_text.strip()
                st.session_state.chat["interrogate"] = data

                intro_resp = fetch_study_full(topic_text.strip(), mode="high")
                intro = intro_resp.get("answer", "").strip()

                st.session_state.chat_intro = intro
                st.session_state.chat["illustrate"] = None
                st.session_state.chat_direct_answer = None
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()

                st.session_state.chat_root_interrogate = {
                **data,
                "ts": now_label(),
                }
                st.session_state.chat_root_illustrate = None
                st.session_state.chat_root_intro = intro
                st.session_state.chat_root_answers = {}
                st.session_state.chat_root_followups = {}
                st.session_state.chat_root_open_questions = set()
                st.session_state.chat_root_visited_questions = set()

                _sync_chat_root_snapshot()
                _persist_new_chat_session(current_sid)

            st.rerun()
        except Exception as e:
            st.error(f"Error calling /interrogate: {e}")

    def _run_new_chat_illustrate(topic_text: str) -> None:
        if not topic_text.strip():
            return
        try:
            current_sid = st.session_state.chat_active_id or st.session_state.chat_loaded_sid

            if current_sid and st.session_state.chat_loaded_sid == current_sid and _session_has_existing_root():
                _run_new_chat_branch_illustrate(topic_text.strip())
                st.rerun()
                return

            st.session_state.chat_popup_sid = None
            _reset_query_to_page("chat")

            with st.spinner("Generating illustrations... please wait."):
                data = fetch_illustrate(topic_text.strip())
                st.session_state.chat["topic"] = topic_text.strip()
                st.session_state.chat_root_topic = topic_text.strip()
                if "chat_bottom_topic_input" in st.session_state:
                    del st.session_state["chat_bottom_topic_input"]
                st.session_state.chat["illustrate"] = {
                    **data,
                    "ts": now_label(),
                }
                st.session_state.chat["interrogate"] = None
                st.session_state.chat_intro = ""
                st.session_state.chat_direct_answer = None
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()

                st.session_state.chat_root_interrogate = None
                st.session_state.chat_root_illustrate = {
                    **data,
                    "ts": now_label(),
                }
                st.session_state.chat_root_intro = ""
                st.session_state.chat_root_answers = {}
                st.session_state.chat_root_followups = {}
                st.session_state.chat_root_open_questions = set()
                st.session_state.chat_root_visited_questions = set()

                _persist_new_chat_session(current_sid)
            st.rerun()
        except Exception as e:
            st.error(f"Error calling /illustrate: {e}")

    

    def _render_new_chat_top_uib() -> None:
        if st.session_state.chat_top_topic_input == "" and st.session_state.chat.get("topic"):
            st.session_state.chat_top_topic_input = st.session_state.chat.get("topic", "")

        st.markdown(
            """
            <style>
            div[data-testid="stTextArea"][aria-label="NC_TOP_TOPIC"]{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextArea"][aria-label="NC_TOP_TOPIC"] > div{
                background: #ffffff !important;
                border: none !important;
                border-radius: 24px !important;
                box-shadow: 0 8px 22px rgba(15,23,42,0.08) !important;
                padding: 0 !important;
                overflow: hidden !important;
            }

            div[data-testid="stTextArea"][aria-label="NC_TOP_TOPIC"] textarea{
                min-height: 118px !important;
                height: 118px !important;
                border: none !important;
                outline: none !important;
                border-radius: 24px !important;
                background: transparent !important;
                box-shadow: none !important;
                font-size: 16px !important;
                line-height: 1.35 !important;
                padding: 34px 24px !important;
                box-sizing: border-box !important;
                resize: none !important;
                overflow: hidden !important;
            }

            div[data-testid="stTextArea"][aria-label="NC_TOP_TOPIC"] textarea::placeholder{
                color: #94a3b8 !important;
            }

            div[data-testid="stTextArea"][aria-label="NC_TOP_TOPIC"] textarea:focus{
                border: none !important;
                outline: none !important;
                box-shadow: none !important;
            }

            div.stButton > button[kind="secondary"]{
                background: #000000 !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                border: 1px solid #000000 !important;
                border-radius: 14px !important;
                width: 100% !important;
                min-width: 0 !important;
                max-width: 128px !important;
                height: 42px !important;
                min-height: 42px !important;
                white-space: nowrap !important;
                text-align: center !important;
                padding: 0 !important;
                box-shadow: none !important;
                margin: 0 !important;
            }

            div.stButton > button[kind="secondary"] p,
            div.stButton > button[kind="secondary"] span,
            div.stButton > button[kind="secondary"] div{
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                font-size: 14px !important;
                font-weight: 900 !important;
                letter-spacing: 0.2px !important;
                opacity: 1 !important;
                margin: 0 !important;
                white-space: nowrap !important;
            }

            button[data-testid="baseButton-secondary"]:hover{
                background: #111111 !important;
                border-color: #111111 !important;
            }

            /* responsive shrink for sidebar mode */

            @media (max-width:1100px){
                button[data-testid="baseButton-secondary"]{
                    max-width:112px !important;
                    height:40px !important;
                }

                div.stButton > button[kind="secondary"] p{
                    font-size:12px !important;
                }
            }

            @media (max-width:900px){
                button[data-testid="baseButton-secondary"]{
                    max-width:96px !important;
                    height:38px !important;
                }

                div.stButton > button[kind="secondary"] p{
                    font-size:11px !important;
                }
            }

            </style>
            """,
            unsafe_allow_html=True,
        )

        import os
        from PIL import Image

        logo_path = os.path.join(os.path.dirname(__file__), "ini_logo.png")
        logo = Image.open(logo_path)

        col_l, col_c, col_r = st.columns([3.7,2,2.5])
        with col_c:
            st.image(logo, width=120)

        left, center, right = st.columns([2.6, 4.8, 2.6])

        run = False
        illustrate_run = False

        with center:

            # --- UIB capsule start ---
            

            st.text_area(
                "NC_TOP_TOPIC",
                placeholder="Ask InI anything to begin...",
                key="chat_top_topic_input",
                label_visibility="collapsed",
                height=118,
            )

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            btn_outer_l, btn_outer_r = st.columns([1,1], gap="small")

            with btn_outer_l:

                btn_pad_l, btn_slot_l = st.columns([1.45,1.0], gap="small")

                with btn_slot_l:
                    run = st.button(
                        "Interrogate",
                        key="nc_top_interrogate",
                        type="secondary",
                        use_container_width=True,
                    )

            with btn_outer_r:

                btn_slot_r, btn_pad_r = st.columns([0.89,1.45], gap="small")

                with btn_slot_r:
                    illustrate_run = st.button(
                        "Illustrate",
                        key="nc_top_illustrate",
                        type="secondary",
                        use_container_width=True,
                    )

            # --- UIB capsule end ---
            

        if run:
            st.session_state.nc_started = True
            _run_new_chat_interrogate(st.session_state.chat_top_topic_input)

        if illustrate_run:
            st.session_state.nc_started = True
            _run_new_chat_illustrate(st.session_state.chat_top_topic_input)


    
        
    
    def _render_new_chat_bottom_uib() -> None:
        st.markdown(
            """
            <style>

            div[data-testid="stTextInput"]:has(input[aria-label="NC_BOTTOM_TOPIC"]){
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextInput"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) > div{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextInput"] input[aria-label="NC_BOTTOM_TOPIC"]{
                height: 46px !important;
                border-radius: 14px !important;
                font-size: 15px !important;
                border: none !important;
                background: transparent !important;
                box-shadow: none !important;
                padding: 10px 14px !important;
            }




            
            div[data-testid="stTextInput"] input[aria-label="NC_BOTTOM_TOPIC"]:focus{
                border: 1px solid #d1d5db !important;
                box-shadow: 0 2px 8px rgba(15,23,42,0.04) !important;
            }

            .nc-bottom-btn-row div.stButton > button{
                background: #000000 !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                border: 1px solid #000000 !important;
                border-radius: 14px !important;
                height: 42px !important;
                min-height: 42px !important;
                max-height: 42px !important;
                white-space: nowrap !important;
                font-size: 12px !important;
                font-weight: 900 !important;
                box-shadow: none !important;
                text-align: center !important;
                justify-content: center !important;
            }

            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) button p,
            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) button span,
            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) button div{
                font-weight: 900 !important;
            }

            .nc-bottom-btn-row div.stButton > button:hover{
                background: #111111 !important;
                border-color: #111111 !important;
            }

            .ini-chatbar-shell{
                border: none !important;
                border-radius: 0 !important;
                background: transparent !important;
                padding: 0 !important;
            }

            .ini-chatbar-shell [data-testid="stHorizontalBlock"]{
                align-items: center !important;
            }


            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]){
                border: 1px solid #e5e7eb !important;
                border-radius: 16px !important;
                background: #ffffff !important;
                padding: 8px !important;
                align-items: center !important;
                gap: 6px !important;
            }

            

            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) input{
                border: none !important;
                box-shadow: none !important;
            }

            div[data-testid="stHorizontalBlock"]:has(input[aria-label="NC_BOTTOM_TOPIC"]) button{
                background: #000000 !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                border-radius: 12px !important;
                font-weight: 900 !important;
            }



            </style>
            """,
            unsafe_allow_html=True,
        )

        # st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        run = False
        illustrate_run = False

        st.markdown('<div class="ini-chatbar-shell">', unsafe_allow_html=True)

        input_col, int_col, ill_col = st.columns(
            [8.5, 1.4, 1.4],
            gap="small"
        )

        with input_col:
            st.text_input(
                "NC_BOTTOM_TOPIC",
                key="chat_bottom_topic_input",
                label_visibility="collapsed",
                placeholder="Ask InI anything to continue...",
                on_change=_request_chat_bottom_enter_submit,
            )

        with int_col:
            run = st.button(
                "Interrogate",
                key="nc_bottom_interrogate",
                use_container_width=True,
            )

        with ill_col:
            illustrate_run = st.button(
                "Illustrate",
                key="nc_bottom_illustrate",
                use_container_width=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)

            

        if st.session_state.chat_bottom_enter_submit:
            st.session_state.chat_bottom_enter_submit = False
            st.session_state.nc_started = True
            _run_new_chat_interrogate(st.session_state.chat_bottom_topic_input)

        if run:
            st.session_state.nc_started = True
            _run_new_chat_interrogate(st.session_state.chat_bottom_topic_input)

        if illustrate_run:
            st.session_state.nc_started = True
            _run_new_chat_illustrate(st.session_state.chat_bottom_topic_input)

    # Auto-run FUQ opened in a new tab for New Chat
    if chat_q and st.session_state.chat_seed_done != chat_q:
        try:
            if chat_sid:
                _load_new_chat_session(chat_sid)

            with st.spinner("Generating details... please wait."):
                resp = fetch_study(chat_q, mode="focused")
                answer = normalize_whitespace_for_readability(
                    normalize_mojibake(resp.get("answer", "") or "")
                ).strip() or "No answer generated."

                followups = resp.get("followups") or []
                _append_chat_branch(chat_q, "fuq")

                st.session_state.chat_direct_answer = {
                    "prompt": chat_q,
                    "text": answer,
                    "incomplete": bool(resp.get("incomplete")),
                    "stop_reason": resp.get("stop_reason") or None,
                    "mode": "focused",
                    "followups": followups,
                    "ts": now_label()
                }

                st.session_state.chat["interrogate"] = None
                st.session_state.chat_intro = ""
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()
                st.session_state.chat_seed_done = chat_q
                _persist_new_chat_session(st.session_state.chat_active_id or st.session_state.chat_loaded_sid)
            st.rerun()
        except Exception as e:
            st.error(f"Error auto-running chat FUQ: {e}")

    has_new_chat_content = any([
        st.session_state.chat.get("interrogate"),
        st.session_state.chat.get("illustrate"),
        st.session_state.chat_direct_answer,
        bool(st.session_state.chat_answers),
    ])

    if not st.session_state.nc_started and not has_new_chat_content:
        _render_new_chat_top_uib()

    illustrate_data = st.session_state.chat.get("illustrate")
    if isinstance(illustrate_data, dict) and (illustrate_data.get("illustration_text") or "").strip():
        _render_nc_user_bubble(
            st.session_state.chat_root_topic or st.session_state.chat.get("topic") or "",
            st.session_state.chat_root_illustrate.get("ts", "") if isinstance(st.session_state.chat_root_illustrate, dict) else "",
)

        _render_nc_ai_bubble(
    "### Illustrations\n\n" + (illustrate_data.get("illustration_text") or ""),
    illustrate_data.get("ts") or "",
)

        if st.session_state.chat_branch_answers:
            st.markdown("---")
            for idx, item in enumerate(st.session_state.chat_branch_answers, start=1):
                kind = (item.get("kind") or "interrogate").strip().lower()
                topic = (item.get("topic") or item.get("prompt") or f"Continued topic {idx}").strip()
                ts = (item.get("ts") or "").strip()

                _render_nc_user_bubble(topic, ts)

                if kind == "illustrate":
                    illustrate_payload = item.get("illustrate") or {}
                    illustration_text = ""
                    if isinstance(illustrate_payload, dict):
                        illustration_text = (illustrate_payload.get("illustration_text") or "").strip()

                    if illustration_text:
                        _render_nc_ai_bubble(
                            illustration_text,
                            illustrate_payload.get("ts", "")
                        )
                    else:
                        st.caption("No illustration generated.")

                elif kind == "direct":
                    direct_payload = item.get("direct_answer") or {}
                    raw_answer = (direct_payload.get("text") or "").strip() if isinstance(direct_payload, dict) else ""

                    if raw_answer:

                        clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

                        _render_nc_ai_bubble(
                            clean_answer or raw_answer,
                            direct_payload.get("ts") or ""
                        )

                        show_followups = bool(direct_payload.get("show_followups", True))
                        followups = embedded_followups or (direct_payload.get("followups") or [])

                        if show_followups and followups:
                            st.markdown("#### Suggested follow-ups")
                            render_followup_links(
                                "chat",
                                followups,
                                st.session_state.chat_active_id
                            )

                    else:
                        st.caption("No direct answer generated.")

                else:
                    _render_branch_question_map(idx - 1, item)

                st.markdown("---")

        if not chat_q:
            _render_new_chat_bottom_uib()
        return

    direct_answer = st.session_state.chat_direct_answer
    if isinstance(direct_answer, dict) and (direct_answer.get("text") or "").strip():
        _render_nc_user_bubble(
            direct_answer.get("prompt") or st.session_state.chat.get("topic") or "",
            direct_answer.get("ts") or "",
        )

        raw_answer = (direct_answer.get("text") or "").strip()
        clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

        _render_nc_ai_bubble(clean_answer or raw_answer, direct_answer.get("ts") or now_label())

        show_followups = bool(direct_answer.get("show_followups", True))
        followups = embedded_followups or (direct_answer.get("followups") or [])

        if show_followups and followups:
            st.markdown("#### Suggested follow-ups")
            render_followup_links("chat", followups, st.session_state.chat_active_id)

        is_incomplete = bool(direct_answer.get("incomplete"))

        

        if is_incomplete:
                direct_key = "__chat_direct_answer__"

                if st.button("Continue", key="nc_cont_direct_answer"):
                    st.session_state._nc_continue_loading_q = direct_key
                    st.rerun()

                if st.session_state._nc_continue_loading_q == direct_key:
                    st.markdown("⏳ **Continuing...**")

                    previous_text = (direct_answer.get("text") or "").strip()
                    mode = (direct_answer.get("mode") or "focused").strip()
                    prompt = (direct_answer.get("prompt") or "").strip()

                    if previous_text and prompt:
                        try:
                            resp = fetch_study(
                                topic=prompt,
                                mode=mode,
                                continue_mode=True,
                                previous_answer=previous_text,
                            )

                            chunk = normalize_whitespace_for_readability(
                                normalize_mojibake(resp.get("answer", "") or "")
                            ).strip()

                            if chunk:
                                combined = (previous_text.rstrip() + "\n\n" + chunk).strip()
                            else:
                                combined = previous_text

                            st.session_state.chat_direct_answer = {
                                "prompt": prompt,
                                "text": combined,
                                "incomplete": bool(resp.get("incomplete")),
                                "stop_reason": resp.get("stop_reason") or None,
                                "mode": mode,
                                "followups": resp.get("followups") or direct_answer.get("followups") or [],
                                "intent": direct_answer.get("intent"),
                                "should_answer_direct": direct_answer.get("should_answer_direct", False),
                                "show_followups": direct_answer.get("show_followups", True),
                                "ts": now_label()
                            }
                            _persist_new_chat_session()

                        except Exception as e:
                            st.error(f"Error continuing answer: {e}")
                        finally:
                            st.session_state._nc_continue_loading_q = None

                        st.rerun()

        if not chat_q:
            _render_new_chat_bottom_uib()
        return

    data = st.session_state.chat.get("interrogate")
    if isinstance(data, dict) and data.get("categories"):
        _render_nc_user_bubble(
            st.session_state.chat_root_topic or st.session_state.chat.get("topic") or "",
            st.session_state.chat_root_interrogate.get("ts", "") if isinstance(st.session_state.chat_root_interrogate, dict) else "",
        )

        



        with st.container():
            root_ts = (
                st.session_state.chat_root_interrogate.get("ts", "")
                if isinstance(st.session_state.chat_root_interrogate, dict)
                else now_label()
            )

            intro = st.session_state.chat_intro
            if intro:
                clean_intro, intro_followups = split_answer_and_embedded_followups(intro)

                intro_text = "### Introduction\n\n" + (clean_intro or intro)
                st.markdown(intro_text)

                if intro_followups:
                    st.markdown("#### Suggested follow-ups")
                    render_followup_links("chat", intro_followups, st.session_state.chat_active_id)

            st.markdown("### Question Map")
            st.caption("Orientation → Foundations → Mechanisms → Methods & Tools → Applications → Pitfalls → Advanced / Future")

            hide_all = st.button("Hide All Answers", key="hide_all_answers_newchat")
            if hide_all:
                st.session_state.chat_open_questions = set()
                _sync_chat_root_snapshot()
                _persist_new_chat_session()
                st.rerun()

            cats = data.get("categories") or {}

            ladder = [
                ("Orientation", ["Orientation"]),
                ("Foundations", ["Foundations"]),
                ("Mechanisms", ["Mechanisms"]),
                ("Methods & Tools", ["Methods & Tools"]),
                ("Applications", ["Applications"]),
                ("Pitfalls", ["Pitfalls"]),
                ("Advanced / Future", ["Advanced / Future"]),
            ]

            for section, cat_keys in ladder:
                qs = []

                for ck in cat_keys:
                    items = cats.get(ck) or []
                    for it in items:
                        q = (it.get("question") or "").strip()
                        if q and q not in qs:
                            qs.append(q)

                if not qs:
                    continue

                open_section = st.toggle(
                    section,
                    value=(section == "Orientation"),
                    key=f"sec_{section}"
                )

                if open_section:
                    for q in qs:
                        visited = q in st.session_state.chat_visited_questions
                        is_open = q in st.session_state.chat_open_questions

                        button_label = f"✓ {q}" if visited else q

                        if st.button(button_label, key=f"q_{section}_{q}", type="secondary"):
                            st.session_state.chat_visited_questions.add(q)

                            if is_open:
                                st.session_state.chat_open_questions.discard(q)
                                _sync_chat_root_snapshot()
                                _persist_new_chat_session()
                                st.rerun()

                            if q in st.session_state.chat_answers:
                                st.session_state.chat_open_questions.add(q)
                                _sync_chat_root_snapshot()
                                _persist_new_chat_session()
                                st.rerun()

                            try:
                                with st.spinner("Generating details... please wait."):
                                    resp = fetch_study(q, mode="focused")
                                    answer = normalize_whitespace_for_readability(
                                        normalize_mojibake(resp.get("answer", "") or "")
                                    ).strip() or "No answer generated."

                                    followups = resp.get("followups") or []

                                    st.session_state.chat_answers[q] = {
                                        "text": answer,
                                        "incomplete": bool(resp.get("incomplete")),
                                        "stop_reason": resp.get("stop_reason") or None,
                                        "prompt": q,
                                        "mode": "deep",
                                    }
                                    st.session_state.chat_followups[q] = followups
                                    st.session_state.chat_open_questions.add(q)
                                    _sync_chat_root_snapshot()
                                    _persist_new_chat_session()

                                st.rerun()

                            except Exception as e:
                                st.error(f"Error calling /study/ai: {e}")

                        if q in st.session_state.chat_open_questions:
                            answer_obj = st.session_state.chat_answers.get(q, {})
                            raw_answer = ""

                            if isinstance(answer_obj, dict):
                                raw_answer = (answer_obj.get("text") or "").strip()
                            else:
                                raw_answer = str(answer_obj or "").strip()

                            if raw_answer:
                                clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

                                _render_nc_ai_bubble(
                                    "#### Answer\n\n" + (clean_answer or raw_answer),
                                    "",
                                )

                                followups = embedded_followups or st.session_state.chat_followups.get(q, [])
                                if followups:
                                    st.markdown("#### Suggested follow-ups")
                                    render_followup_links("chat", followups, st.session_state.chat_active_id, target="_blank")

                                is_incomplete = False
                                if isinstance(answer_obj, dict):
                                    is_incomplete = bool(answer_obj.get("incomplete"))

                                if is_incomplete:
                                    if st.button("Continue", key=f"nc_cont_{section}_{q}"):
                                        st.session_state._nc_continue_loading_q = q
                                        st.rerun()

                                    if st.session_state._nc_continue_loading_q == q:
                                        st.markdown("⏳ **Continuing...**")

                                        answer_obj = st.session_state.chat_answers.get(q, {})
                                        if isinstance(answer_obj, dict):
                                            previous_text = (answer_obj.get("text") or "").strip()
                                            mode = (answer_obj.get("mode") or "deep").strip()
                                        else:
                                            previous_text = str(answer_obj or "").strip()
                                            mode = "deep"

                                        if previous_text:
                                            try:
                                                resp = fetch_study(
                                                    topic=q,
                                                    mode=mode,
                                                    continue_mode=True,
                                                    previous_answer=previous_text,
                                                )

                                                chunk = normalize_whitespace_for_readability(
                                                    normalize_mojibake(resp.get("answer", "") or "")
                                                ).strip()

                                                if chunk:
                                                    combined = (previous_text.rstrip() + "\n\n" + chunk).strip()
                                                else:
                                                    combined = previous_text

                                                st.session_state.chat_answers[q] = {
                                                    "text": combined,
                                                    "incomplete": bool(resp.get("incomplete")),
                                                    "stop_reason": resp.get("stop_reason") or None,
                                                    "prompt": q,
                                                    "mode": mode,
                                                }

                                                if resp.get("followups"):
                                                    st.session_state.chat_followups[q] = resp.get("followups") or []

                                                _sync_chat_root_snapshot()
                                                _persist_new_chat_session()

                                            except Exception as e:
                                                st.error(f"Error continuing answer: {e}")

                                            finally:
                                                st.session_state._nc_continue_loading_q = None

                                            st.rerun()

                                st.markdown("---")

            st.markdown(
                f"<div style='margin-top:14px; text-align:right; color:#64748b; font-size:11px;'>{root_ts}</div>",
                unsafe_allow_html=True,
            )
        



                    

        if st.session_state.chat_branch_answers:
            for idx, item in enumerate(st.session_state.chat_branch_answers, start=1):
                kind = (item.get("kind") or "interrogate").strip().lower()
                topic = (item.get("topic") or item.get("prompt") or f"Continued topic {idx}").strip()
                ts = (item.get("ts") or "").strip()

                _render_nc_user_bubble(topic, ts)

                if kind == "illustrate":
                    illustrate_payload = item.get("illustrate") or {}
                    illustration_text = ""
                    if isinstance(illustrate_payload, dict):
                        illustration_text = (illustrate_payload.get("illustration_text") or "").strip()

                    if illustration_text:
                        _render_nc_ai_bubble(illustration_text, item.get("ts") or "")
                    else:
                        st.caption("No illustration generated.")

                elif kind == "direct":
                    direct_payload = item.get("direct_answer") or {}
                    raw_answer = (direct_payload.get("text") or "").strip() if isinstance(direct_payload, dict) else ""


                    if raw_answer:
                            clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)
                            _render_nc_ai_bubble(clean_answer or raw_answer, direct_payload.get("ts") or "")

                            show_followups = bool(direct_payload.get("show_followups", True))
                            followups = embedded_followups or (direct_payload.get("followups") or [])
                            if show_followups and followups:
                                st.markdown("#### Suggested follow-ups")
                                render_followup_links("chat", followups, st.session_state.chat_active_id)
                    else:
                            st.caption("No direct answer generated.")

                
                        

                else:
                    _render_branch_question_map(idx - 1, item)

                st.markdown("---")

        _render_new_chat_bottom_uib()
        return


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

    resp = fetch_study(
        topic=prompt,
        mode=mode,
        continue_mode=True,
        previous_answer=m.get("text") or "",
    )

    chunk_raw = normalize_mojibake(resp.get("answer", "") or "")
    chunk = normalize_whitespace_for_readability(chunk_raw).strip()

    if not chunk:
        m["incomplete"] = False
        m["stop_reason"] = None
        m["ts"] = now_label()
        return

    root_id = m.get("continued_root") or m.get("id")
    parts = 1
    for mm in sess["messages"]:
        if mm.get("role") == "assistant" and (mm.get("continued_root") or mm.get("id")) == root_id:
            if mm.get("continued_part"):
                parts = max(parts, int(mm["continued_part"]))

    next_part = parts + 1
    labeled = f"**Continued (Part {next_part})**\n\n{chunk}"

    m["incomplete"] = False
    m["stop_reason"] = None
    m["ts"] = now_label()

    followups = resp.get("followups") or []
    sess["messages"].append(
        {
            "id": new_msg_id("a"),
            "role": "assistant",
            "text": labeled,
            "ts": now_label(),
            "incomplete": bool(resp.get("incomplete")),
            "stop_reason": resp.get("stop_reason") or None,
            "prompt": prompt,
            "mode": mode,
            "continued_root": root_id,
            "continued_part": next_part,
            "followups": followups,
        }
    )

    _persist_learning_session(st.session_state.learning_active_id, sess)


def _mode_hint_text(mode: str) -> str:
    m = (mode or "deep").lower()
    if m == "high":
        return "Overview"
    if m == "quiz":
        return "Quiz"
    return "Deep (default)"


def _request_chat_top_enter_submit() -> None:
    st.session_state.chat_top_enter_submit = True

def _request_chat_bottom_enter_submit() -> None:
    st.session_state.chat_bottom_enter_submit = True


def _is_typed_continue_intent(user_text: str) -> bool:
    t = (user_text or "").strip().lower()
    if not t:
        return False
    t = re.sub(r"\s+", " ", t)

    intents = {
        "continue", "cont", "go ahead", "go on", "carry on", "next", "more",
        "yes", "y", "yeah", "yep", "ok", "okay", "sure", "pls continue",
        "please continue", "see more", "show more"
    }
    return t in intents


def _find_last_incomplete_assistant_id(sess: Dict[str, Any]) -> Optional[str]:
    for m in reversed(sess.get("messages", [])):
        if m.get("role") == "assistant" and needs_continue_flag(m):
            return m.get("id")
    return None


def _typed_continue_should_fire(sess: Dict[str, Any], user_text: str) -> bool:
    if not _is_typed_continue_intent(user_text):
        return False
    return _find_last_incomplete_assistant_id(sess) is not None


def _queue_learning_request(
    sess: Dict[str, Any],
    prompt: str,
    mode: str,
    *,
    display_prompt: Optional[str] = None,
    fetch_full: bool = False,
) -> bool:
    prompt = (prompt or "").strip()
    mode = (mode or "deep").strip().lower()
    if mode not in {"deep", "high", "quiz"}:
        mode = "deep"

    if (
        not prompt
        or st.session_state._mnl_pending_request
        or st.session_state._mnl_generating
    ):
        return False

    if _typed_continue_should_fire(sess, prompt):
        sess["messages"].append(
            {"id": new_msg_id("u"), "role": "user", "text": prompt, "ts": now_label(), "mode_label": mode_label(mode)}
        )

        target_id = _find_last_incomplete_assistant_id(sess)
        if target_id:
            st.session_state._mnl_continue_loading_id = target_id

        st.session_state.uib_text = ""
        _persist_learning_session(st.session_state.learning_active_id, sess)
        return True

    sess["messages"].append(
        {
            "id": new_msg_id("u"),
            "role": "user",
            "text": (display_prompt or prompt).strip(),
            "ts": now_label(),
            "mode_label": mode_label(mode),
        }
    )
    sess["last_prompt"] = (display_prompt or prompt).strip()
    st.session_state.uib_text = ""
    st.session_state._mnl_pending_request = {
        "prompt": prompt,
        "mode": mode,
        "fetch_full": bool(fetch_full),
    }
    _persist_learning_session(st.session_state.learning_active_id, sess)
    return True


def _consume_requested_learning_send(sess: Dict[str, Any]) -> None:
    if not st.session_state._uib_send_requested:
        return

    st.session_state._uib_send_requested = False
    _queue_learning_request(
        sess,
        st.session_state.uib_text,
        st.session_state.uib_mode,
    )


def _generate_pending_learning_response(sess: Dict[str, Any]) -> None:
    pending = st.session_state._mnl_pending_request
    if not isinstance(pending, dict) or st.session_state._mnl_generating:
        return

    prompt = (pending.get("prompt") or "").strip()
    mode = (pending.get("mode") or "deep").strip().lower()
    fetch_full = bool(pending.get("fetch_full"))
    st.session_state._mnl_generating = True

    try:
        with st.container(key="mnl_generation"):
            with st.spinner("Generating answer... may take some time."):
                if fetch_full:
                    resp = fetch_study_full(prompt, mode=mode)
                else:
                    resp = fetch_study(prompt, mode=mode)

            answer = normalize_whitespace_for_readability(normalize_mojibake(resp.get("answer", "") or "")) or "No answer generated."
            followups = resp.get("followups") or []
            sess["messages"].append(
                {
                    "id": new_msg_id("a"),
                    "role": "assistant",
                    "text": answer,
                    "ts": now_label(),
                    "incomplete": bool(resp.get("incomplete")),
                    "stop_reason": resp.get("stop_reason") or None,
                    "prompt": prompt,
                    "mode": mode,
                    "response_id": resp.get("response_id"),
                    "continue_token": resp.get("continue_token"),
                    "followups": followups,
                }
            )
    except Exception as e:
        sess["messages"].append({"id": new_msg_id("e"), "role": "assistant", "text": f"Error calling API: {e}", "ts": now_label()})
    finally:
        st.session_state._mnl_pending_request = None
        st.session_state._mnl_generating = False
        _persist_learning_session(st.session_state.learning_active_id, sess)

    st.rerun()


def _render_user_mode_hint(mode_lbl: str) -> None:
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


def _render_my_learning_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stMainBlockContainer"]:has(.mnl-page-marker) {
          width: 100%;
          max-width: 1280px;
          margin-left: auto;
          margin-right: auto;
          padding-top: 1.8rem;
          padding-bottom: 2rem;
        }
        [data-testid="stMainBlockContainer"]:has(.mnl-empty-spacer) {
          max-width: none;
        }
        [data-testid="stMainBlockContainer"]:has(.mnl-empty-spacer) .mnl-header {
          width: min(100%, 840px);
        }
        [data-testid="stVerticalBlock"]:has(.mnl-page-marker) {
          min-height: calc(100vh - 64px);
        }
        .mnl-page-marker { display: none; }
        .mnl-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 0;
        }
        .mnl-title {
          color: #111827;
          font-size: 32px;
          font-weight: 780;
          line-height: 1.15;
        }
        .mnl-status {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: #92400e;
          font-size: 13px;
          font-weight: 650;
          white-space: nowrap;
        }
        .mnl-status::before {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #f59e0b;
          content: "";
        }
        .mnl-mode-label {
          margin-bottom: 7px;
          color: #6b7280;
          font-size: 12px;
          font-weight: 650;
          text-transform: uppercase;
        }
        div[data-testid="stHorizontalBlock"]:has(.st-key-mnl_mode_deep) {
          width: min(100%, 520px);
          gap: 4px;
          flex-wrap: nowrap;
          padding: 4px;
          border: 1px solid #dfe3e8;
          border-radius: 7px;
          background: #f4f6f7;
        }
        div[data-testid="stHorizontalBlock"]:has(.st-key-mnl_mode_deep)
        > div[data-testid="stColumn"] {
          width: 0 !important;
          min-width: 0 !important;
          flex: 1 1 0 !important;
        }
        .st-key-mnl_mode_deep button,
        .st-key-mnl_mode_overview button,
        .st-key-mnl_mode_quiz button {
          min-width: 0 !important;
          height: 38px;
          border: 0 !important;
          border-radius: 5px !important;
          box-shadow: none !important;
          font-weight: 650 !important;
        }
        .st-key-mnl_mode_deep button[kind="secondary"],
        .st-key-mnl_mode_overview button[kind="secondary"],
        .st-key-mnl_mode_quiz button[kind="secondary"] {
          color: #4b5563 !important;
          background: transparent !important;
        }
        .st-key-mnl_mode_deep button[kind="primary"],
        .st-key-mnl_mode_overview button[kind="primary"],
        .st-key-mnl_mode_quiz button[kind="primary"] {
          color: #ffffff !important;
          background: #087f7b !important;
        }
        .mnl-divider {
          height: 1px;
          margin: 18px 0 26px;
          background: #e5e7eb;
        }
        .mnl-assistant-label {
          display: flex;
          align-items: center;
          gap: 9px;
          margin: 24px 0 10px;
          color: #374151;
          font-size: 13px;
          font-weight: 700;
        }
        .mnl-assistant-mark {
          display: inline-flex;
          width: 29px;
          height: 29px;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          color: #ffffff;
          background: #087f7b;
          font-size: 11px;
        }
        .mnl-mode-tag {
          display: inline-block;
          margin-top: 7px;
          color: #52606d;
          font-size: 11px;
          font-weight: 650;
        }
        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
          width: min(78%, 720px);
          margin-left: auto;
          padding: 13px 16px;
          border: 1px solid #e3e7ea;
          border-radius: 7px;
          background: #f5f7f8;
        }
        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
        [data-testid="stChatMessageAvatarUser"] {
          display: none;
        }
        .st-key-mnl_generation {
          width: min(78%, 720px);
          min-height: 32px;
          margin-left: auto;
        }
        .mnl-empty-spacer {
          height: clamp(150px, calc(50vh - 125px), 320px);
        }
        [data-testid="stElementContainer"]:has(.mnl-active-spacer) {
          min-height: 44px;
          flex: 1 1 auto;
        }
        .mnl-active-spacer { height: 100%; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"]) {
          width: min(100%, 920px);
          align-items: center;
          gap: 10px;
          flex-wrap: nowrap;
          margin-inline: auto;
          padding: 7px 8px 7px 17px;
          border: 1px solid #cfd5da;
          border-radius: 999px;
          background: #ffffff;
          box-shadow: 0 7px 22px rgba(17, 24, 39, 0.08);
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"] {
          min-width: 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:first-child {
          width: auto !important;
          flex: 1 1 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(n+2) {
          width: 44px !important;
          flex: 0 0 44px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(1) { order: 1; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(2) { order: 4; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(3) { order: 2; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        > div[data-testid="stColumn"]:nth-child(4) { order: 3; }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        [data-testid="stTextInput"],
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        [data-testid="stTextInputRootElement"] {
          border: 0 !important;
          background: transparent !important;
          box-shadow: none !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"])
        [data-testid="stTextInputRootElement"] > div {
          border: 0 !important;
          background: transparent !important;
          box-shadow: none !important;
        }
        div[data-testid="stHorizontalBlock"]:has(input[aria-label="MNL_PROMPT"]) input {
          min-height: 43px;
          padding: 0 !important;
          color: #111827;
          background: transparent !important;
        }
        .st-key-mnl_quiz button,
        .st-key-mnl_overview button,
        .st-key-mnl_send button {
          width: 44px !important;
          min-width: 44px !important;
          height: 44px !important;
          padding: 0 !important;
          border: 1px solid #cbd2d8 !important;
          border-radius: 50% !important;
          font-size: 18px !important;
          box-shadow: none !important;
        }
        .st-key-mnl_quiz button[kind^="secondary"],
        .st-key-mnl_overview button[kind^="secondary"],
        .st-key-mnl_send button[kind^="secondary"] {
          color: #374151 !important;
          background: #ffffff !important;
        }
        .st-key-mnl_quiz button[kind^="primary"],
        .st-key-mnl_overview button[kind^="primary"],
        .st-key-mnl_send button[kind^="primary"] {
          color: #ffffff !important;
          border-color: #087f7b !important;
          background: #087f7b !important;
        }
        .mnl-icon-legend {
          width: min(100%, 920px);
          margin: 13px auto 0;
          padding-left: 22px;
          color: #66717d;
          font-size: 11px;
          line-height: 1.75;
        }
        .mnl-icon-legend-row {
          display: flex;
          align-items: center;
          gap: 7px;
        }
        .mnl-legend-symbol {
          display: inline-block;
          width: 14px;
          color: #374151;
          font-weight: 700;
          text-align: center;
        }
        @media (max-width: 700px) {
          [data-testid="stMainBlockContainer"]:has(.mnl-page-marker) { padding-top: 1.1rem; }
          .mnl-header {
            align-items: flex-start;
            flex-direction: column;
            gap: 7px;
          }
          .mnl-title { font-size: 27px; }
          div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            width: 92%;
          }
          .mnl-empty-spacer { height: 120px; }
          .mnl-icon-legend { padding-left: 12px; }
        }
        </style>
        <div class="mnl-page-marker"></div>
        """,
        unsafe_allow_html=True,
    )


def _render_learning_mode_tag(mode_lbl: str) -> None:
    active = (mode_lbl or "Deep").strip()
    if active not in {"Deep", "Overview", "Quiz"}:
        active = "Deep"
    st.markdown(
        f'<span class="mnl-mode-tag">{active} mode</span>',
        unsafe_allow_html=True,
    )


def _set_learning_mode(mode: str) -> None:
    st.session_state.uib_mode = mode
    st.rerun()


def page_my_new_learning() -> None:
    _render_my_learning_styles()
    st.markdown(
        """
        <div class="mnl-header">
          <div class="mnl-title">My New Learning</div>
          <div class="mnl-status">In active development</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sid = ensure_learning_session()
    sess = st.session_state.learning_sessions[sid]

    if "learn_seed_done" not in st.session_state:
        st.session_state.learn_seed_done = ""

    if learn_q and st.session_state.learn_seed_done != learn_q:
        resolved_learn_q = normalize_clicked_followup_prompt(learn_q)
        if _queue_learning_request(
            sess,
            resolved_learn_q,
            "deep",
            display_prompt=learn_q,
            fetch_full=True,
        ):
            st.session_state.learn_seed_done = learn_q

    _consume_requested_learning_send(sess)

    last_incomplete_id = None
    for mm in reversed(sess.get("messages", [])):
        if mm.get("role") == "assistant" and needs_continue_flag(mm):
            last_incomplete_id = mm.get("id")
            break

    for msg in sess["messages"]:
        role = msg.get("role", "assistant")
        ts = msg.get("ts") or ""
        text = normalize_whitespace_for_readability(
            normalize_mojibake(msg.get("text", "") or "")
        )

        if role == "user":
            with st.chat_message("user"):
                st.markdown(text)
                _render_learning_mode_tag(msg.get("mode_label") or "Deep")
                st.markdown(
                    f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>",
                    unsafe_allow_html=True,
                )

        else:
            if (msg.get("text") or "").lstrip().startswith("**Continued (Part "):
                st.markdown("---")

            st.markdown(
                """
                <div class="mnl-assistant-label">
                  <span class="mnl-assistant-mark">InI</span>
                  <span>InI Tutor</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            clean_answer, embedded_followups = split_answer_and_embedded_followups(text)

            st.markdown(clean_answer or text)

            if ts:
                st.markdown(
                    f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>",
                    unsafe_allow_html=True,
                )

            followups = embedded_followups or (msg.get("followups") or [])
            if followups:
                st.markdown("#### Suggested follow-ups")
                render_followup_links(
                    "learn",
                    followups,
                    st.session_state.learning_active_id,
                    target="_self",
                )

            if needs_continue_flag(msg) and (msg.get("id") == last_incomplete_id):
                msg_id = msg.get("id")

                if st.button("Continue", key=f"cont-{msg_id}"):
                    st.session_state._mnl_continue_loading_id = msg_id
                    st.rerun()

                if st.session_state._mnl_continue_loading_id == msg_id:
                    st.markdown("⏳ **Continuing...**")

                    try:
                        _continue_one_chunk(sess, msg_id)

                    except Exception as e:
                        sess["messages"].append(
                            {
                                "id": new_msg_id("e"),
                                "role": "assistant",
                                "text": f"Error continuing: {e}",
                                "ts": now_label(),
                            }
                        )

                    finally:
                        st.session_state._mnl_continue_loading_id = None

                    st.rerun()

    if st.session_state._mnl_pending_request:
        _generate_pending_learning_response(sess)

    spacer_class = "mnl-active-spacer" if sess["messages"] else "mnl-empty-spacer"
    st.markdown(f'<div class="{spacer_class}"></div>', unsafe_allow_html=True)

    current_mode = st.session_state.uib_mode
    with st.form(
        "mnl_composer",
        clear_on_submit=False,
        enter_to_submit=True,
        border=False,
    ):
        input_cols = st.columns([11, 0.75, 0.75, 0.75], gap="small")
        with input_cols[0]:
            st.text_input(
                "MNL_PROMPT",
                key="uib_text",
                label_visibility="collapsed",
                placeholder="Ask InI anything to learn...",
            )

        with input_cols[1]:
            with st.container(key="mnl_send"):
                send_submitted = st.form_submit_button(
                    "➤",
                    help="Send (Deep by default)",
                    type="primary" if current_mode == "deep" else "secondary",
                    shortcut="Enter",
                )

        with input_cols[2]:
            with st.container(key="mnl_quiz"):
                quiz_selected = st.form_submit_button(
                    "?",
                    help="Quiz",
                    type="primary" if current_mode == "quiz" else "secondary",
                )

        with input_cols[3]:
            with st.container(key="mnl_overview"):
                overview_selected = st.form_submit_button(
                    "◎",
                    help="Overview",
                    type="primary" if current_mode == "high" else "secondary",
                )

    if quiz_selected:
        _set_learning_mode("deep" if current_mode == "quiz" else "quiz")
    elif overview_selected:
        _set_learning_mode("deep" if current_mode == "high" else "high")
    elif send_submitted:
        st.session_state._uib_send_requested = True
        st.rerun()

    if not sess["messages"]:
        st.markdown(
            """
            <div class="mnl-icon-legend">
              <div class="mnl-icon-legend-row">
                <span class="mnl-legend-symbol">?</span>
                <span>Quiz</span>
              </div>
              <div class="mnl-icon-legend-row">
                <span class="mnl-legend-symbol">◎</span>
                <span>Overview</span>
              </div>
              <div class="mnl-icon-legend-row">
                <span class="mnl-legend-symbol">➤</span>
                <span>Deep / Send</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

def page_new_project() -> None:
    st.markdown('<div class="bigtitle">New Project</div>', unsafe_allow_html=True)
    st.info("Coming soon in v1.", icon="🧩")


# =========================
# Router
# =========================
if st.session_state.page == "Home":
    page_home()
elif st.session_state.page == "New Chat":
    page_new_chat()
elif st.session_state.page == "My New Learning":
    page_my_new_learning()
else:
    page_new_project()

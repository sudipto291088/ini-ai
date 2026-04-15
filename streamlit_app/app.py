import os
import time
import re
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

import requests
import streamlit as st
from storage_sqlite import (
    cleanup_empty_sessions,
    init_db,
    save_session,
    list_sessions,
    load_session,
    delete_session,
    rename_session,
)



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



/* Question buttons */
div.stButton > button {
  text-align: left !important;
  justify-content: flex-start !important;
  white-space: normal !important;
  height: auto !important;
  line-height: 1.45 !important;
  padding: 0.7rem 0.9rem !important;
}
</style>
"""

init_db()
# cleanup_empty_sessions()

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


def _chat_popup_href(sid: str) -> str:
    return _query_href(popup_chat_sid=sid)


def _chat_root_href(sid: str) -> str:
    return f"?page=chat&chat_sid={quote(sid, safe='')}"

def _chat_root_view_href(sid: str) -> str:
    return f"?page=chat&chat_sid={quote(sid, safe='')}&chat_root=1"



def _chat_branch_href(sid: Optional[str], question: str) -> str:
    q = quote(question, safe="")
    if sid:
        return f"?page=chat&chat_sid={quote(sid, safe='')}&chat_q={q}"
    return f"?page=chat&chat_q={q}"


def _learn_session_href(sid: str) -> str:
    return f"?page=learn&learn_sid={quote(sid, safe='')}"


def _learn_branch_href(sid: Optional[str], question: str) -> str:
    q = quote(question, safe="")
    if sid:
        return f"?page=learn&learn_sid={quote(sid, safe='')}&learn_q={q}"
    return f"?page=learn&learn_q={q}"


def _chat_rename_href(sid: str) -> str:
    return f"?page=chat&session_action=rename&session_sid={quote(sid, safe='')}"


def _chat_delete_href(sid: str) -> str:
    return f"?page=chat&session_action=delete&session_sid={quote(sid, safe='')}"


def _learn_rename_href(sid: str) -> str:
    return f"?page=learn&session_action=rename&session_sid={quote(sid, safe='')}"


def _learn_delete_href(sid: str) -> str:
    return f"?page=learn&session_action=delete&session_sid={quote(sid, safe='')}"


def render_followup_links(
    page: str,
    followups: list[str],
    sid: Optional[str] = None,
    target: Optional[str] = None,
) -> None:
    cleaned: list[str] = []
    seen = set()
    for fu in followups or []:
        item = (fu or "").strip()
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            cleaned.append(item)

    if not cleaned:
        return

    if target is None:
        target = "_blank" if page == "chat" else "_self"

    lines = ['<div style="text-align:left;">']
    for idx, fu in enumerate(cleaned, start=1):
        if page == "chat":
            href = _chat_branch_href(sid, fu)
        else:
            href = _learn_branch_href(sid, fu)

        lines.append(
            f'<a class="ini_plain_link" href="{href}" target="{target}">{idx}. {fu}</a>'
        )
    lines.append("</div>")
    st.markdown("\n".join(lines), unsafe_allow_html=True)


def render_followup_text(followups: list[str]) -> None:
    cleaned: list[str] = []
    seen = set()

    for fu in followups or []:
        item = (fu or "").strip()
        key = item.lower()
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

if "_uib_clear_next" not in st.session_state:
    st.session_state._uib_clear_next = False

if "_uib_send_requested" not in st.session_state:
    st.session_state._uib_send_requested = False

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

    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {
        "created": datetime.now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
        "_title_set": False,
    }
    st.session_state.learning_active_id = sid
    return sid


def start_new_learning_session() -> str:
    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {
        "created": datetime.now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
        "_title_set": False,
    }
    st.session_state.learning_active_id = sid
    return sid


def _persist_learning_session(sid: str, sess: Dict[str, Any]) -> None:
    created = sess.get("created") or datetime.now().strftime("%b %d.%Y")

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
        sid = f"chat-{int(time.time())}"

    st.session_state.chat_active_id = sid
    st.session_state.chat_loaded_sid = sid

    created = datetime.now().strftime("%b %d.%Y")
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
        session_id=sid,
        title=title,
        created_at=created,
        messages=payload,
    )
    return sid


def _load_new_chat_session(sid: str) -> bool:
    loaded = load_session(sid)
    if not loaded:
        return False

    payload = loaded.get("messages") or {}
    if not isinstance(payload, dict):
        return False

    st.session_state.chat_active_id = sid
    st.session_state.chat_loaded_sid = sid
    st.session_state.chat_sessions[sid] = {
        "created": loaded.get("created") or datetime.now().strftime("%b %d.%Y"),
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
    st.session_state.chat_root_interrogate = st.session_state.chat.get("interrogate")
    st.session_state.chat_root_illustrate = st.session_state.chat.get("illustrate")
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

    loaded = load_session(sid)
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
        s = re.sub(r"^\d+\.\s*", "", s)
        s = re.sub(r"^[-•*o]\s*", "", s).strip()
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
page_param = (qp.get("page") or "chat").lower()
learn_sid = (qp.get("learn_sid") or "").strip()
chat_sid = (qp.get("chat_sid") or "").strip()
popup_chat_sid = (qp.get("popup_chat_sid") or "").strip()
chat_root = (qp.get("chat_root") or "").strip()
chat_q = (qp.get("chat_q") or "").strip()
learn_q = (qp.get("learn_q") or "").strip()
session_action = (qp.get("session_action") or "").strip().lower()
session_sid = (qp.get("session_sid") or "").strip()

param_to_page = {"chat": "New Chat", "learn": "My New Learning", "proj": "New Project"}

if page_param in param_to_page:
    new_page = param_to_page[page_param]
    st.session_state.page = new_page

st.session_state._last_page_param = page_param

if popup_chat_sid:
    st.session_state.chat_popup_sid = popup_chat_sid
else:
    st.session_state.chat_popup_sid = None

if learn_sid:
    loaded = load_session(learn_sid)
    if loaded:
        st.session_state.learning_active_id = learn_sid
        st.session_state.learning_sessions[learn_sid] = {
            "created": loaded.get("created") or datetime.now().strftime("%b %d.%Y"),
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
        delete_session(session_sid)

        if st.session_state.chat_active_id == session_sid:
            st.session_state.chat_active_id = None
            st.session_state.chat_loaded_sid = None

        if st.session_state.learning_active_id == session_sid:
            st.session_state.learning_active_id = None

        st.query_params.clear()
        st.query_params["page"] = page_param
        st.rerun()

    elif session_action == "rename":
        st.session_state.rename_session_sid = session_sid
        st.session_state.rename_session_page = page_param
        st.query_params.clear()
        st.query_params["page"] = page_param






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
    st.markdown('<span class="badge">v0 • AI Tutor</span>', unsafe_allow_html=True)

    st.markdown('<div class="small" style="color:var(--muted); font-weight:750; margin-top:10px;">Navigation</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="?page=chat" target="_self">💬&nbsp;&nbsp;New Chat</a>
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="?page=learn" target="_self">📚&nbsp;&nbsp;My New Learning</a>
          <a style="text-decoration:none; border:1px solid var(--stroke); background:var(--card); padding:9px 10px; border-radius:12px; color:var(--ink); font-size:13px; font-weight:650;"
             href="?page=proj" target="_self">🧩&nbsp;&nbsp;New Project</a>
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

    chat_rows = [row for row in list_sessions(limit=30) if str(row[0]).startswith("chat-")]
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


    rows = [row for row in list_sessions(limit=30) if str(row[0]).startswith("learn-")]
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

    loaded = load_session(sid)
    current_title = ""
    if loaded:
        current_title = (loaded.get("title") or "").strip()

    new_title = st.text_input("Session name", value=current_title, key="rename_session_input")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save", key="rename_session_save_btn"):
            rename_session(sid, new_title.strip())
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

            open_section = st.toggle(section, value=(section == "Orientation"), key=f"branch_{branch_idx}_sec_{section}")

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
                                resp = fetch_study(q, mode="deep")
                                answer = normalize_whitespace_for_readability(normalize_mojibake(resp.get("answer", "") or "")).strip() or "No answer generated."
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
                        raw_answer = (answer_obj.get("text") or "").strip() if isinstance(answer_obj, dict) else str(answer_obj or "").strip()

                        if raw_answer:
                            clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)
                            st.markdown("##### Answer")
                            st.markdown(clean_answer or raw_answer)

                            followups = embedded_followups or branch_followups.get(q, [])
                            if followups:
                                st.markdown("##### Suggested follow-ups")
                                render_followup_links("chat", followups, st.session_state.chat_active_id, target="_blank")

                            is_incomplete = False
                            if isinstance(answer_obj, dict):
                                is_incomplete = bool(answer_obj.get("incomplete")) or ((answer_obj.get("stop_reason") or "").strip().lower() == "max_output_tokens")

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
                                            resp = fetch_study(topic=q, mode=mode, continue_mode=True, previous_answer=previous_text)
                                            chunk = normalize_whitespace_for_readability(normalize_mojibake(resp.get("answer", "") or "")).strip()
                                            combined = (previous_text.rstrip() + "\n\n" + chunk).strip() if chunk else previous_text
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

    def _render_nc_user_bubble(text: str, ts: str = "") -> None:
        prompt = (text or "").strip()
        if not prompt:
            return
        with st.chat_message("user"):
            st.markdown(prompt)
            if ts:
                st.markdown(
                    f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>",
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
            st.query_params.clear()
            st.query_params["page"] = "chat"

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

                st.session_state.chat_root_interrogate = data
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
            st.query_params.clear()
            st.query_params["page"] = "chat"

            with st.spinner("Generating illustrations... please wait."):
                data = fetch_illustrate(topic_text.strip())
                st.session_state.chat["topic"] = topic_text.strip()
                st.session_state.chat_root_topic = topic_text.strip()
                if "chat_bottom_topic_input" in st.session_state:
                    del st.session_state["chat_bottom_topic_input"]
                st.session_state.chat["illustrate"] = data
                st.session_state.chat["interrogate"] = None
                st.session_state.chat_intro = ""
                st.session_state.chat_direct_answer = None
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()

                st.session_state.chat_root_interrogate = None
                st.session_state.chat_root_illustrate = data
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

        st.text_input(
        "Topic",
        placeholder="Type a topic (e.g., Artificial Intelligence, Data Science)...",
        key="chat_top_topic_input",
        on_change=_request_chat_top_enter_submit,
)

        colA, colB, colC = st.columns([1, 1, 4])
        with colA:
            run = st.button("Interrogate", key="nc_top_interrogate")
        with colB:
            illustrate_run = st.button("Illustrate", key="nc_top_illustrate")
        with colC:
            st.caption("Tip: backend must be running (FastAPI).")

        if st.session_state.chat_top_enter_submit:
           st.session_state.chat_top_enter_submit = False
           _run_new_chat_interrogate(st.session_state.chat_top_topic_input)

        if run:
            _run_new_chat_interrogate(st.session_state.chat_top_topic_input)
        if illustrate_run:
            _run_new_chat_illustrate(st.session_state.chat_top_topic_input)

    def _render_new_chat_bottom_uib() -> None:
        st.markdown("---")
        st.text_input(
            "Topic",
            key="chat_bottom_topic_input",
            label_visibility="collapsed",
            placeholder="Type another topic...",
            on_change=_request_chat_bottom_enter_submit,
)

        colA, colB, colC = st.columns([1, 1, 4])
        with colA:
            run = st.button("Interrogate", key="nc_bottom_interrogate")
        with colB:
            illustrate_run = st.button("Illustrate", key="nc_bottom_illustrate")
        with colC:
            st.caption("Type a new topic above to continue exploring.")

        if st.session_state.chat_bottom_enter_submit:
            st.session_state.chat_bottom_enter_submit = False
            _run_new_chat_interrogate(st.session_state.chat_bottom_topic_input)

        if run:
            _run_new_chat_interrogate(st.session_state.chat_bottom_topic_input)
        if illustrate_run:
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

    if not has_new_chat_content:
        _render_new_chat_top_uib()

    illustrate_data = st.session_state.chat.get("illustrate")
    if isinstance(illustrate_data, dict) and (illustrate_data.get("illustration_text") or "").strip():
        _render_nc_user_bubble(st.session_state.chat_root_topic or st.session_state.chat.get("topic") or "")

        with st.chat_message("assistant"):
            st.markdown("### Illustrations")
            st.markdown(illustrate_data.get("illustration_text") or "")

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

                    with st.chat_message("assistant"):
                        if illustration_text:
                            st.markdown(illustration_text)
                        else:
                            st.caption("No illustration generated.")

                elif kind == "direct":
                    direct_payload = item.get("direct_answer") or {}
                    raw_answer = (direct_payload.get("text") or "").strip() if isinstance(direct_payload, dict) else ""

                    with st.chat_message("assistant"):
                        if raw_answer:
                            clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)
                            st.markdown(clean_answer or raw_answer)

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

        if not chat_q:
            _render_new_chat_bottom_uib()
        return

    direct_answer = st.session_state.chat_direct_answer
    if isinstance(direct_answer, dict) and (direct_answer.get("text") or "").strip():
        _render_nc_user_bubble(
            direct_answer.get("prompt") or st.session_state.chat.get("topic") or ""
        )

        raw_answer = (direct_answer.get("text") or "").strip()
        clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

        with st.chat_message("assistant"):
            st.markdown(clean_answer or raw_answer)

            show_followups = bool(direct_answer.get("show_followups", True))
            followups = embedded_followups or (direct_answer.get("followups") or [])

            if show_followups and followups:
                st.markdown("#### Suggested follow-ups")
                render_followup_links("chat", followups, st.session_state.chat_active_id)

            is_incomplete = bool(direct_answer.get("incomplete")) or (
                (direct_answer.get("stop_reason") or "").strip().lower() == "max_output_tokens"
            )

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
        _render_nc_user_bubble(st.session_state.chat_root_topic or st.session_state.chat.get("topic") or "")
        intro = st.session_state.chat_intro
        if intro:
            clean_intro, intro_followups = split_answer_and_embedded_followups(intro)

            st.markdown("### Introduction")
            st.markdown(clean_intro or intro)

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
                                resp = fetch_study(q, mode="deep")
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

                            st.markdown("#### Answer")
                            st.markdown(clean_answer or raw_answer)

                            followups = embedded_followups or st.session_state.chat_followups.get(q, [])
                            if followups:
                                st.markdown("#### Suggested follow-ups")
                                render_followup_links("chat", followups, st.session_state.chat_active_id, target="_blank")

                            is_incomplete = False
                            if isinstance(answer_obj, dict):
                                is_incomplete = bool(answer_obj.get("incomplete")) or (
                                    (answer_obj.get("stop_reason") or "").strip().lower() == "max_output_tokens"
                                )

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

                    with st.chat_message("assistant"):
                        if illustration_text:
                            st.markdown(illustration_text)
                        else:
                            st.caption("No illustration generated.")

                elif kind == "direct":
                    direct_payload = item.get("direct_answer") or {}
                    raw_answer = (direct_payload.get("text") or "").strip() if isinstance(direct_payload, dict) else ""

                    with st.chat_message("assistant"):
                        if raw_answer:
                            clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)
                            st.markdown(clean_answer or raw_answer)

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
            "id": f"a-{int(time.time())}",
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


def _request_send() -> None:
    st.session_state._uib_send_requested = True

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


def _process_send(sess: Dict[str, Any]) -> None:
    prompt = (st.session_state.uib_text or "").strip()
    mode = (st.session_state.uib_mode or "deep").strip().lower()
    if mode not in {"deep", "high", "quiz"}:
        mode = "deep"

    if not prompt:
        return

    if _typed_continue_should_fire(sess, prompt):
        sess["messages"].append(
            {"id": f"u-{int(time.time())}", "role": "user", "text": prompt, "ts": now_label(), "mode_label": mode_label(mode)}
        )

        target_id = _find_last_incomplete_assistant_id(sess)
        if target_id:
            st.session_state._mnl_continue_loading_id = target_id

        st.session_state._uib_clear_next = True
        st.rerun()

    sess["messages"].append(
        {"id": f"u-{int(time.time())}", "role": "user", "text": prompt, "ts": now_label(), "mode_label": mode_label(mode)}
    )
    sess["last_prompt"] = prompt

    try:
        with st.spinner("Generating answer... may take some time."):
            resp = fetch_study(prompt, mode=mode)
            answer = normalize_whitespace_for_readability(normalize_mojibake(resp.get("answer", "") or "")) or "No answer generated."
            followups = resp.get("followups") or []
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
                    "response_id": resp.get("response_id"),
                    "continue_token": resp.get("continue_token"),
                    "followups": followups,
                }
            )
    except Exception as e:
        sess["messages"].append({"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error calling API: {e}", "ts": now_label()})

    st.session_state._uib_clear_next = True
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


def page_my_new_learning() -> None:
    st.markdown('<div class="bigtitle">My New Learning</div>', unsafe_allow_html=True)
    st.caption("Interactive AI tutor (v0): AI topics only. Deep is default; use Overview/Quiz when needed.")

    sid = ensure_learning_session()
    sess = st.session_state.learning_sessions[sid]

    if "learn_seed_done" not in st.session_state:
        st.session_state.learn_seed_done = ""

    if learn_q and st.session_state.learn_seed_done != learn_q:
        try:
            resolved_learn_q = normalize_clicked_followup_prompt(learn_q)

            sess["messages"].append(
                {"id": f"u-{int(time.time())}", "role": "user", "text": learn_q, "ts": now_label(), "mode_label": "Deep"}
            )

            with st.spinner("Generating answer... may take some time."):
                resp = fetch_study_full(resolved_learn_q, mode="deep")
                answer = (resp.get("answer") or "").strip() or "No answer generated."
                followups = resp.get("followups") or []

                sess["messages"].append(
                    {
                        "id": f"a-{int(time.time())}",
                        "role": "assistant",
                        "text": answer,
                        "ts": now_label(),
                        "followups": followups,
                    }
                )

                sess["last_prompt"] = learn_q
                _persist_learning_session(st.session_state.learning_active_id, sess)
                st.session_state.learn_seed_done = learn_q
            st.rerun()
        except Exception as e:
            sess["messages"].append(
                {"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error auto-running learning FUQ: {e}", "ts": now_label()}
            )

    last_incomplete_id = None
    for mm in reversed(sess.get("messages", [])):
        if mm.get("role") == "assistant" and needs_continue_flag(mm):
            last_incomplete_id = mm.get("id")
            break

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
                if (msg.get("text") or "").lstrip().startswith("**Continued (Part "):
                    st.markdown("---")

                clean_answer, embedded_followups = split_answer_and_embedded_followups(text)

                st.markdown(clean_answer or text)
                st.markdown(f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>", unsafe_allow_html=True)

                followups = embedded_followups or (msg.get("followups") or [])
                if followups:
                    st.markdown("#### Suggested follow-ups")
                    render_followup_links("learn", followups, st.session_state.learning_active_id, target="_self")

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
                                {"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error continuing: {e}", "ts": now_label()}
                            )
                        finally:
                            st.session_state._mnl_continue_loading_id = None

                        st.rerun()

    if st.session_state._uib_clear_next:
        st.session_state.uib_text = ""
        st.session_state._uib_clear_next = False

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
            on_change=_request_send,
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

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

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
    st.markdown("</div>", unsafe_allow_html=True)

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
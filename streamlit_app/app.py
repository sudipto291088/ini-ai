

import os
import time
import re
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote



import requests
import streamlit as st
from storage_sqlite import cleanup_empty_sessions, init_db, save_session, list_sessions, load_session, delete_session






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

@import url("https://fonts.googleapis.com/icon?family=Material+Icons");
.material-icons, [class*="material-icons"]{
  font-family: "Material Icons" !important;
  font-weight: normal !important;
  font-style: normal !important;
}


html, body{
  font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif !important;
  color: var(--ink);
}
button, input, textarea, select, label, p, div{
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

/* --- Fix Streamlit expander arrows showing as text --- */
@import url("https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200");
@import url("https://fonts.googleapis.com/icon?family=Material+Icons");

/* Streamlit uses Material Symbols in many builds */
.material-symbols-rounded,
.material-symbols-outlined,
.material-symbols-sharp {
  font-family: "Material Symbols Rounded" !important;
  font-weight: normal !important;
  font-style: normal !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  display: inline-block !important;
  white-space: nowrap !important;
  direction: ltr !important;
}

/* Some components still use Material Icons */
.material-icons, [class*="material-icons"] {
  font-family: "Material Icons" !important;
}


/* Force icon fonts for Streamlit chevrons/arrows */
span[class*="material-symbols"], i[class*="material-icons"]{
  font-family: "Material Symbols Rounded","Material Icons" !important;
}


/* --- Permanent fix: remove Material Icons text and use our own arrows --- */

/* Hide the Material Icons text inside expanders */
.stExpander summary span.material-icons,
.stExpander summary span.material-symbols-rounded,
.stExpander summary span.material-symbols-outlined,
.stExpander summary span.material-symbols-sharp {
  display: none !important;
}


/* Hide any icon-text spans Streamlit uses in expander summary */
.stExpander summary span {
  font-family: inherit;
}
.stExpander summary span.material-icons,
.stExpander summary span[class*="material"],
.stExpander summary i[class*="material"]{
  display: none !important;
}


/* Add our own arrow */
.stExpander summary::before {
  content: "▸";
  display: inline-block;
  margin-right: 8px;
  font-size: 16px;
  line-height: 1;
}

/* When expanded, show down arrow */
.stExpander details[open] > summary::before {
  content: "▾";
}

/* Hide ONLY the icon span, not the expander label text */
.stExpander summary span.material-icons,
.stExpander summary span[class*="material-symbols"],
.stExpander summary i[class*="material-icons"]{
  display: none !important;
}

.material-icons{ font-family: "Material Icons" !important; }
[class*="material-symbols"]{ font-family: "Material Symbols Rounded" !important; }

/* New Chat question buttons: plain white and left-aligned */
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
    # 1) If we already have a valid active session in memory, keep it
    if (
        st.session_state.learning_active_id
        and st.session_state.learning_active_id in st.session_state.learning_sessions
    ):
        return st.session_state.learning_active_id

    # 2) Otherwise, try to load the most recently-updated session from DB
    rows = [row for row in list_sessions(limit=30) if str(row[0]).startswith("learn-")]  # [(sid,title,created,updated)]
    if rows:
        sid, title, created_at, updated_at = rows[0]
        loaded = load_session(sid)
        if loaded:
            st.session_state.learning_active_id = sid
            st.session_state.learning_sessions[sid] = {
                "created": loaded.get("created") or datetime.now().strftime("%b %d.%Y"),
                "messages": loaded.get("messages") or [],
                "last_prompt": "",
                "title": (loaded.get("title") or "Learning Session"),
                "_title_set": (loaded.get("title") or "").strip() not in {"", "Learning Session", "Session", "New Session"},
            }
            return sid

    # 3) If nothing exists yet, create a new one (ONLY once)
    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {
        "created": datetime.now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
        "_title_set": False,
    }
    st.session_state.learning_active_id = sid
    _persist_learning_session(sid, st.session_state.learning_sessions[sid])
    return sid


def start_new_learning_session() -> str:
    sid = f"learn-{int(time.time())}"
    st.session_state.learning_sessions[sid] = {
        "created": datetime.now().strftime("%b %d.%Y"),
        "messages": [],
        "last_prompt": "",
        "title": "Learning Session",
    }
    st.session_state.learning_active_id = sid

    # NEW: persist immediately so it appears in sidebar even before first message
    _persist_learning_session(sid, st.session_state.learning_sessions[sid])

    return sid




def _persist_learning_session(sid: str, sess: Dict[str, Any]) -> None:
    created = sess.get("created") or datetime.now().strftime("%b %d.%Y")

    default_titles = {"", "Learning Session", "Session", "New Session"}

    # Pick the FIRST user message as the session title seed (best behavior for tutors)
    first_user_prompt = ""
    for m in sess.get("messages", []):
        if m.get("role") == "user":
            t = (m.get("text") or "").strip()
            if t:
                first_user_prompt = t
                break

    current_title = (sess.get("title") or "").strip()

    # Lock title ONLY once, when we have a real first prompt
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
    }


def _new_chat_title_from_payload(payload: Dict[str, Any]) -> str:
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
        return st.session_state.chat_active_id or ""

    if not sid:
        sid = st.session_state.chat_active_id

    if not sid:
        sid = f"chat-{int(time.time())}"
        st.session_state.chat_active_id = sid

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

    return True

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


def fetch_interrogate(topic: str) -> Dict[str, Any]:
    return post_json("/interrogate", {"topic": topic}, timeout=240)


def fetch_illustrate(topic: str) -> Dict[str, Any]:
    return post_json("/illustrate", {"topic": topic}, timeout=240)
    

def fetch_study_full(topic: str, mode: str = "deep", max_rounds: int = 4) -> Dict[str, Any]:
    """
    Fetches a study answer and automatically continues if the backend marks it incomplete.
    Mirrors the continuation pattern already used in My New Learning.
    """
    resp = fetch_study(topic, mode=mode)
    answer = normalize_whitespace_for_readability(
        normalize_mojibake(resp.get("answer", "") or "")
    )

    rounds = 0
    while rounds < max_rounds and (
        resp.get("incomplete") is True or (resp.get("stop_reason") or "").strip().lower() == "max_output_tokens"
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


def fuq_href(page: str, question: str) -> str:
    q = quote(question, safe="")
    if page == "learn":
        return f"?page=learn&learn_q={q}"
    return f"?page=chat&chat_q={q}"


def split_answer_and_embedded_followups(text: str) -> tuple[str, list[str]]:
    """
    Extract follow-up prompts already visible inside the answer text.

    Supports:
    - explicit sections like 'Suggested follow-ups:'
    - CTA headers like 'If you want, I can now:' followed by bullets
    """
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
        s = (ln or "").strip().lower()
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
            body_lines.append("")  # keeps spacing where CTA block was
            i += 1

            while i < len(lines):
                next_raw = lines[i]
                next_s = (next_raw or "").strip()

                # stop CTA collection on blank line
                if not next_s:
                    break

                cleaned = _clean_fu_line(next_s)

                # ignore nested CTA headers accidentally echoed by model
                if any(re.match(p, cleaned.lower()) for p in cta_header_patterns):
                    i += 1
                    continue

                # only collect real actionable follow-up lines
                if cleaned and len(cleaned) >= 8 and not cleaned.endswith(":"):
                    followups.append(cleaned)

                i += 1

            # skip the blank line that ended the CTA block
            while i < len(lines) and not (lines[i] or "").strip():
                i += 1
            continue

        body_lines.append(raw)
        i += 1

    # de-duplicate while preserving order
    seen = set()
    deduped = []
    for fu in followups:
        key = fu.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(fu)

    return "\n".join(body_lines).strip(), deduped


# =========================
# URL / Query routing
# =========================
qp = st.query_params
page_param = (qp.get("page") or "chat").lower()
learn_sid = qp.get("learn_sid")
chat_sid = qp.get("chat_sid")
chat_q = (qp.get("chat_q") or "").strip()
learn_q = (qp.get("learn_q") or "").strip()


param_to_page = {"chat": "New Chat", "learn": "My New Learning", "proj": "New Project"}


if page_param in param_to_page:
    new_page = param_to_page[page_param]
    st.session_state.page = new_page


st.session_state._last_page_param = page_param


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

if chat_sid and st.session_state.chat_loaded_sid != chat_sid:
    _load_new_chat_session(chat_sid)


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

    if st.session_state.page == "New Chat":
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown('<div class="small" style="color:var(--muted); font-weight:750;">Your Chat</div>', unsafe_allow_html=True)

        chat_rows = [row for row in list_sessions(limit=30) if str(row[0]).startswith("chat-")]

        if chat_rows:
            for sid, title, created_at, updated_at in chat_rows:
                label = (title or "New Chat Session").strip()
                st.markdown(f"- [{label}](?page=chat&chat_sid={sid})")
        else:
            current_topic = (st.session_state.chat.get("topic") or "").strip()
            if current_topic:
                st.markdown(f"- 💬 {current_topic}")
            else:
                st.markdown('<div class="small" style="color:var(--muted);">No chat yet.</div>', unsafe_allow_html=True)

        

    if st.session_state.page == "My New Learning":
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown('<div class="small" style="color:var(--muted); font-weight:750;">Your Learning</div>', unsafe_allow_html=True)

        rows = [row for row in list_sessions(limit=30) if str(row[0]).startswith("learn-")]
        if rows:
            for sid, title, created_at, updated_at in rows:
                active = (sid == st.session_state.learning_active_id)
                dot = "🔵" if active else "⚪"
                label = (title or "Learning Session").strip()
                st.markdown(f"- [{label}](?page=learn&learn_sid={sid})")
        else:
            st.markdown('<div class="small" style="color:var(--muted);">No learning sessions yet.</div>', unsafe_allow_html=True)

        if st.button("🗑️ Delete this session"):
            sid = st.session_state.learning_active_id
            if sid:
                delete_session(sid)
                st.session_state.learning_sessions.pop(sid, None)
                st.session_state.learning_active_id = None
                start_new_learning_session()
                st.rerun()


# =========================
# Pages
# =========================
def page_new_chat() -> None:
    st.markdown('<div class="bigtitle">New Chat</div>', unsafe_allow_html=True)
    st.caption(
        "InI Question Engine (v0): Interrogate generates a progressive question ladder. "
        "Click a question to open or hide its answer."
    )

    # -------------------------
    # State for persistent Q&A
    # -------------------------
    if "chat_answers" not in st.session_state:
        st.session_state.chat_answers = {}   # q -> answer text
    if "chat_open_questions" not in st.session_state:
        st.session_state.chat_open_questions = set()   # visible answers
    if "chat_visited_questions" not in st.session_state:
        st.session_state.chat_visited_questions = set()   # ever clicked
    if "chat_intro" not in st.session_state:
        st.session_state.chat_intro = ""
    if "chat_followups" not in st.session_state:
        st.session_state.chat_followups = {}   # q -> list[str]
    if "chat_seed_done" not in st.session_state:
        st.session_state.chat_seed_done = ""
    


    
      
    
    
    # Auto-run FUQ opened in a new tab for New Chat
    if chat_q and st.session_state.chat_seed_done != chat_q:
        try:
            with st.spinner("Generating details... please wait."):
                resp = fetch_study(chat_q, mode="focused")
                answer = normalize_whitespace_for_readability(
                    normalize_mojibake(resp.get("answer", "") or "")
                ).strip() or "No answer generated."

                followups = resp.get("followups") or []

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
                _persist_new_chat_session()  # save the seeded FUQ state immediately
            st.rerun()
        except Exception as e:
            st.error(f"Error auto-running chat FUQ: {e}")


    

    topic = st.text_input(
    "Topic",
    value=st.session_state.chat.get("topic", ""),
    placeholder="Type a topic (e.g., Artificial Intelligence, Data Science)...",
)
    st.session_state.chat["topic"] = topic
    





    colA, colB, colC = st.columns([1, 1, 4])

    with colA:
        run = st.button("Interrogate")

    with colB:
        illustrate_run = st.button("Illustrate")

    with colC:
        st.caption("Tip: backend must be running (FastAPI).")

   

    if run and topic.strip():
        try:
            with st.spinner("Generating question map... may take some time."):
                data = fetch_interrogate(topic.strip())
                st.session_state.chat["interrogate"] = data

            # --- Generate intro paragraph ---
                intro_resp = fetch_study_full(topic.strip(), mode="high")
                intro = intro_resp.get("answer", "").strip()

                st.session_state.chat_intro = intro

            # Reset topic state
                st.session_state.chat["illustrate"] = None
                st.session_state.chat_direct_answer = None
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()
                _persist_new_chat_session()  # save state immediately after generation

        except Exception as e:
            st.error(f"Error calling /interrogate: {e}")

    if illustrate_run and topic.strip():
        try:
            with st.spinner("Generating illustrations... please wait."):
                data = fetch_illustrate(topic.strip())
                st.session_state.chat["illustrate"] = data

                # Clear other New Chat views
                st.session_state.chat["interrogate"] = None
                st.session_state.chat_intro = ""
                st.session_state.chat_direct_answer = None
                st.session_state.chat_answers = {}
                st.session_state.chat_followups = {}
                st.session_state.chat_open_questions = set()
                st.session_state.chat_visited_questions = set()
                _persist_new_chat_session()

        except Exception as e:
            st.error(f"Error calling /illustrate: {e}")

    illustrate_data = st.session_state.chat.get("illustrate")
    if isinstance(illustrate_data, dict) and (illustrate_data.get("illustration_text") or "").strip():
        st.markdown("### Illustrations")
        st.markdown(illustrate_data.get("illustration_text") or "")
        st.markdown("---")
        return

    direct_answer = st.session_state.chat_direct_answer
    if isinstance(direct_answer, dict) and (direct_answer.get("text") or "").strip():
        raw_answer = (direct_answer.get("text") or "").strip()
        clean_answer, embedded_followups = split_answer_and_embedded_followups(raw_answer)

        st.markdown("### Answer")
        st.markdown(clean_answer or raw_answer)

        followups = embedded_followups or (direct_answer.get("followups") or [])
        if followups:
            st.markdown("#### Suggested follow-ups")
            for fu in followups:
                href = fuq_href("chat", fu)
                st.markdown(
                    f'<a href="{href}" target="_blank" style="text-decoration:none;">• {fu}</a>',
                    unsafe_allow_html=True,
                )

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
                        }
                        _persist_new_chat_session()

                    except Exception as e:
                        st.error(f"Error continuing answer: {e}")
                    finally:
                        st.session_state._nc_continue_loading_q = None

                    st.rerun()

        st.markdown("---")
        return

    data = st.session_state.chat.get("interrogate")
    if isinstance(data, dict) and data.get("categories"):
        intro = st.session_state.chat_intro
        if intro:
            clean_intro, intro_followups = split_answer_and_embedded_followups(intro)

            st.markdown("### Introduction")
            st.markdown(clean_intro or intro)

            if intro_followups:
                st.markdown("#### Suggested follow-ups")
                for fu in intro_followups:
                    href = fuq_href("chat", fu)
                    st.markdown(
                        f'<a href="{href}" target="_blank" style="text-decoration:none;">• {fu}</a>',
                        unsafe_allow_html=True,
                    )
        

        st.markdown("### Question Map")
        st.caption("Orientation → Foundations → Mechanisms → Methods & Tools → Applications → Pitfalls → Advanced / Future")

        
        hide_all = st.button("Hide All Answers", key="hide_all_answers_newchat")
        if hide_all:
            st.session_state.chat_open_questions = set()
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

                    if visited:
                        button_label = f"✓ {q}"
                    else:
                        button_label = q

                    if st.button(button_label, key=f"q_{section}_{q}", type="secondary"):
                        # Mark as visited forever
                        st.session_state.chat_visited_questions.add(q)

                        # Toggle closed if already open
                        if is_open:
                            st.session_state.chat_open_questions.discard(q)
                            _persist_new_chat_session()  # save state immediately after toggling
                            st.rerun()

                        # Open if cached already
                        if q in st.session_state.chat_answers:
                            st.session_state.chat_open_questions.add(q)
                            _persist_new_chat_session()  # save state immediately after opening
                            st.rerun()

                        
                        # Otherwise fetch first answer chunk, cache it, and open it
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
                                _persist_new_chat_session()  # save state immediately after fetching answer
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error calling /study/ai: {e}")

                    
                    # Persistently show answer if open
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
                                for fu in followups:
                                    href = fuq_href("chat", fu)
                                    st.markdown(
                                        f'<a href="{href}" target="_blank" style="text-decoration:none;">• {fu}</a>',
                                        unsafe_allow_html=True,
                                    )

                            # New Chat Continue button
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
                                            _persist_new_chat_session()

                                        except Exception as e:
                                            st.error(f"Error continuing answer: {e}")
                                        finally:
                                            st.session_state._nc_continue_loading_q = None

                                        st.rerun()

                            st.markdown("---")
                    


def _continue_one_chunk(sess: Dict[str, Any], msg_id: str) -> None:
    # Find the message being continued
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

    # If we somehow don't have prompt metadata, stop continuation for this message
    if not prompt:
        m["incomplete"] = False
        m["stop_reason"] = None
        return

    # Ask backend for continuation using the CURRENT text as context
    resp = fetch_study(
        topic=prompt,
        mode=mode,
        continue_mode=True,
        previous_answer=m.get("text") or "",
    )

    chunk_raw = normalize_mojibake(resp.get("answer", "") or "")
    chunk = normalize_whitespace_for_readability(chunk_raw).strip()

    # If backend returned nothing, don't create a new part
    if not chunk:
        m["incomplete"] = False
        m["stop_reason"] = None
        m["ts"] = now_label()
        return

    # ---- OPTION A: append a NEW message instead of mutating the original ----
    root_id = m.get("continued_root") or m.get("id")
    # Count existing parts (original + any continuations)
    parts = 1
    for mm in sess["messages"]:
        if mm.get("role") == "assistant" and (mm.get("continued_root") or mm.get("id")) == root_id:
            if mm.get("continued_part"):
                parts = max(parts, int(mm["continued_part"]))

    next_part = parts + 1
    labeled = f"**Continued (Part {next_part})**\n\n{chunk}"

    # Mark the previous message as complete so ONLY the latest part shows "Continue"
    m["incomplete"] = False
    m["stop_reason"] = None
    m["ts"] = now_label()

    # Append the new assistant chunk as a new bubble
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



def _is_typed_continue_intent(user_text: str) -> bool:
    """
    Detects ultra-short "continue" intents like:
    'go ahead', 'continue', 'yes', 'ok', 'sure', 'more', 'next', etc.
    This is ONLY used when there is an incomplete assistant message.
    """
    t = (user_text or "").strip().lower()
    if not t:
        return False
    # normalize multiple spaces
    t = re.sub(r"\s+", " ", t)

    intents = {
        "continue", "cont", "go ahead", "go on", "carry on", "next", "more",
        "yes", "y", "yeah", "yep", "ok", "okay", "sure", "pls continue",
        "please continue", "see more", "show more"
    }
    return t in intents


def _find_last_incomplete_assistant_id(sess: Dict[str, Any]) -> Optional[str]:
    """Return the most recent assistant msg id that still needs continuation."""
    for m in reversed(sess.get("messages", [])):
        if m.get("role") == "assistant" and needs_continue_flag(m):
            return m.get("id")
    return None


def _typed_continue_should_fire(sess: Dict[str, Any], user_text: str) -> bool:
    """
    Only treat 'go ahead' etc. as continuation if there is an actual incomplete assistant msg.
    """
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

    # 1) If user typed "go ahead" / "continue" AND there is an incomplete assistant msg,
    # treat this as Continue, not a new question.
    if _typed_continue_should_fire(sess, prompt):
        # record the user's message (so chat history shows what user typed)
        sess["messages"].append(
            {"id": f"u-{int(time.time())}", "role": "user", "text": prompt, "ts": now_label(), "mode_label": mode_label(mode)}
        )

        target_id = _find_last_incomplete_assistant_id(sess)
        if target_id:
            st.session_state._mnl_continue_loading_id = target_id

        st.session_state._uib_clear_next = True
        st.rerun()

    # 2) Normal path: treat as a new question
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

    if "learn_seed_done" not in st.session_state:
        st.session_state.learn_seed_done = ""

    

    # Auto-run FUQ opened in a new tab for My New Learning
    if learn_q and st.session_state.learn_seed_done != learn_q:
        try:
            sess["messages"].append(
                {"id": f"u-{int(time.time())}", "role": "user", "text": learn_q, "ts": now_label(), "mode_label": "Deep"}
            )

            with st.spinner("Generating answer... may take some time."):
                resp = fetch_study_full(learn_q, mode="deep")
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

    # # Handle Continue
    # if st.session_state._continue_msg_id:
    #     msg_id = st.session_state._continue_msg_id
    #     st.session_state._continue_msg_id = None
    #     try:
    #         with st.spinner("Generating answer... may take some time."):
    #             _continue_one_chunk(sess, msg_id)
    #     except Exception as e:
    #         sess["messages"].append({"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error continuing: {e}", "ts": now_label()})
    #     st.rerun()

    # Show "Continue" only for the most recent incomplete assistant message
    last_incomplete_id = None
    for mm in reversed(sess.get("messages", [])):
        if mm.get("role") == "assistant" and needs_continue_flag(mm):
            last_incomplete_id = mm.get("id")
            break

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
                # Divider for threaded tutor parts
                if (msg.get("text") or "").lstrip().startswith("**Continued (Part "):
                    st.markdown("---")

                clean_answer, embedded_followups = split_answer_and_embedded_followups(text)

                st.markdown(clean_answer or text)
                st.markdown(f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>", unsafe_allow_html=True)

                followups = embedded_followups or (msg.get("followups") or [])
                if followups:
                    st.markdown("#### Suggested follow-ups")
                    for fu in followups:
                        href = fuq_href("learn", fu)
                        st.markdown(
                            f'<a href="{href}" target="_blank" style="text-decoration:none;">• {fu}</a>',
                            unsafe_allow_html=True,
                        )

                 # Only the latest incomplete assistant message gets the Continue button
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















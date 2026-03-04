

import os
import time
import re
from datetime import datetime
from typing import Any, Dict, Optional

import requests
import streamlit as st
from storage_sqlite import cleanup_empty_sessions, init_db, save_session, list_sessions, load_session, delete_session


st.write("RUNNING FILE:", __file__)



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



# def _overlap_dedupe_append(existing: str, chunk: str, max_window: int = 2500) -> str:
#     """
#     Stronger append logic for Continue:
#     - Detects short + mid-line overlaps (not only long exact matches)
#     - Normalizes whitespace for overlap comparison
#     - Removes repeated headers/bullets that restart the same section
#     - Keeps formatting of the final appended text readable
#     """
#     if not existing:
#         return (chunk or "").strip()

#     if not (chunk or "").strip():
#         return existing.strip()

#     ex = (existing or "").rstrip()
#     ch_raw = _strip_duplicate_chunk_prefix(chunk or "").lstrip()

#     if not ch_raw.strip():
#         return ex

#     # ---------- helpers ----------
#     def _norm(s: str) -> str:
#         # normalize for overlap matching only (do NOT return this to UI)
#         s = s.replace("\r\n", "\n").replace("\r", "\n")
#         s = s.replace("\t", " ")
#         s = re.sub(r"[ ]{2,}", " ", s)
#         s = re.sub(r"\n{3,}", "\n\n", s)
#         return s.strip()

#     def _is_header_line(line: str) -> bool:
#         t = (line or "").strip()
#         if not t:
#             return False
#         # markdown headers or "Title:" style
#         if t.startswith("#"):
#             return True
#         if t.endswith(":") and len(t) <= 80:
#             return True
#         # very short title-ish lines
#         if len(t) <= 60 and t.lower() == t and t.isalpha():
#             return True
#         return False

#     def _strip_replayed_opening_lines(ex_text: str, ch_text: str) -> str:
#         """
#         If the new chunk starts by replaying the last few lines (headers/bullets),
#         drop those opening lines from the chunk.
#         """
#         ex_lines = [ln.rstrip() for ln in ex_text.splitlines() if ln.strip()]
#         ch_lines = [ln.rstrip() for ln in ch_text.splitlines()]

#         # Compare against last N meaningful lines of existing
#         last = ex_lines[-12:] if len(ex_lines) >= 12 else ex_lines

#         # Remove leading empties first
#         while ch_lines and not ch_lines[0].strip():
#             ch_lines.pop(0)

#         # Try removing up to 6 opening lines if they match (or are near-match) to recent lines
#         removed_any = True
#         tries = 0
#         while removed_any and ch_lines and tries < 6:
#             removed_any = False
#             first = ch_lines[0].strip()
#             if not first:
#                 ch_lines.pop(0)
#                 removed_any = True
#                 tries += 1
#                 continue

#             # Exact match with any of last lines
#             if first in last:
#                 ch_lines.pop(0)
#                 removed_any = True
#                 tries += 1
#                 continue

#             # Header replay: chunk starts with same header-ish text
#             if _is_header_line(first):
#                 for ln in last[::-1]:
#                     if _is_header_line(ln) and _norm(ln).lower() == _norm(first).lower():
#                         ch_lines.pop(0)
#                         removed_any = True
#                         tries += 1
#                         break
#                 if removed_any:
#                     continue

#             # Bullet replay: "- X" vs "• X" vs "X" (same stem)
#             stem = re.sub(r"^[-*•\u2022]+\s*", "", first).strip()
#             if stem and len(stem) >= 18:
#                 for ln in last[::-1]:
#                     ln_stem = re.sub(r"^[-*•\u2022]+\s*", "", ln).strip()
#                     if _norm(ln_stem).lower().startswith(_norm(stem).lower()) or _norm(stem).lower().startswith(_norm(ln_stem).lower()):
#                         ch_lines.pop(0)
#                         removed_any = True
#                         tries += 1
#                         break

#         return "\n".join(ch_lines).lstrip()

#     # ---------- phase 1: strip obvious replay lines ----------
#     ch = _strip_replayed_opening_lines(ex, ch_raw)
#     if not ch.strip():
#         return ex

#     # ---------- phase 2: overlap match (supports shorter overlaps + mid-line) ----------
#     tail = ex[-max_window:]
#     head = ch[:max_window]

#     tail_n = _norm(tail)
#     head_n = _norm(head)

#     # Find the longest suffix(prefix) overlap on normalized strings
#     best = 0
#     max_k = min(len(tail_n), len(head_n))

#     # Allow short overlaps (mid-line splits) — start from ~40 chars
#     min_k = 40 if max_k >= 200 else 20

#     # scan increasing to get best (simple + stable)
#     for k in range(min_k, max_k + 1):
#         if tail_n[-k:] == head_n[:k]:
#             best = k

#     if best > 0:
#         # Map normalized overlap back to raw by trimming head using a safer heuristic:
#         # remove the first raw characters until normalized(head_raw_prefix) reaches the overlap.
#         target = head_n[:best]
#         cut = 0
#         acc = ""
#         for i, c in enumerate(head):
#             acc = _norm(head[: i + 1])
#             if acc.startswith(target) and len(acc) >= len(target):
#                 cut = i + 1
#                 break
#         if cut > 0:
#             ch = ch[cut:].lstrip()

#     # ---------- phase 3: last-line / first-line partial overlap ----------
#     # If last line of existing is a prefix of first line of chunk (or vice versa), trim it.
#     ex_last = (ex.splitlines()[-1] if ex.splitlines() else "").rstrip()
#     ch_first = (ch.splitlines()[0] if ch.splitlines() else "").lstrip()

#     ex_last_n = _norm(ex_last).lower()
#     ch_first_n = _norm(ch_first).lower()

#     if ex_last_n and ch_first_n:
#         if ch_first_n.startswith(ex_last_n) and len(ex_last_n) >= 12:
#             # drop the repeated prefix from the FIRST LINE only (preserve indentation)
#             ch_lines = ch.splitlines()
#             if ch_lines:
#                 first_raw = ch_lines[0]
#                 indent = first_raw[: len(first_raw) - len(first_raw.lstrip())]
#                 content = first_raw.lstrip()

#                 ex_last_clean = ex_last.strip()
#                 if content.lower().startswith(ex_last_clean.lower()):
#                     content = content[len(ex_last_clean):].lstrip()
#                     ch_lines[0] = indent + content
#                     ch = "\n".join(ch_lines).lstrip()

            
#         elif ex_last_n.startswith(ch_first_n) and len(ch_first_n) >= 12:
#             # chunk repeats a shorter fragment; drop first line entirely
#             ch_lines = ch.splitlines()
#             ch = "\n".join(ch_lines[1:]).lstrip()


 

    
#     # ---------- phase 4: word-fragment stitching ----------
#     ex_lines = ex.splitlines()
#     ex_last_line = (ex_lines[-1] if ex_lines else "")
#     ch_lines = ch.splitlines()

#     if ex_last_line and ch_lines:
#         first_line = ch_lines[0]
#         rest = ch_lines[1:]

#         # Case 1: hyphenated split (retrieval-aug + mented)
#         if ex_last_line.rstrip().endswith("-"):
#             stitched_last = ex_last_line.rstrip() + first_line.lstrip()
#             ex = ("\n".join(ex_lines[:-1]) + "\n" + stitched_last).rstrip()
#             ch = "\n".join(rest).lstrip()

#         # Case 2: plain word split without hyphen
#         elif ex_last_line[-1].isalnum() and first_line and first_line[0].isalnum():
#             stitched_last = ex_last_line + first_line
#             ex = ("\n".join(ex_lines[:-1]) + "\n" + stitched_last).rstrip()
#             ch = "\n".join(rest).lstrip()
   

    
    
    
#     # ---------- phase 5: punctuation + header cleanup ----------
#     lines = ch.splitlines()

#     # Remove lines that are just punctuation or leading comma fragments
#     cleaned = []
#     for ln in lines:
#         stripped = ln.strip()

#         # drop punctuation-only lines
#         if stripped in {",", ".", ";"}:
#             continue

#         # remove a leading ", " but KEEP indentation
#         if stripped.startswith(", "):
#             # preserve the original leading whitespace
#             indent = ln[: len(ln) - len(ln.lstrip())]
#             content = ln.lstrip()
#             if content.startswith(", "):
#                 content = content[2:]
#             ln = indent + content

#         # IMPORTANT: keep original ln (indentation preserved)
#         cleaned.append(ln)

#     ch = "\n".join(cleaned).lstrip()

#     # Remove duplicated header variants (case-insensitive)
#     ex_tail_lines = [l.strip().lower() for l in ex.splitlines()[-8:] if l.strip()]
#     ch_lines = ch.splitlines()
#     if ch_lines:
#         first = ch_lines[0].strip().lower()
#         if any(first.startswith(t) for t in ex_tail_lines):
#             ch = "\n".join(ch_lines[1:]).lstrip()
    
    
    
    
    
    
    
    
    
#     # Final join with clean spacing
#     return (ex.rstrip() + "\n\n" + ch.lstrip()).strip()

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
    # 1) If we already have a valid active session in memory, keep it
    if (
        st.session_state.learning_active_id
        and st.session_state.learning_active_id in st.session_state.learning_sessions
    ):
        return st.session_state.learning_active_id

    # 2) Otherwise, try to load the most recently-updated session from DB
    rows = list_sessions(limit=1)  # [(sid,title,created,updated)]
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
    return post_json("/interrogate", {"topic": topic}, timeout=120)


# =========================
# URL / Query routing
# =========================
qp = st.query_params
page_param = (qp.get("page") or "chat").lower()
learn_sid = qp.get("learn_sid")

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

        
        rows = list_sessions(limit=30)  # [(sid,title,created,updated),...]
        if rows:
            for sid, title, created_at, updated_at in rows:
                active = (sid == st.session_state.learning_active_id)
                dot = "🔵" if active else "⚪"
                label = (title or "Session").strip()
                st.markdown(f"- {dot} [{label}](?page=learn&learn_sid={sid})")
        else:
            st.markdown('<div class="small" style="color:var(--muted);">No sessions yet.</div>', unsafe_allow_html=True)

    
        if st.button("🗑️ Delete this session"):
            sid = st.session_state.learning_active_id
            if sid:
                delete_session(sid)
                # reset local state
                st.session_state.learning_sessions.pop(sid, None)
                st.session_state.learning_active_id = None
                start_new_learning_session()
                st.rerun()


# =========================
# Pages
# =========================
def page_new_chat() -> None:
    st.markdown('<div class="bigtitle">New Chat</div>', unsafe_allow_html=True)
    st.caption("InI Question Engine (v0): Interrogate generates a progressive question ladder. Answers will be on-click in the next step.")

    topic = st.text_input(
        "Topic",
        value=st.session_state.chat.get("topic", ""),
        placeholder="Type a topic (e.g., Artificial Intelligence, Data Science)...",
        key="chat_topic_input",
    )
    st.session_state.chat["topic"] = topic

    colA, colB = st.columns([1, 5])
    with colA:
        run = st.button("Interrogate")
    with colB:
        st.caption("Tip: backend must be running (FastAPI).")

    if run and topic.strip():
        try:
            data = fetch_interrogate(topic.strip())
            st.session_state.chat["interrogate"] = data
        except Exception as e:
            st.error(f"Error calling /interrogate: {e}")

    data = st.session_state.chat.get("interrogate")
    if isinstance(data, dict) and data.get("categories"):
        st.markdown("### Question Map")
        st.caption("Orientation → Foundations → Mechanisms → Methods/Tools → Applications → Pitfalls → Advanced/Future")

        # Show questions grouped by category (for now)
        cats = data.get("categories") or {}
        for cat, items in cats.items():
            if not items:
                continue
            with st.expander(cat, expanded=(cat in {"What", "Why"})):
                for it in items:
                    q = it.get("question", "").strip()
                    if q:
                        st.markdown(f"- {q}")



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
            try:
                _continue_one_chunk(sess, target_id)
            except Exception as e:
                sess["messages"].append(
                    {"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error continuing: {e}", "ts": now_label()}
                )

        st.session_state._uib_clear_next = True
        st.rerun()

    # 2) Normal path: treat as a new question
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
                "response_id": resp.get("response_id"),
                "continue_token": resp.get("continue_token"),
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

    # Handle Continue
    if st.session_state._continue_msg_id:
        msg_id = st.session_state._continue_msg_id
        st.session_state._continue_msg_id = None
        try:
            _continue_one_chunk(sess, msg_id)
        except Exception as e:
            sess["messages"].append({"id": f"e-{int(time.time())}", "role": "assistant", "text": f"Error continuing: {e}", "ts": now_label()})
        st.rerun()

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

                st.markdown(text)
                st.markdown(f"<div style='text-align:right; color:#6b7280; font-size:12px;'>{ts}</div>", unsafe_allow_html=True)

                # Only the latest incomplete assistant message gets the Continue button
                if needs_continue_flag(msg) and (msg.get("id") == last_incomplete_id):
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















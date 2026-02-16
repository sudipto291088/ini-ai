import hashlib
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import requests
import streamlit as st
import streamlit.components.v1 as components


# =========================
# Ship / Dev mode
# =========================
# IMPORTANT:
# - Set DEV_MODE=False before shipping so users never see API settings.
DEV_MODE = False


# =========================
# Page + Theme
# =========================
st.set_page_config(page_title="InI.ai", layout="wide")

st.markdown(
    """
<style>
/* Layout */
.block-container { padding-top: 1.05rem; padding-bottom: 2.2rem; max-width: 1240px; }
h1, h2, h3 { letter-spacing: -0.02em; }
label { font-weight: 650; }

/* Sidebar polish */
.badge {
  display: inline-block;
  padding: 0.18rem 0.55rem;
  border: 1px solid rgba(49,51,63,0.18);
  border-radius: 999px;
  font-size: 0.80rem;
  color: rgba(49,51,63,0.75);
  background: rgba(255,255,255,0.75);
}
.muted { color: rgba(49,51,63,0.75); }
.small { font-size: 0.9rem; }

/* Cards */
.card {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  background: rgba(255,255,255,0.75);
  word-break: normal !important;
  overflow-wrap: normal !important;
  hyphens: none !important;
}
.card * {
  word-break: normal !important;
  overflow-wrap: normal !important;
  hyphens: none !important;
}

/* Expander */
div[data-testid="stExpander"] details {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 14px;
  padding: 0.25rem 0.75rem;
  background: rgba(255,255,255,0.60);
}
div[data-testid="stExpander"] summary { font-weight: 650; }

/* Timestamp under messages */
.ts {
  margin-top: 0.15rem;
  font-size: 0.82rem;
  color: rgba(49,51,63,0.55);
}

/* Centered "Continue" as subtle see-more */
.center-link { text-align: center; margin-top: 0.35rem; margin-bottom: 0.75rem; }
.center-link button {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  color: rgba(49,51,63,0.72) !important;
  font-weight: 650 !important;
}
.center-link button:hover {
  text-decoration: underline;
  color: rgba(49,51,63,0.90) !important;
}

/* UIB wrapper */
.uib {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 18px;
  padding: 0.62rem 0.75rem 0.55rem 0.75rem;
  background: rgba(255,255,255,0.72);
}
.uib-help {
  margin-top: 0.35rem;
  color: rgba(49,51,63,0.60);
  font-size: 0.86rem;
}

/* Round icon buttons (nice, non-rudimentary) */
.roundbtn button {
  border-radius: 999px !important;
  width: 44px !important;
  height: 40px !important;
  padding: 0 !important;
  font-weight: 900 !important;
  border: 1px solid rgba(49,51,63,0.16) !important;
}

/* Arrow send button */
.sendbtn button {
  border-radius: 999px !important;
  width: 52px !important;
  height: 40px !important;
  padding: 0 !important;
  font-weight: 900 !important;
  border: 1px solid rgba(49,51,63,0.16) !important;
}

/* Small B button */
.bbtn button {
  border-radius: 999px !important;
  height: 40px !important;
  padding: 0 0.85rem !important;
  font-weight: 850 !important;
  border: 1px solid rgba(49,51,63,0.16) !important;
}

/* Remove extra whitespace at the top of chat messages */
div[data-testid="stChatMessage"] { margin-top: 0.25rem; margin-bottom: 0.25rem; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Defaults (hidden for users)
# =========================
DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_STUDY_PATH = "/study/ai"
DEFAULT_STUDY_PAYLOAD_KEY = "topic"


# =========================
# Helpers
# =========================
def safe_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def safe_post(api_base: str, path: str, payload: dict, timeout: int = 60):
    try:
        r = requests.post(f"{api_base}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def sanitize_for_display(text: str) -> str:
    """Keep content intact, remove only invisible garbage chars and normalize newlines."""
    if not isinstance(text, str):
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    invis = ["\u200b", "\ufeff", "\u00ad", "\u2060"]
    for ch in invis:
        t = t.replace(ch, "")
    return t.strip()


def strip_debug_lines(text: str) -> str:
    """
    Do NOT shorten answers. Only remove debug-only lines that pollute UI.
    We keep all actual content.
    """
    if not isinstance(text, str) or not text:
        return ""
    lines = text.splitlines()
    kept = []
    for ln in lines:
        if ln.strip().startswith("[LLM DEBUG]"):
            continue
        kept.append(ln)
    return "\n".join(kept).strip()


def fmt_ts(dt: datetime) -> str:
    # Example: Sun 06:16 PM
    return dt.strftime("%a %I:%M %p")


def tail_text(parts: list[str], max_chars: int = 1600) -> str:
    joined = "\n\n".join([p for p in parts if isinstance(p, str) and p.strip()])
    if not joined:
        return ""
    return joined[-max_chars:]


def fetch_answer(api_base: str, topic_text: str, question_text: str) -> Tuple[Optional[str], Optional[str]]:
    data, err = safe_post(
        api_base,
        "/answer",
        {"topic": topic_text, "question": question_text},
        timeout=180,
    )
    if err:
        return None, err
    if not isinstance(data, dict):
        return None, "Bad response from /answer"
    return (data.get("answer") or "").strip(), None


def fetch_study(api_base: str, study_path: str, payload_key: str, prompt: str):
    """
    Returns:
      answer_text (str), incomplete (bool), error (str|None)

    Continue should show ONLY when:
      - incomplete is explicitly true, OR
      - model emits explicit INCOMPLETE debug marker.
    """
    data, err = safe_post(
        api_base,
        study_path,
        {payload_key: prompt},
        timeout=240,
    )
    if err:
        return None, False, err
    if not isinstance(data, dict):
        return None, False, "Bad response from study endpoint"

    answer = (data.get("answer") or "").strip()
    incomplete = bool(data.get("incomplete", False))

    if isinstance(answer, str) and "[LLM DEBUG] INCOMPLETE" in answer:
        incomplete = True

    return answer, incomplete, None


def inject_floating_scroll_controls():
    """
    True floating Top/Bottom controls using fixed-position HTML + JS.
    (No Streamlit state needed.)
    """
    components.html(
        """
<style>
.floater {
  position: fixed;
  right: 18px;
  bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 999999;
}
.fbtn {
  width: 44px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(49,51,63,0.22);
  background: rgba(255,255,255,0.92);
  cursor: pointer;
  font-weight: 900;
  line-height: 40px;
  text-align: center;
  user-select: none;
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
}
.fbtn:hover { background: rgba(255,255,255,1.0); }
</style>

<div class="floater">
  <div class="fbtn" onclick="window.scrollTo({top: 0, behavior: 'smooth'});" title="Top">↑</div>
  <div class="fbtn" onclick="window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});" title="Bottom">↓</div>
</div>
""",
        height=0,
    )


# =========================
# Session State
# =========================
if "page" not in st.session_state:
    st.session_state.page = "New Chat"

# API config (dev-only UI; values still used internally)
if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE
if "study_path" not in st.session_state:
    st.session_state.study_path = DEFAULT_STUDY_PATH
if "study_payload_key" not in st.session_state:
    st.session_state.study_payload_key = DEFAULT_STUDY_PAYLOAD_KEY

# New Chat state
if "interrogate_data" not in st.session_state:
    st.session_state.interrogate_data = None
if "interrogate_err" not in st.session_state:
    st.session_state.interrogate_err = None

if "illustrate_data" not in st.session_state:
    st.session_state.illustrate_data = None
if "illustrate_err" not in st.session_state:
    st.session_state.illustrate_err = None

if "last_topic" not in st.session_state:
    st.session_state.last_topic = None
if "show_more" not in st.session_state:
    st.session_state.show_more = False
if "open_ids" not in st.session_state:
    st.session_state.open_ids = set()
if "viewed_ids" not in st.session_state:
    st.session_state.viewed_ids = set()
if "answer_cache" not in st.session_state:
    st.session_state.answer_cache = {}
if "new_chat_history" not in st.session_state:
    st.session_state.new_chat_history = []

# My Learning multi-session
# learning_sessions: dict[session_id] => {title, created_ts, messages, incomplete, last_prompt, draft, last_choice}
if "learning_sessions" not in st.session_state:
    st.session_state.learning_sessions: Dict[str, Dict[str, Any]] = {}

if "learning_active_id" not in st.session_state:
    st.session_state.learning_active_id: Optional[str] = None

if "learning_err" not in st.session_state:
    st.session_state.learning_err = None


def _first_keyword(text: str) -> str:
    t = (text or "").strip().split()
    if not t:
        return "AI"
    return t[0][:18]


def new_learning_session() -> str:
    sid = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + safe_key(str(datetime.now().timestamp()))[:8]
    now = datetime.now()
    st.session_state.learning_sessions[sid] = {
        "title": now.strftime("%m/%d %I:%M%p") + " • " + "AI",
        "created_ts": now.strftime("%Y-%m-%d %H:%M:%S"),
        "messages": [],  # list of {role, content, ts, meta}
        "incomplete": False,
        "last_prompt": "",
        "draft": "",
        "last_choice": "DEEP",  # not persisted across messages as mode; only informative
    }
    st.session_state.learning_active_id = sid
    return sid


def get_active_session() -> Dict[str, Any]:
    if (
        not st.session_state.learning_active_id
        or st.session_state.learning_active_id not in st.session_state.learning_sessions
    ):
        # Create first session silently
        new_learning_session()
    return st.session_state.learning_sessions[st.session_state.learning_active_id]


# =========================
# Sidebar
# =========================
st.sidebar.markdown("## InI.ai")
st.sidebar.markdown('<span class="badge">v0 • AI Tutor</span>', unsafe_allow_html=True)
now_str = datetime.now().strftime("%a, %b %d • %I:%M %p")
st.sidebar.markdown(f"<div class='muted small'>🕒 {now_str}</div>", unsafe_allow_html=True)
st.sidebar.divider()

nav = st.sidebar.radio(
    "Navigation",
    options=["New Chat", "My Learning", "New Project"],
    index=["New Chat", "My Learning", "New Project"].index(st.session_state.page),
    format_func=lambda x: "💬 New Chat" if x == "New Chat"
    else ("🎓 My Learning" if x == "My Learning" else "📁 New Project"),
)
st.session_state.page = nav

if st.session_state.page == "New Project":
    st.sidebar.info("Coming soon in v1.")

# Your Learning sessions only visible in My Learning
if st.session_state.page == "My Learning":
    st.sidebar.divider()
    st.sidebar.markdown("### Your Learning")

    # Ensure one session exists
    if len(st.session_state.learning_sessions) == 0:
        new_learning_session()

    items = list(st.session_state.learning_sessions.items())
    items.sort(key=lambda kv: kv[1].get("created_ts", ""), reverse=True)

    for sid, sess in items[:12]:
        label = sess.get("title", "Session")
        is_active = (sid == st.session_state.learning_active_id)
        btn_label = f"• {label}" if is_active else label
        if st.sidebar.button(btn_label, key=f"learn_sess_{sid}"):
            st.session_state.learning_active_id = sid
            st.session_state.learning_err = None
            st.rerun()

# Dev-only controls
if DEV_MODE:
    st.sidebar.divider()
    with st.sidebar.expander("Developer settings", expanded=False):
        st.session_state.api_base = st.text_input("API base", st.session_state.api_base)
        st.session_state.study_path = st.text_input("Study path", st.session_state.study_path)
        st.session_state.study_payload_key = st.text_input("Study payload key", st.session_state.study_payload_key)
        st.caption("Tip: open FastAPI docs at /docs to confirm Study route + body.")

# New Chat history (kept)
st.sidebar.divider()
st.sidebar.markdown("### Session History")
if len(st.session_state.new_chat_history) == 0:
    st.sidebar.caption("No New Chat history yet.")
else:
    for i, item in enumerate(reversed(st.session_state.new_chat_history[-8:]), start=1):
        label = f"{item.get('ts','')} • {item.get('topic','')[:24]}"
        if st.sidebar.button(label, key=f"hist_{i}_{safe_key(label)}"):
            st.session_state.interrogate_data = item.get("interrogate_data")
            st.session_state.illustrate_data = item.get("illustrate_data")
            st.session_state.interrogate_err = None
            st.session_state.illustrate_err = None
            st.session_state.last_topic = (item.get("topic") or "").strip().lower()
            st.session_state.show_more = False
            st.session_state.open_ids = set()
            st.session_state.viewed_ids = set()
            st.session_state.answer_cache = {}
            st.rerun()


# =========================
# Page: New Chat (stable for now)
# =========================
def render_new_chat():
    st.title("InI.ai")
    st.markdown(
        "<div class='muted'>New Chat stays stable for now; we’ll modernize it after My Learning is perfect.</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    topic = st.text_area("Topic", placeholder="Type a topic…", height=110)

    c1, c2 = st.columns([1, 1])
    with c1:
        interrogate_clicked = st.button("Interrogate", use_container_width=True)
    with c2:
        illustrate_clicked = st.button("Illustrate", use_container_width=True)

    api_base = st.session_state.api_base

    if interrogate_clicked and topic.strip():
        with st.spinner("Generating structured questions…"):
            data, err = safe_post(api_base, "/interrogate", {"topic": topic}, timeout=240)
        st.session_state.interrogate_data = data
        st.session_state.interrogate_err = err

        if data and not err:
            st.session_state.new_chat_history.append(
                {
                    "topic": topic.strip(),
                    "interrogate_data": data,
                    "illustrate_data": st.session_state.illustrate_data,
                    "ts": datetime.now().strftime("%m/%d %I:%M%p"),
                }
            )

            clean = data.get("topic", "").strip().lower()
            if st.session_state.last_topic != clean:
                st.session_state.last_topic = clean
                st.session_state.show_more = False
                st.session_state.open_ids = set()
                st.session_state.viewed_ids = set()
                st.session_state.answer_cache = {}

    if illustrate_clicked and topic.strip():
        with st.spinner("Creating a clear illustration…"):
            data, err = safe_post(api_base, "/illustrate", {"topic": topic}, timeout=240)
        st.session_state.illustrate_data = data
        st.session_state.illustrate_err = err

        if data and not err:
            st.session_state.new_chat_history.append(
                {
                    "topic": topic.strip(),
                    "interrogate_data": st.session_state.interrogate_data,
                    "illustrate_data": data,
                    "ts": datetime.now().strftime("%m/%d %I:%M%p"),
                }
            )

    idata = st.session_state.interrogate_data
    ierr = st.session_state.interrogate_err

    if ierr:
        st.error(ierr)

    if idata and not ierr:
        st.markdown("---")
        st.subheader(f"Interrogating: {idata.get('topic','')}")
        for line in idata.get("summary", []):
            st.write(line)

        categories = idata.get("categories", {}) or {}

        flat = []
        for cat, items in categories.items():
            if isinstance(items, list):
                for qa in items:
                    if qa.get("question"):
                        flat.append((cat, qa))

        if st.button("Clear opened answers", key="clear_opened"):
            st.session_state.open_ids = set()
            st.rerun()

        if not st.session_state.show_more:
            st.markdown("### Top most questions")
            for idx, (cat, qa) in enumerate(flat[:8], start=1):
                qid = qa.get("id") or f"{cat}_{safe_key(qa.get('question',''))}"
                q = qa["question"]

                visited = qid in st.session_state.viewed_ids
                dot = "🔵" if visited else "⚪"

                if st.button(f"{dot} {q}", key=f"top_{idx}_{safe_key(qid)}"):
                    if qid not in st.session_state.answer_cache:
                        with st.spinner("Generating answer (first time may take ~30s)…"):
                            ans, err = fetch_answer(api_base, idata.get("topic", ""), q)
                        st.session_state.answer_cache[qid] = sanitize_for_display(ans or "") if not err else f"Error: {err}"

                    st.session_state.open_ids.add(qid)
                    st.session_state.viewed_ids.add(qid)
                    st.rerun()

                if qid in st.session_state.open_ids:
                    with st.expander("", expanded=True):
                        st.write(st.session_state.answer_cache.get(qid, "Loading..."))

            if st.button("See more…", key="see_more_btn"):
                st.session_state.show_more = True
                st.rerun()
        else:
            st.markdown("### All questions")
            for cat, items in categories.items():
                st.markdown(f"#### {cat}")
                if not isinstance(items, list) or len(items) == 0:
                    continue

                for qa in items:
                    if not qa.get("question"):
                        continue
                    qid = qa.get("id") or f"{cat}_{safe_key(qa.get('question',''))}"
                    q = qa["question"]

                    visited = qid in st.session_state.viewed_ids
                    dot = "🔵" if visited else "⚪"

                    if st.button(f"{dot} {q}", key=f"all_{safe_key(qid)}"):
                        if qid not in st.session_state.answer_cache:
                            with st.spinner("Generating answer (first time may take ~30s)…"):
                                ans, err = fetch_answer(api_base, idata.get("topic", ""), q)
                            st.session_state.answer_cache[qid] = sanitize_for_display(ans or "") if not err else f"Error: {err}"

                        st.session_state.open_ids.add(qid)
                        st.session_state.viewed_ids.add(qid)
                        st.rerun()

                    if qid in st.session_state.open_ids:
                        with st.expander("", expanded=True):
                            st.write(st.session_state.answer_cache.get(qid, "Loading..."))

            if st.button("Back", key="back_btn"):
                st.session_state.show_more = False
                st.rerun()

    ldata = st.session_state.illustrate_data
    lerr = st.session_state.illustrate_err
    if lerr:
        st.error(lerr)

    if ldata and not lerr:
        st.markdown("---")
        st.subheader(f"Illustrating: {ldata.get('topic','')}")
        for k, v in (ldata.get("illustrations") or {}).items():
            st.markdown(f"**{k.replace('_',' ').title()}**")
            st.write(v)


# =========================
# Page: My Learning
# =========================
def render_learning_transcript(sess: Dict[str, Any]):
    for msg in sess.get("messages", []):
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        ts = msg.get("ts", "")

        with st.chat_message(role):
            st.markdown(content if isinstance(content, str) else "")
            if ts:
                st.markdown(f"<div class='ts'>{ts}</div>", unsafe_allow_html=True)


def build_prompt(user_prompt: str, mode: str) -> str:
    user_prompt = (user_prompt or "").strip()

    if mode == "HIGH":
        return f"{user_prompt}\n\nPATH=HIGH"

    if mode == "QUIZ":
        return (
            f"{user_prompt}\n\n"
            "PATH=HIGH\n\n"
            "MODE=QUIZ\n"
            "Create a short interactive quiz based on the user's topic.\n"
            "- Ask 5 questions.\n"
            "- Mix: 2 conceptual, 2 applied, 1 misconception/trick.\n"
            "- Do NOT provide answers yet.\n"
            "- End by asking the user to reply with answers.\n"
        )

    # DEEP default
    return f"{user_prompt}\n\nPATH=DEEP"


def ensure_session_title(sess: Dict[str, Any], first_user_prompt: str):
    # Title = timestamp + first keyword
    if sess.get("messages") and len(sess["messages"]) >= 1:
        # Only set title if it still has placeholder "AI"
        title = sess.get("title", "")
        if "• AI" in title or title.strip().endswith("AI"):
            kw = _first_keyword(first_user_prompt)
            # keep the left timestamp part
            left = title.split("•")[0].strip()
            sess["title"] = f"{left} • {kw}"


def send_learning(sess: Dict[str, Any], prompt: str, mode: str):
    api_base = st.session_state.api_base
    study_path = st.session_state.study_path
    payload_key = st.session_state.study_payload_key

    user_prompt = (prompt or "").strip()
    if not user_prompt:
        return

    st.session_state.learning_err = None

    # Store user message (with timestamp)
    sess["messages"].append(
        {"role": "user", "content": user_prompt, "ts": fmt_ts(datetime.now()), "meta": {"mode": mode}}
    )
    ensure_session_title(sess, user_prompt)

    # Track last prompt for B and continuation
    sess["last_prompt"] = user_prompt
    sess["last_choice"] = mode

    with st.spinner("Tutoring… (deep answers may take ~20–40s)"):
        ans, inc, err = fetch_study(api_base, study_path, payload_key, build_prompt(user_prompt, mode))

    st.session_state.learning_err = err

    if ans:
        clean = strip_debug_lines(sanitize_for_display(ans))
        sess["messages"].append(
            {"role": "assistant", "content": clean, "ts": fmt_ts(datetime.now()), "meta": {"mode": mode}}
        )

    sess["incomplete"] = bool(inc)


def render_continue_if_needed(sess: Dict[str, Any]):
    if not sess.get("incomplete", False):
        return

    st.markdown("<div class='center-link'>", unsafe_allow_html=True)
    cont = st.button("Continue ⏭", key=f"continue_{st.session_state.learning_active_id}")
    st.markdown("</div>", unsafe_allow_html=True)

    if not cont:
        return

    api_base = st.session_state.api_base
    study_path = st.session_state.study_path
    payload_key = st.session_state.study_payload_key

    assistant_parts = [
        m.get("content", "")
        for m in sess.get("messages", [])
        if m.get("role") == "assistant"
    ]
    tail = tail_text(assistant_parts, max_chars=1600)

    continuation_prompt = (
        (sess.get("last_prompt", "") or "")
        + "\n\n"
        + "CONTEXT (last part shown to the user):\n"
        + tail
        + "\n\n"
        + "Continue EXACTLY from the end of the context above. "
          "Do NOT repeat earlier content. "
          "Preserve clean Markdown structure and indentation. "
          "End naturally when complete."
    )

    with st.spinner("Continuing…"):
        ans2, inc2, err2 = fetch_study(api_base, study_path, payload_key, continuation_prompt)

    st.session_state.learning_err = err2
    if ans2:
        clean2 = strip_debug_lines(sanitize_for_display(ans2))
        sess["messages"].append(
            {"role": "assistant", "content": clean2, "ts": fmt_ts(datetime.now()), "meta": {}}
        )
    sess["incomplete"] = bool(inc2)
    st.rerun()


def render_uib(sess: Dict[str, Any], position: str):
    """
    Clean UIB:
      - Enter key / Arrow ➤ submits DEEP by default
      - ◎ submits HIGH
      - ? submits QUIZ
      - B brings last prompt back into the input for editing
    """
    if position == "top":
        st.markdown("### My Learning")
        st.markdown("<div class='muted'>Ask about AI. ➤ Deep • ◎ Overview • ? Quiz</div>", unsafe_allow_html=True)

    # UIB wrapper
    st.markdown("<div class='uib'>", unsafe_allow_html=True)

    # Single-row UIB form
    with st.form(key=f"uib_{position}_{st.session_state.learning_active_id}", clear_on_submit=False):
        cols = st.columns([0.72, 0.07, 0.07, 0.07, 0.07])

        with cols[0]:
            sess["draft"] = st.text_input(
                "Ask about AI",
                value=sess.get("draft", ""),
                placeholder="Type your topic/question…",
                label_visibility="collapsed",
            )

        with cols[1]:
            st.markdown("<div class='roundbtn'>", unsafe_allow_html=True)
            hlo = st.form_submit_button("◎")
            st.markdown("</div>", unsafe_allow_html=True)

        with cols[2]:
            st.markdown("<div class='roundbtn'>", unsafe_allow_html=True)
            quiz = st.form_submit_button("?")
            st.markdown("</div>", unsafe_allow_html=True)

        with cols[3]:
            st.markdown("<div class='sendbtn'>", unsafe_allow_html=True)
            deep = st.form_submit_button("➤")
            st.markdown("</div>", unsafe_allow_html=True)

        with cols[4]:
            # B is not a submit; handled below as regular button outside form
            st.markdown("<div class='bbtn'>", unsafe_allow_html=True)
            b_placeholder = st.form_submit_button("B")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Interpret submission.
    # IMPORTANT: we keep B inside the form for consistent layout, but treat it as a "non-send" action.
    drafted = (sess.get("draft", "") or "").strip()

    if b_placeholder:
        # Bring back last prompt (or keep current draft if none)
        last = (sess.get("last_prompt", "") or "").strip()
        if last:
            sess["draft"] = last
        st.rerun()

    if hlo and drafted:
        send_learning(sess, drafted, "HIGH")
        sess["draft"] = ""
        st.rerun()

    if quiz and drafted:
        send_learning(sess, drafted, "QUIZ")
        sess["draft"] = ""
        st.rerun()

    if deep and drafted:
        send_learning(sess, drafted, "DEEP")
        sess["draft"] = ""
        st.rerun()

    st.markdown("<div class='uib-help'>➤ Deep (default) • ◎ High-level overview • ? Quiz • B = edit last prompt</div>", unsafe_allow_html=True)


def render_my_learning():
    # True floating Top/Bottom
    inject_floating_scroll_controls()

    sess = get_active_session()

    if st.session_state.learning_err:
        st.error(st.session_state.learning_err)

    # Landing: UIB at top
    if len(sess.get("messages", [])) == 0:
        render_uib(sess, position="top")
        return

    # Ongoing: transcript + continue + UIB bottom
    render_learning_transcript(sess)
    render_continue_if_needed(sess)
    render_uib(sess, position="bottom")


# =========================
# Router
# =========================
if st.session_state.page == "New Chat":
    render_new_chat()
elif st.session_state.page == "My Learning":
    render_my_learning()
else:
    st.title("New Project")
    st.info("Coming soon in v1.")

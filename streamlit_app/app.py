import hashlib
from datetime import datetime

import requests
import streamlit as st


# =========================
# Page + Theme
# =========================
st.set_page_config(page_title="InI.ai", layout="wide")

st.markdown(
    """
<style>
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1240px; }
h1, h2, h3 { letter-spacing: -0.02em; }

.badge {
  display: inline-block;
  padding: 0.18rem 0.55rem;
  border: 1px solid rgba(49,51,63,0.18);
  border-radius: 999px;
  font-size: 0.8rem;
  color: rgba(49,51,63,0.75);
  background: rgba(255,255,255,0.75);
}

.muted { color: rgba(49,51,63,0.75); }
.small { font-size: 0.9rem; }

.card {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  background: rgba(255,255,255,0.75);
  /* Prevent ugly mid-word wraps like "halluc / inations" */
  word-break: normal !important;
  overflow-wrap: normal !important;
  hyphens: none !important;
}

.card * {
  word-break: normal !important;
  overflow-wrap: normal !important;
  hyphens: none !important;
}

div[data-testid="stExpander"] details {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 14px;
  padding: 0.25rem 0.75rem;
  background: rgba(255,255,255,0.60);
}

div[data-testid="stExpander"] summary { font-weight: 650; }
label { font-weight: 650; }

/* Centered "See more" style button */
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
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Defaults
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


def qa_id(qa: dict, prefix: str):
    if qa.get("id"):
        return str(qa["id"])
    return f"{prefix}_{safe_key(qa.get('question',''))}"


def fetch_answer(api_base: str, topic_text: str, question_text: str):
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
    data, err = safe_post(
        api_base,
        study_path,
        {payload_key: prompt},
        timeout=240,
    )
    if err:
        return None, err
    if not isinstance(data, dict):
        return None, "Bad response from study endpoint"
    return (data.get("answer") or "").strip(), None


def tail_text(parts: list[str], max_chars: int = 1200) -> str:
    joined = "\n\n".join([p for p in parts if isinstance(p, str) and p.strip()])
    if not joined:
        return ""
    return joined[-max_chars:]


def sanitize_for_display(text: str) -> str:
    """
    Remove invisible characters that can cause mid-word wrap glitches:
    - zero-width space, BOM, soft hyphen
    """
    if not isinstance(text, str):
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")

    # Invisible / problematic wrap chars
    invis = [
        "\u200b",  # zero-width space
        "\ufeff",  # BOM
        "\u00ad",  # soft hyphen
        "\u2060",  # word joiner
    ]
    for ch in invis:
        t = t.replace(ch, "")

    return t.strip()


# =========================
# Session State
# =========================
if "page" not in st.session_state:
    st.session_state.page = "New Chat"

if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE
if "study_path" not in st.session_state:
    st.session_state.study_path = DEFAULT_STUDY_PATH
if "study_payload_key" not in st.session_state:
    st.session_state.study_payload_key = DEFAULT_STUDY_PAYLOAD_KEY

# Chat state
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

# Learning state
if "learning_prompt" not in st.session_state:
    st.session_state.learning_prompt = ""
if "learning_err" not in st.session_state:
    st.session_state.learning_err = None
if "learning_parts" not in st.session_state:
    st.session_state.learning_parts = []
if "learning_last_prompt" not in st.session_state:
    st.session_state.learning_last_prompt = ""


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

st.sidebar.divider()
st.sidebar.markdown("### API Settings")
st.session_state.api_base = st.sidebar.text_input("API base", st.session_state.api_base)
st.session_state.study_path = st.sidebar.text_input("Study path", st.session_state.study_path)
st.session_state.study_payload_key = st.sidebar.text_input("Study payload key", st.session_state.study_payload_key)
st.sidebar.caption("Tip: open FastAPI docs at /docs to confirm Study route + body.")


# =========================
# Page: New Chat
# =========================
def render_new_chat():
    st.title("InI.ai")
    st.markdown(
        "<div class='muted'>Interrogate → get the right questions. Click a question → generate a research-grade answer (cached).</div>",
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
                qid = qa_id(qa, cat.lower().replace(" ", "_"))
                q = qa["question"]

                visited = qid in st.session_state.viewed_ids
                dot = "🔵" if visited else "⚪"

                if st.button(f"{dot} {q}", key=f"top_{idx}_{safe_key(qid)}"):
                    if qid not in st.session_state.answer_cache:
                        with st.spinner("Generating answer (first time may take ~30s)…"):
                            ans, err = fetch_answer(api_base, idata.get("topic", ""), q)
                        if err:
                            st.session_state.answer_cache[qid] = f"Error: {err}"
                        else:
                            st.session_state.answer_cache[qid] = sanitize_for_display(ans) or "(No answer returned.)"

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

                    qid = qa_id(qa, cat.lower().replace(" ", "_"))
                    q = qa["question"]

                    visited = qid in st.session_state.viewed_ids
                    dot = "🔵" if visited else "⚪"

                    if st.button(f"{dot} {q}", key=f"all_{safe_key(qid)}"):
                        if qid not in st.session_state.answer_cache:
                            with st.spinner("Generating answer (first time may take ~30s)…"):
                                ans, err = fetch_answer(api_base, idata.get("topic", ""), q)
                            if err:
                                st.session_state.answer_cache[qid] = f"Error: {err}"
                            else:
                                st.session_state.answer_cache[qid] = sanitize_for_display(ans) or "(No answer returned.)"

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
def render_my_learning():
    st.title("My Learning")
    st.markdown(
        "<div class='muted'>AI Tutor (v0): Ask anything about AI. Use ⏎ to submit.</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    prompt = st.text_input(
        "Ask about AI",
        value=st.session_state.learning_prompt,
        placeholder="e.g., Explain AI from classical to agents with examples",
        key="learning_input",
    )

    cols = st.columns([0.72, 0.14, 0.14])
    with cols[0]:
        st.caption("Tip: shorter prompts respond faster. deeper prompts give deeper answers.")
    with cols[1]:
        go = st.button("⏎", help="Submit", use_container_width=True)
    with cols[2]:
        clear = st.button("Clear", help="Clear this tutor session", use_container_width=True)

    if clear:
        st.session_state.learning_prompt = ""
        st.session_state.learning_err = None
        st.session_state.learning_parts = []
        st.session_state.learning_last_prompt = ""
        st.rerun()

    api_base = st.session_state.api_base
    study_path = st.session_state.study_path
    payload_key = st.session_state.study_payload_key

    if go and prompt.strip():
        st.session_state.learning_prompt = prompt
        st.session_state.learning_err = None
        st.session_state.learning_parts = []
        st.session_state.learning_last_prompt = prompt

        with st.spinner("Tutoring… (may take ~30s)"):
            ans, err = fetch_study(api_base, study_path, payload_key, prompt)

        st.session_state.learning_err = err
        if ans:
            st.session_state.learning_parts.append(sanitize_for_display(ans))
        st.rerun()

    if st.session_state.learning_err:
        st.error(st.session_state.learning_err)

    if len(st.session_state.learning_parts) > 0:
        st.markdown("---")
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        full_text = "\n\n".join(
            [p for p in st.session_state.learning_parts if isinstance(p, str) and p.strip()]
        )
        # Use markdown for proper bullets/indentation; CSS prevents mid-word wrap glitches.
        st.markdown(full_text)

        st.markdown("</div>", unsafe_allow_html=True)

        # Centered "Continue" as subtle text
        st.write("")
        left, mid, right = st.columns([1, 1, 1])
        with mid:
            st.markdown("<div class='center-link'>", unsafe_allow_html=True)
            cont = st.button("Continue ⏭", key="continue_link")
            st.markdown("</div>", unsafe_allow_html=True)

        if cont:
            tail = tail_text(st.session_state.learning_parts, max_chars=1200)

            continuation_prompt = (
                st.session_state.learning_last_prompt
                + "\n\n"
                + "CONTEXT (last part shown to the user):\n"
                + tail
                + "\n\n"
                + "Continue EXACTLY from the end of the context above. "
                  "Do NOT repeat earlier content. "
                  "Do NOT ask the user questions. "
                  "Do NOT include meta commentary. "
                  "Preserve clean Markdown structure and indentation. "
                  "Just continue with the next sections in the same style."
            )

            with st.spinner("Continuing…"):
                ans2, err2 = fetch_study(api_base, study_path, payload_key, continuation_prompt)

            st.session_state.learning_err = err2
            if ans2:
                st.session_state.learning_parts.append(sanitize_for_display(ans2))
            st.rerun()


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

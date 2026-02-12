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
/* Layout */
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1240px; }
h1, h2, h3 { letter-spacing: -0.02em; }

/* Subtle badge */
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
}

div[data-testid="stExpander"] details {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 14px;
  padding: 0.25rem 0.75rem;
  background: rgba(255,255,255,0.60);
}

div[data-testid="stExpander"] summary { font-weight: 650; }
label { font-weight: 650; }

</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Defaults (safe)
# =========================
DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_STUDY_PATH = "/study/ai"          # can override in sidebar
DEFAULT_STUDY_PAYLOAD_KEY = "topic"       # can override in sidebar


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
        timeout=120,
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
        timeout=180,
    )
    if err:
        return None, err
    if not isinstance(data, dict):
        return None, "Bad response from study endpoint"
    return (data.get("answer") or "").strip(), None


# =========================
# Session State
# =========================
if "page" not in st.session_state:
    st.session_state.page = "New Chat"  # default landing page

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

# Learning (Tutor) state
if "learning_prompt" not in st.session_state:
    st.session_state.learning_prompt = ""
if "learning_answer" not in st.session_state:
    st.session_state.learning_answer = ""
if "learning_err" not in st.session_state:
    st.session_state.learning_err = None


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

    # Interrogate: fetch
    if interrogate_clicked and topic.strip():
        with st.spinner("Generating structured questions…"):
            data, err = safe_post(api_base, "/interrogate", {"topic": topic}, timeout=180)
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

    # Illustrate: fetch
    if illustrate_clicked and topic.strip():
        with st.spinner("Creating a clear illustration…"):
            data, err = safe_post(api_base, "/illustrate", {"topic": topic}, timeout=180)
        st.session_state.illustrate_data = data
        st.session_state.illustrate_err = err

    # Interrogate: render
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

        # Flatten questions (do NOT require answer)
        flat = []
        for cat, items in categories.items():
            if isinstance(items, list):
                for qa in items:
                    if qa.get("question"):
                        flat.append((cat, qa))

        if st.button("Clear opened answers", key="clear_opened"):
            st.session_state.open_ids = set()
            st.rerun()

        # Top view
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
                            st.session_state.answer_cache[qid] = ans or "(No answer returned.)"

                    st.session_state.open_ids.add(qid)
                    st.session_state.viewed_ids.add(qid)
                    st.rerun()

                if qid in st.session_state.open_ids:
                    with st.expander("", expanded=True):
                        st.write(st.session_state.answer_cache.get(qid, "Loading..."))

            if st.button("See more…", key="see_more_btn"):
                st.session_state.show_more = True
                st.rerun()

        # All view
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
                                st.session_state.answer_cache[qid] = ans or "(No answer returned.)"

                        st.session_state.open_ids.add(qid)
                        st.session_state.viewed_ids.add(qid)
                        st.rerun()

                    if qid in st.session_state.open_ids:
                        with st.expander("", expanded=True):
                            st.write(st.session_state.answer_cache.get(qid, "Loading..."))

            if st.button("Back", key="back_btn"):
                st.session_state.show_more = False
                st.rerun()

    # Illustrate: render
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
# Page: My Learning (AI Tutor)
# =========================
def render_my_learning():
    st.title("My Learning")
    st.markdown(
        "<div class='muted'>AI Tutor (v0): Ask anything about AI. Use ⏎ to submit. (No Interrogate/Illustrate buttons here.)</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    prompt = st.text_input(
        "Ask about AI",
        value=st.session_state.learning_prompt,
        placeholder="e.g., Explain supervised vs unsupervised learning with examples",
        key="learning_input",
    )

    cols = st.columns([0.86, 0.14])
    with cols[0]:
        st.caption("Tip: shorter prompts respond faster. deeper prompts give deeper answers.")
    with cols[1]:
        go = st.button("⏎", help="Submit", use_container_width=True)

    if go and prompt.strip():
        st.session_state.learning_prompt = prompt
        st.session_state.learning_err = None
        st.session_state.learning_answer = ""

        api_base = st.session_state.api_base
        study_path = st.session_state.study_path
        payload_key = st.session_state.study_payload_key

        with st.spinner("Tutoring… (first time may take ~30s)"):
            ans, err = fetch_study(api_base, study_path, payload_key, prompt)

        st.session_state.learning_err = err
        st.session_state.learning_answer = ans or ""

    if st.session_state.learning_err:
        st.error(st.session_state.learning_err)

    if st.session_state.learning_answer:
        st.markdown("---")
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write(st.session_state.learning_answer)
        st.markdown("</div>", unsafe_allow_html=True)


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

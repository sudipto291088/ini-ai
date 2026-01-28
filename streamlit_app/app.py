import hashlib
import streamlit as st
import requests

st.set_page_config(page_title="InI.ai", layout="centered")

st.markdown("""
<style>
/* Slightly tighter spacing */
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

/* Make expanders look like “answer cards” */
div[data-testid="stExpander"] details {
  border: 1px solid rgba(49,51,63,0.15);
  border-radius: 12px;
  padding: 0.25rem 0.75rem;
  background: rgba(255,255,255,0.55);
}

/* Make expander header text a bit stronger */
div[data-testid="stExpander"] summary {
  font-weight: 650;
}

/* Make topic input label lighter */
label { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

API_BASE = "http://127.0.0.1:8000"


# ---------------- Helpers ----------------
def safe_post(path: str, payload: dict, timeout: int = 10):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def safe_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def qa_id(qa: dict, prefix: str):
    if qa.get("id"):
        return str(qa["id"])
    return f"{prefix}_{safe_key(qa.get('question',''))}"


# ---------------- State ----------------
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

# Var A state
if "open_ids" not in st.session_state:
    st.session_state.open_ids = set()

if "viewed_ids" not in st.session_state:
    st.session_state.viewed_ids = set()


# ---------------- UI: Home ----------------
st.title("InI.ai")

topic = st.text_area(
    "Topic",
    placeholder="Type your message here…",
    height=110
)

c1, c2 = st.columns(2)
with c1:
    interrogate_clicked = st.button("Interrogate")
with c2:
    illustrate_clicked = st.button("Illustrate")


# ---------------- Interrogate: fetch ----------------
if interrogate_clicked and topic.strip():
    data, err = safe_post("/interrogate", {"topic": topic})
    st.session_state.interrogate_data = data
    st.session_state.interrogate_err = err

    if data and not err:
        clean = data.get("topic", "").strip().lower()
        if st.session_state.last_topic != clean:
            st.session_state.last_topic = clean
            st.session_state.show_more = False
            st.session_state.open_ids = set()
            st.session_state.viewed_ids = set()


# ---------------- Illustrate: fetch ----------------
if illustrate_clicked and topic.strip():
    data, err = safe_post("/illustrate", {"topic": topic})
    st.session_state.illustrate_data = data
    st.session_state.illustrate_err = err


# ---------------- Interrogate: render ----------------
idata = st.session_state.interrogate_data
ierr = st.session_state.interrogate_err

if ierr:
    st.error(ierr)

if idata and not ierr:
    st.subheader(f"Interrogating: {idata.get('topic','')}")

    # short orientation
    for line in idata.get("summary", []):
        st.write(line)

    categories = idata.get("categories", {}) or {}

    # flatten questions
    flat = []
    for cat, items in categories.items():
        if isinstance(items, list):
            for qa in items:
                if qa.get("question") and qa.get("answer"):
                    flat.append((cat, qa))

    # ONE clear button (works in both views)
    if st.button("Clear opened answers", key="clear_opened"):
        st.session_state.open_ids = set()
        st.rerun()

    # -------- Top 7 --------
    if not st.session_state.show_more:
        st.markdown("### Top most questions")

        for idx, (cat, qa) in enumerate(flat[:7], start=1):
            qid = qa_id(qa, cat.lower().replace(" ", "_"))
            q = qa["question"]
            a = qa["answer"]

            visited = qid in st.session_state.viewed_ids
            dot = "🔵" if visited else "⚪"

            if st.button(f"{dot} {q}", key=f"top_{idx}_{safe_key(qid)}"):
                if qid in st.session_state.open_ids:
                    st.session_state.open_ids.remove(qid)
                else:
                    st.session_state.open_ids.add(qid)
                    st.session_state.viewed_ids.add(qid)
                st.rerun()

            # answer directly below the question
            if qid in st.session_state.open_ids:
                with st.expander("", expanded=True):
                    st.write(a)

        if st.button("See more…", key="see_more_btn"):
            st.session_state.show_more = True
            st.rerun()

    # -------- All questions --------
    else:
        st.markdown("### All questions")

        for cat, items in categories.items():
            st.markdown(f"#### {cat}")
            for qa in items:
                if not qa.get("question") or not qa.get("answer"):
                    continue

                qid = qa_id(qa, cat.lower().replace(" ", "_"))
                q = qa["question"]
                a = qa["answer"]

                visited = qid in st.session_state.viewed_ids
                dot = "🔵" if visited else "⚪"

                if st.button(f"{dot} {q}", key=f"all_{safe_key(qid)}"):
                    if qid in st.session_state.open_ids:
                        st.session_state.open_ids.remove(qid)
                    else:
                        st.session_state.open_ids.add(qid)
                        st.session_state.viewed_ids.add(qid)
                    st.rerun()

                if qid in st.session_state.open_ids:
                    with st.expander("", expanded=True):
                        st.write(a)

        if st.button("Back", key="back_btn"):
            st.session_state.show_more = False
            st.rerun()


# ---------------- Illustrate: render ----------------
ldata = st.session_state.illustrate_data
lerr = st.session_state.illustrate_err

if lerr:
    st.error(lerr)

if ldata and not lerr:
    st.subheader(f"Illustrating: {ldata.get('topic','')}")
    for k, v in (ldata.get("illustrations") or {}).items():
        st.markdown(f"**{k.replace('_',' ').title()}**")
        st.write(v)

import json
import streamlit as st
import requests



st.set_page_config(page_title="InI.ai", layout="centered")



API_BASE = "http://127.0.0.1:8000"

def safe_post(path: str, payload: dict, timeout: int = 10):
    url = f"{API_BASE}{path}"
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        # Raise HTTP error codes (400/500) as exceptions
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.Timeout:
        return None, f"Timeout: backend took too long at {url}"
    except requests.exceptions.ConnectionError:
        return None, f"ConnectionError: backend not reachable at {url}. Is uvicorn running?"
    except requests.exceptions.HTTPError:
        # show response body for debugging
        body = r.text if "r" in locals() else ""
        return None, f"HTTPError {getattr(r, 'status_code', '')}: {body}"
    except Exception as e:
        return None, f"Unexpected error: {e}"





with st.sidebar:
    st.markdown("## Diagnostics")
    if st.button("Check backend /health"):
        try:
            hr = requests.get(f"{API_BASE}/health", timeout=5)
            st.write("Status code:", hr.status_code)
            st.json(hr.json())
        except Exception as e:
            st.error(f"Health check failed: {e}")
    show_raw = st.checkbox("Show raw JSON", value=False)





st.markdown(
    """
    <style>
    /* Center the main block and limit its width */
    section.main > div {
        max-width: 820px;
        margin: 0 auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)



st.markdown(
    """
    <style>
    /* ===== App background ===== */
    html, body, [data-testid="stApp"] {
        background-color: white !important;
    }

    /* ===== Page vertical centering ===== */
    div.block-container {
        padding-top: 28vh;
    }

    /* ===== Title (InI.ai) ===== */
    h1 {
    color: black !important;
    font-size: 78px !important;
        text-align: center !important;
        position: relative;
        left: 30px;            /* your chosen alignment */
        font-weight: 8200 !important;
    }

    /* ===== Input container (WIDTH + POSITION) ===== */
    div[data-testid="stTextInput"] {
        width: 800px !important;
        margin: 0 auto !important;
        position: relative;
        right: 120px;          /* your chosen alignment */
    }

    /* ===== Input wrapper (FULL BAR COLOR + BORDER + HEIGHT) ===== */
    div[data-testid="stTextInput"] > div {
        border: 4px solid black !important;
        border-radius: 6px !important;
        box-shadow: none !important;

        background-color: black !important;   /* FULL inside color */
        min-height: 184px !important;

        display: flex !important;
        align-items: stretch !important;         /* key: prevents "strip" */
        padding: 0 !important;                   /* key: prevents inner band */
    }

    /* ===== Actual input (TRANSPARENT so no inner strip) ===== */
    div[data-testid="stTextInput"] input {
        border: black !important;
        outline: black !important;
        box-shadow: none !important;

        background: transparent !important;      /* key: removes inner strip */
        width: 100% !important;
        height: 100% !important;
        box-sizing: border-box !important;

        padding: 18px 20px !important;           /* text spacing only */
        font-size: 18px !important;
        color: black !important;
    }

    /* ===== Hide "Press Enter to apply" helper ===== */
    div[data-testid="stTextInput"] [data-testid="InputInstructions"],
    div[data-testid="stTextInput"] div[aria-live],
    div[data-testid="stTextInput"] small {
        display: none !important;
    }

    /* ===== Buttons (keep slim, bold text) ===== */
    div.stButton > button {
        background-color: black !important;
        min-width: 160px !important;
        height: 44px !important;                 /* keep NOT too thick */
        padding: 8px 16px !important;
        border-radius: 8px !important;
        border: none !important;
        white-space: nowrap !important;
    }

    div.stButton > button,
    div.stButton > button span,
    div.stButton > button p {
        color: white !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        text-align: center !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)


st.title("InI.ai")

left, mid, right = st.columns([1,6,1])

with mid:
    topic = st.text_area(
    "Topic",
    placeholder="Type your message here...",
    height=110
)

    #topic = st.text_input("", placeholder="Try: Artificial Intelligence")

    # keep the two buttons close (centered under the input)
    _l, b1, gap, b2, _r = st.columns([2, 2, 0.6, 2, 2])

    with b1:
        interrogate_clicked = st.button("Interrogate")

    with b2:
        illustrate_clicked = st.button("Illustrate")



if interrogate_clicked and topic.strip():
    data, err = safe_post("/interrogate", {"topic": topic})
    if err:
        st.error(err)
    else:
        st.subheader(f"Interrogating: {data['topic']}")

        # --- Summary (top) ---
        if "summary" in data and data["summary"]:
            for line in data["summary"]:
                st.write(line)
            st.write("")

        if show_raw:
            st.markdown("### Raw response")
            st.json(data)

        for cat, items in data["categories"].items():
            st.markdown(f"**{cat}**")
            for item in items:
                q_text = item.get("question", "")
                a_text = item.get("answer", "")
                with st.expander("• " + q_text):
                    st.write(a_text)

        # --- Few examples (quick preview) ---
        if "quick_examples" in data and data["quick_examples"]:
            st.markdown("### Few examples")
            for ex in data["quick_examples"]:
                st.write("• " + ex)





if illustrate_clicked and topic.strip():
    data, err = safe_post("/illustrate", {"topic": topic})
    if err:
        st.error(err)
    else:
        st.subheader(f"Illustrating: {data['topic']}")

        if show_raw:
            st.markdown("### Raw response")
            st.json(data)

        illustrations = data.get("illustrations", {})
        for k, v in illustrations.items():
            st.markdown(f"**{k.replace('_',' ').title()}**")
            st.write("• " + str(v))







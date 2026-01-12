import streamlit as st
import requests



st.set_page_config(page_title="InI.ai", layout="centered")

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


# st.markdown(
#     """
#     <style>
#     /* Button background */
#     div.stButton > button {
#         background-color: black !important;
#         border: none !important;
#     }

#     /* Button text (Streamlit wraps it inside) */
#     div.stButton > button,
#     div.stButton > button span,
#     div.stButton > button p {
#         color: white !important;
#         font-weight: 900 !important;
#         font-size: 18px !important;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )


# st.markdown(
#     """
#     <style>
#     div.stButton > button {
#         background-color: black !important;
#         color: white !important;
#         font-weight: 900 !important;
#         font-size: 18px !important;

#         min-width: 160px;          /* forces equal width */
#         padding: 10px 16px;
#         white-space: nowrap;       /* prevents word wrapping */
#         text-align: center;
#         border-radius: 8px;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# st.markdown(
#     """
#     <style>
#     /* Center the title above the input */
# h1 {
#     text-align: center !important;
#     position: relative;
#     left: 30px;
# }

#     /* Push content down (your current vertical centering) */
#     div.block-container {
#         padding-top: 28vh;
#     }


#     # div[data-testid="stTextInput"] input {
#     #     height: 52px !important;
#     # }


#     /* --- Input: force a true 4-side border by styling BOTH wrapper + input --- */
#     div[data-testid="stTextInput"] > div {
#         border: 2px solid black !important;
#         border-radius: 6px !important;
#         box-shadow: none !important;
#         background: white !important;

#         min-height: 64px !important;      /* <-- controls bar thickness */
#     display: flex !important;
#     align-items: center !important;
#     }

#     div[data-testid="stTextInput"] input {
#         padding: 30px 32px !important;
#         border: none !important;          /* border is handled by wrapper */
#         box-shadow: none !important;
#         outline: none !important;
#         #height: 48px !important;
#         font-size: 18px !important;
#         background: transparent !important;
#     }

#     div[data-testid="stTextInput"] input:focus {
#         box-shadow: none !important;
#         outline: none !important;
#     }

#     /* Input width (we can revisit later) */
#     div[data-testid="stTextInput"] {
#         width: 800px !important;
#         margin-left: auto !important;
#         margin-right: auto !important;
#         right: 120px;
#         }

#     /* --- Buttons: same height + style --- */
#     div.stButton > button {
#         background-color: black !important;
#         min-width: 160px !important;
#         height: 44px !important;
#         padding: 10px 18px !important;
#         border-radius: 8px !important;
#         white-space: nowrap !important;
#         border: none !important;
#     }

#     div.stButton > button,
#     div.stButton > button span,
#     div.stButton > button p {
#         color: white !important;
#         font-weight: 900 !important;
#         font-size: 18px !important;
#         text-align: center !important;
#     }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# st.markdown(
#     """
#     <style>

#     /* ===== Page vertical centering ===== */
#     div.block-container {
#         padding-top: 28vh;
#     }

#     /* ===== Title (InI.ai) ===== */
#     h1 {
#         text-align: center !important;
#         position: relative;
#         left: 30px;   /* aligns dot with button gap */
#         font-weight: 800 !important;
#     }

#     /* ===== Input container (controls WIDTH + POSITION) ===== */
#     div[data-testid="stTextInput"] {
#         width: 800px !important;        /* horizontal length */
#         margin: 0 auto !important;
#         position: relative;
#         right: 120px;                   /* your chosen visual alignment */
#     }

#     /* ===== Input wrapper (controls BORDER + HEIGHT) ===== */
#     div[data-testid="stTextInput"] > div {
#         border: 3px solid black !important;
#         border-radius: 8px !important;
#         background: white !important;

#         min-height: 154px !important;    /* TOP–BOTTOM thickness */
#         display: flex !important;
#         align-items: center !important;
#         box-shadow: none !important;
#     }

#     /* ===== Actual text input ===== */
#     div[data-testid="stTextInput"] input {
#         border: none !important;
#         outline: none !important;
#         box-shadow: none !important;

#         padding: 18px 18px !important;  /* fine control of thickness */
#         font-size: 18px !important;
#         background: transparent !important;

#         width: 100% !important;
#         box-sizing: border-box !important;
#     }

#     /* ===== Remove Streamlit focus underline ===== */
#     div[data-testid="stTextInput"] input:focus {
#         box-shadow: none !important;
#         outline: none !important;
#     }

#     /* ===== Buttons ===== */
#     div.stButton > button {
#         background-color: black !important;
#         min-width: 160px !important;
#         height: 44px !important;         /* MATCHES input thickness */
#         padding: 10px 18px !important;
#         border-radius: 8px !important;
#         border: none !important;
#         white-space: nowrap !important;
#     }

#     div.stButton > button,
#     div.stButton > button span,
#     div.stButton > button p {
#         color: white !important;
#         font-weight: 900 !important;
#         font-size: 20px !important;
#         text-align: top !important;
#     }

    
#     /* 1) Hide the "Press Enter to apply" helper */
# div[data-testid="stTextInput"] [data-testid="InputInstructions"],
# div[data-testid="stTextInput"] div[aria-live="polite"],
# div[data-testid="stTextInput"] small {
#     display: none !important;
# }

# /* 2) Remove grey background inside the bar (make it pure white) */
# div[data-testid="stTextInput"] > div {
#     background: 8c92ac !important;
# }

# div[data-testid="stTextInput"] input {
#     background: 8c92ac !important;
# }

# /* 3) Make the whole app background ghost white */
# html, body, [data-testid="stApp"] {
#     background-color: #fffafa !important;
# }

#     </style>
#     """,
#     unsafe_allow_html=True
# )

st.markdown(
    """
    <style>
    /* ===== App background ===== */
    html, body, [data-testid="stApp"] {
        background-color: #eb6d46 !important;
    }

    /* ===== Page vertical centering ===== */
    div.block-container {
        padding-top: 28vh;
    }

    /* ===== Title (InI.ai) ===== */
    h1 {
    color: white !important;
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
        border: none !important;
        outline: none !important;
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



# st.title("InI.ai (v0)")

# topic = st.text_input("Topic", placeholder="Try: Artificial Intelligence")


# left, b1, spacer, b2, right = st.columns([3,2,0.8,2,4])


# with b1:
#     interrogate_clicked = st.button("Interrogate")

# with b2:
#     illustrate_clicked = st.button("Illustrate")

# --- TOP UI (title + input + buttons) kept in ONE centered column ---
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
    r = requests.post("http://127.0.0.1:8000/interrogate", json={"topic": topic})
    data = r.json()
    st.subheader(f"Interrogating: {data['topic']}")

    for cat, qs in data["categories"].items():
        st.markdown(f"**{cat}**")
        for q in qs:
            st.write("• " + q)

if illustrate_clicked and topic.strip():
    r = requests.post("http://127.0.0.1:8000/illustrate", json={"topic": topic})
    data = r.json()
    st.subheader(f"Illustrating: {data['topic']}")
    for ex in data["examples"]:
        st.write("• " + ex)


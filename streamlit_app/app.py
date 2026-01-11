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

st.markdown(
    """
    <style>
     /* Make the text input match the button-group width and stay centered */
    div[data-testid="stTextInput"] {
        width: 340px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }


    /* Button container */
    div.stButton > button {
        background-color: black !important;
        min-width: 160px;
        padding: 10px 18px;
        border-radius: 8px;
        white-space: nowrap;
        margin-right: 12px;   /* space between buttons */
    }

    /* Button text */
    div.stButton > button,
    div.stButton > button span,
    div.stButton > button p {
        color: white !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        text-align: center;
    }

    /* Push the main content down (vertical centering feel) */
    div.block-container {
        padding-top: 28vh;
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
    topic = st.text_input("", placeholder="Try: Artificial Intelligence")

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
    for q in data["questions"]:
        st.write("• " + q)

if illustrate_clicked and topic.strip():
    r = requests.post("http://127.0.0.1:8000/illustrate", json={"topic": topic})
    data = r.json()
    st.subheader(f"Illustrating: {data['topic']}")
    for ex in data["examples"]:
        st.write("• " + ex)


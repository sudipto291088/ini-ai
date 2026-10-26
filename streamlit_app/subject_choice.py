"""Conservative subject discovery: exact catalogue matches, never inferred intent."""
import re
import importlib
import unicodedata
from html import escape

import streamlit as st

SUBJECT_CHOICE_VERSION = 3
learning_trail = importlib.import_module("streamlit_app.learning_trail")
if not hasattr(learning_trail, "render_trail_rows"):
    learning_trail = importlib.reload(learning_trail)

# These are recognised fields, not a claim that every generated course is audited.
# Ambiguous abbreviations (AI, ML, OS, etc.) deliberately have no aliases.
SUBJECTS = (
    "Physics", "Chemistry", "Biology", "Mathematics", "Statistics", "Astronomy",
    "Geology", "Ecology", "Genetics", "Microbiology", "Biochemistry", "Neuroscience",
    "Computer Science", "Machine Learning", "Artificial Intelligence", "Data Science",
    "Operating Systems", "Computer Networks", "Database Systems", "Software Engineering",
    "Cybersecurity", "Cryptography", "Computer Architecture", "Algorithms",
    "Quantum Computing", "Kubernetes", "Robotics", "Electrical Engineering", "Mechanical Engineering",
    "Civil Engineering", "Chemical Engineering", "Materials Science",
    "Economics", "Microeconomics", "Macroeconomics", "Accounting", "Finance",
    "Psychology", "Sociology", "Anthropology", "Political Science", "Philosophy",
    "Logic", "Linguistics", "History", "Geography", "Environmental Science",
    "Calculus", "Linear Algebra", "Discrete Mathematics", "Number Theory",
    "Organic Chemistry", "Physical Chemistry", "Evolutionary Biology", "Cell Biology",
)


def recognised_subject(prompt: str) -> str:
    value = unicodedata.normalize("NFKC", str(prompt or ""))
    value = re.sub(r"\s+", " ", value).strip().rstrip(".").strip().casefold()
    return next((subject for subject in SUBJECTS if subject.casefold() == value), "")


def render_subject_choice(subject: str) -> str | None:
    """Native, keyboard-accessible actions, with no preselected learning mode."""
    st.markdown('''<style>
    .st-key-ini_subject_choice {
      max-width:720px; margin:24px 0 32px; padding:26px 28px 18px;
      border:1px solid rgba(15,23,42,.045); border-radius:22px;
      background:#fff; box-shadow:0 10px 36px rgba(15,23,42,.025);
    }
    .st-key-ini_subject_choice .subject-choice-title {
      color:#172033; font-size:20px; font-weight:400; line-height:1.5; margin:0 0 8px;
    }
    .st-key-ini_subject_choice .subject-choice-copy {
      color:#64748b; font-size:13px; font-weight:400; line-height:1.6; margin:0;
    }
    .st-key-ini_subject_choice .st-key-ini_subject_cancel div.stButton > button {
      background:transparent !important; border:0 !important; box-shadow:none !important;
      color:#64748b !important; min-width:0 !important; padding:6px 10px !important;
      min-height:32px !important; height:auto !important; width:auto !important;
      font-weight:400 !important; border-radius:8px !important;
    }
    .st-key-ini_subject_choice .st-key-ini_subject_cancel button p {font-size:12px !important; font-weight:400 !important;}
    @media(max-width:560px) {
      .st-key-ini_subject_choice {padding:22px 16px 14px; margin:16px 0 24px;}
      .st-key-ini_subject_choice .subject-choice-title {font-size:18px;}
    }
    </style>''', unsafe_allow_html=True)
    result = None
    with st.container(key="ini_subject_choice"):
        st.markdown(f'<p class="subject-choice-title">How would you like to explore {escape(subject)}?</p>'
                    '<p class="subject-choice-copy">Start with the essentials, or build your understanding step by step.</p>',
                    unsafe_allow_html=True)
        selected = learning_trail.render_trail_rows([
            dict(action="overview", title="Quick overview", icon="explore",
                 description="The key ideas, with a clear starting point."),
            dict(action="study", title="Study as a subject", icon="route",
                 description="A structured learning path, guided by questions."),
        ], f"subject-choice-{subject}", heading="Choose your approach")
        if selected:
            result = selected["action"]
        with st.container(key="ini_subject_cancel", width="content"):
            if st.button("Cancel", key="ini_subject_dismiss", width="content", type="tertiary"):
                result = "cancel"
    return result

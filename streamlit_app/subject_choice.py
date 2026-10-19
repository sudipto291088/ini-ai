"""Conservative subject discovery: exact catalogue matches, never inferred intent."""
import re
import unicodedata
from html import escape

import streamlit as st

# These are recognised fields, not a claim that every generated course is audited.
# Ambiguous abbreviations (AI, ML, OS, etc.) deliberately have no aliases.
SUBJECTS = (
    "Physics", "Chemistry", "Biology", "Mathematics", "Statistics", "Astronomy",
    "Geology", "Ecology", "Genetics", "Microbiology", "Biochemistry", "Neuroscience",
    "Computer Science", "Machine Learning", "Artificial Intelligence", "Data Science",
    "Operating Systems", "Computer Networks", "Database Systems", "Software Engineering",
    "Cybersecurity", "Cryptography", "Computer Architecture", "Algorithms",
    "Quantum Computing", "Robotics", "Electrical Engineering", "Mechanical Engineering",
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
      max-width:640px; margin:24px 0 32px; padding:22px 24px;
      border:1px solid rgba(15,23,42,.07); border-radius:18px;
      background:#fff; box-shadow:0 8px 28px rgba(15,23,42,.035);
    }
    .st-key-ini_subject_choice .subject-choice-title {
      color:#172033; font-size:18px; font-weight:450; line-height:1.5; margin:0 0 5px;
    }
    .st-key-ini_subject_choice .subject-choice-copy {
      color:#64748b; font-size:13px; font-weight:400; line-height:1.6; margin:0 0 18px;
    }
    .st-key-ini_subject_choice button {
      min-height:40px !important; border-radius:11px !important; font-weight:450 !important;
      border:1px solid rgba(15,23,42,.09) !important; background:#f8fafc !important; color:#263247 !important;
      box-shadow:0 2px 5px rgba(15,23,42,.025) !important; padding:8px 16px !important;
    }
    .st-key-ini_subject_choice button p {font-size:13px !important; font-weight:450 !important;}
    .st-key-ini_subject_choice button:hover {border-color:#cbd5e1 !important; background:#f1f5f9 !important;}
    .st-key-ini_subject_choice .st-key-ini_subject_study div.stButton > button {background:#101b30 !important; color:#fff !important; border-color:#101b30 !important;}
    .st-key-ini_subject_choice .st-key-ini_subject_study div.stButton > button:hover {background:#1e2d47 !important; color:#fff !important;}
    .st-key-ini_subject_choice .st-key-ini_subject_cancel div.stButton > button {background:transparent !important; border-color:transparent !important; box-shadow:none !important; color:#64748b !important; min-width:0 !important; padding:4px 0 !important; min-height:28px !important;}
    @media(max-width:560px) {
      .st-key-ini_subject_choice {padding:18px 16px; margin:16px 0 24px;}
      .st-key-ini_subject_choice .subject-choice-title {font-size:17px;}
    }
    </style>''', unsafe_allow_html=True)
    result = None
    with st.container(key="ini_subject_choice"):
        st.markdown(f'<p class="subject-choice-title">How would you like to explore {escape(subject)}?</p>'
                    '<p class="subject-choice-copy">A brief introduction, or a structured path through the subject.</p>',
                    unsafe_allow_html=True)
        with st.container(horizontal=True, gap="small"):
            if st.button("Quick overview", key="ini_subject_overview", width="content"):
                result = "overview"
            with st.container(key="ini_subject_study", width="content"):
                if st.button("Study as a subject", key="ini_subject_curriculum", width="content"):
                    result = "study"
        with st.container(key="ini_subject_cancel", width="content"):
            if st.button("Cancel", key="ini_subject_dismiss", width="content"):
                result = "cancel"
    return result

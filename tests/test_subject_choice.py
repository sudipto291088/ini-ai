import unittest
from streamlit.testing.v1 import AppTest
from streamlit_app.subject_choice import SUBJECTS, recognised_subject


class SubjectChoiceTests(unittest.TestCase):
    def test_actual_app_choice_routes_without_reopening_or_cross_account_state(self):
        from pathlib import Path
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        start = source.index('    subject_choice = st.session_state.get("_ini_subject_choice")')
        end = source.index('    pending_qc = st.session_state.get("qc_pending_request")', start)
        script = '''
import streamlit as st
from streamlit_app.subject_choice import render_subject_choice
st.session_state.setdefault("visitor_id", "A")
st.session_state.setdefault("chat_active_id", "chat-a")
if not st.session_state.get("seeded"):
    st.session_state["_ini_subject_choice"] = {"subject":"Physics", "prompt":"Physics", "owner":"A", "chat":"chat-a"}
    st.session_state["seeded"] = True
st.session_state.setdefault("api_base", "unused")
def _queue_new_chat_request(prompt, action, **kwargs):
    st.session_state["routed"] = ("overview", prompt, kwargs)
def _session_has_existing_timeline(): return False
def _render_new_chat_bottom_uib(): pass
def _attach_curriculum_to_new_chat(*args): pass
def _advance_new_chat_composer(): pass
class QC:
    def maybe_start_qc(self, prompt, *args):
        st.session_state["routed"] = ("study", prompt)
qc_ui = QC()
def render():
'''
        for label in ("Quick overview", "Study as a subject", "Cancel"):
            app = AppTest.from_string(script + source[start:end] + '\nrender()').run()
            next(button for button in app.button if button.label.split("\n\n")[0] == label).click().run()
            app.run()
            self.assertEqual(len(app.exception), 0)
            self.assertNotIn("_ini_subject_choice", app.session_state)
            if label == "Quick overview":
                self.assertEqual(app.session_state["routed"], ("overview", "Physics", {"offer_subject_choice": False}))
            elif label == "Study as a subject":
                self.assertEqual(app.session_state["routed"], ("study", "Teach me Physics as a subject"))
            else:
                self.assertFalse(app.session_state["nc_started"])
        app = AppTest.from_string(script + source[start:end] + '\nrender()').run()
        app.session_state["visitor_id"] = "B"
        app.run()
        self.assertEqual(len(app.button), 0)
        self.assertNotIn("_ini_subject_choice", app.session_state)

    def test_catalogue_names_match_case_and_spacing_only(self):
        for subject in SUBJECTS:
            self.assertEqual(recognised_subject("  " + subject.upper() + "  "), subject)
        self.assertEqual(recognised_subject("machine   learning"), "Machine Learning")

    def test_questions_topics_and_ambiguous_queries_do_not_match(self):
        for prompt in ("What is physics?", "Physics?", "Explain physics", "Teach me physics",
                       "cancer mutation", "gradient descent", "CPU scheduling", "transformers",
                       "AI", "ML", "OS", "history of my chats", "random query", "", "physics and chemistry",
                       "I don't want to study physics", "Python", "Java", "Marketing tips"):
            self.assertEqual(recognised_subject(prompt), "", prompt)

    def test_subject_choice_is_explicit_and_cancelable(self):
        script = '''
import streamlit as st
from streamlit_app.subject_choice import render_subject_choice
result = render_subject_choice("Physics")
if result:
    st.session_state["result"] = result
'''
        for label, expected in (("Quick overview", "overview"), ("Study as a subject", "study"), ("Cancel", "cancel")):
            app = AppTest.from_string(script).run()
            self.assertNotIn("result", app.session_state)
            next(button for button in app.button if button.label.split("\n\n")[0] == label).click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.session_state["result"], expected)

    def test_overview_bypasses_choice_and_subject_study_uses_existing_qc(self):
        from pathlib import Path
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        self.assertIn('offer_subject_choice=False', source)
        self.assertIn('f"Teach me {subject_choice[\'subject\']} as a subject"', source)
        self.assertIn('subject_choice.get("owner") != st.session_state.visitor_id', source)
        self.assertIn('subject_choice.get("chat") != st.session_state.chat_active_id', source)


if __name__ == "__main__":
    unittest.main()

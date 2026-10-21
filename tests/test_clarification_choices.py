import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from api.abbreviation_clarification import clarification_choices


class ClarificationChoiceTests(unittest.TestCase):
    def test_meanings_are_explicit_and_exactly_matched(self):
        self.assertEqual(clarification_choices(" ML? "),
                         ("Machine learning", "Maximum likelihood", "Millilitres"))
        self.assertEqual(clarification_choices("OS"), ("Operating system",))
        for query in ("Explain ML", "What is ML?", "5 ml", "Physics", ""):
            self.assertEqual(clarification_choices(query), ())

    def test_each_native_button_returns_its_full_meaning(self):
        script = '''
import streamlit as st
from streamlit_app.clarification_choices import render_clarification_choices
choice = render_clarification_choices("ml", "response-one")
if choice:
    st.session_state.selected = choice
'''
        for index, expected in enumerate(clarification_choices("ml")):
            app = AppTest.from_string(script).run()
            self.assertEqual([button.label.split("\n\n")[0] for button in app.button], list(clarification_choices("ml")))
            self.assertTrue(all(button.icon for button in app.button))
            app.button[index].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.session_state.selected, expected)

    def test_disabled_and_separate_response_keys(self):
        app = AppTest.from_string('''
from streamlit_app.clarification_choices import render_clarification_choices
render_clarification_choices("ml", "first", disabled=True)
render_clarification_choices("ml", "second", disabled=True)
render_clarification_choices("Explain ML", "not-a-clarification")
''').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.button), 6)
        self.assertTrue(all(button.disabled for button in app.button))

    def test_main_chat_uses_confirmed_meaning_and_normal_subject_flow(self):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        self.assertIn("if is_meaning_check:\n                    meaning = render_clarification_choices(", source)
        self.assertIn('_queue_new_chat_request(meaning, "interrogate")', source)

    def test_choices_share_learning_trail_renderer(self):
        source = (Path(__file__).parents[1] / "streamlit_app/clarification_choices.py").read_text(encoding="utf-8")
        self.assertIn("learning_trail.render_trail_rows(", source)
        self.assertNotIn("<style>", source)
        self.assertNotIn("horizontal=True", source)


if __name__ == "__main__":
    unittest.main()

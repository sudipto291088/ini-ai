import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from streamlit_app.learning_trail import trail_actions, continuation_prompt

ANSWER = "The **learning rate** determines the step size. " * 8
PAYLOAD = {"prompt": "Gradient descent", "question_intelligence": True, "profile_prompt": "Gradient descent"}


class LearningTrailTests(unittest.TestCase):
    def test_actions_use_the_source_answer_not_another_chat_topic(self):
        actions = trail_actions("Gradient descent", ANSWER, PAYLOAD)
        self.assertEqual([item["action"] for item in actions], ["example", "connect", "practice"])
        self.assertIn("learning rate", actions[0]["description"])
        request = continuation_prompt("example", actions[0]["topic"], ANSWER)
        self.assertIn("Gradient descent", request)
        self.assertIn(ANSWER, request)
        self.assertIn("Do not restart the whole topic", request)

    def test_quiz_does_not_reveal_the_answer(self):
        request = continuation_prompt("practice", "Physics", ANSWER)
        self.assertIn("exactly one", request)
        self.assertIn("do not provide the answer", request)
        self.assertEqual(trail_actions("Physics", ANSWER, {**PAYLOAD, "learning_trail_action_kind":"practice"}), [])

    def test_continuation_keeps_source_and_does_not_repeat_the_same_action_copy(self):
        payload = {"intent":"learning_trail", "learning_trail_source":"Physics", "learning_trail_action_kind":"example"}
        actions = trail_actions("Make it concrete", ANSWER, payload)
        self.assertEqual(actions[0]["title"], "Try another example")
        self.assertEqual(actions[0]["topic"], "Physics")

    def test_no_trail_for_smalltalk_clarification_or_partial_answers(self):
        for payload in ({}, {**PAYLOAD, "incomplete": True}, {**PAYLOAD, "needs_clarification": True},
                        {**PAYLOAD, "intent": "abbreviation_clarification"}, {**PAYLOAD, "intent": "greeting"}):
            self.assertEqual(trail_actions("ML", ANSWER, payload), [])
        self.assertEqual(trail_actions("Physics", "Short text.", PAYLOAD), [])

    def test_writing_uses_editing_actions_instead_of_a_quiz(self):
        for prompt in ("Draft an email to my professor", "Write a short message for Ganesh", "get me one more message"):
            actions = trail_actions(prompt, ANSWER, {"should_answer_direct": True})
            self.assertEqual([item["action"] for item in actions], ["refine", "shorten", "tone"])

    def test_context_is_bounded_and_unknown_actions_rejected(self):
        self.assertLess(len(continuation_prompt("connect", "a" * 1000, "b" * 20000)), 7000)
        with self.assertRaises(ValueError):
            continuation_prompt("delete", "Physics", ANSWER)

    def test_native_buttons_return_the_selected_action_and_topic(self):
        script = '''
import streamlit as st
from streamlit_app.learning_trail import render_learning_trail
answer = "The **learning rate** controls the step. " * 10
payload = {"question_intelligence":True, "profile_prompt":"Gradient descent"}
action = render_learning_trail("Gradient descent", answer, payload, "answer-one")
if action:
    st.session_state["selected"] = action
'''
        for index, expected in enumerate(("example", "connect", "practice")):
            app = AppTest.from_string(script).run()
            self.assertEqual(len(app.button), 3)
            app.button[index].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.session_state["selected"]["action"], expected)
            self.assertEqual(app.session_state["selected"]["topic"], "Gradient descent")

    def test_pipeline_keeps_context_and_checks_owner(self):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        self.assertIn('request_kind="learning_trail", offer_subject_choice=False', source)
        self.assertIn('learning_trail_action.get("owner") != st.session_state.visitor_id', source)
        self.assertIn('learning_trail_action.get("chat") != st.session_state.chat_active_id', source)
        self.assertIn('learning_trail_action=learning_trail_action', source)
        self.assertIn('"learning_trail_source": (learning_trail_action or {}).get("topic", "")', source)


if __name__ == "__main__":
    unittest.main()

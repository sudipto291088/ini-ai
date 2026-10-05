import unittest
import ast
from pathlib import Path

from api.intent_layer import detect_intent
from api.conversation_interpreter import should_preserve_conversation_context


class SubstantiveQuestionRoutingTests(unittest.TestCase):
    def test_active_discussion_cannot_override_substantive_learning(self):
        source = (Path(__file__).resolve().parents[1] / "streamlit_app" / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        guarded = [ast.unparse(node.test) for node in ast.walk(tree)
                   if isinstance(node, ast.If)
                   and "discussion_freeform_followup" in ast.unparse(node.test)
                   and isinstance(node.test, ast.BoolOp)]
        self.assertIn("discussion_freeform_followup and (not substantive_learning_turn)", guarded)

    QUESTIONS = (
        "What has to be true inside a boundary for something to count as alive, and what fails that test?",
        "Why did long-distance trade change what counted as money, and what stopped being money once that happened?",
        "What has to stay fixed for a model to count as the same system after fine-tuning, and what change means it is no longer that system?",
        "What must remain constant for a chemical reaction to reach equilibrium?",
        "Why did a scientific theory change after new evidence challenged it?",
        "How does this statistical test distinguish signal from noise?",
        "When does a correlation become strong enough to justify a decision, and what still has to be true before it counts as a cause?",
        "Where does statistical inference stop being reliable under distribution shift?",
        "Which constraints must hold for an experiment to establish causality?",
    )

    def test_fresh_and_conversation_to_learning_transition(self):
        for question in self.QUESTIONS:
            with self.subTest(question=question):
                intent = detect_intent(question)
                self.assertEqual(intent["intent"], "topic_explore")
                self.assertTrue(intent["should_interrogate"])
                self.assertFalse(should_preserve_conversation_context(
                    user_text=question, prior_response_mode="conversation",
                    study_mode_established=False, requests_learning_map=True,
                    explicit_question_map_request=False,
                ))

    def test_casual_testing_and_social_questions_stay_conversational(self):
        for question in ("I'm just testing you", "just checking this", "How are you?", "Why did you ask me that?", "When can you talk?", "Where are you?"):
            with self.subTest(question=question):
                self.assertTrue(should_preserve_conversation_context(
                    user_text=question, prior_response_mode="conversation",
                    study_mode_established=False, requests_learning_map=True,
                    explicit_question_map_request=False,
                ))

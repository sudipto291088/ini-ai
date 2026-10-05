import unittest

from api.intent_layer import detect_intent
from api.conversation_interpreter import should_preserve_conversation_context


class SubstantiveQuestionRoutingTests(unittest.TestCase):
    QUESTIONS = (
        "What has to be true inside a boundary for something to count as alive, and what fails that test?",
        "Why did long-distance trade change what counted as money, and what stopped being money once that happened?",
        "What has to stay fixed for a model to count as the same system after fine-tuning, and what change means it is no longer that system?",
        "What must remain constant for a chemical reaction to reach equilibrium?",
        "Why did a scientific theory change after new evidence challenged it?",
        "How does this statistical test distinguish signal from noise?",
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
        for question in ("I'm just testing you", "just checking this", "How are you?", "Why did you ask me that?"):
            with self.subTest(question=question):
                self.assertTrue(should_preserve_conversation_context(
                    user_text=question, prior_response_mode="conversation",
                    study_mode_established=False, requests_learning_map=True,
                    explicit_question_map_request=False,
                ))

import unittest

from api.interrogate import interrogate


class ConversationEngineTests(unittest.TestCase):
    def test_greeting_uses_conversation_engine_without_map(self):
        result = interrogate("Hello, how are you doing?")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertTrue(result["should_answer_direct"])
        self.assertEqual(result["categories"], {})
        self.assertIn("natural conversation", result["direct_answer_prompt"])

    def test_unclear_message_gets_cross_question_policy(self):
        result = interrogate("It is doing that thing again")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertIn("ask exactly one useful cross-question", result["direct_answer_prompt"])

    def test_thanks_does_not_generate_topic_suggestions(self):
        result = interrogate("Thanks, that helped")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertEqual(result["followups"], [])

    def test_wellbeing_question_with_time_word_stays_conversational(self):
        result = interrogate("How are you doing today?")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertEqual(result["intent"], "greeting")
        self.assertEqual(result["categories"], {})

    def test_natural_status_check_stays_conversational(self):
        for message in (
            "How's everything going?",
            "How are things going?",
            "Hello InI, how are you?",
        ):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["categories"], {})

    def test_permission_to_use_ini_name_is_conversational(self):
        result = interrogate("Can I call you InI?")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertEqual(result["categories"], {})

    def test_capability_question_does_not_create_question_map(self):
        result = interrogate("What can you help me with?")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertEqual(result["categories"], {})

    def test_casual_meta_conversation_does_not_create_question_map(self):
        for message in (
            "No no, just casually testing you",
            "I am only checking this",
            "Just trying things with you",
        ):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["categories"], {})

    def test_expressive_casual_spelling_stays_conversational(self):
        for message in (
            "heyyy whats up?",
            "helloooo how are you?",
            "hiiii InI",
        ):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["categories"], {})


if __name__ == "__main__":
    unittest.main()

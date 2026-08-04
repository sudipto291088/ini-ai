import unittest

from api.interrogate import interrogate
from api.intent_layer import detect_intent


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

    def test_acknowledgements_never_generate_question_maps(self):
        for message in ("its ok....", "that's fine", "all good", "no problem"):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["categories"], {})

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
            "So what's going on?",
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

    def test_personal_weather_observation_stays_conversational(self):
        result = interrogate("Too hot today")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertEqual(result["categories"], {})

    def test_freeform_chat_request_stays_conversational(self):
        result = interrogate("nothin lets just talk")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertFalse(result.get("categories"))

    def test_self_introductions_are_conversation_not_topics(self):
        for message in ("I am Sid", "My name is Maya", "You can call me Sam"):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["intent"], "self_introduction")
                self.assertFalse(result.get("categories"))

    def test_short_acknowledgements_and_endings_are_conversational(self):
        expected = {
            "cool": "affirmation",
            "rest for today": "farewell",
            "done for today": "farewell",
        }
        for message, intent in expected.items():
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["intent"], intent)
                self.assertFalse(result.get("categories"))

    def test_correction_about_question_map_stays_conversational(self):
        result = interrogate("why are you going to generate a question map for that?")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertFalse(result.get("categories"))

    def test_explicit_question_map_command_is_not_live_data(self):
        result = interrogate("generate a question map for quad core")
        self.assertNotEqual(result.get("intent"), "direct_factual_query")
        if not result.get("categories"):
            self.assertEqual(result.get("intent"), "unsupported_learning_topic")
            self.assertIn("quad core", result.get("reply", "").lower())

    def test_ambiguous_continuation_does_not_become_a_question_map(self):
        for message in ("what else", "so what else", "and what else", "well, anything else"):
            with self.subTest(message=message):
                result = detect_intent(message)
                self.assertEqual(result["intent"], "clarify")
                self.assertFalse(result["should_interrogate"])

    def test_explicit_question_map_for_ambiguous_words_still_obeys_command(self):
        result = interrogate("generate a question map for what else")
        self.assertNotEqual(result.get("intent"), "clarify")

    def test_failed_generation_never_returns_generic_question_templates(self):
        from unittest.mock import patch

        with patch("api.interrogate._llm_is_enabled", return_value=False):
            result = interrogate("photosynthesis")

        self.assertEqual(result["categories"], {})
        self.assertEqual(result["intent"], "unsupported_learning_topic")
        self.assertTrue(result["suppress_profile"])
        self.assertIn("photosynthesis", result["reply"].lower())
        self.assertNotIn("send a topic", result["reply"].lower())

    def test_single_word_subject_is_a_learning_topic(self):
        for subject in ("photosynthesis", "mitosis", "thermodynamics"):
            with self.subTest(subject=subject):
                result = detect_intent(subject)
                self.assertEqual(result["intent"], "topic_explore")
                self.assertTrue(result["should_interrogate"])

    def test_unknown_concept_definition_routes_to_learning(self):
        result = detect_intent("What is quantum entanglement?")
        self.assertEqual(result["intent"], "topic_explore")
        self.assertTrue(result["should_interrogate"])
        self.assertFalse(result["should_answer_direct"])

    def test_live_definition_lookup_remains_direct(self):
        result = detect_intent("What is the current bitcoin price?")
        self.assertEqual(result["intent"], "direct_factual_query")
        self.assertTrue(result["should_answer_direct"])

    def test_single_word_conversation_is_not_a_learning_topic(self):
        for message in ("thanks", "continue", "sorry", "nothing"):
            with self.subTest(message=message):
                result = detect_intent(message)
                self.assertNotEqual(result["intent"], "topic_explore")


if __name__ == "__main__":
    unittest.main()

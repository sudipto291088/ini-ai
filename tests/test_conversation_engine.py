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

    def test_status_check_with_social_address_never_creates_question_map(self):
        for message in (
            "what's going on man",
            "what's going on, buddy?",
            "so what's up mate",
        ):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertIn(result["intent"], {"greeting", "smalltalk"})
                self.assertEqual(result["categories"], {})

    def test_permission_to_use_ini_name_is_conversational(self):
        result = interrogate("Can I call you InI?")
        self.assertEqual(result["response_mode"], "conversation")
        self.assertEqual(result["categories"], {})

    def test_capability_question_does_not_create_question_map(self):
        for message in (
            "What can you help me with?",
            "What kind of humor do you understand?",
            "Which types of jokes do you recognize?",
            "Do you understand sarcasm?",
        ):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["categories"], {})

    def test_personal_preference_statement_is_conversation(self):
        for message in (
            "I prefer quiet evenings",
            "I like rainy afternoons",
            "We enjoy slow weekends",
            "I don't like crowded rooms",
        ):
            with self.subTest(message=message):
                result = interrogate(message)
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

    def test_explicit_casual_chat_declaration_overrides_topic_shift(self):
        for message in (
            "no i am just casually chatting",
            "I am only chatting",
            "I'm casually talking",
        ):
            with self.subTest(message=message):
                intent = detect_intent(message)
                self.assertEqual(intent["intent"], "smalltalk")
                self.assertFalse(intent["should_interrogate"])

                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")

    def test_negated_learning_language_remains_conversational(self):
        for message in (
            "I'm just chatting, not trying to study anything.",
            "We are only talking, not asking you to teach us.",
            "Let's chat; I do not want a Question Map.",
            "Let’s keep chatting—I don’t want to learn a topic.",
            "Don’t explain anything—I just want company.",
            "I don’t need a Question Map; tell me how you’re doing.",
        ):
            with self.subTest(message=message):
                intent = detect_intent(message)
                self.assertEqual(intent["intent"], "smalltalk")
                self.assertFalse(intent["should_interrogate"])

                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")

    def test_varied_casual_sequence_never_creates_question_maps(self):
        messages = (
            "You seem unusually serious tonight.",
            "Relax, I’m only teasing you.",
            "No analysis please; just play along.",
            "I don’t want an explanation—I want a casual answer.",
            "Let’s not turn every thought into a lesson.",
            "Could we simply hang out for a minute?",
            "What snack goes best with late-night tea?",
            "I’m leaning toward biscuits.",
            "That is probably the safest choice.",
            "Do you have a terrible biscuit joke?",
            "I regret asking already.",
            "My window is making strange noises in the wind.",
            "It sounds more dramatic than it is.",
            "Would you investigate or ignore it?",
            "I’d probably hide under the blanket.",
            "That was obviously a heroic plan.",
            "Anyway, are you still enjoying this chat?",
            "Don’t teach me about bravery; I’m joking.",
            "We can leave the serious topics for tomorrow.",
            "Thanks for keeping me company.",
            "Okay, now I really am saying good night.",
        )
        for message in messages:
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["categories"], {})

    def test_casual_wording_with_named_subject_remains_learning(self):
        result = detect_intent("I am casually chatting about linear regression")
        self.assertTrue(result["should_interrogate"])

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

    def test_praise_for_ini_is_conversation_not_a_learning_topic(self):
        for message in (
            "Good job InI",
            "Amazing job ini",
            "Well done InI",
            "That's awesome",
            "thats awesome",
            "This is brilliant",
            "That is really helpful",
        ):
            with self.subTest(message=message):
                result = interrogate(message)
                self.assertEqual(result["response_mode"], "conversation")
                self.assertEqual(result["intent"], "affirmation")
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

    def test_compound_learning_question_routes_to_full_interrogate(self):
        result = detect_intent(
            "What is linear regression, what are its main types, and how does "
            "it relate to regression analysis and machine learning?"
        )
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

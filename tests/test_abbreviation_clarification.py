import unittest
from pathlib import Path
from api.abbreviation_clarification import abbreviation_clarification
from api.intent_layer import detect_intent
from streamlit_app.subject_choice import recognised_subject


class AbbreviationClarificationTests(unittest.TestCase):
    def test_bare_ml_requires_meaning_confirmation(self):
        for text in ("ML", "ml", " ML ", "ML?", "ML."):
            intent = detect_intent(text)
            self.assertEqual(intent["intent"], "abbreviation_clarification")
            self.assertIn("maximum likelihood", intent["reply"])
            self.assertIn("millilitres", intent["reply"])
            self.assertFalse(intent["should_interrogate"])
            self.assertFalse(intent["should_answer_direct"])
            self.assertEqual(intent["followups"], [])
            self.assertEqual(recognised_subject(text), "")

    def test_other_known_ambiguous_abbreviations_are_narrowly_matched(self):
        for text in ("AI", "OS", "CV", "RL"):
            self.assertTrue(abbreviation_clarification(text))
        for text in ("Machine Learning", "Explain ML models", "What is ML?", "ML in healthcare",
                     "maximum likelihood", "5 ml", "CPU", "DNA", "Physics", "", "small"):
            self.assertEqual(abbreviation_clarification(text), "", text)

    def test_full_subject_still_qualifies_for_subject_choice(self):
        self.assertEqual(recognised_subject("Machine Learning"), "Machine Learning")
        self.assertNotEqual(detect_intent("Machine Learning")["intent"], "abbreviation_clarification")

    def test_ui_guard_precedes_context_and_provider_generation(self):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        self.assertIn('and not abbreviation_clarification(topic_text)', source)
        self.assertIn('if abbreviation_clarification(display_topic_text):', source)
        self.assertIn('"needs_clarification": False, "suppress_profile": True', source)
        self.assertIn('abbreviation_clarification(prompt)\n            or _local_conversation_answer', source)
        self.assertIn('is_meaning_check = payload_info.get("intent") == "abbreviation_clarification"', source)


if __name__ == "__main__":
    unittest.main()

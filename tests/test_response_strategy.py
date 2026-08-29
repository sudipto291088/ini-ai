import unittest

from api.response_strategy import (
    CONDITIONAL_KS,
    KS_EXPLICIT,
    KS_RECOMMENDED,
    NO_KS,
    assess_ks_suitability,
    extract_knowledge_structure_topic,
    fallback_learning_questions,
    select_lightweight_questions,
)


class ResponseStrategyTests(unittest.TestCase):
    def test_explicit_knowledge_structure_request(self):
        query = "Show me the complete Knowledge Structure for linear regression."
        self.assertEqual(assess_ks_suitability(query, {}), KS_EXPLICIT)
        self.assertEqual(extract_knowledge_structure_topic(query), "linear regression")

    def test_conversation_never_surfaces_knowledge_structure(self):
        self.assertEqual(
            assess_ks_suitability(
                "Thanks InI.",
                {"response_mode": "conversation", "intent": "thanks"},
            ),
            NO_KS,
        )

    def test_negated_knowledge_structure_request_is_not_explicit(self):
        self.assertEqual(
            assess_ks_suitability(
                "Don't open the Knowledge Structure; just answer me.",
                {"response_mode": "conversation", "intent": "smalltalk"},
            ),
            NO_KS,
        )

    def test_normal_learning_query_is_conditional(self):
        self.assertEqual(
            assess_ks_suitability(
                "What is Docker?",
                {"intent": "topic_explore", "categories": {"Foundations": ["Q"]}},
            ),
            CONDITIONAL_KS,
        )

    def test_broad_learning_query_recommends_knowledge_structure(self):
        self.assertEqual(
            assess_ks_suitability(
                "Teach me linear regression from scratch.",
                {"intent": "topic_explore", "categories": {"Foundations": ["Q"]}},
            ),
            KS_RECOMMENDED,
        )

    def test_lightweight_questions_are_intellectually_diverse(self):
        categories = {
            "Foundations": [{"question": "What problem does Docker solve?"}],
            "Mechanisms": [{"question": "What happens when a container starts?"}],
            "Applications": [{"question": "Where does Kubernetes enter the picture?"}],
            "Pitfalls": [{"question": "Where can containers fail operationally?"}],
        }
        self.assertEqual(
            select_lightweight_questions("What is Docker?", categories),
            [
                "What problem does Docker solve?",
                "What happens when a container starts?",
                "Where does Kubernetes enter the picture?",
            ],
        )

    def test_compound_ethics_query_preserves_named_dimensions(self):
        categories = {
            "Mechanisms": [{"question": "How does Cas9 cut a DNA target?"}],
            "Methods & Tools": [{"question": "How are guide RNAs designed?"}],
            "Pitfalls": [
                {"question": "Which off-target and delivery risks limit CRISPR?"},
                {"question": "What ethical and consent concerns affect germline editing?"},
            ],
            "Applications": [{"question": "Which diseases could CRISPR treat?"}],
        }
        selected = select_lightweight_questions(
            "How does CRISPR edit DNA, and what scientific and ethical limitations affect its use?",
            categories,
        )
        joined = " ".join(selected).lower()
        self.assertEqual(len(selected), 3)
        self.assertIn("ethical", joined)
        self.assertTrue("risk" in joined or "off-target" in joined)
        self.assertTrue("cas9" in joined or "mechanism" in joined)

    def test_learning_fallback_still_supplies_three_directions(self):
        questions = fallback_learning_questions(
            "Why does inflation occur, and how do interest-rate increases attempt to control it?"
        )
        self.assertEqual(len(questions), 3)
        self.assertIn("mechanisms", questions[0])


if __name__ == "__main__":
    unittest.main()

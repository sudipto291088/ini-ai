import unittest

from api.response_strategy import (
    CONDITIONAL_KS,
    KS_EXPLICIT,
    KS_RECOMMENDED,
    NO_KS,
    assess_ks_suitability,
    extract_knowledge_structure_topic,
    fallback_learning_questions,
    initial_answer_opening,
    knowledge_structure_bridge,
    knowledge_structure_action,
    no_knowledge_structure_notice,
    question_intelligence_limit,
    related_questions_bridge,
    select_lightweight_questions,
)


class ResponseStrategyTests(unittest.TestCase):
    def test_human_guidance_copy_is_stable_and_contextual(self):
        query = "What is data science?"
        self.assertEqual(initial_answer_opening(query), initial_answer_opening(query))
        self.assertTrue(initial_answer_opening(query).strip())
        self.assertIn("questions", related_questions_bridge(query, 6).casefold())
        self.assertIn(
            "knowledge structure",
            knowledge_structure_bridge(query, CONDITIONAL_KS).casefold(),
        )

    def test_question_bridge_uses_the_real_available_count(self):
        seed_with_counted_variant = next(
            seed
            for seed in (f"topic-{index}" for index in range(100))
            if "six" in related_questions_bridge(seed, 6).casefold()
        )
        bridge = related_questions_bridge(seed_with_counted_variant, 6)
        self.assertIn("six", bridge.casefold())
        self.assertNotIn("three", bridge.casefold())

    def test_direct_current_query_explains_why_no_ks_was_created(self):
        notice = no_knowledge_structure_notice("What is today's gas price?")
        self.assertIn("knowledge structure", notice.casefold())
        self.assertTrue(
            any(term in notice.casefold() for term in ("direct", "current", "factual"))
        )

    def test_explicit_knowledge_structure_request(self):
        query = "Show me the complete Knowledge Structure for linear regression."
        self.assertEqual(assess_ks_suitability(query, {}), KS_EXPLICIT)
        self.assertEqual(extract_knowledge_structure_topic(query), "linear regression")

    def test_knowledge_structure_button_builds_typed_action(self):
        action = knowledge_structure_action("  Inflation: causes and effects  ")
        self.assertEqual(action["request_kind"], "knowledge_structure")
        self.assertEqual(action["semantic_topic"], "Inflation: causes and effects")
        self.assertIn("Knowledge Structure", action["prompt"])

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
            "Why does inflation occur, and how do interest-rate increases attempt to control it?",
            limit=6,
        )
        self.assertEqual(len(questions), 6)
        self.assertIn("mechanisms", questions[0])

    def test_question_intelligence_uses_three_six_nine_model(self):
        self.assertEqual(question_intelligence_limit("What is Docker?"), 3)
        self.assertEqual(
            question_intelligence_limit(
                "Why does inflation occur, and how do interest rates control it?"
            ),
            6,
        )
        self.assertEqual(
            question_intelligence_limit(
                "How does CRISPR edit DNA, and what scientific and ethical limitations affect its use?"
            ),
            9,
        )

    def test_deep_map_can_supply_nine_diverse_questions(self):
        categories = {
            category: [
                {"question": f"{category} question {index}?"}
                for index in range(1, 4)
            ]
            for category in (
                "Orientation", "Foundations", "Mechanisms", "Methods & Tools",
                "Applications", "Pitfalls", "Advanced / Future",
            )
        }
        selected = select_lightweight_questions(
            "Teach me this topic in depth, step by step.", categories, limit=9
        )
        self.assertEqual(len(selected), 9)
        self.assertEqual(len(set(selected)), 9)


if __name__ == "__main__":
    unittest.main()

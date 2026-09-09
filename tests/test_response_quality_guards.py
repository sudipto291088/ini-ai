import unittest
from unittest.mock import patch

from api.interrogate import CATEGORY_ORDER, _question_map_content_issues, interrogate
from api.response_accuracy import normalize_response_accuracy
from streamlit_app.knowledge_map import (
    _qualify_map_description,
    expanded_knowledge_map_entry,
)
from streamlit_app.response_profile import build_response_profile
from streamlit_app.structured_validation import validate_structured_learning_answer
from tests.test_structured_validation import VALID_RESPONSE


class ResponseQualityGuardTests(unittest.TestCase):
    def test_crisp_dm_recurring_claims_are_corrected_idempotently(self) -> None:
        source = (
            "CRISP-DM says feature engineering is usually the largest time sink and "
            "finds causal or predictive signals. ASUM-DM is a variant."
        )
        corrected = normalize_response_accuracy(source, "CRISP-DM")
        self.assertIn("Cross-Industry Standard Process for Data Mining (CRISP-DM)", corrected)
        self.assertNotIn("largest time sink", corrected)
        self.assertIn("predictive or associative patterns", corrected)
        self.assertIn("Analytics Solutions Unified Method (ASUM)", corrected)
        self.assertEqual(corrected, normalize_response_accuracy(corrected, "CRISP-DM"))

    def test_unknown_learning_topics_never_use_placeholder_profiles(self) -> None:
        for query in (
            "Explain plate tectonics",
            "Tell me about sonnet structure",
            "What is supply-chain resilience?",
        ):
            with self.subTest(query=query):
                rows = dict(build_response_profile(query, intent="topic_explore"))
                self.assertNotIn(rows["Entity type"].casefold(), {"learning inquiry", "learning question"})
                self.assertNotEqual(rows["Broad field"].casefold(), "not yet classified")
                self.assertTrue(rows["Prerequisites"])

    def test_validator_rejects_missing_acronym_expansion_and_risky_claims(self) -> None:
        source = VALID_RESPONSE.replace(
            '"Subject":"Gradient descent"',
            '"Subject":"CRISP-DM"',
        ).replace(
            "Major areas: Loss design, gradients, step sizes, and convergence.",
            "Major areas: Feature work is usually the largest time sink and reveals causal or predictive signals.",
        )
        result = validate_structured_learning_answer(source, "Explain CRISP-DM")
        self.assertFalse(result["valid"])
        self.assertTrue(any("Full form" in issue for issue in result["issues"]))
        self.assertTrue(any("ranking claim" in issue for issue in result["issues"]))
        self.assertTrue(any("causal language" in issue for issue in result["issues"]))

    def test_comparison_map_title_is_completed_without_word_clipping(self) -> None:
        title, _ = expanded_knowledge_map_entry(
            {
                "question": "How does CRISP-DM differ between industrial and customer analytics?",
                "map_title": "Industrial vs. customer",
                "map_description": "Different project settings change stakeholders, data access, and evaluation constraints.",
            },
            "Applications",
        )
        self.assertEqual(title, "Industrial and customer analytics")

        long_title = "Business understanding and deployment feedback across regulated analytics projects"
        preserved, _ = expanded_knowledge_map_entry(
            {"question": "How do regulated projects work?", "map_title": long_title},
            "Methods & Tools",
        )
        self.assertEqual(preserved, long_title)

    def test_asum_and_mlops_are_separated_from_core_crisp_dm(self) -> None:
        value = _qualify_map_description(
            "ASUM-DM adds model registries, drift monitoring, and automated retraining.",
            "CRISP-DM advanced practices",
        )
        self.assertIn("Analytics Solutions Unified Method (ASUM)", value)
        self.assertIn("Modern extensions", value)
        self.assertIn("not core phases", value)
        self.assertIn("not an official CRISP-DM variant", value)

    def test_generated_map_validation_rejects_fragments_and_meta_copy(self) -> None:
        categories = {
            "Orientation": [{
                "question": "How do industrial and customer analytics differ?",
                "map_title": "Industrial vs. customer",
                "map_description": "Explores the differences.",
            }]
        }
        issues = _question_map_content_issues(categories)
        self.assertTrue(any("description" in issue for issue in issues))

    def test_question_map_returns_its_canonical_profile_for_later_answers(self) -> None:
        counts = (5, 4, 4, 4, 3, 3, 3)
        categories = {
            category: [
                {
                    "question": f"How does photosynthesis relate to {category} item {index}?",
                    "map_title": f"{category.split()[0]} concept",
                    "map_description": "Named components and mechanisms form a concrete progressive learning branch.",
                }
                for index in range(count)
            ]
            for category, count in zip(CATEGORY_ORDER, counts)
        }
        profile = {
            "Entity type": "Biological process",
            "Broad field": "Biology",
            "Subject": "Photosynthesis",
            "Prerequisites": "Basic cell structure",
            "Related topics": "Chloroplasts; light reactions; carbon fixation",
            "Difficulty": "Beginner",
        }
        with patch("api.interrogate._llm_is_enabled", return_value=True), patch(
            "api.interrogate._llm_generate_questions_only",
            return_value=(["one", "two", "three"], categories, profile),
        ):
            result = interrogate("Tell me about photosynthesis")

        self.assertEqual(result["topic_profile"]["Subject"], "Photosynthesis")
        self.assertEqual(result["topic_profile"]["Broad field"], "Biology")


if __name__ == "__main__":
    unittest.main()

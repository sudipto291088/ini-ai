import unittest
from unittest.mock import patch

from api.interrogate import CATEGORY_ORDER, _topic_profile_issues, interrogate
from streamlit_app.subject_metadata import canonical_subject, normalize_topic_profile


QUERY = "Why can a strong correlation still fail to prove causation? Explain with one simple example."


class CausalSubjectMapTests(unittest.TestCase):
    def profile(self, subject):
        return {
            "Entity type": "Conceptual principle",
            "Broad field": "Statistics and causal inference",
            "Subject": subject,
            "Prerequisites": "Basic probability and statistics",
            "Related topics": "Confounding; reverse causation; causal graphs",
            "Difficulty": "Beginner",
        }

    def categories(self):
        return {
            category: [{
                "question": f"How does correlation relate to {category} concept {index}?",
                "map_title": f"Correlation concept {index}",
                "map_description": "Confounding and reverse causation distinguish statistical association from causal evidence.",
            } for index in range(count)]
            for category, count in zip(CATEGORY_ORDER, (5, 4, 4, 4, 3, 3, 3))
        }

    def test_observed_subjects_become_valid_without_losing_causal_clause(self):
        for subject in (
            "Why a strong correlation can fail to prove causation",
            "Why a strong correlation can still fail to prove causation",
            "Why correlation does not imply causation",
        ):
            with self.subTest(subject=subject):
                profile = normalize_topic_profile(self.profile(subject), QUERY)
                self.assertEqual(profile["Subject"], "Reasons " + subject[0].lower() + subject[1:])
                self.assertEqual(_topic_profile_issues(profile, QUERY), [])
                self.assertEqual(normalize_topic_profile(profile, QUERY), profile)

    def test_map_is_accepted_on_first_attempt_after_subject_repair(self):
        with patch("api.interrogate._llm_is_enabled", return_value=True), patch(
            "api.interrogate._llm_generate_questions_only",
            return_value=(["one", "two", "three"], self.categories(), self.profile("Why correlation does not imply causation")),
        ) as generate, patch("api.interrogate._llm_generate_questions_only_rescue") as rescue:
            result = interrogate(QUERY)
        self.assertTrue(result["categories"])
        self.assertEqual(result["topic_profile"]["Broad field"], "Statistics and causal inference")
        self.assertEqual(result["topic_profile"]["Subject"], "Reasons why correlation does not imply causation")
        generate.assert_called_once()
        rescue.assert_not_called()

    def test_repair_does_not_bypass_map_quality_checks(self):
        categories = self.categories()
        categories["Orientation"][0]["map_description"] = "Explores this topic."
        bad_map = (["one", "two", "three"], categories, self.profile("Why correlation does not imply causation"))
        with patch("api.interrogate._llm_is_enabled", return_value=True), patch(
            "api.interrogate._llm_generate_questions_only", return_value=bad_map,
        ), patch("api.interrogate._llm_generate_questions_only_rescue", return_value=bad_map):
            result = interrogate(QUERY)
        self.assertFalse(result.get("categories"))

    def test_existing_specialized_subjects_are_preserved(self):
        self.assertEqual(canonical_subject("Why do neural networks need activation functions?"), "activation functions in neural networks")
        self.assertEqual(canonical_subject("Photosynthesis"), "Photosynthesis")


if __name__ == "__main__":
    unittest.main()

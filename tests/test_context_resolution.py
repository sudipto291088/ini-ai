import unittest

from api.context_resolution import find_contextual_topic_match


class ContextResolutionTests(unittest.TestCase):
    def test_strong_contextual_near_match_is_detected(self):
        result = find_contextual_topic_match(
            "multi score scaling",
            [
                "multi-core scaling",
                "cache coherence",
                "task scheduling",
            ],
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["candidate"], "multi-core scaling")

    def test_unrelated_topic_is_not_forced_into_context(self):
        self.assertIsNone(
            find_contextual_topic_match(
                "data science",
                ["multi-core scaling", "cache coherence", "task scheduling"],
            )
        )

    def test_ambiguous_near_matches_are_not_silently_selected(self):
        self.assertIsNone(
            find_contextual_topic_match(
                "core scaling",
                ["multi-core scaling", "many-core scaling"],
            )
        )

    def test_long_sentence_is_not_treated_as_a_topic_typo(self):
        self.assertIsNone(
            find_contextual_topic_match(
                "can you explain how multi score scaling works in modern processors",
                ["multi-core scaling"],
            )
        )

    def test_specific_topic_containing_parent_topic_is_preserved(self):
        for query in (
            "quant artificial intelligence",
            "quantum artificial intelligence",
            "sovereign artificial intelligence",
        ):
            with self.subTest(query=query):
                self.assertIsNone(
                    find_contextual_topic_match(
                        query,
                        ["artificial intelligence"],
                    )
                )


if __name__ == "__main__":
    unittest.main()

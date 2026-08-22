import unittest

from api.context_resolution import (
    find_contextual_topic_match,
    resolve_learning_followup,
    should_continue_practical_context,
)


class ContextResolutionTests(unittest.TestCase):
    def test_new_short_learning_topics_break_old_mcp_context(self):
        context = {
            "original_request": "How do I configure a local MCP server for VS Code?",
            "resolved_request": "Configure a local MCP server for VS Code",
            "last_answer": "Choose STDIO or HTTP, then verify the MCP server.",
        }
        for query in (
            "a/b testing",
            "conversion rate optimization",
            "controlled experimentation",
        ):
            with self.subTest(query=query):
                self.assertFalse(
                    should_continue_practical_context(query, **context)
                )

    def test_relevant_short_replies_keep_practical_context(self):
        context = {
            "original_request": "How do I configure a local MCP server for VS Code?",
            "resolved_request": "Configure a local MCP server for VS Code",
            "last_answer": "Is the provider STDIO or HTTP?",
        }
        for reply in ("VS Code", "STDIO", "I don't know", "go ahead"):
            with self.subTest(reply=reply):
                self.assertTrue(
                    should_continue_practical_context(reply, **context)
                )

    def test_single_token_topic_does_not_revive_old_practical_context(self):
        self.assertFalse(
            should_continue_practical_context(
                "5G",
                original_request="How does OAuth2 work?",
                last_answer="Which network are you using?",
            )
        )

    def test_learning_references_resolve_against_latest_topic(self):
        oauth = "How does OAuth2 authorization-code flow with PKCE work?"
        self.assertEqual(
            resolve_learning_followup(
                "How is it different from OpenID Connect?", oauth
            ),
            "How is OAuth2 different from OpenID Connect?",
        )
        self.assertIn(
            "Should governments ban facial recognition",
            resolve_learning_followup(
                "I don't know enough to judge—what should I learn first?",
                "Should governments ban facial recognition in public spaces?",
            ),
        )
        self.assertEqual(resolve_learning_followup("5G", oauth), "5G")
        self.assertEqual(
            resolve_learning_followup(
                "What about its health risks, and how strong is the evidence?",
                "5G",
            ),
            "What are the health risks of 5G, and how strong is the evidence specifically about 5G?",
        )

    def test_complete_new_topic_is_not_contaminated_by_previous_topic(self):
        query = (
            "What caused the Renaissance, what were its major intellectual "
            "and artistic movements, and how did it influence modern science?"
        )

        self.assertEqual(
            resolve_learning_followup(query, "DNA replication"),
            query,
        )

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

import unittest

from streamlit_app.response_profile import build_response_profile


class ResponseProfileTests(unittest.TestCase):
    def test_casual_greeting_has_sociolinguistic_profile(self):
        rows = dict(build_response_profile("Heyyyy what's up?", "greeting", "conversation"))
        self.assertEqual(rows["Name type"], "Informal greeting")
        self.assertEqual(rows["Broad field"], "Sociolinguistics")

    def test_casual_testing_has_interaction_profile(self):
        rows = dict(build_response_profile("Just casually testing you", "smalltalk", "conversation"))
        self.assertEqual(rows["Subject"], "Casual testing of InI")
        self.assertIn("Intent detection", rows["Related topics"])

    def test_positive_acknowledgement_has_conversational_profile(self):
        rows = dict(
            build_response_profile(
                "That's awesome",
                intent="affirmation",
                response_mode="conversation",
            )
        )
        self.assertEqual(rows["Name type"], "Positive acknowledgement")
        self.assertEqual(rows["Entity type"], "Social utterance")
        self.assertEqual(rows["Broad field"], "Interpersonal communication")

    def test_practical_query_has_full_task_profile(self):
        rows = dict(
            build_response_profile(
                "How do I install an MCP server locally?",
                response_mode="carm",
                context_intent="installation",
            )
        )
        self.assertEqual(rows["Entity type"], "Procedure")
        self.assertEqual(rows["Broad field"], "Technical configuration")

    def test_enterprise_bridge_is_classified_as_implementation_guidance(self):
        rows = dict(
            build_response_profile(
                "How do I add Siebel CRM as a local MCP server?",
                response_mode="carm",
                context_intent="integration",
            )
        )
        self.assertEqual(rows["Name type"], "Implementation guidance")
        self.assertEqual(rows["Entity type"], "Technical integration and configuration")
        self.assertEqual(rows["Broad field"], "Systems integration")

    def test_learning_conversation_uses_subject_profile_with_prerequisites(self):
        rows = dict(
            build_response_profile(
                "How do transformer-based AI models understand context and hallucinate?",
                intent="topic_explore",
                response_mode="conversation",
                context_intent="explore",
            )
        )
        self.assertEqual(rows["Name type"], "Learning question")
        self.assertEqual(
            rows["Broad field"],
            "Artificial intelligence / Natural language processing",
        )
        self.assertIn("probability", rows["Prerequisites"])

    def test_marine_biology_question_has_specific_profile(self):
        rows = dict(
            build_response_profile(
                "How do coral reefs recover after bleaching?",
                response_mode="conversation",
                context_intent="learning",
            )
        )
        self.assertEqual(rows["Broad field"], "Marine biology / Ecology")
        self.assertIn("Coral symbiosis", rows["Related topics"])
        self.assertIn("Ecosystems", rows["Prerequisites"])

    def test_bare_computer_vision_topic_is_not_a_learning_question(self):
        rows = dict(
            build_response_profile(
                "Computer vision",
                intent="topic_explore",
                response_mode="conversation",
                context_intent="explore",
            )
        )
        self.assertEqual(rows["Name type"], "Learning topic")
        self.assertEqual(rows["Entity type"], "Artificial-intelligence discipline")
        self.assertEqual(
            rows["Broad field"],
            "Artificial intelligence / Computer science",
        )
        self.assertIn("convolutional networks", rows["Related topics"])

    def test_bare_artificial_intelligence_topic_has_real_classification(self):
        rows = dict(
            build_response_profile(
                "Artificial intelligence",
                intent="topic_explore",
                response_mode="conversation",
                context_intent="explore",
            )
        )
        self.assertEqual(rows["Name type"], "Learning topic")
        self.assertEqual(rows["Entity type"], "Computing discipline")
        self.assertEqual(rows["Broad field"], "Computer science")
        self.assertIn("knowledge representation", rows["Related topics"])

    def test_algorithm_is_classified_under_computer_science(self):
        rows = dict(
            build_response_profile(
                "algorithm",
                intent="topic_explore",
                response_mode="conversation",
                context_intent="explore",
            )
        )
        self.assertEqual(rows["Name type"], "Learning topic")
        self.assertEqual(rows["Entity type"], "Computational procedure or method")
        self.assertEqual(rows["Broad field"], "Computer science / Algorithms")
        self.assertIn("time complexity", rows["Related topics"])
        self.assertIn("programming", rows["Prerequisites"])

    def test_unknown_learning_subject_never_returns_placeholder_labels(self):
        rows = dict(
            build_response_profile(
                "How are medieval manuscripts preserved?",
                response_mode="conversation",
                context_intent="learning",
            )
        )
        self.assertNotEqual(rows["Entity type"], "Concept, process, or subject")
        self.assertNotEqual(rows["Broad field"], "Knowledge domain")
        self.assertNotEqual(
            rows["Related topics"],
            "Foundations, mechanisms, applications, limitations",
        )

    def test_rag_and_antibiotic_resistance_have_subject_profiles(self):
        cases = (
            (
                "How does retrieval-augmented generation reduce hallucinations?",
                "Artificial intelligence / Information retrieval",
                "vector search",
            ),
            (
                "What causes antibiotic resistance?",
                "Microbiology / Public health",
                "stewardship",
            ),
        )
        for query, expected_field, expected_related in cases:
            with self.subTest(query=query):
                rows = dict(
                    build_response_profile(
                        query,
                        intent="topic_explore",
                        response_mode="standard",
                        context_intent="learning",
                    )
                )
                self.assertEqual(rows["Name type"], "Learning question")
                self.assertEqual(rows["Broad field"], expected_field)
                self.assertIn(expected_related, rows["Related topics"])

    def test_federated_learning_privacy_profile_is_specific(self):
        rows = dict(
            build_response_profile(
                "How does federated learning protect privacy, what information can still leak, and which techniques reduce those risks?",
                intent="topic_explore",
                response_mode="standard",
                context_intent="learning",
            )
        )
        self.assertEqual(rows["Subject"], "Privacy in federated learning")
        self.assertEqual(
            rows["Broad field"],
            "Machine learning / Privacy-preserving AI / Distributed systems",
        )
        self.assertIn("gradient leakage", rows["Related topics"])
        self.assertIn("secure aggregation", rows["Related topics"])
        self.assertIn("distributed optimization", rows["Prerequisites"])
        self.assertNotIn("directly related", rows["Prerequisites"])

    def test_rag_profile_uses_concept_subject_instead_of_truncated_question(self):
        rows = dict(
            build_response_profile(
                "How does retrieval-augmented generation (RAG) work, why can it still "
                "produce incorrect answers, and which retrieval and evaluation techniques "
                "improve its reliability?",
                intent="topic_explore",
                response_mode="standard",
                context_intent="learning",
            )
        )

        self.assertEqual(rows["Subject"], "Retrieval-Augmented Generation (RAG)")
        self.assertIn("reranking", rows["Related topics"])
        self.assertNotIn("incorrect answe", rows["Subject"])

    def test_qec_does_not_leak_rag_profile_from_fragile(self):
        rows = dict(build_response_profile(
            "How does quantum error correction protect fragile qubits, and why is fault-tolerant quantum computing so difficult?",
            intent="topic_explore", response_mode="standard", context_intent="learning",
        ))
        self.assertEqual(rows["Subject"], "Quantum error correction and fault tolerance")
        self.assertIn("Quantum computing", rows["Broad field"])
        self.assertNotIn("retrieval", rows["Related topics"].lower())

    def test_mrna_profile_is_specific_and_not_truncated(self):
        rows = dict(build_response_profile(
            "How do mRNA vaccines work, how does the immune system respond, and why can protection weaken over time?",
            intent="topic_explore", response_mode="standard", context_intent="learning",
        ))
        self.assertEqual(rows["Subject"], "mRNA vaccines and immune protection")
        self.assertIn("Immunology", rows["Broad field"])
        self.assertIn("antigen presentation", rows["Related topics"])

    def test_carbon_policy_profile_is_environmental_economics(self):
        rows = dict(build_response_profile(
            "How do carbon taxes and cap-and-trade systems differ, and what determines whether either policy reduces emissions effectively?",
            intent="topic_explore", response_mode="standard", context_intent="learning",
        ))
        self.assertEqual(rows["Subject"], "Carbon pricing and emissions trading")
        self.assertEqual(rows["Broad field"], "Environmental economics / Climate policy")

    def test_reviewed_database_inflation_and_backprop_profiles_are_specific(self):
        cases = {
            "How does a database index make queries faster?": "Database indexing and query performance",
            "Why does inflation occur, and what effects does it have on an economy?": "Inflation: causes and economic effects",
            "How does a neural network learn through backpropagation?": "Neural-network learning through backpropagation",
        }
        for query, subject in cases.items():
            rows = dict(build_response_profile(
                query, intent="topic_explore", response_mode="standard", context_intent="learning"
            ))
            self.assertEqual(rows["Subject"], subject)
            self.assertNotEqual(rows["Broad field"], "Interdisciplinary study")


if __name__ == "__main__":
    unittest.main()

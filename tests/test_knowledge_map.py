import unittest

from streamlit_app.knowledge_map import (
    compact_knowledge_map_projection,
    expanded_knowledge_map_entry,
)


def test_compound_linear_regression_query_uses_canonical_anchor():
    projection = compact_knowledge_map_projection(
        "What is linear regression, what are its main types, and how does it "
        "relate to regression analysis and machine learning?"
    )

    assert projection.anchor == "linear regression"
    assert projection.directions == (
        "Define the topic",
        "Explore the main types",
        "Connect related fields",
    )


def test_rewritten_compound_query_does_not_fill_central_capsule():
    projection = compact_knowledge_map_projection(
        "Linear regression, what are Artificial intelligence's main types, "
        "and how does Artificial intelligence relate to regression analysis "
        "and machine learning"
    )

    assert projection.anchor == "Linear regression"
    assert "Artificial intelligence" not in projection.anchor
    assert "Explore the main types" in projection.directions
    assert "Connect related fields" in projection.directions


def test_direct_topic_and_mechanism_queries_remain_compact():
    assert compact_knowledge_map_projection("Artificial intelligence").anchor == (
        "Artificial intelligence"
    )
    assert compact_knowledge_map_projection("How does backpropagation work?").anchor == (
        "backpropagation"
    )
    assert compact_knowledge_map_projection(
        "What caused the French Revolution, what were its major stages, and how did it influence democracy?"
    ).anchor == "French Revolution"
    assert compact_knowledge_map_projection("What is a neural network?").anchor == (
        "neural network"
    )


def test_compound_outcome_queries_use_short_subject_anchors():
    assert compact_knowledge_map_projection(
        "What does the research show about how universal basic income affects "
        "employment, poverty, and psychological well-being?"
    ).anchor == "universal basic income"
    assert compact_knowledge_map_projection(
        "How should a retrieval-augmented generation system be evaluated for "
        "retrieval quality, answer faithfulness, and end-to-end usefulness?"
    ).anchor == "retrieval-augmented generation system"
    assert compact_knowledge_map_projection(
        "How do light intensity, carbon dioxide concentration, and temperature "
        "affect the rate of photosynthesis?"
    ).anchor == "photosynthesis"


def test_trailing_mechanism_verbs_do_not_enter_compact_anchor():
    assert compact_knowledge_map_projection(
        "How do CRISPR-Cas9 off-target effects occur, and what methods are used "
        "to detect and reduce them?"
    ).anchor == "CRISPR-Cas9 off-target effects"


def test_privacy_questions_use_grammatical_concept_led_anchors():
    projection = compact_knowledge_map_projection(
        "How does federated learning protect privacy, what information can still "
        "leak, and which techniques reduce those risks?"
    )

    assert projection.anchor == "Privacy in federated learning"

    assert compact_knowledge_map_projection(
        "How does secure messaging protect privacy, and what can still leak?"
    ).anchor == "Privacy in secure messaging"
    assert compact_knowledge_map_projection(
        "How does sensor fusion improve accuracy, and what are its limits?"
    ).anchor == "Accuracy of sensor fusion"


def test_generated_map_descriptions_qualify_absolute_claims():
    title, description = expanded_knowledge_map_entry(
        {
            "question": "What problems does retrieval-augmented generation address?",
            "map_title": "RAG problem scope",
            "map_description": "Solves knowledge staleness and reduces hallucinations.",
        },
        "Orientation",
    )

    assert title == "RAG problem scope"
    assert description == "Helps address knowledge staleness and reduces hallucinations."


def test_saved_map_mechanism_repairs_are_scoped_to_misleading_claims():
    cases = (
        ("Clients create pairwise masks; masks cancel so the aggregate remains decryptable.", "pairwise masks cancel during summation"),
        ("Edge devices favor local DP; enterprises prefer central DP.", "trust assumptions"),
        ("Prompts and weak verification chains reduce hallucinations.", "claim-to-source entailment checks"),
        ("Retrieve-then-generate, retrieve-and-read, and fusion-in-decoder merge evidence.", "overlapping design choices"),
    )
    for description, expected in cases:
        _, actual = expanded_knowledge_map_entry(
            {"map_title": "Mechanism choices", "map_description": description},
            "Mechanisms",
        )
        assert expected in actual

    _, unchanged = expanded_knowledge_map_entry(
        {"map_title": "Gaussian elimination", "map_description": "Solves a nonsingular linear system by elimination and back substitution."},
        "Methods & Tools",
    )
    assert unchanged.startswith("Solves a nonsingular linear system")


def test_negative_performance_questions_use_general_concept_led_anchors():
    cases = {
        "Why does linear regression perform badly when there are outliers?": (
            "Performance of linear regression with outliers"
        ),
        "Why do neural networks perform poorly when the data is imbalanced?": (
            "Performance of neural networks with imbalanced data"
        ),
        "Why does GPS work unreliably in dense urban areas?": (
            "Performance of GPS in dense urban areas"
        ),
        "Why do lithium-ion batteries behave worse under extreme cold?": (
            "Performance of lithium-ion batteries under extreme cold"
        ),
        "Linear regression perform badly when there are outliers": (
            "Performance of Linear regression with outliers"
        ),
        "Neural networks perform poorly when data is imbalanced": (
            "Performance of Neural networks with imbalanced data"
        ),
    }

    for query, expected in cases.items():
        assert compact_knowledge_map_projection(query).anchor == expected


def test_conversational_learning_prefixes_leave_only_the_subject():
    cases = {
        "What can you tell me about quant?": "quant",
        "Could you tell me about DNA replication?": "DNA replication",
        "Tell me about plate tectonics.": "plate tectonics",
    }

    for query, expected in cases.items():
        assert compact_knowledge_map_projection(query).anchor == expected


class CompactKnowledgeMapTitleTests(unittest.TestCase):
    def test_technical_process_queries_use_concept_led_titles(self):
        cases = {
            (
                "How should time-series features be engineered without data leakage, "
                "and how do lag features, rolling statistics, seasonality, and validation "
                "strategy fit together?"
            ): "Time-series feature engineering",
            (
                "How can causal effects be estimated from observational data, and how do "
                "confounding, propensity scores, instrumental variables, and sensitivity "
                "analysis fit together?"
            ): "Causal-effect estimation",
            (
                "How do batch, stochastic, and mini-batch gradient descent differ, and how "
                "do learning rate, momentum, and adaptive optimizers affect convergence?"
            ): "Gradient-descent optimization",
            (
                "How does self-attention work in a Transformer, what roles do queries, "
                "keys, values, positional encoding, and multi-head attention play?"
            ): "Transformer self-attention",
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(
                    compact_knowledge_map_projection(query).anchor,
                    expected,
                )

    def test_generic_convergence_topic_uses_question_map_context(self):
        projection = compact_knowledge_map_projection(
            "convergence",
            {
                "Orientation": [{"question": "What optimizer families include gradient descent?"}],
                "Mechanisms": [{"question": "How do batch size, stochastic noise, and momentum affect convergence?"}],
            },
        )

        self.assertEqual(projection.anchor, "Gradient-descent optimization")


def test_expanded_map_prefers_topic_metadata_over_question_text():
    title, description = expanded_knowledge_map_entry(
        {
            "question": "How does ordinary least squares compute coefficient estimates?",
            "map_title": "Ordinary least squares",
            "map_description": "Connects the objective function to coefficient estimation.",
        },
        "Mechanisms",
    )

    assert title == "Ordinary least squares"
    assert description == "Connects the objective function to coefficient estimation."


def test_expanded_map_fallback_never_displays_a_long_question():
    title, description = expanded_knowledge_map_entry(
        {"question": "How does gradient descent work and why does its learning rate matter?"},
        "Mechanisms",
    )

    assert title == "gradient descent"
    assert "?" not in title
    assert len(title.split()) <= 7
    assert description == "Explains the process, relationships, and forces that make it work."


def test_expanded_map_fallback_recognizes_common_curriculum_topics():
    title, _ = expanded_knowledge_map_entry(
        {"question": "Which delivery methods are appropriate for CRISPR editors?"},
        "Methods & Tools",
    )
    assert title == "Delivery methods"

    title, _ = expanded_knowledge_map_entry(
        {"question": "What are the major open research problems for safe editing?"},
        "Advanced / Future",
    )
    assert title == "Open research problems"

    title, _ = expanded_knowledge_map_entry(
        {"question": "Define and contrast the major CRISPR subtypes: DNA-cleaving nucleases and base editors."},
        "Foundations",
    )
    assert title == "Major CRISPR subtypes"

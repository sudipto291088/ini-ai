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

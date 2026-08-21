from streamlit_app.knowledge_map import compact_knowledge_map_projection


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

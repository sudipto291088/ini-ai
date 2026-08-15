from api.intent_layer import detect_intent
from api.interrogate import (
    _normalize_question_map_terminology,
    extract_topic,
    interrogate,
)


def test_question_map_repairs_duplicate_meiotic_stage_label():
    categories = {
        "Orientation": [
            {
                "question": "Compare meiotic I vs meiotic I in chromosome segregation."
            }
        ]
    }

    normalized = _normalize_question_map_terminology(categories)

    assert normalized["Orientation"][0]["question"] == (
        "Compare meiotic I vs meiotic II in chromosome segregation."
    )


def test_question_map_repairs_meiosis_stage_variants():
    categories = {
        "Orientation": [
            {"question": "What does meiosis I + meiosis I achieve?"},
            {"question": "How do errors in I vs I differ?"},
            {"question": "Which outcomes map to meiosis I and I?"},
        ]
    }

    normalized = _normalize_question_map_terminology(categories)
    questions = [item["question"] for item in normalized["Orientation"]]

    assert questions == [
        "What does meiosis I + meiosis II achieve?",
        "How do errors in I vs II differ?",
        "Which outcomes map to meiosis I and meiosis II?",
    ]


def test_question_map_repairs_numbered_stage_comparisons():
    categories = {
        "Orientation": [
            {"question": "Compare metaphase I and metaphase I."},
            {"question": "How do anaphase I versus anaphase I differ?"},
        ]
    }

    normalized = _normalize_question_map_terminology(categories)
    questions = [item["question"] for item in normalized["Orientation"]]

    assert questions == [
        "Compare metaphase I and metaphase II.",
        "How do anaphase I versus anaphase II differ?",
    ]


def test_greeting_is_natural_and_generic():
    greetings = (
        "hello InI",
        "Hello, how are you doing?",
        "Hey there, how's it going?",
        "Good morning, how are you?",
    )

    for greeting in greetings:
        result = detect_intent(greeting)
        assert result["intent"] == "greeting"
        assert result["should_interrogate"] is False
        assert "Boss" not in result["reply"]
        assert "What would you like to understand today?" in result["reply"]


def test_greeting_prefix_does_not_hide_a_learning_request():
    result = detect_intent("Hello, explain artificial intelligence")

    assert result["intent"] == "topic_explore"
    assert result["response_intent"] == "explain"


def test_greetings_never_create_question_maps():
    greetings = (
        "hello",
        "hello InI",
        "hello how are you doing?",
        "Hello, how are you doing?",
        "Hey there, how's it going?",
        "Good morning, how are you?",
    )

    for greeting in greetings:
        result = interrogate(greeting)
        assert result["intent"] == "greeting"
        assert result["categories"] == {}
        assert result["reply"]


def test_conversation_invitations_never_create_question_maps():
    invitations = (
        "lets chat",
        "let's chat",
        "let us talk",
        "can we chat?",
        "could we talk for a bit?",
        "I want to have a conversation",
        "shall we just talk casually?",
        "chat with me",
    )

    for invitation in invitations:
        intent = detect_intent(invitation)
        assert intent["intent"] == "smalltalk"
        assert intent["should_interrogate"] is False

        result = interrogate(invitation)
        assert result["response_mode"] == "conversation"
        assert result["suppress_profile"] is True
        assert result["categories"] == {}
        assert result["topic"] == ""


def test_conversational_lead_in_does_not_hide_named_learning_subject():
    learning_requests = (
        "Let's talk about machine learning",
        "Can we chat about neural networks?",
        "I want to talk about quantum computing",
        "Let us have a conversation about linear regression",
    )

    for prompt in learning_requests:
        result = detect_intent(prompt)
        assert result["intent"] == "topic_explore"
        assert result["should_interrogate"] is True


def test_learning_intents_are_detected():
    examples = {
        "Explain neural networks": "explain",
        "Compare Python versus Java": "compare",
        "Teach me machine learning from scratch": "teach",
        "Quiz me on quantum computing": "quiz",
        "Give me a worked example of PCA": "example",
        "Help me decide between SQL and NoSQL": "decide",
        "Help me decide between SQL and NoSQL for a rapidly growing e-commerce platform.": "decide",
        "Artificial intelligence": "explore",
    }

    for prompt, expected in examples.items():
        result = detect_intent(prompt)
        assert result["intent"] == "topic_explore"
        assert result["response_intent"] == expected


def test_substantive_how_questions_use_structured_learning():
    for prompt in (
        "How does quantum tunneling work?",
        "How do confidence intervals work?",
    ):
        result = detect_intent(prompt)
        assert result["intent"] == "topic_explore"
        assert result["should_interrogate"] is True
        assert result["should_answer_direct"] is False


def test_where_used_question_uses_structured_learning_not_location_lookup():
    result = detect_intent(
        "Where is the Fourier transform used in real-world signal processing?"
    )

    assert result["intent"] == "topic_explore"
    assert result["should_interrogate"] is True
    assert result["should_answer_direct"] is False


def test_quant_artificial_intelligence_uses_structured_learning():
    prompt = "what is quant artificial intelligence"

    result = detect_intent(prompt)

    assert result["intent"] == "topic_explore"
    assert result["should_interrogate"] is True
    assert result["should_answer_direct"] is False
    assert extract_topic(prompt) == "Quantitative Artificial Intelligence"


def test_quan_artificial_intelligence_requires_domain_clarification():
    result = interrogate("what is quan artificial intelligence")

    assert result["categories"] == {}
    assert result["needs_clarification"] is True
    assert result["intent"] == "clarify_topic_ambiguity"
    assert result["suppress_profile"] is True
    assert result["followups"] == [
        "Quantitative Artificial Intelligence",
        "Quantum Artificial Intelligence",
    ]


def test_alphanumeric_bare_topics_generate_full_learning_responses():
    for topic in ("web3", "oauth2", "ipv6", "5g"):
        result = detect_intent(topic)
        assert result["intent"] == "topic_explore", topic
        assert result["should_interrogate"] is True, topic
        assert result["should_answer_direct"] is False, topic


def test_specialized_intents_extract_clean_topics():
    examples = {
        "Compare Python versus Java": "Python versus Java",
        "Quiz me on quantum computing": "Quantum computing",
        "Give me a worked example of PCA": "PCA",
        "Help me decide between SQL and NoSQL": "SQL and NoSQL",
    }

    for prompt, expected in examples.items():
        assert extract_topic(prompt) == expected


def test_topic_extraction_ignores_conversational_lead_ins():
    examples = {
        "allright, explain spatial artificial intelligence": "Spatial artificial intelligence",
        "Alright, explain spatial artificial intelligence": "Spatial artificial intelligence",
        "okay, tell me about quantum computing": "Quantum computing",
        "well, teach me machine learning": "Machine Learning",
        "can you explain artificial intelligence": "Artificial intelligence",
        "could you tell me about cognitive science": "Cognitive science",
    }

    for prompt, expected in examples.items():
        assert extract_topic(prompt) == expected


def test_local_mcp_requests_are_treated_as_learning_topics():
    prompts = (
        "MCP server in the local system",
        "How do I add an MCP server locally?",
        "Set up MCP server on my computer",
        "I want to install Model Context Protocol server locally",
    )

    for prompt in prompts:
        result = detect_intent(prompt)
        assert result["intent"] == "topic_explore"
        assert result["should_interrogate"] is True


def test_local_mcp_requests_get_a_clean_topic_title():
    prompts = (
        "How do I add an MCP server locally?",
        "Set up MCP server on my computer",
        "My wife wants to add an MCP server in the local system. How should she do it?",
    )

    for prompt in prompts:
        assert extract_topic(prompt) == "Setting up an MCP server locally"


def test_normative_question_wording_routes_to_decision_learning():
    prompts = (
        "Should hospitals use AI to prioritize emergency patients?",
        "Is nuclear power a responsible solution to climate change?",
        "Are facial-recognition attendance systems ethical for schools?",
        "Would employee monitoring be an appropriate policy for remote teams?",
    )

    for prompt in prompts:
        result = detect_intent(prompt)
        assert result["intent"] == "topic_explore"
        assert result["response_intent"] == "decide"
        assert result["should_interrogate"] is True
        assert result["should_answer_direct"] is False


def test_ml_regression_sequence_never_routes_as_conversation():
    prompts = (
        "How does class imbalance affect a classification model, why can accuracy become misleading, and which evaluation metrics should be used instead?",
        "Why do decision trees tend to overfit, how does pruning address this, and what trade-offs does pruning introduce?",
        "How does gradient descent train a machine-learning model, what role does the learning rate play, and what happens when it is too high or too low?",
    )

    for prompt in prompts:
        result = detect_intent(prompt)
        assert result["intent"] == "topic_explore"
        assert result["should_interrogate"] is True
        assert result["should_answer_direct"] is False


def test_rate_named_learning_topics_are_not_mistaken_for_live_rates():
    for query in (
        "conversion rate optimization",
        "rate limiting",
        "heart rate variability",
    ):
        result = detect_intent(query)
        assert result["should_interrogate"] is True
        assert result["should_answer_direct"] is False

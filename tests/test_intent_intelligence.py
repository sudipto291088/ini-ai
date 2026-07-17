from api.intent_layer import detect_intent
from api.interrogate import extract_topic, interrogate


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


def test_specialized_intents_extract_clean_topics():
    examples = {
        "Compare Python versus Java": "Python versus Java",
        "Quiz me on quantum computing": "Quantum computing",
        "Give me a worked example of PCA": "PCA",
        "Help me decide between SQL and NoSQL": "SQL and NoSQL",
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

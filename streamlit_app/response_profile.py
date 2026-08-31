"""Small, structured profiles for every New Chat response mode."""

from __future__ import annotations

import re
from typing import List, Tuple


ProfileRows = List[Tuple[str, str]]


def _subject(text: str, limit: int = 92) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    return clean[:limit].rstrip() or "User message"


def _learning_name_type(text: str) -> str:
    """Distinguish a named topic from a question about that topic."""
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    question_openers = (
        "what ", "why ", "how ", "when ", "where ", "who ", "which ",
        "should ", "can ", "could ", "does ", "do ", "is ", "are ",
        "explain ", "compare ", "describe ", "show ",
    )
    return (
        "Learning question"
        if normalized.endswith("?") or normalized.startswith(question_openers)
        else "Learning topic"
    )


def _illustration_topic_profile(text: str, normalized: str) -> ProfileRows:
    """Describe the illustrated subject, rather than the user's UI action."""
    profiles = [
        (
            ("computer vision", "image recognition", "object detection"),
            "AI discipline",
            "Artificial intelligence",
            "Image processing, pattern recognition, deep learning, visual perception",
        ),
        (
            ("neural network", "deep learning"),
            "Machine learning model family",
            "Artificial intelligence",
            "Backpropagation, optimization, representation learning, model architectures",
        ),
        (
            ("machine learning",),
            "Computational learning field",
            "Artificial intelligence",
            "Supervised learning, unsupervised learning, model evaluation, deployment",
        ),
        (
            ("artificial intelligence",),
            "Computing discipline",
            "Computer science",
            "Machine learning, reasoning, perception, autonomous systems",
        ),
        (
            ("quantum computing", "quantum computer"),
            "Computing paradigm",
            "Quantum information science",
            "Qubits, superposition, entanglement, quantum algorithms",
        ),
        (
            ("kubernetes",),
            "Container orchestration platform",
            "Cloud computing",
            "Containers, clusters, deployments, scaling, DevOps",
        ),
        (
            ("data science",),
            "Interdisciplinary field",
            "Data science",
            "Statistics, data analysis, machine learning, visualization",
        ),
        (
            ("cognitive science",),
            "Interdisciplinary field",
            "Cognitive science",
            "Psychology, neuroscience, linguistics, artificial intelligence",
        ),
        (
            ("geothermal",),
            "Energy technology",
            "Renewable energy",
            "Earth heat, power generation, heat pumps, sustainability",
        ),
        (
            ("linear algebra", "calculus", "geometry", "algebra"),
            "Mathematical discipline",
            "Mathematics",
            "Definitions, operations, geometric meaning, practical applications",
        ),
    ]
    for keywords, entity_type, broad_field, related in profiles:
        if any(keyword in normalized for keyword in keywords):
            return [
                ("Name type", "Learning topic"),
                ("Entity type", entity_type),
                ("Broad field", broad_field),
                ("Subject", _subject(text)),
                ("Related topics", related),
            ]

    return [
        ("Name type", "Learning topic"),
        ("Entity type", "Concept or subject"),
        ("Broad field", "Knowledge domain"),
        ("Subject", _subject(text)),
        ("Related topics", "Foundations, mechanisms, applications, limitations"),
    ]


def _educational_topic_profile(text: str, normalized: str) -> ProfileRows:
    """Describe a learning subject and expose its foundations immediately."""
    profiles = [
        (
            ("algorithm", "data structure", "computational complexity"),
            "Computational procedure or method",
            "Computer science / Algorithms",
            "Correctness, termination, time complexity, space complexity, data structures, algorithm design",
            "Logical reasoning, basic programming, functions, discrete mathematics, and problem decomposition",
        ),
        (
            ("computer vision", "image recognition", "object detection"),
            "Artificial-intelligence discipline",
            "Artificial intelligence / Computer science",
            "Image processing, convolutional networks, pattern recognition, object detection, visual perception",
            "Linear algebra, probability, Python, image representation, and basic machine learning",
        ),
        (
            ("reinforcement learning", "q-learning", "policy gradient"),
            "Machine-learning paradigm",
            "Artificial intelligence / Machine learning",
            "Agents, environments, rewards, policies, value functions, exploration, sequential decisions",
            "Probability, expected value, optimization, Python, and basic machine learning",
        ),
        (
            ("feature scaling", "standardization", "normalization"),
            "Data-preprocessing technique",
            "Machine learning / Data preparation",
            "Standardization, min–max scaling, robust scaling, distance-based models, optimization",
            "Basic algebra, descriptive statistics, tabular data, and introductory machine learning",
        ),
        (
            ("gradient descent", "stochastic gradient descent", "sgd"),
            "Optimization algorithm",
            "Mathematical optimization / Machine learning",
            "Loss functions, gradients, learning rates, convergence, momentum, model training",
            "Functions, derivatives, vectors, basic linear algebra, and introductory model training",
        ),
        (
            ("statistics", "statistical inference", "descriptive statistics"),
            "Mathematical discipline",
            "Statistics and data analysis",
            "Distributions, sampling, estimation, uncertainty, hypothesis testing, regression",
            "Arithmetic, algebra, percentages, graphs, and basic probability",
        ),
        (
            ("transformer", "large language model", "llm", "language model"),
            "Machine learning model architecture",
            "Artificial intelligence / Natural language processing",
            "Attention, tokenization, embeddings, generation, hallucination",
            "Basic neural networks, vectors and matrices, probability, and tokenization",
        ),
        (
            ("neural network", "deep learning"),
            "Machine-learning model family",
            "Artificial intelligence / Machine learning",
            "Artificial neurons, layers, activation functions, backpropagation, optimization, architectures",
            "Algebra, functions, vectors and matrices, probability, Python, and basic machine learning",
        ),
        (
            ("machine learning",),
            "Computational learning field",
            "Artificial intelligence / Computer science",
            "Supervised learning, unsupervised learning, model evaluation, optimization, generalization",
            "Algebra, probability, statistics, programming, and working with tabular data",
        ),
        (
            ("artificial intelligence",),
            "Computing discipline",
            "Computer science",
            "Machine learning, reasoning, knowledge representation, perception, language, autonomous systems",
            "Programming concepts, algorithms, basic probability, linear algebra, and data representation",
        ),
        (
            ("data science", "data analysis"),
            "Data-analysis discipline",
            "Data science",
            "Statistics, data preparation, visualization, machine learning",
            "Basic statistics, spreadsheets or tabular data, and introductory programming",
        ),
        (
            ("crispr", "gene editing", "genome editing"),
            "Genome-editing technique",
            "Molecular biology / Genetic engineering",
            "DNA repair, guide RNA, nucleases, delivery, bioethics",
            "DNA structure, genes and proteins, cell biology, and basic inheritance",
        ),
        (
            ("dna replication", "genetics", "genome"),
            "Biological process or concept",
            "Molecular biology / Genetics",
            "DNA structure, enzymes, inheritance, mutation, repair",
            "Cells, DNA base pairing, genes, proteins, and basic chemistry",
        ),
        (
            ("a/b testing", "controlled experiment", "randomized experiment"),
            "Controlled experimentation method",
            "Statistics / Product experimentation",
            "Randomization, hypotheses, metrics, significance, decision-making",
            "Percentages, probability, descriptive statistics, and basic hypothesis testing",
        ),
        (
            ("linear regression", "logistic regression", "regression"),
            "Statistical learning method",
            "Statistics / Machine learning",
            "Model assumptions, coefficients, estimation, regularization, evaluation",
            "Algebra, functions, descriptive statistics, probability, and coordinate graphs",
        ),
        (
            ("quantum computing", "quantum computer"),
            "Computing paradigm",
            "Quantum information science",
            "Qubits, superposition, measurement, entanglement, algorithms",
            "Vectors and matrices, probability, complex numbers, and basic computing concepts",
        ),
        (
            ("kubernetes",),
            "Container orchestration platform",
            "Cloud computing",
            "Containers, clusters, deployments, networking, scaling",
            "Containers, Linux command-line basics, networking, and YAML configuration",
        ),
        (
            ("mcp server", "model context protocol"),
            "Technical integration standard",
            "AI systems integration",
            "Clients, servers, tools, transports, permissions, verification",
            "Client–server basics, JSON, command-line use, and local process or HTTP concepts",
        ),
        (
            ("coral reef", "coral bleaching", "marine ecosystem"),
            "Ecological process or system",
            "Marine biology / Ecology",
            "Coral symbiosis, thermal stress, bleaching, recruitment, reef resilience, climate change",
            "Ecosystems, food webs, cells, photosynthesis, ocean temperature, and basic climate science",
        ),
    ]
    for keywords, entity_type, broad_field, related, prerequisites in profiles:
        if any(keyword in normalized for keyword in keywords):
            return [
                ("Name type", _learning_name_type(text)),
                ("Entity type", entity_type),
                ("Broad field", broad_field),
                ("Subject", _subject(text)),
                ("Related topics", related),
                ("Prerequisites", prerequisites),
            ]

    subject = _subject(text)
    return [
        ("Name type", _learning_name_type(text)),
        ("Entity type", "Interdisciplinary learning inquiry"),
        ("Broad field", "Interdisciplinary study"),
        ("Subject", subject),
        (
            "Related topics",
            f"Definitions of {subject}; underlying mechanisms; evidence; applications; limitations",
        ),
        (
            "Prerequisites",
            f"Core terminology and introductory principles directly related to {subject}",
        ),
    ]


def build_response_profile(
    prompt: str,
    intent: str = "",
    response_mode: str = "",
    context_intent: str = "",
) -> ProfileRows:
    """Return truthful display metadata without inventing personal statistics."""
    text = (prompt or "").strip()
    normalized = re.sub(r"\s+", " ", text.lower())
    intent = (intent or "").strip().lower()
    response_mode = (response_mode or "").strip().lower()
    context_intent = (context_intent or "").strip().lower()

    if intent == "topic_recommendation":
        if "kubernetes" in normalized:
            return [
                ("Name type", "Recommended learning topic"),
                ("Entity type", "Container orchestration platform"),
                ("Broad field", "Cloud computing"),
                ("Subject", _subject(text)),
                ("Related topics", "Containers, deployments, scaling, clusters, DevOps"),
            ]
        if "spatial artificial intelligence" in normalized:
            return [
                ("Name type", "Recommended learning topic"),
                ("Entity type", "Interdisciplinary AI field"),
                ("Broad field", "Artificial intelligence"),
                ("Subject", _subject(text)),
                ("Related topics", "Computer vision, robotics, mapping, spatial reasoning"),
            ]
        if "quantum computing" in normalized:
            return [
                ("Name type", "Recommended learning topic"),
                ("Entity type", "Computing paradigm"),
                ("Broad field", "Quantum information science"),
                ("Subject", _subject(text)),
                ("Related topics", "Qubits, superposition, entanglement, quantum algorithms"),
            ]
        return [
            ("Name type", "Recommended learning topic"),
            ("Entity type", "Optimization algorithm"),
            ("Broad field", "Machine learning"),
            ("Subject", _subject(text)),
            ("Related topics", "Calculus, loss functions, model training, learning rates"),
        ]

    if intent == "topic_explore" or context_intent in {
        "learning", "explore", "explain", "teach", "compare", "decide", "quiz", "example",
    }:
        return _educational_topic_profile(text, normalized)

    if response_mode == "conversation":
        if re.search(r"\b(call you|your name|who are you|what should i call)\b", normalized):
            return [
                ("Name type", "Relational naming question"),
                ("Entity type", "Conversational expression"),
                ("Broad field", "Human–AI interaction"),
                ("Subject", "How the user addresses InI"),
                ("Related topics", "Identity, rapport, personalization, conversational norms"),
            ]
        if re.search(r"\b(test|testing|check|checking|trying)\b", normalized):
            return [
                ("Name type", "Informal conversational statement"),
                ("Entity type", "User utterance"),
                ("Broad field", "Conversation and interaction"),
                ("Subject", "Casual testing of InI"),
                ("Related topics", "Intent detection, rapport, response adaptation"),
            ]
        if intent == "thanks":
            return [
                ("Name type", "Gratitude expression"),
                ("Entity type", "Social utterance"),
                ("Broad field", "Interpersonal communication"),
                ("Subject", "Acknowledgment and appreciation"),
                ("Related topics", "Politeness, rapport, conversational closure"),
            ]
        if intent == "affirmation":
            return [
                ("Name type", "Positive acknowledgement"),
                ("Entity type", "Social utterance"),
                ("Broad field", "Interpersonal communication"),
                ("Subject", "Approval or positive conversational feedback"),
                ("Related topics", "Encouragement, rapport, acknowledgement, conversational continuity"),
            ]
        if intent == "farewell":
            return [
                ("Name type", "Conversational closing"),
                ("Entity type", "Social utterance"),
                ("Broad field", "Pragmatics"),
                ("Subject", "Ending or pausing the conversation"),
                ("Related topics", "Farewells, rapport, conversation continuity"),
            ]
        if intent in {"greeting", "smalltalk"}:
            return [
                ("Name type", "Informal greeting"),
                ("Entity type", "Phrase or expression"),
                ("Broad field", "Sociolinguistics"),
                ("Subject", "Casual conversational opening"),
                ("Related topics", "Greetings, pragmatics, register, social rapport"),
            ]
        if intent == "clarify":
            return [
                ("Name type", "Context-dependent utterance"),
                ("Entity type", "Conversational reference"),
                ("Broad field", "Pragmatics"),
                ("Subject", "Resolving missing conversational context"),
                ("Related topics", "Reference, ambiguity, clarification, dialogue repair"),
            ]
        return [
            ("Name type", "Conversational query"),
            ("Entity type", "User utterance"),
            ("Broad field", "Human–AI interaction"),
            ("Subject", _subject(text)),
            ("Related topics", "Intent, context, tone, conversational response"),
        ]

    practical = {
        "installation": (
            "Practical setup request", "Procedure", "Technical configuration",
            "Installation, dependencies, permissions, verification",
        ),
        "debugging": (
            "Diagnostic request", "Technical problem", "Software debugging",
            "Symptoms, root cause, diagnostics, corrective action",
        ),
        "troubleshooting": (
            "Problem-solving request", "Operational issue", "Technical troubleshooting",
            "Failure conditions, diagnosis, recovery, prevention",
        ),
        "integration": (
            "Implementation guidance", "Technical integration and configuration", "Systems integration",
            "Source system, integration interface, MCP bridge, client, security",
        ),
    }
    if context_intent in practical:
        name_type, entity_type, broad_field, related = practical[context_intent]
        return [
            ("Name type", name_type),
            ("Entity type", entity_type),
            ("Broad field", broad_field),
            ("Subject", _subject(text)),
            ("Related topics", related),
        ]

    if response_mode == "illustration":
        return _illustration_topic_profile(text, normalized)

    return [
        ("Name type", "Information request"),
        ("Entity type", "Question or prompt"),
        ("Broad field", "Knowledge and information"),
        ("Subject", _subject(text)),
        ("Related topics", "Context, evidence, explanation, related concepts"),
    ]

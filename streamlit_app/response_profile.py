"""Small, structured profiles for every New Chat response mode."""

from __future__ import annotations

import re
from typing import List, Tuple


ProfileRows = List[Tuple[str, str]]


def _subject(text: str, limit: int = 92) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    return clean[:limit].rstrip() or "User message"


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

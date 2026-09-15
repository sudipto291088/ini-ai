"""Static copy and local content for InI.ai's First Conversation Experience."""

from typing import Any, Dict, List


FCE_MESSAGES: List[Dict[str, Any]] = [
    {
        "text": "Hello! 👋\n\nI’m InI.ai — a Question Engine built to help you understand, not just collect answers.",
        "emphasis": "identity",
    },
    {
        "text": "Start with a question, a topic, or even an unfinished thought.\n\nI’ll reveal a learning path around it.",
        "visual": "question-path",
    },
    {
        "text": "Read each answer at the level you need — clear intuition or technical depth.",
        "visual": "answer-views",
    },
    {
        "text": "When you want the bigger picture, open Knowledge Structure to see prerequisites, connections, and the questions that move you forward.",
        "visual": "knowledge-map",
    },
    {
        "text": "You don’t need the perfect question. Pick a topic that interests you and begin.",
        "topics": True,
    },
    {
        "text": "Bring your curiosity.\n\nI’ll help with the rest.",
        "emphasis": "final",
    },
]


FCE_TOPIC_EXAMPLES = [
    "Artificial Intelligence",
    "Quantum Computing",
    "Cognitive Science",
    "Kubernetes",
]


FCE_QUOTES = [
    {
        "quote": "If a man will begin with certainties, he shall end in doubts; but if he will be content to begin with doubts, he shall end in certainties.",
        "author": "Francis Bacon",
        "attribution_note": "The Advancement of Learning (1605)",
    },
    {
        "quote": "Nothing in life is to be feared, it is only to be understood.",
        "author": "Marie Curie",
        "attribution_note": "Published in The New York Times, 1921",
    },
    {
        "quote": "There are no right answers to wrong questions.",
        "author": "Ursula K. Le Guin",
        "attribution_note": "The Language of the Night",
    },
    {
        "quote": "Asking the right questions takes as much skill as giving the right answers.",
        "author": "Robert Half",
        "attribution_note": "The Robert Half Way",
    },
    {
        "quote": "The scientific mind does not so much provide the right answers as ask the right questions.",
        "author": "Claude Lévi-Strauss",
        "attribution_note": "The Savage Mind",
    },
    {
        "quote": "A question asked in the right way often points to its own answer.",
        "author": "Edward Hodnett",
        "attribution_note": "The Art of Problem Solving",
    },
    {
        "quote": "Questions are the engines of intellect, the cerebral machines which convert energy to motion, and curiosity to controlled inquiry.",
        "author": "David Hackett Fischer",
        "attribution_note": "Historians' Fallacies",
    },
]

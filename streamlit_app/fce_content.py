"""Static copy and local content for InI.ai's First Conversation Experience."""

from typing import Any, Dict, List


FCE_MESSAGES: List[Dict[str, Any]] = [
    {
        "text": "Hello! 👋\n\nI’m InI.ai — a Question Engine built to help you understand how knowledge is formed, connected, and learned.",
        "emphasis": "identity",
    },
    {
        "text": "You can begin with a question, explore a topic, or ask me to teach you an entire subject.\n\nYou don’t need to know which mode to choose.",
        "visual": "question-path",
    },
    {
        "text": "Ask a question and I’ll form an Initial Answer — structured for clear intuition or technical depth.",
        "visual": "answer-views",
    },
    {
        "text": "Explore a topic and I’ll build a Knowledge Structure — revealing its prerequisites, connections, and the questions that move you forward.",
        "visual": "knowledge-map",
    },
    {
        "text": "Learn an entire subject and I’ll create a Question Curriculum — a visual Subject Map of progressive chapters, questions, and focused answers.",
        "visual": "question-curriculum",
    },
    {
        "text": "Simply tell me what you want to understand. I’ll determine the right way to begin.",
        "topics": True,
    },
    {
        "text": "You don’t need the perfect question.\n\nBring your curiosity, and I’ll help with the rest.",
        "emphasis": "final",
    },
]


FCE_TOPIC_EXAMPLES = [
    "What is consciousness?",
    "Explore artificial intelligence",
    "Teach me biology as a subject",
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

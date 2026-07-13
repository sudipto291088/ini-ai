"""Static copy and local content for InI.ai's First Conversation Experience."""

from typing import Any, Dict, List


FCE_MESSAGES: List[Dict[str, Any]] = [
    {"text": "Hello! 👋\n\nWe’re glad to have you here."},
    {"text": "I’m InI.ai.\n\nA Question Engine.", "emphasis": "identity"},
    {"text": "You’re probably wondering…\n\n“What exactly is a Question Engine?”"},
    {"text": "Most AI systems answer your question.\n\nI do something a little different."},
    {
        "text": "I discover the important questions surrounding your topic—\n\nincluding questions you may not have thought to ask.",
    },
    {
        "text": "Because…\n\npeople often don’t know what they don’t know.",
        "emphasis": "philosophy",
    },
    {
        "text": "Sometimes, people are deeply curious…\n\nbut may not yet have the vocabulary to express what they want to understand.\n\nThat’s where I can help.",
    },
    {
        "text": "I won’t treat your topic as the destination.\n\nI’ll treat it as the beginning of a much larger knowledge journey.",
        "emphasis": "journey",
    },
    {"text": "I’m improving continuously.\n\nNew capabilities and new ways to explore knowledge are being added as I grow."},
    {
        "text": "There are two simple ways to begin.\n\nIntroduction helps you understand the philosophy and features behind InI.\n\nNew Chat lets you begin exploring immediately.",
    },
    {
        "text": "My New Learning is also evolving.\n\nIt is being developed to help turn individual explorations into a more continuous learning journey.",
    },
    {
        "text": "In New Chat, try entering any topic that interests you.\n\nYou don’t need the perfect question.\n\nA topic, an idea, or simple curiosity is enough.",
        "topics": True,
    },
    {
        "text": "A thought on asking the right questions",
        "quote": True,
    },
    {
        "text": "One last thing…\n\nBring your curiosity.\n\nI’ll help with the rest.",
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

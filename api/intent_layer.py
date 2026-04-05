from __future__ import annotations

import re
from typing import Any, Dict, List

GREETING_PATTERNS = [
    r"^(hi|hello|hey|yo|hola|namaste|good morning|good afternoon|good evening)[!. ]*$",
    r"^(hi|hello|hey)\b.*\b(ini|cg)\b.*$",
]

THANKS_PATTERNS = [
    r"^(thanks|thank you|thx|tysm|appreciate it)[!. ]*$",
]

FAREWELL_PATTERNS = [
    r"^(bye|goodbye|see you|talk to you later|catch you later|gn|good night)[!. ]*$",
]

HELP_PATTERNS = [
    r"^(help|help me|what can you do|how does this work|how do i use this|what should i do here)\??$",
    r"^what is this\??$",
]

AFFIRM_PATTERNS = [
    r"^(yes|yeah|yep|sure|okay|ok|go ahead|continue)\b[!. ]*$",
]

NEGATIVE_PATTERNS = [
    r"^(no|nope|nah|not now|stop)\b[!. ]*$",
]

TOPIC_CUES = {
    "explain", "tell", "teach", "learn", "what", "why", "how", "compare",
    "difference", "versus", "vs", "roadmap", "guide", "steps", "introduction",
    "overview", "deep", "architecture", "system", "model", "algorithm"
}


def _normalize(text: str) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _matches_any(text: str, patterns: List[str]) -> bool:
    return any(re.match(p, text, flags=re.IGNORECASE) for p in patterns)


def _looks_like_topic(text: str) -> bool:
    s = _normalize(text)
    if not s:
        return False
    if len(s.split()) >= 2:
        return True
    return any(tok in s for tok in TOPIC_CUES)


def detect_intent(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    s = _normalize(raw)

    if not s:
        return {
            "intent": "empty",
            "reply": "Give me a topic to explore and I will build a question map for it.",
            "followups": [
                "Artificial Intelligence",
                "Neural Networks",
                "Transformers",
            ],
            "should_interrogate": False,
            "confidence": 0.99,
        }

    if _matches_any(s, GREETING_PATTERNS):
        return {
            "intent": "greeting",
            "reply": (
                "Hey. I am ready. Give me any topic and I will either build a structured question map "
                "or help you explore it directly."
            ),
            "followups": [
                "Artificial Intelligence",
                "Explain transformers",
                "Compare AI and machine learning",
            ],
            "should_interrogate": False,
            "confidence": 0.95,
        }

    if _matches_any(s, THANKS_PATTERNS):
        return {
            "intent": "thanks",
            "reply": "Always. Drop the next topic whenever you are ready.",
            "followups": [
                "Artificial Intelligence",
                "Neural Networks",
                "Prompt Engineering",
            ],
            "should_interrogate": False,
            "confidence": 0.95,
        }

    if _matches_any(s, FAREWELL_PATTERNS):
        return {
            "intent": "farewell",
            "reply": "Alright. We can pick this up anytime. Bring the next topic when you return.",
            "followups": [],
            "should_interrogate": False,
            "confidence": 0.95,
        }

    if _matches_any(s, HELP_PATTERNS):
        return {
            "intent": "help",
            "reply": (
                "Use Interrogate when you want a structured question ladder. Use Illustrate when you want a direct explanation. "
                "In My New Learning, you can ask for deep, overview, or quiz-style answers."
            ),
            "followups": [
                "Artificial Intelligence",
                "Explain neural networks",
                "Compare supervised and unsupervised learning",
            ],
            "should_interrogate": False,
            "confidence": 0.97,
        }

    if _matches_any(s, AFFIRM_PATTERNS):
        return {
            "intent": "affirmation",
            "reply": "Got it. Send the topic or question you want to explore next.",
            "followups": [
                "Artificial Intelligence",
                "Explain transformers",
            ],
            "should_interrogate": False,
            "confidence": 0.90,
        }

    if _matches_any(s, NEGATIVE_PATTERNS):
        return {
            "intent": "negative",
            "reply": "No problem. Send a different topic whenever you want.",
            "followups": [],
            "should_interrogate": False,
            "confidence": 0.90,
        }

    if _looks_like_topic(raw):
        return {
            "intent": "topic_explore",
            "reply": "",
            "followups": [],
            "should_interrogate": True,
            "confidence": 0.75,
        }

    return {
        "intent": "clarify",
        "reply": (
            "I can help, but that looks more like a conversational message than a topic. "
            "Send a topic, a concept, or a direct learning question."
        ),
        "followups": [
            "Artificial Intelligence",
            "What is a neural network?",
            "Roadmap to learn machine learning",
        ],
        "should_interrogate": False,
        "confidence": 0.70,
    }
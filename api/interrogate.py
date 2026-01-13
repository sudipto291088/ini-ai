# api/interrogate.py

from __future__ import annotations

from typing import Dict, List





def extract_topic(user_text: str) -> str:
    """
    Extract a clean topic phrase from a natural language user prompt.
    v0: rule-based normalization.
    """
    t = user_text.strip().lower()

    # Common leading phrases to strip
    prefixes = [
        "can you teach me about",
        "about",
        "teach me about",
        "explain",
        "what is",
        "what are",
        "tell me about",
        "help me understand",
        "i want to learn about",
        "i would like to learn about",
        "could you explain",
        "hi there, explain",
        "hello, explain",
        "please explain",
        " hi, tell me about",
        " hello, tell me about",
        " please tell me about",
        "whats up with",
        "what's up with",
        "i want to know about",
        "i would like to know about",
        "i want to understand",
        "whats up",
        "what's up",
        "can you explain",
        "how do i",
        "how to",
        "give me information on",
        "give me details on",
        "provide insights on",
        "i need to know about",
        "information about",
        "details about",
        "insights about",
        "i'm interested in",
        "i am interested in",
        "looking for information on",
        "looking for details on",
        "looking for insights on",
        "could you explain",
        "would you explain",
        "please explain",
        "what do you know about",
        "what do you know about",
        "give me an overview of",
        "overview of",
        "summary of",
        "i want to understand",
        "help me with",
        "assist me with",
        "i have a question about",
        "my question is about",
        "teach me",
        "learn about",
        "information on",
        "details on",
        "insights on",
        "explanation of",
        "whose",
        "who is",
        "where is",
        "when is",
        "why is",
        "how is",
        "what's",
        "whats",
        "define",
        "definition of",
        "describe",
        "description of",
        "i want to know",
        "i would like to know",
        "could you tell me about",
        "would you tell me about",
        "please tell me about",
        "give me a brief on",
        "brief on",
        "i'm curious about",
        "i am curious about",
        "can you explain",
        "could you explain",
        "would you explain",
        "please explain",
        "what are the basics of",
        "basics of",
        "fundamentals of",
        "introduction to",
        "intro to",
        "i need help with",
        "assist me in understanding",
        "help me in understanding",
        "i want assistance with",
        "i would like assistance with",
        "could you assist me with",
        "would you assist me with",
        "please assist me with",
        "what probably is",
        "what likely is",
        "what generally is",
        "what typically is",
        "what possibly is"
        "give me clarity on",
        "clarity on",
        "shed light on",
        "i seek knowledge on",
        "i am seeking knowledge on",
        "i would like to learn about",
        "i want to gain knowledge on",
        "i would like to gain knowledge on",
        "could you provide information on",
        "would you provide information on",
        "please provide information on",
        "i'm looking to understand",
        "i'm looking to explore",
        "i look forward to explore",
        "i am looking to understand",
        "i would like to understand",
        "i want to explore",
        "i would like to explore",
        "could you explore",
        "would you explore",
        "please explore",
        "give me insights into",
        "insights into",
        "i need insights into",
        "i would like insights into",
        "could you give me insights into",
        "would you give me insights into",
        "please give me insights into",
        "wish you could explain",
        "hope you can explain",
        "looking forward to understanding",
        "looking forward to exploring",
        "wish you could tell me about",
        "hope you can tell me about",
        'please shed light on',
        'could you shed light on',
        'would you shed light on',
        "please teach me about"



    ]

    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].strip()
            break

    # Remove trailing punctuation
    t = t.rstrip("?.!")

    # Capitalize nicely (simple heuristic)
    t = " ".join(word.capitalize() for word in t.split())

    return t




def detect_topic_type(topic: str) -> str:
    t = topic.lower()

    troubleshooting_signals = [
        "error", "not working", "failed", "issue", "problem", "exception",
        "refused", "cannot", "can't"
    ]

    decision_signals = [
        "vs", "versus", "should i", "or", "better", "which", "choose",
        "leasing", "buying", "rent"
    ]

    skill_signals = [
        "how to", "learn", "practice", "trading", "coding", "programming",
        "using", "develop"
    ]

    if any(s in t for s in troubleshooting_signals):
        return "troubleshooting"

    if any(s in t for s in decision_signals):
        return "decision"

    if any(s in t for s in skill_signals):
        return "skill"

    return "concept"


def build_categories(topic: str, topic_type: str) -> dict:
    t = topic

    if topic_type == "troubleshooting":
        return {
            "Describe": [
                "What exactly is happening (symptoms) in one sentence?",
                "What is the exact error message (copy/paste if possible)?",
            ],
            "Reproduce": [
                "What steps reliably reproduce the issue?",
                "What changed right before it started (code, install, settings, update)?",
            ],
            "Environment": [
                "What OS, Python version, and dependency versions are you using?",
                "Are you using a virtual environment? If yes, which one?",
            ],
            "Isolate": [
                f"What is the smallest example where {t} fails?",
                "Does it fail for everyone or only in a specific case?",
            ],
            "Fix": [
                "What are the top 3 most likely causes?",
                "What is the safest next fix to try first (lowest risk)?",
            ],
        }

    if topic_type == "decision":
        return {
            "Goal": [
                f"What outcome are you trying to achieve with {t}?",
                "What constraints matter most (budget, time, risk, convenience)?",
            ],
            "Options": [
                f"What are the main options/choices within {t}?",
                "What are viable alternatives you should compare against?",
            ],
            "Tradeoffs": [
                "What are the biggest pros/cons of each option?",
                "What hidden costs or downsides do people miss?",
            ],
            "Risks": [
                "What can go wrong, and how likely is it?",
                "What are the red flags that indicate a bad choice?",
            ],
            "Decision": [
                "What simple decision rule can you use to decide?",
                "What would a 'good enough' decision look like?",
            ],
        }

    if topic_type == "skill":
        return {
            "Basics": [
                f"What does 'good' look like in {t} (skills/behaviors)?",
                f"What are the core sub-skills inside {t}?",
            ],
            "Learning Path": [
                f"What should a beginner learn first in {t} (3-step path)?",
                "What are common beginner mistakes to avoid?",
            ],
            "Practice": [
                "What drills/practice tasks build the skill fastest?",
                "How much practice per day/week is realistic and effective?",
            ],
            "Feedback": [
                "How do you measure progress (metrics or checkpoints)?",
                "How do you get feedback quickly (tests, mentors, reviews)?",
            ],
            "Next Level": [
                "What does intermediate/advanced look like?",
                "What projects prove competence?",
            ],
        }

    # default: concept
    return {
        "What": [
            f"What is {t} in plain language?",
            f"What are the key parts/components of {t}?",
            f"What problem does {t} exist to solve?",
        ],
        "Why": [
            f"Why does {t} matter?",
            f"Why did {t} become necessary (history/context)?",
            f"Why do people get confused about {t}?",
        ],
        "How": [
            f"How does {t} work at a high level?",
            f"How do beginners start learning {t} (first 3 steps)?",
            f"How can I tell if I truly understand {t}?",
        ],
        "When": [
            f"When should someone use {t} (and when should they avoid it)?",
            f"When did {t} become important/popular?",
        ],
        "Where": [
            f"Where is {t} used in real life?",
            f"Where does {t} usually fail or break in practice?",
        ],
    }





def interrogate(topic: str) -> Dict[str, object]:
    """
    Return structured, relevant interrogative questions for a topic.
    v0 intelligence: templates + light normalization.
    """
    clean_topic = extract_topic(topic)
    if not clean_topic:
        return {"topic": topic, "categories": {}, "notes": ["Empty topic received."]}
    
    topic_type = detect_topic_type(clean_topic)
    categories = build_categories(clean_topic, topic_type)

    notes = [
        "v0: template-based interrogation (no external knowledge yet).",
        "Next: add topic-type detection (concept vs skill vs decision vs troubleshooting).",
    ]

    return {
    "topic": clean_topic,
    "topic_type": topic_type,
    "categories": categories,
    "notes": notes
}



from typing import Dict, List, Tuple


# -----------------------------
# Archetype ordering (learning flow)
# -----------------------------
ARCHETYPE_ORDER = [
    "ORIENT",
    "MECHANISM",
    "APPLY",
    "LEARN",
    "COMPARE",
    "DECIDE",
    "RISK",
    "NEXT",
]

ARCHETYPE_MAP = {
    "What": "ORIENT",
    "Why": "ORIENT",
    "When": "ORIENT",
    "who": "ORIENT",
    "how to": "LEARN",
    "How": "MECHANISM",
    "Where": "APPLY",
    "Examples": "APPLY",
    "Misconceptions": "RISK",
    "Common Challenges": "RISK",
    "Related Topics": "NEXT",
}


# -----------------------------
# Era awareness (light, v0)
# -----------------------------
ERA_HOOKS = {
    "Artificial Intelligence": "Modern AI discussions include generative models and agentic systems.",
    "AI": "Modern AI discussions include generative models and agentic systems.",
}


def get_era_note(topic: str) -> str | None:
    for k, v in ERA_HOOKS.items():
        if k.lower() in topic.lower():
            return v
    return None


# -----------------------------
# Topic extraction
# -----------------------------
def extract_topic(text: str) -> str:
    t = text.strip().lower()
    prefixes = [
        "explain to me",
        "explain",
        "tell me about",
        "can you teach me about",
        "teach me about",
        "help me understand",
        "what is",
        "what are",
        "how to",
        "how do i",
    ]
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].strip()
            break
    t = t.rstrip("?.!")
    return " ".join(w.capitalize() for w in t.split())


# -----------------------------
# Topic type detection
# -----------------------------
def detect_topic_type(topic: str) -> Tuple[str, float]:
    t = topic.lower()

    if any(x in t for x in [" vs ", " versus ", "compare"]):
        return "comparison", 0.67

    if any(x in t for x in ["should i", "better", "choose"]):
        return "decision", 0.67

    if any(x in t for x in ["error", "not working", "failed", "issue"]):
        return "troubleshooting", 0.75

    if any(x in t for x in ["learn", "practice", "how to"]):
        return "skill", 0.67

    return "concept", 0.67


# -----------------------------
# Summary block
# -----------------------------
def build_summary(topic: str, topic_type: str, confidence: float) -> List[str]:
    if confidence < 0.5:
        return [
            f"Topic: {topic}.",
            "I might need a bit more context to be precise.",
            "Start with a simple overview, then we can go deeper.",
        ]

    return [
        f"{topic} is a topic worth understanding clearly.",
        "We’ll build clarity first, then explore how it works and where it applies.",
        "Finally, we’ll highlight common mistakes and next steps.",
    ]


# -----------------------------
# Question generation
# -----------------------------
def build_categories(topic: str, topic_type: str) -> Dict[str, List[str]]:
    t = topic
    return {
        "What": [
            f"What is {t} in plain language?",
            f"What problem does {t} exist to solve?",
            f"What are the main benefits of {t}?",
            f"What are the limitations of {t}?",
        ],
        "Why": [
            f"Why does {t} matter?",
            f"Why do people get confused about {t}?",
        ],
        "How": [
            f"How does {t} work at a high level?",
            f"How can I tell if I truly understand {t}?",
        ],
        "Where": [
            f"Where is {t} used in real life?",
            f"Where does {t} fail or break in practice?",
        ],
        "Examples": [
            f"What is a simple example of {t}?",
            f"What are real-world examples of {t}?",
        ],
        "Misconceptions": [
            f"What is a common misconception about {t}?",
        ],
        "Common Challenges": [
            f"What challenges do people face when working with {t}?",
        ],
        "Related Topics": [
            f"What topics are closely related to {t}?",
        ],
    }


# -----------------------------
# ORIENT answers
# -----------------------------
def _orient_answer(topic: str, question: str, category: str) -> str:
    era = get_era_note(topic)

    if "plain language" in question.lower():
        parts = [
            f"{topic} refers to building systems that can perform tasks normally requiring human intelligence.",
            "Instead of following fixed rules, these systems learn patterns from data.",
            "They are goal-driven but limited by data, design, and evaluation."
        ]
        if era:
            parts.append(era)
        return "\n\n".join(parts)

    if "problem" in question.lower():
        return (
            "It exists to automate or assist tasks where writing explicit rules is impractical.\n\n"
            "This includes perception, prediction, language understanding, and decision support."
        )

    if "benefits" in question.lower():
        return (
            "Key benefits include scalability, speed, and the ability to detect patterns humans may miss.\n\n"
            "Its value comes from augmenting human decision-making, not replacing it entirely."
        )

    if "limitations" in question.lower():
        return (
            "AI systems can fail silently, inherit bias from data, and behave unpredictably outside tested conditions.\n\n"
            "They require monitoring, evaluation, and human oversight."
        )

    if "confused" in question.lower():
        return (
            "People confuse AI with human intelligence or consciousness.\n\n"
            "In reality, most AI systems are specialized statistical tools."
        )

    return (
        f"{topic} is best understood by defining its purpose, limits, and real-world use.\n\n"
        "Clarity comes from understanding both what it can and cannot do."
    )


# -----------------------------
# MECHANISM answers
# -----------------------------
def _mechanism_answer(topic: str, question: str) -> str:
    era = get_era_note(topic)

    parts = [
        "At a high level, AI works by learning patterns from data rather than following explicit rules.",
        "The core loop is: data → model → training → evaluation → deployment → monitoring.",
        "Under the hood, many systems use neural networks that adjust parameters to minimize error."
    ]
    if era:
        parts.append(era)
    return "\n\n".join(parts)


# -----------------------------
# APPLY answers
# -----------------------------
def _apply_answer(topic: str, question: str) -> str:
    q = question.lower()

    if "simple example" in q:
        return (
            "Spam detection is a simple example.\n\n"
            "The system learns from labeled emails and predicts whether new emails are spam."
        )

    if "real-world" in q:
        return (
            "AI is used in recommendations, fraud detection, search ranking, translation, and content generation.\n\n"
            "These systems operate at scale where manual decision-making is impractical."
        )

    if "fail" in q:
        return (
            "AI often fails when data changes, bias exists, or the system is used outside its tested scope.\n\n"
            "Failures usually come from misuse rather than the algorithm itself."
        )

    return (
        f"{topic} is applied wherever large volumes of data must be interpreted or acted upon efficiently."
    )


# -----------------------------
# RISK answers (KEY UPDATE)
# -----------------------------
def _risk_answer(topic: str, question: str) -> str:
    tl = topic.lower()
    ql = question.lower()

    is_ai = any(x in tl for x in ["ai", "artificial intelligence", "machine learning"])

    if is_ai:
        if "misconception" in ql:
            return (
                "A common misconception is that AI understands or reasons like a human.\n\n"
                "In reality, it recognizes statistical patterns without true understanding.\n\n"
                "Overtrusting AI leads to poor decisions and hidden failures."
            )

        return (
            "The biggest risk is assuming AI outputs are correct without evaluation.\n\n"
            "Most real-world failures come from misuse, weak data, or lack of oversight."
        )

    return (
        f"People often misuse {topic} by assuming it works universally.\n\n"
        "Understanding limits is as important as understanding capabilities."
    )


# -----------------------------
# NEXT answers
# -----------------------------
def _next_answer(topic: str) -> str:
    return (
        f"A good next step is to apply {topic} in a small, controlled way.\n\n"
        "Hands-on experience reveals limits faster than theory alone."
    )


# -----------------------------
# Attach answers
# -----------------------------
def attach_answers(categories: Dict[str, List[str]], topic: str, topic_type: str):
    out = {}
    for cat, questions in categories.items():
        items = []
        for idx, q in enumerate(questions, start=1):
            archetype = ARCHETYPE_MAP.get(cat, "ORIENT")

            if archetype == "ORIENT":
                ans = _orient_answer(topic, q, cat)
            elif archetype == "MECHANISM":
                ans = _mechanism_answer(topic, q)
            elif archetype == "APPLY":
                ans = _apply_answer(topic, q)
            elif archetype == "RISK":
                ans = _risk_answer(topic, q)
            elif archetype == "NEXT":
                ans = _next_answer(topic)
            else:
                ans = f"This question relates to {topic}."

            items.append({
                "id": f"{cat.lower().replace(' ', '_')}_{idx}",
                "archetype": archetype,
                "question": q,
                "answer": ans,
            })

        out[cat] = items
    return out


# -----------------------------
# Main interrogate entry
# -----------------------------
def interrogate(text: str) -> Dict[str, object]:
    clean_topic = extract_topic(text)
    topic_type, confidence = detect_topic_type(clean_topic)

    categories = build_categories(clean_topic, topic_type)
    qa = attach_answers(categories, clean_topic, topic_type)

    return {
        "topic": clean_topic,
        "topic_type": topic_type,
        "categories": qa,
        "summary": build_summary(clean_topic, topic_type, confidence),
        "confidence": confidence,
        "notes": [
            "v0: template-based interrogation",
            "v0: intent-aware ORIENT, MECHANISM, APPLY, RISK",
        ],
    }

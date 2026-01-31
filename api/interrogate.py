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
# (COHESION RULE: Only ORIENT mentions era note)
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
# Topic Core (COHESION ENGINE)
# -----------------------------
TOPIC_CORE = {
    "artificial intelligence": {
        "one_liner": "AI is software that achieves goals by learning patterns from data to predict, generate, or decide.",
        "mechanism": [
            "Pipeline: data → model → training (optimize loss) → evaluation → deployment → monitoring.",
            "Under the hood: models adjust parameters to reduce error on examples."
        ],
        "apply": [
            "Recommendations (what to watch/buy next).",
            "Search ranking (what results appear first).",
            "Fraud/spam detection (flagging suspicious patterns).",
            "Forecasting (demand, time series, risk).",
            "Translation and speech (text↔speech, language translation).",
            "Content generation (text/code/images, with guardrails).",
        ],
        "risk": [
            "AI does not truly understand; it matches patterns.",
            "Main failure mode is overtrust without evaluation or monitoring.",
            "Data drift (the world changes) can silently break performance.",
            "Bias in training data can produce unfair or unsafe outputs."
        ],
        "next": [
            "Learn evaluation habits: define success metrics + test failure cases.",
            "Build a tiny project: dataset → baseline → error analysis.",
            "Practice monitoring thinking: what can change and how you’d detect it."
        ]
    }
}


def _get_core_key(topic: str) -> str | None:
    """
    Return a TOPIC_CORE key if the topic matches.
    v0: only AI core is defined.
    """
    tl = (topic or "").strip().lower()
    if "artificial intelligence" in tl or tl == "ai":
        return "artificial intelligence"
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
# (COHESION: define the topic here once; others assume this.)
# -----------------------------
def _orient_answer(topic: str, question: str, category: str) -> str:
    ql = (question or "").lower()
    core_key = _get_core_key(topic)
    era = get_era_note(topic)

    # AI cohesive ORIENT
    if core_key == "artificial intelligence":
        core = TOPIC_CORE[core_key]
        one_liner = core["one_liner"]

        if "plain language" in ql:
            parts = [
                one_liner,
                "In practice, AI systems learn from examples (data) and generalize to new inputs.",
                "They can be powerful, but they are limited by data quality, evaluation, and how they’re used."
            ]
            if era:
                parts.append(era)
            return "\n\n".join(parts)

        if "problem" in ql:
            parts = [
                "AI exists because many real-world tasks are too complex for hand-written rules.",
                "It helps when you need predictions/decisions/generation based on patterns in large data."
            ]
            if era:
                parts.append(era)
            return "\n\n".join(parts)

        if "benefits" in ql:
            parts = [
                "Benefits: speed and scale (automation), pattern detection, and decision support.",
                "It’s most valuable when it augments people and processes—especially with good evaluation."
            ]
            if era:
                parts.append(era)
            return "\n\n".join(parts)

        if "limitations" in ql:
            parts = [
                "Limitations: it can be confidently wrong, inherit bias, and fail when the environment changes (drift).",
                "You need evaluation, monitoring, and guardrails—especially in high-stakes uses."
            ]
            if era:
                parts.append(era)
            return "\n\n".join(parts)

        if "confused" in ql:
            parts = [
                "People often confuse AI with human understanding or reasoning.",
                "Most AI is pattern-based: it can look smart without truly understanding."
            ]
            if era:
                parts.append(era)
            return "\n\n".join(parts)

        parts = [one_liner]
        if era:
            parts.append(era)
        return "\n\n".join(parts)

    # Generic ORIENT fallback
    if "plain language" in ql:
        parts = [
            f"{topic} refers to a concept or method people use to solve a problem or achieve a goal.",
            "A good understanding starts with what it is, why it exists, and where it helps in real life."
        ]
        if era:
            parts.append(era)
        return "\n\n".join(parts)

    if "problem" in ql:
        return (
            f"{topic} exists to address a real need where simpler approaches fall short.\n\n"
            "Understanding the problem it solves clarifies when it’s useful."
        )

    if "benefits" in ql:
        return (
            f"{topic} can bring speed, clarity, or better outcomes when applied correctly.\n\n"
            "The benefits depend on the context and constraints."
        )

    if "limitations" in ql:
        return (
            f"{topic} has limits and failure modes that matter in practice.\n\n"
            "Knowing where it breaks prevents overconfidence."
        )

    if "confused" in ql:
        return (
            f"People get confused about {topic} when they mix it up with similar concepts or skip fundamentals.\n\n"
            "A clear definition plus examples usually fixes it."
        )

    parts = [
        f"{topic} is best understood by defining its purpose, limits, and real-world use."
    ]
    if era:
        parts.append(era)
    return "\n\n".join(parts)


# -----------------------------
# MECHANISM answers
# (COHESION: do NOT redefine topic; assume ORIENT already defined it.)
# -----------------------------
def _mechanism_answer(topic: str, question: str) -> str:
    core_key = _get_core_key(topic)
    ql = (question or "").lower()

    if core_key == "artificial intelligence":
        core = TOPIC_CORE[core_key]

        if "tell if" in ql or "truly understand" in ql:
            return "\n\n".join([
                "Mechanism check (do you really understand it?):",
                "• what the inputs/outputs are\n• what data it learns from\n• what objective it optimizes\n• how you evaluate it\n• what can make it fail (bias/drift).",
                "If you can explain the pipeline and how you’d test failures, you understand it."
            ])

        # default mechanism
        parts = ["Mechanism:"]
        parts.extend(core["mechanism"])
        return "\n\n".join(parts)

    # Generic fallback mechanism
    return "\n\n".join([
        "Mechanism:",
        f"{topic} works by taking inputs, applying steps or rules, and producing outputs.",
        "A useful model is: inputs → transformation → outputs → feedback/iteration."
    ])


# -----------------------------
# APPLY answers
# (COHESION: use core examples; avoid re-definition.)
# -----------------------------
def _apply_answer(topic: str, question: str) -> str:
    core_key = _get_core_key(topic)
    ql = (question or "").lower()

    if core_key == "artificial intelligence":
        core = TOPIC_CORE[core_key]

        if "fail" in ql or "break" in ql:
            return "\n\n".join([
                "Where it breaks in practice:",
                "• data drift (the world changes)\n• biased or incomplete data\n• missing evaluation/monitoring\n• using it outside tested scope.",
                "Most failures happen because humans overtrust outputs without verification."
            ])

        if "simple example" in ql:
            return "\n\n".join([
                "Simple example: spam detection.",
                "A model learns from labeled emails (spam/not spam) and predicts the label for new emails.",
                "It works well when training data matches the real inbox and you monitor drift."
            ])

        # real-world / where used
        return "Where you see AI in real life:\n\n• " + "\n• ".join(core["apply"])

    # Generic fallback
    if "fail" in ql:
        return "\n\n".join([
            f"{topic} tends to fail when:",
            "• assumptions don’t hold\n• context changes\n• people skip fundamentals\n• it’s applied outside its intended use."
        ])

    if "simple example" in ql:
        return "\n\n".join([
            f"Simple example of {topic}:",
            "• One everyday case where it appears.",
            "If you share your context, I can make the example specific."
        ])

    return "\n\n".join([
        f"{topic} is applied wherever it helps solve a recurring problem or achieve a goal more effectively.",
        "Use-cases depend strongly on context."
    ])


# -----------------------------
# RISK answers
# (COHESION: use core risk points; corrective, not preachy.)
# -----------------------------
def _risk_answer(topic: str, question: str) -> str:
    core_key = _get_core_key(topic)
    ql = (question or "").lower()

    if core_key == "artificial intelligence":
        core = TOPIC_CORE[core_key]

        if "misconception" in ql:
            # pick the most important misconception first
            return "\n\n".join([
                "Common misconception:",
                "AI 'understands' like a human. It usually doesn’t—it matches patterns.",
                "This misconception leads to overtrust and missed failure modes."
            ])

        # challenges/pitfalls
        return "Common traps:\n\n• " + "\n• ".join(core["risk"])

    # Generic fallback
    if "misconception" in ql:
        return "\n\n".join([
            f"A common misconception about {topic} is assuming it works universally.",
            "Most tools/concepts have a scope where they work well—and places they don’t."
        ])

    return "\n\n".join([
        f"People often misuse {topic} by skipping fundamentals or ignoring constraints.",
        "The risk is false confidence rather than the concept itself."
    ])


# -----------------------------
# NEXT answers
# (COHESION: actionable next steps; consistent voice.)
# -----------------------------
def _next_answer(topic: str) -> str:
    core_key = _get_core_key(topic)

    if core_key == "artificial intelligence":
        core = TOPIC_CORE[core_key]
        return "Next steps:\n\n• " + "\n• ".join(core["next"])

    return "\n\n".join([
        f"A good next step is to apply {topic} in a small, controlled way.",
        "Hands-on practice reveals limits faster than theory alone."
    ])


# -----------------------------
# Attach answers
# -----------------------------
def attach_answers(categories: Dict[str, List[str]], topic: str, topic_type: str):
    out: Dict[str, List[Dict[str, str]]] = {}

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
            "v0: cohesion pass for AI via TOPIC_CORE (consistent ORIENT→NEXT flow).",
        ],
    }

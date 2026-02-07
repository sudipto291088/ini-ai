import re
from typing import Dict, List, Tuple, Any

# ------------------------------------------------------------
# OPTIONAL LLM HOOKS (safe import)
# ------------------------------------------------------------
# We will use LLM only for AI / Machine Learning topics (Option A).
# If api.llm_answers isn't available or doesn't expose these names,
# the app will fall back to template answers.
# ------------------------------------------------------------
# LLM HOOKS (robust)
# ------------------------------------------------------------
try:
    # Your repo already uses generate_dynamic_answer earlier, so we support it.
    from api.llm_answers import llm_enabled as _llm_enabled
    from api.llm_answers import generate_dynamic_answer as llm_answer_question
except Exception:
    _llm_enabled = None
    llm_answer_question = None


def _llm_is_enabled() -> bool:
    """
    Supports both:
    - llm_enabled == True/False
    - llm_enabled() -> True/False
    """
    if _llm_enabled is None:
        return False
    try:
        return bool(_llm_enabled()) if callable(_llm_enabled) else bool(_llm_enabled)
    except Exception:
        return False



# ------------------------------------------------------------
# Imperative: DO NOT delete prefix logic.
# Keep robust extraction so: "tell me about AI" -> "AI"
# ------------------------------------------------------------
PREFIX_PATTERNS = [
    r"^can you\s+",
    r"^could you\s+",
    r"^would you\s+",
    r"^please\s+",
    r"^tell me\s+",
    r"^tell me about\s+",
    r"^explain\s+",
    r"^explain to me\s+",
    r"^teach me\s+",
    r"^help me\s+",
    r"^i want to learn\s+",
    r"^i want to know\s+",
    r"^i need to know\s+",
    r"^what is\s+",
    r"^what are\s+",
    r"^how to\s+",
    r"^how do i\s+",
    r"^why does\s+",
    r"^why do\s+",
    r"^give me\s+",
    r"^share\s+",
    r"^describe\s+",
]


def extract_topic(user_text: str) -> str:
    if not user_text:
        return ""

    text = user_text.strip()
    text = re.sub(r"\s+", " ", text)

    # Remove trailing punctuation
    text = re.sub(r"[?.!]+$", "", text).strip()

    lowered = text.lower()

    # Strip common leading phrases (imperative)
    for pat in PREFIX_PATTERNS:
        if re.search(pat, lowered):
            text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
            lowered = text.lower()
            break

    # Handle common "about X"
    m = re.search(r"\babout\s+(.+)$", text, flags=re.IGNORECASE)
    if m and len(m.group(1).strip()) >= 2:
        text = m.group(1).strip()

    # Normalize simple cases like "ai" -> "AI"
    if text.lower() == "ai":
        return "Artificial Intelligence"
    if text.lower() in ["ml", "machine learning"]:
        return "Machine Learning"

    # Title-case but keep acronyms
    # (Don’t overdo. Keep user's wording mostly.)
    if len(text) <= 4 and text.isalpha():
        return text.upper()

    return text[:1].upper() + text[1:]


# ------------------------------------------------------------
# Topic type detection (kept)
# ------------------------------------------------------------
def detect_topic_type(topic: str) -> Tuple[str, float]:
    t = (topic or "").strip().lower()
    if not t:
        return "unknown", 0.0

    # comparison
    if any(x in t for x in [" vs ", "versus", "compare", "comparison", "difference between"]):
        return "comparison", 0.67

    # how-to / learning intent
    if any(x in t for x in ["how to", "learn", "study", "become", "start with", "roadmap"]):
        return "how_to", 0.67

    # decision
    if any(x in t for x in ["should i", "choose", "buy or", "pick", "decide"]):
        return "decision", 0.67

    return "concept", 0.67


# ------------------------------------------------------------
# Archetypes + category ordering
# Imperative: RISK should come immediately after ORIENT in the guided flow.
# ------------------------------------------------------------
ARCHETYPE_MAP = {
    "What": "ORIENT",
    "Why": "ORIENT",
    "When": "ORIENT",
    "Who": "ORIENT",
    "How to": "ORIENT",

    "Misconceptions": "RISK",
    "Common Challenges": "RISK",

    "How": "MECHANISM",

    "Where": "APPLY",
    "Examples": "APPLY",

    "Related Topics": "NEXT",
}


def build_categories(topic: str, topic_type: str) -> Dict[str, List[str]]:
    """Return category -> list of questions.
    Keep it deterministic and readable (v0).
    """
    T = topic

    categories: Dict[str, List[str]] = {}

    # ORIENT
    categories["What"] = [
        f"What is {T} in plain language?",
        f"What problem does {T} exist to solve?",
        f"What are the main benefits of {T}?",
        f"What are the limitations of {T}?",
    ]

    categories["Why"] = [
        f"Why does {T} matter?",
        f"Why do people get confused about {T}?",
    ]

    # RISK (immediately after ORIENT)
    categories["Misconceptions"] = [
        f"What is a common misconception about {T}?",
    ]
    categories["Common Challenges"] = [
        f"What pitfalls should I avoid when learning or using {T}?",
    ]

    # MECHANISM
    categories["How"] = [
        f"How does {T} work at a high level?",
        f"How can I tell if I truly understand {T}?",
    ]

    # APPLY (this is where your screenshot showed “Where used / Where fails” missing)
    categories["Where"] = [
        f"Where is {T} used in real life?",
        f"Where does {T} usually fail or break in practice?",
    ]
    categories["Examples"] = [
        f"What is a simple example of {T}?",
        f"What are real-world examples of {T}?",
    ]

    # NEXT
    categories["Related Topics"] = [
        f"What topics are closely related to {T}?",
    ]

    return categories


# ------------------------------------------------------------
# Summaries (keep friendly and not capped)
# ------------------------------------------------------------
def build_summary(topic: str, topic_type: str, confidence: float) -> List[str]:
    if topic_type == "comparison":
        return [
            f"{topic} is a comparison topic.",
            "We’ll clarify both sides, when each wins, and common traps.",
        ]
    if topic_type == "how_to":
        return [
            f"{topic} is a learning / action topic.",
            "We’ll clarify goals, prerequisites, and a sensible path forward.",
        ]
    return [
        f"{topic} is a topic worth understanding clearly.",
        "We’ll build clarity first, then explore how it works and where it applies.",
        "Finally, we’ll highlight common mistakes and next steps.",
    ]


# ------------------------------------------------------------
# Template answers (fallback when LLM is off or for non-AI/ML topics)
# NOTE: No “answer length capping” here—answers can be long.
# ------------------------------------------------------------
def _orient_answer(topic: str, question: str, cat: str) -> str:
    tl = topic.lower()
    ql = question.lower()

    # Slightly richer for AI/ML even in template fallback
    is_ai = any(x in tl for x in ["artificial intelligence", "ai", "machine learning", "ml"])
    if is_ai and ("plain language" in ql or ql.startswith("what is")):
        return (
            "Artificial Intelligence (AI) is when computers perform tasks that usually require human intelligence—"
            "like recognizing patterns, understanding language, making predictions, or generating content.\n\n"
            "Most modern AI is built from machine learning: models learn patterns from data and then use those patterns "
            "to classify, predict, or generate outputs.\n\n"
            "AI isn’t automatically ‘human-like understanding’—it’s typically narrow, goal-driven, and constrained by "
            "training data and design."
        )

    if "problem" in ql:
        return (
            f"{topic} exists to help make better decisions or automate tasks when rules are too complex to write by hand.\n\n"
            "It’s especially useful when you have patterns in data, repeated decisions, or large scale processes."
        )

    if "benefit" in ql:
        return (
            f"Key benefits of {topic} include speed, consistency, and the ability to detect patterns humans may miss.\n\n"
            "It can reduce manual effort, improve accuracy for certain tasks, and unlock new capabilities (like personalization)."
        )

    if "limitation" in ql:
        return (
            f"{topic} can fail when data is biased, incomplete, or different from real-world conditions.\n\n"
            "It can also be brittle: it may perform well in testing but degrade when inputs change, objectives shift, or humans misuse it."
        )

    if "confused" in ql:
        return (
            f"People get confused about {topic} because marketing terms blur boundaries and because outputs can look confident.\n\n"
            "A good mental model: the system is optimizing a goal using patterns—not ‘understanding’ like a person."
        )

    return f"{topic} is best understood by defining it, seeing its parts, and mapping it to real-life use."


def _mechanism_answer(topic: str, question: str) -> str:
    ql = question.lower()
    if "high level" in ql:
        return (
            f"At a high level, {topic} works by taking inputs, transforming them through a learned or designed process, "
            "and producing outputs that support a decision or action.\n\n"
            "In machine learning systems, the transformation is a model trained on examples; in rule systems, it’s logic written by humans.\n\n"
            "What matters most is: the data, the objective, and how you evaluate performance."
        )
    return (
        f"You can test understanding of {topic} by explaining it simply, giving a real example, and stating when it fails.\n\n"
        "If you can do that without buzzwords, you’re on the right track."
    )


def _apply_answer(topic: str, question: str) -> str:
    ql = question.lower()
    if "used in real life" in ql:
        return (
            f"{topic} shows up in products and workflows where decisions repeat at scale.\n\n"
            "Common places: recommendations, search, fraud detection, forecasting, customer support, routing, quality checks, and personalization.\n\n"
            "The best applications have clear goals and measurable success criteria."
        )
    if "fail" in ql or "break" in ql:
        return (
            f"{topic} often fails when real-world inputs differ from what the system was designed or trained for.\n\n"
            "Typical failure causes: distribution shift, hidden bias, unclear objectives, lack of monitoring, and overtrust by users.\n\n"
            "A strong system includes feedback loops, guardrails, and evaluation—not just a model."
        )
    if "simple example" in ql:
        return (
            f"Simple example of {topic}: a spam filter that learns patterns from labeled emails and predicts whether a new email is spam.\n\n"
            "Even simpler: a rules-based system that flags emails with suspicious links—less flexible but easy to explain."
        )
    return (
        f"Real-world examples of {topic} include automation in workplaces, smarter products, and systems that adapt based on data.\n\n"
        "The exact form depends on the domain and constraints."
    )


def _risk_answer(topic: str, question: str) -> str:
    ql = question.lower()
    if "misconception" in ql:
        return (
            f"A common misconception is that {topic} ‘understands’ the way humans do.\n\n"
            "Often it is pattern-matching and optimization. It can look intelligent without having human reasoning.\n\n"
            "A second misconception: higher accuracy automatically means the system is safe—real usage still needs monitoring and constraints."
        )
    return (
        f"Common pitfalls with {topic}: skipping fundamentals, trusting outputs without checking, and using it outside its intended scope.\n\n"
        "Avoid treating it like magic—treat it like an engineered system with limits, failure modes, and responsibilities."
    )


def _next_answer(topic: str) -> str:
    return (
        f"Next step: apply {topic} in a small controlled project.\n\n"
        "Pick one clear goal, measure success, and iterate. Practical work reveals gaps quickly."
    )


# ------------------------------------------------------------
# LLM routing (Option A)
# AI/ML topics -> LLM answers for ALL categories when enabled
# ------------------------------------------------------------
def _is_llm_topic(topic: str) -> bool:
    tl = (topic or "").lower()
    return any(x in tl for x in ["artificial intelligence", "ai", "machine learning", "ml"])


def _llm_answer(topic: str, question: str, meta: Dict[str, Any]) -> str:
    # meta can help your llm_answers.py craft better responses
    return llm_answer_question(topic, question, meta)


def attach_answers(categories: Dict[str, List[str]], topic: str, topic_type: str) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}

    use_llm = _llm_is_enabled() and _is_llm_topic(topic) and (llm_answer_question is not None)


    for cat, questions in categories.items():
        items: List[Dict[str, Any]] = []
        for idx, q in enumerate(questions, start=1):
            archetype = ARCHETYPE_MAP.get(cat, "ORIENT")

            ans = None

            if use_llm:
                meta = {
        "topic_type": topic_type,
        "category": cat,
        "archetype": archetype,
        "mode": "llm",
    }
                ans = _llm_answer(topic, q, meta)

    # IMPORTANT: for AI/ML we DO NOT fall back
                if not ans:
                    ans = (
            "LLM answer could not be generated at this time. "
            "Please retry."
        )
            else:
                    # Non-AI/ML topics may use templates
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

            
            



           

            items.append(
                {
                    "id": f"{cat.lower().replace(' ', '_')}_{idx}",
                    "archetype": archetype,
                    "question": q,
                    "answer": ans,
                }
            )

        out[cat] = items

    return out


# ------------------------------------------------------------
# Main entry
# ------------------------------------------------------------
def interrogate(text: str) -> Dict[str, Any]:
    clean_topic = extract_topic(text)

    if not clean_topic:
        return {
            "topic": "",
            "topic_type": "unknown",
            "categories": {},
            "notes": ["Empty topic received."],
            "summary": [],
            "confidence": 0.0,
            "needs_clarification": True,
            "clarifying_question": "Please provide a topic to explore.",
        }

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
            "v0: interrogation engine",
            "v0: RISK follows ORIENT (guided flow)",
            "v0: AI/ML uses LLM answers when enabled (Option A)",
        ],
        "llm_used": bool(_llm_enabled) and _is_llm_topic(clean_topic),
    }

# api/interrogate.py
# InI.ai – Interrogation Engine (v0)
# Guided thinking order: ORIENT → RISK → MECHANISM → APPLY → NEXT
#
# Imperatives respected:
# - No answer-length capping.
# - Natural language topic extraction preserved.
# - APPLY includes where-used + where-fails.
# - AI + ML may use LLM dynamically; others fallback.

from typing import Dict, List, Tuple, Any
from api.llm_answers import generate_dynamic_answer


LLM_TOPICS = {"Artificial Intelligence", "Machine Learning"}
LLM_ARCHEYPES_ALLOWED = {"ORIENT", "RISK", "MECHANISM", "APPLY", "NEXT"}

ARCHETYPE_ORDER = ["ORIENT", "RISK", "MECHANISM", "APPLY", "LEARN", "COMPARE", "DECIDE", "NEXT"]

ARCHETYPE_MAP = {
    "What": "ORIENT",
    "Why": "ORIENT",
    "When": "ORIENT",
    "who": "ORIENT",
    "Misconceptions": "RISK",
    "Common Challenges": "RISK",
    "How": "MECHANISM",
    "Examples": "APPLY",
    "Where": "APPLY",
    "how to": "LEARN",
    "Related Topics": "NEXT",
}


ERA_HOOKS = {
    "Artificial Intelligence": (
        "Modern AI discussions include Generative AI (GenAI), Large Language Models (LLMs), "
        "Retrieval-Augmented Generation (RAG), and agentic systems that plan, use tools, and act."
    ),
    "Machine Learning": (
        "Modern ML underpins deep learning, recommendation systems, forecasting, and GenAI models."
    ),
}


TOPIC_CORE = {
    "artificial intelligence": {

        "one_liner": (
            "Artificial Intelligence (AI) is the field of building systems that achieve goals by learning patterns from data."
        ),

        # ---------------- ORIENT ----------------
        "orient_plain": (
            "Artificial Intelligence (AI) refers to computer systems that can perform tasks normally requiring human intelligence, "
            "such as understanding language, recognizing patterns, learning from experience, and making decisions.\n\n"
            "Unlike traditional software, AI systems are not driven by fixed rules alone. Instead, they learn statistical patterns "
            "from data and use those patterns to predict, generate, or decide outcomes.\n\n"
            "In the modern era, AI includes Generative AI (GenAI) systems that create text, code, images, audio, and video, as well as "
            "agentic systems that can plan steps, call tools, and act toward goals.\n\n"
            "AI does not possess human understanding or consciousness. Its apparent intelligence comes from scale, optimization, "
            "and exposure to large amounts of data."
        ),

        "orient_problem": (
            "AI exists to solve problems where writing explicit rules is impractical or impossible.\n\n"
            "These include perception (vision, speech), language understanding, prediction, pattern detection, and decision-making "
            "under uncertainty.\n\n"
            "Instead of encoding every rule, humans provide examples, feedback, and objectives, allowing the system to learn what "
            "works.\n\n"
            "Modern AI expands this by enabling systems that generate content (GenAI) and coordinate actions across tools and services "
            "(agentic AI)."
        ),

        "orient_benefits": (
            "AI enables speed, scale, and consistency in tasks involving large volumes of data or repeated decisions.\n\n"
            "It can automate cognitive labor (drafting, summarizing, classifying), enhance decision support (forecasting, risk signals), "
            "and unlock new creative workflows through generative models.\n\n"
            "When applied correctly, AI augments human capability rather than replacing human judgment."
        ),

        "orient_limits": (
            "AI systems are limited by their training data, objectives, and evaluation methods.\n\n"
            "They can produce confident but incorrect outputs, reflect historical bias, and fail when real-world conditions change.\n\n"
            "Generative AI systems may hallucinate—producing plausible but false information—especially when asked beyond their "
            "grounded knowledge.\n\n"
            "AI does not reason about truth or intent; it optimizes patterns. Human oversight remains essential."
        ),

        # ---------------- RISK ----------------
        "risk": [
            "Hallucinations: GenAI systems can produce fluent but false answers. Mitigation requires grounding (RAG), verification, and human review.",
            "Overtrust: Treating AI output as authority rather than hypothesis leads to silent failures.",
            "Bias: Models inherit and amplify biases present in data and labeling decisions.",
            "Drift: Model performance degrades as user behavior or environments change.",
            "Agent risk: Tool-using AI can take harmful actions without strict permissions, sandboxing, and checks.",
            "Security issues: Prompt injection and data leakage can compromise AI systems if not guarded.",
        ],

        # ---------------- MECHANISM ----------------
        "mech_high_level": (
            "At a high level, AI works by training models to minimize error or maximize reward.\n\n"
            "Data is transformed into numerical representations, processed by models, and evaluated against objectives.\n\n"
            "Modern systems combine models with memory, retrieval, tools, and control logic—especially in agentic AI."
        ),

        "mech_beginner_steps": (
            "A practical beginner path:\n\n"
            "1) Learn fundamentals: data, features, labels, training vs inference.\n"
            "2) Build small projects (classification, regression, text tasks).\n"
            "3) Learn evaluation and error analysis.\n\n"
            "Then move into GenAI, retrieval (RAG), and agent workflows."
        ),

        "mech_understanding_check": (
            "You understand AI when you can explain how learning replaces rules, predict failure modes, "
            "and design evaluation for real-world use."
        ),

        # ---------------- APPLY ----------------
        "apply_simple_example": (
            "Example: an AI writing assistant that drafts emails. "
            "It generates suggestions, but a human reviews and approves before sending."
        ),

        "apply_real_world": (
            "AI is used in recommendations, fraud detection, forecasting, medical decision support, "
            "content generation, and agent-based automation."
        ),

        "apply_where_used": (
            "AI is used where decisions repeat at scale and sufficient data exists—such as retail, finance, healthcare, and software."
        ),

        "apply_where_fails": (
            "AI fails when environments change, data is biased, context is missing, or outputs are blindly trusted."
        ),

        # ---------------- NEXT ----------------
        "next_map": (
            "Recommended next steps:\n\n"
            "1) Machine Learning fundamentals\n"
            "2) Deep Learning\n"
            "3) Generative AI (LLMs)\n"
            "4) AI Systems (RAG, monitoring)\n"
            "5) Agentic AI"
        ),
    }
}


# ---------------- Helper functions (UNCHANGED) ----------------

def get_era_note(topic: str) -> str | None:
    for k, v in ERA_HOOKS.items():
        if k.lower() in topic.lower():
            return v
    return None


def extract_topic(user_text: str) -> str:
    t = (user_text or "").strip().lower().rstrip("?.!,;:")
    prefixes = [
        "can you please tell me about", "can you tell me about", "tell me something about",
        "tell me about", "i want to learn about", "i want to know about",
        "can you explain", "please explain", "explain to me",
        "can you teach me about", "teach me about", "what is", "what are"
    ]
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].strip()
            break
    return " ".join(word.capitalize() for word in t.split())


def detect_topic_type(topic: str) -> Tuple[str, float]:
    return "concept", 0.67


def build_summary(topic: str, topic_type: str, confidence: float) -> List[str]:
    return [
        f"{topic} is a topic worth understanding clearly.",
        "We’ll start with fundamentals, examine risks, then explore how it works and applies."
    ]


def build_categories(topic: str, topic_type: str) -> Dict[str, List[str]]:
    return {
        "What": [
            f"What is {topic} in plain language?",
            f"What problem does {topic} exist to solve?",
            f"What are the main benefits of {topic}?",
            f"What are the limitations of {topic}?",
        ],
        "Misconceptions": [
            f"What is a common misconception about {topic}?",
        ],
        "How": [
            f"How does {topic} work at a high level?",
            f"How do beginners start learning {topic}?",
        ],
        "Examples": [
            f"What is a simple example of {topic}?",
            f"What are real-world examples of {topic}?",
        ],
        "Where": [
            f"Where is {topic} used in real life?",
            f"Where does {topic} fail in practice?",
        ],
        "Related Topics": [
            f"What should I learn after {topic}?",
        ],
    }


def build_answer(topic: str, topic_type: str, question: str, archetype: str) -> str:
    core = TOPIC_CORE.get(topic.lower())
    if core:
        if archetype == "ORIENT":
            if "plain" in question.lower():
                return core["orient_plain"]
            if "problem" in question.lower():
                return core["orient_problem"]
            if "benefit" in question.lower():
                return core["orient_benefits"]
            if "limit" in question.lower():
                return core["orient_limits"]
            return core["one_liner"]

        if archetype == "RISK":
            return "Key risks:\n\n" + "\n".join(f"- {r}" for r in core["risk"])

        if archetype == "MECHANISM":
            return core["mech_high_level"]

        if archetype == "APPLY":
            if "fail" in question.lower():
                return core["apply_where_fails"]
            return core["apply_real_world"]

        if archetype == "NEXT":
            return core["next_map"]

    return f"{topic} is a topic worth exploring further."


def interrogate(topic: str) -> Dict[str, Any]:
    clean = extract_topic(topic)
    topic_type, confidence = detect_topic_type(clean)
    summary = build_summary(clean, topic_type, confidence)
    categories = build_categories(clean, topic_type)

    result = {}
    for cat, qs in categories.items():
        items = []
        arch = ARCHETYPE_MAP.get(cat, "ORIENT")
        for i, q in enumerate(qs, 1):
            items.append({
                "id": f"{cat.lower()}_{i}",
                "archetype": arch,
                "question": q,
                "answer": build_answer(clean, topic_type, q, arch),
            })
        result[cat] = items

    return {
        "topic": clean,
        "topic_type": topic_type,
        "categories": result,
        "summary": summary,
        "confidence": confidence,
        "needs_clarification": False,
        "notes": ["AI ORIENT + RISK content polished (v0)"],
    }

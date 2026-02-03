# api/interrogate.py
# InI.ai – Interrogation Engine (v0)
# Guided thinking order: ORIENT → RISK → MECHANISM → APPLY → NEXT

from typing import Dict, List, Tuple, Any


# ==================================================
# Archetype ordering (learning flow)
# ==================================================
ARCHETYPE_ORDER = [
    "ORIENT",
    "RISK",
    "MECHANISM",
    "APPLY",
    "LEARN",
    "COMPARE",
    "DECIDE",
    "NEXT",
]

ARCHETYPE_MAP = {
    "What": "ORIENT",
    "Why": "ORIENT",
    "When": "ORIENT",
    "who": "ORIENT",
    "Misconceptions": "RISK",
    "Common Challenges": "RISK",
    "How": "MECHANISM",
    "Examples": "APPLY",
    "Where": "APPLY",          # IMPORTANT: supported + now surfaced in build_categories()
    "how to": "LEARN",
    "Related Topics": "NEXT",
}


# ==================================================
# Era awareness (light, v0)
# ==================================================
ERA_HOOKS = {
    # Keep it light, but modern. This should not replace deeper topic-core content.
    "Artificial Intelligence": (
        "Modern AI discussions often include Generative AI (GenAI), Large Language Models (LLMs), "
        "Retrieval-Augmented Generation (RAG), and agentic systems that can plan and use tools."
    ),
    "AI": (
        "Modern AI discussions often include Generative AI (GenAI), Large Language Models (LLMs), "
        "Retrieval-Augmented Generation (RAG), and agentic systems that can plan and use tools."
    ),
}


# ==================================================
# Topic-specific intelligence core (v0)
# NOTE: This is intentionally deep for flagship topics like AI.
# ==================================================
TOPIC_CORE = {
    "artificial intelligence": {
        "one_liner": (
            "AI is software that achieves goals by learning patterns from data to predict, generate, or decide."
        ),

        # ---------- ORIENT ----------
        "orient_plain": (
            "Artificial Intelligence (AI) refers to systems that perform tasks by learning patterns from data "
            "rather than following fixed, hand-written rules.\n\n"
            "Most modern AI systems are narrow: they excel at specific tasks such as prediction, generation, "
            "or classification, but they are not general human intelligence.\n\n"
            "In today’s world, AI also includes Generative AI (GenAI) systems that can produce text, code, images, "
            "audio, and video, plus agentic systems that can plan steps and use tools.\n\n"
            "AI often appears intelligent because it is trained on large amounts of data and optimized to produce useful outputs."
        ),
        "orient_problem": (
            "AI exists to solve problems where explicit rules are too complex, too brittle, or too costly to write.\n\n"
            "These include pattern recognition, language processing, prediction, and decision-making under uncertainty.\n\n"
            "Instead of coding rules, humans provide examples and feedback, and the system learns what works.\n\n"
            "Modern AI extends this by enabling systems that can generate content (GenAI) and coordinate actions (agentic workflows)."
        ),
        "orient_benefits": (
            "AI enables speed, scale, and consistency in tasks that involve large volumes of data or repeated decisions.\n\n"
            "It can reduce repetitive cognitive labor (drafting, summarizing, classifying), improve decision support "
            "(forecasting, risk flags), and enable new creative workflows (GenAI).\n\n"
            "When used well, AI amplifies human capability rather than replacing judgment."
        ),
        "orient_limits": (
            "AI systems are limited by their data, objectives, and evaluation methods.\n\n"
            "They can be confidently wrong, reflect bias, and fail when conditions change (drift).\n\n"
            "Generative systems can hallucinate (produce plausible but false content) and may not reliably cite ground truth.\n\n"
            "AI does not understand meaning or truth—it optimizes statistical patterns and objective functions."
        ),

        # ---------- RISK ----------
        # Keep long-form + practical. No forced brevity.
        "risk": [
            "AI does not understand like a human; it learns correlations and patterns and can sound confident while being wrong.",
            "Overtrust is the biggest failure mode: people treat outputs as truth instead of hypotheses to verify.",
            "GenAI can hallucinate: fluent answers that may be partially or fully incorrect without clear warning signs.",
            "Bias can enter through data, labeling, evaluation choices, and deployment context—'neutral AI' is a myth.",
            "Drift happens: models degrade when real-world conditions change and monitoring/retraining are ignored.",
            "Security risks: prompt injection, data leakage, and unsafe tool-use can break agentic systems if not sandboxed.",
        ],

        # ---------- MECHANISM ----------
        "mech_high_level": (
            "At a high level, AI works as a loop: data → model → outputs → evaluation → improvement.\n\n"
            "A model is a mathematical function with adjustable parameters. Training modifies those parameters so outputs "
            "match desired outcomes (supervised), discover structure (unsupervised), or maximize reward (reinforcement).\n\n"
            "Modern AI often uses large neural networks trained on massive datasets to learn representations for language, vision, and decision tasks.\n\n"
            "In GenAI, models learn to generate likely continuations (text/code) or synthesize media from learned representations.\n\n"
            "In agentic AI, the 'AI system' is not only the model: it is typically model + tools + memory/context + planner/controller + evaluators/guards."
        ),
        "mech_beginner_steps": (
            "A practical beginner path:\n\n"
            "1) Learn core concepts: data, features, labels, training vs inference, overfitting.\n"
            "2) Build small projects: one classifier, one regression, one text-based task.\n"
            "3) Learn evaluation: accuracy/F1, error analysis, and how models fail.\n\n"
            "Then add modern AI system skills:\n"
            "- Prompting and verification habits\n"
            "- Retrieval (RAG) basics: grounding answers in sources\n"
            "- Simple agent loops: plan → act (tool) → check → iterate\n\n"
            "Understanding the workflow matters more than memorizing algorithms."
        ),
        "mech_understanding_check": (
            "You understand AI when you can:\n\n"
            "- Explain rules-based code vs learning from data.\n"
            "- Describe training vs inference in one minute.\n"
            "- Predict failure modes such as bias, overfitting, drift, and hallucinations.\n\n"
            "A simple test: given a dataset, you can choose a baseline model, evaluate it, and explain its errors.\n\n"
            "For GenAI: you can describe why hallucinations happen, and how grounding (RAG) + verification reduces them.\n\n"
            "For agentic AI: you can explain why tool-use needs constraints (permissions, sandboxes, checks)."
        ),

        # ---------- APPLY ----------
        "apply_simple_example": (
            "Simple example: your email spam filter.\n\n"
            "You don’t write hard rules for every spam message. Instead, the system learns patterns from labeled examples "
            "(spam vs not spam) and predicts what new emails are likely to be.\n\n"
            "Modern GenAI example: a writing assistant that drafts an email based on your prompt, which you then edit and verify."
        ),
        "apply_real_world": (
            "Real-world AI examples (today):\n\n"
            "1) Search & recommendations: ranking posts/videos/products you’re likely to engage with.\n"
            "2) Customer support: chat + ticket triage + suggested replies (humans still supervise).\n"
            "3) Fraud detection: spotting unusual transactions using patterns.\n"
            "4) Medical imaging assistance: highlighting areas of concern (requires clinician judgment).\n"
            "5) Generative tools: drafting text, code, images (must be reviewed and grounded when accuracy matters).\n"
            "6) Agentic workflows: AI that can plan steps, call tools/APIs, and iterate toward a goal (needs guardrails)."
        ),
        "apply_where_used": (
            "AI is used where decisions repeat at scale and reliable data exists:\n\n"
            "- Retail: demand forecasting, personalization, inventory signals\n"
            "- Finance: fraud, risk scoring, anomaly detection\n"
            "- Healthcare: decision support, imaging assistance\n"
            "- Software: autocomplete, test assistance, monitoring/triage\n"
            "- Operations: scheduling, routing, quality checks\n"
            "- Knowledge work: summarization, drafting, research assistance (with verification)\n\n"
            "Rule of thumb: AI shines when it augments humans with speed + pattern detection, not when it replaces judgment."
        ),
        "apply_where_fails": (
            "AI often fails when:\n\n"
            "- The environment changes (drift) and the model isn’t updated.\n"
            "- The data is biased, incomplete, or unrepresentative.\n"
            "- The task needs hidden context the model cannot access.\n"
            "- People over-trust outputs without verification.\n"
            "- Agentic systems get unsafe tool access (prompt injection / bad actions).\n\n"
            "Practical rule: treat AI like a strong assistant, not an authority. Add checks, monitoring, and human review."
        ),
    }
}


# ==================================================
# Helpers
# ==================================================
def get_era_note(topic: str) -> str | None:
    for k, v in ERA_HOOKS.items():
        if k.lower() in topic.lower():
            return v
    return None


def extract_topic(user_text: str) -> str:
    """
    v0-but-robust topic extraction.

    Imperative: DO NOT regress on natural phrasing.
    Handles:
    - "can you tell me about AI"
    - "please explain machine learning"
    - "can you teach me about AI and how to learn it?"
    - "tell me about AI, and also its applications"
    - "what is AI?"
    """

    t = (user_text or "").strip().lower()
    t = t.strip().rstrip("?.!,;:")

    # 1) Strip common polite/intent prefixes (kept + expanded; no removals)
    prefixes = [
        "can you please tell me about",
        "can you tell me about",
        "could you tell me about",
        "would you tell me about",
        "please tell me about",
        "tell me something about",
        "tell me about",
        "i want to learn about",
        "i want to know about",
        "i want to understand",
        "can you explain",
        "could you explain",
        "would you explain",
        "please explain",
        "explain to me",
        "explain",
        "help me understand",
        "can you teach me about",
        "could you teach me about",
        "teach me about",
        "teach me",
        "what is",
        "what are",
        "how to",
        "how do i",
        "how can i",
    ]
    for p in prefixes:
        if t.startswith(p):
            t = t[len(p):].strip()
            break

    # 2) Remove leftover filler words at start
    fillers = {"the", "a", "an", "about", "regarding", "on", "of"}
    while True:
        parts = t.split()
        if parts and parts[0] in fillers:
            t = " ".join(parts[1:]).strip()
        else:
            break

    # 3) Extract topic from full sentences by cutting at common tail-clauses
    cut_markers = [
        " and how to",
        " and how do i",
        " and how can i",
        " and what about",
        " and also",
        " and its",
        " and their",
        " and then",
        " and where",
        " and when",
        " and why",
        " and who",
        " and what",
        " because",
        " so that",
        " so i can",
        " for beginners",
        " in simple words",
        " step by step",
        " with examples",
    ]
    for m in cut_markers:
        idx = t.find(m)
        if idx != -1:
            t = t[:idx].strip()
            break

    # Cut plain "x and y" (treat as extra request), but keep "x vs y"
    if " vs " not in t and " versus " not in t:
        if " and " in t:
            t = t.split(" and ", 1)[0].strip()

    # 4) Normalize whitespace
    t_clean = " ".join(t.split()).strip()

    # 5) Abbreviation normalization (v0-high impact)
    norm_map = {
        "ai": "Artificial Intelligence",
        "genai": "Generative AI",
        "gen ai": "Generative AI",
        "llm": "Large Language Models",
        "llms": "Large Language Models",
        "rag": "Retrieval-Augmented Generation",
        "ml": "Machine Learning",
        "dl": "Deep Learning",
        "nlp": "Natural Language Processing",
        "agentic ai": "Agentic AI",
        "agents": "AI Agents",
        "agent ai": "AI Agents",
    }

    if not t_clean:
        return ""

    if t_clean in norm_map:
        return norm_map[t_clean]

    return " ".join(w.capitalize() for w in t_clean.split())


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


def build_summary(topic: str, topic_type: str, confidence: float) -> List[str]:
    # Keep existing behavior; it only triggers if confidence is low.
    if confidence < 0.5:
        return [
            f"Topic: {topic}.",
            "I might need a bit more context to be precise.",
            "Start with a simple overview, then we can go deeper.",
        ]

    return [
        f"{topic} is a topic worth understanding clearly.",
        "We’ll build clarity first, then examine risks and how it works.",
        "Finally, we’ll connect it to real-world use.",
    ]


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
        "Misconceptions": [
            f"What is a common misconception about {t}?",
        ],
        "How": [
            f"How does {t} work at a high level?",
            f"How do beginners start learning {t} (first 3 steps)?",
            f"How can I tell if I truly understand {t}?",
        ],
        "Examples": [
            f"What is a simple example of {t}?",
            f"What are real-world examples of {t}?",
        ],

        # ✅ RESTORED / GUARANTEED VISIBILITY
        "Where": [
            f"Where is {t} used in real life?",
            f"Where does {t} usually fail or break in practice?",
        ],

        "Related Topics": [
            f"What topics are closely related to {t}?",
        ],
    }


# ==================================================
# Core Answer Engine
# ==================================================
def build_answer(topic, topic_type, category, question, archetype):
    topic = topic.strip()
    ql = question.lower()
    era_note = get_era_note(topic)
    core = TOPIC_CORE.get(topic.lower())

    # ---------- ORIENT ----------
    if archetype == "ORIENT":
        if core:
            if "plain language" in ql:
                ans = core["orient_plain"]
            elif "problem" in ql:
                ans = core["orient_problem"]
            elif "benefit" in ql:
                ans = core["orient_benefits"]
            elif "limit" in ql:
                ans = core["orient_limits"]
            else:
                ans = core["one_liner"]
        else:
            if "plain language" in ql:
                ans = (
                    f"{topic} refers to an idea or system people use to solve a specific kind of problem.\n\n"
                    "The simplest way to understand it is: what it is, why it exists, and where it shows up."
                )
            elif "problem" in ql:
                ans = (
                    f"{topic} exists to solve problems where a simple approach is too slow, too manual, or too error-prone.\n\n"
                    f"If rules are hard to write but examples are easy to show, {topic} is often relevant."
                )
            elif "benefit" in ql:
                ans = (
                    f"{topic} often brings speed, scale, and consistency.\n\n"
                    "It helps people make better decisions or build more capable systems with less manual work."
                )
            elif "limit" in ql:
                ans = (
                    f"{topic} has limits that appear when assumptions break.\n\n"
                    "A good habit is to ask: when does it fail, and what happens then?"
                )
            else:
                ans = (
                    f"{topic} is worth breaking down into parts and examples to make it intuitive.\n\n"
                    "Start simple, then deepen gradually."
                )

        if era_note and era_note not in ans:
            ans += "\n\n" + era_note
        return ans

    # ---------- RISK ----------
    if archetype == "RISK":
        if core and core.get("risk"):
            bullets = "\n".join([f"- {x}" for x in core["risk"]])
            ans = (
                f"Key risks and misconceptions about {topic}:\n\n"
                f"{bullets}\n\n"
                "Safe practice:\n"
                "- Validate outputs (treat them as hypotheses).\n"
                "- Define success metrics.\n"
                "- Monitor behavior over time.\n"
                "- Use guardrails when tools/actions are involved."
            )
        else:
            if "misconception" in ql:
                ans = (
                    f"A common misconception is thinking {topic} guarantees correctness.\n\n"
                    "Many ideas/tools are useful but still fail under certain conditions.\n\n"
                    "Always ask what assumptions it relies on, and where it breaks."
                )
            else:
                ans = (
                    f"Common risks include misunderstanding {topic}, overestimating it, "
                    "or applying it without validation.\n\n"
                    "A good habit is to ask: where can this fail, and how will I notice?"
                )

        if era_note and era_note not in ans:
            ans += "\n\n" + era_note
        return ans

    # ---------- MECHANISM ----------
    if archetype == "MECHANISM":
        if core:
            if "work at a high level" in ql:
                ans = core["mech_high_level"]
            elif "first 3 steps" in ql or "start learning" in ql:
                ans = core["mech_beginner_steps"]
            elif "truly understand" in ql:
                ans = core["mech_understanding_check"]
            else:
                ans = core["mech_high_level"]
        else:
            if "work at a high level" in ql:
                ans = (
                    f"{topic} works by taking inputs, applying a process or model, and producing outputs.\n\n"
                    "To understand the mechanism, identify inputs → transformation → outputs → feedback."
                )
            elif "first 3 steps" in ql or "start learning" in ql:
                ans = (
                    f"To start learning {topic}:\n\n"
                    "1) Learn a simple definition + core terms.\n"
                    "2) Do one tiny example or demo.\n"
                    "3) Learn one common failure/mistake and how to avoid it.\n\n"
                    "Repeat with slightly harder examples until it becomes intuitive."
                )
            elif "truly understand" in ql:
                ans = (
                    f"You understand {topic} when you can explain it simply, apply it to one example, "
                    "and predict where it fails.\n\n"
                    "A good test: teach it in 60 seconds, then solve one small problem using it."
                )
            else:
                ans = (
                    f"{topic} works through components that interact to turn inputs into outputs.\n\n"
                    "Focus on the flow: inputs → steps → outputs → feedback."
                )

        if era_note and era_note not in ans:
            ans += "\n\n" + era_note
        return ans

    # ---------- APPLY ----------
    if archetype == "APPLY":
        # Topic-core APPLY (best quality)
        if core:
            if "simple example" in ql:
                ans = core.get("apply_simple_example")
            elif "real-world examples" in ql or "real world examples" in ql:
                ans = core.get("apply_real_world")
            elif ql.startswith("where is") or "where is" in ql or "where used" in ql:
                ans = core.get("apply_where_used")
            elif "fail" in ql or "break" in ql:
                ans = core.get("apply_where_fails")
            else:
                ans = core.get("apply_real_world") or core.get("apply_where_used")

            if ans:
                if era_note and era_note not in ans:
                    ans += "\n\n" + era_note
                return ans

        # Generic APPLY (works for any topic)
        if "simple example" in ql:
            return (
                f"Simple example of {topic}:\n\n"
                f"Imagine a small everyday situation where you use {topic} to get a better result faster. "
                "The goal is to see the idea in action, not memorize theory."
            )

        if "real-world examples" in ql:
            return (
                f"Real-world examples of {topic} usually show up in workplaces, products, or daily decisions.\n\n"
                "To make it concrete: find one consumer example, one business example, and one failure case."
            )

        if "where is" in ql or "where used" in ql:
            return (
                f"{topic} is used wherever it reliably improves outcomes—speed, quality, cost, or clarity.\n\n"
                "A good lens: where does this reduce repeated effort or reduce mistakes?"
            )

        if "fail" in ql or "break" in ql:
            return (
                f"{topic} often fails when assumptions break, context changes, or people over-trust it.\n\n"
                "A practical habit: list 3 ways it can go wrong before you rely on it."
            )

        return (
            f"In practice, {topic} appears in tools, systems, or workflows that solve real problems.\n\n"
            "Application is where usefulness becomes obvious—and where limitations show up."
        )

    # ---------- NEXT ----------
    if archetype == "NEXT":
        return (
            f"A good next step is to apply {topic} in a small, controlled way.\n\n"
            "Build something simple, observe failures, and iterate."
        )

    return f"This question relates to {topic}."


# ==================================================
# Assembly
# ==================================================
def interrogate(topic: str) -> Dict[str, Any]:
    clean_topic = extract_topic(topic)

    if not clean_topic:
        return {
            "topic": topic,
            "categories": {},
            "notes": ["Empty topic received."],
            "summary": [],
            "confidence": 0.0,
            "needs_clarification": True,
            "clarifying_question": "Please provide a topic to explore.",
        }

    topic_type, confidence = detect_topic_type(clean_topic)
    summary = build_summary(clean_topic, topic_type, confidence)

    categories = build_categories(clean_topic, topic_type)

    out = {}
    for cat, qs in categories.items():
        items = []
        for i, q in enumerate(qs, start=1):
            arch = ARCHETYPE_MAP.get(cat, "ORIENT")
            items.append({
                "id": f"{cat.lower()}_{i}",
                "archetype": arch,
                "question": q,
                "answer": build_answer(clean_topic, topic_type, cat, q, arch)
            })
        out[cat] = items

    # order categories by archetype flow
    ordered = {}
    seen = set()
    for arch in ARCHETYPE_ORDER:
        for cat, items in out.items():
            if items and items[0].get("archetype") == arch and cat not in seen:
                ordered[cat] = items
                seen.add(cat)

    # keep leftovers (just in case)
    for cat, items in out.items():
        if cat not in seen:
            ordered[cat] = items

    return {
        "topic": clean_topic,
        "topic_type": topic_type,
        "categories": ordered,
        "summary": summary,
        "confidence": confidence,
        "needs_clarification": False,
        "clarifying_question": "",
        "notes": [
            "v0: guided thinking order enforced",
            "v0: robust topic extraction (natural phrasing + abbreviations)",
            "v0: ORIENT tuned (deep, non-trimmed answers)",
            "v0: RISK tuned (misconceptions + modern failure modes)",
            "v0: MECHANISM tuned (model + systems framing for modern AI)",
            "v0: APPLY tuned (examples + where-used + where-fails restored)",
        ],
    }

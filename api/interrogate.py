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


TOPIC_CORE = {
    "artificial intelligence": {
        "one_liner": "AI is software that achieves goals by learning patterns from data to predict, generate, or decide.",
        "orient_plain": (
            "Artificial Intelligence (AI) refers to systems that perform tasks by learning patterns from data "
            "instead of following fixed, hand-written rules.\n\n"
            "Most modern AI is task-specific (narrow): it can be excellent at a particular job, but it is not "
            "general human intelligence.\n\n"
            "AI often looks smart because it is trained on many examples and optimized to produce useful outputs."
        ),
        "orient_problem": (
            "AI exists to handle problems where rules are too complex, too brittle, or too costly to write manually.\n\n"
            "These are often tasks like recognizing patterns, predicting outcomes, ranking options, understanding language, "
            "or generating content from examples.\n\n"
            "AI shifts work from 'coding rules' to 'learning from data + measuring performance'."
        ),
        "orient_benefits": (
            "AI can automate repetitive decisions, improve accuracy on pattern-heavy tasks, and scale expertise.\n\n"
            "It is valuable when speed, personalization, detection (fraud/spam), prediction, or generation is needed.\n\n"
            "Used well, AI augments humans; used blindly, it can create silent failures."
        ),
        "orient_limits": (
            "AI is limited by its data, objective, and evaluation setup.\n\n"
            "It can output confident but wrong results, reflect bias in data, and degrade when conditions change (data drift).\n\n"
            "AI does not 'understand' truth—most systems optimize patterns and probabilities."
        ),
        "risk": [
            "AI does not truly understand; it matches patterns.",
            "Main failure mode: overtrust without evaluation/monitoring; also bias + data drift."
        ],
    }
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
# ORIENT answers (legacy; kept)
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
            "If you can’t easily write rules, but you can show examples, AI is often a fit."
        )

    if "benefit" in question.lower():
        return (
            "Benefits typically include speed, scale, and consistency.\n\n"
            "AI can detect patterns humans miss and automate repetitive decisions."
        )

    if "limit" in question.lower() or "downside" in question.lower():
        parts = [
            "Limitations include errors, bias, and brittleness outside training data.",
            "AI can be confidently wrong and requires monitoring."
        ]
        if era:
            parts.append(era)
        return "\n\n".join(parts)

    return f"{topic} is a concept worth breaking down into parts and examples."


# -----------------------------
# Quick examples
# -----------------------------
def build_quick_examples(topic: str, topic_type: str, confidence: float) -> list[str]:
    t = topic

    if confidence < 0.5:
        return [
            f"Everyday: a simple place you might notice {t}.",
            f"Work/real-life: one practical situation involving {t}.",
        ]

    if topic_type == "comparison":
        return [
            f"Scenario: choosing between two options related to {t}.",
            "Quick rule: pick A when speed/short-term matters; pick B when long-term stability matters.",
            "Common mistake: comparing prices only, ignoring total cost/constraints.",
        ]

    if topic_type == "decision":
        return [
            f"Scenario: you must decide something involving {t} this week.",
            "Tradeoff example: saving money vs saving time/effort.",
            "Regret case: choosing quickly without checking constraints.",
        ]

    if topic_type == "troubleshooting":
        return [
            f"Symptom: something goes wrong related to {t}.",
            "First check: confirm the simplest cause before deeper steps.",
            "Fix example: apply one safe change, then re-test.",
        ]

    if topic_type == "skill":
        return [
            f"Practice: spend 20 minutes/day doing one small task in {t}.",
            "Beginner mistake: trying advanced stuff before basics.",
            "Progress sign: you can explain it in 2 sentences + do a tiny demo.",
        ]

    return [
        f"Everyday: a simple example of {t}.",
        f"Work: how {t} shows up in a job or project.",
        f"Without it: what becomes confusing or fails when you ignore {t}.",
    ]


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

            "Common Mistakes": [
                f"What are the top 3 beginner mistakes in {t}?",
                "What habit causes most people to plateau?",
            ],

            "Resources": [
                f"What are the best resources to learn {t} effectively?",
                f"What communities or groups focus on {t}?",
            ],

            "who": [
                f"Who are the top experts or influencers in {t}?",
                f"Who created or pioneered {t}?",
            ],

            "Common Traps": [
                f"What do people commonly overlook when deciding about {t}?",
                "What terms/conditions should be read carefully?",
            ],
        }

    if topic_type == "comparison":
        return {
            "Define": [
                f"What is {t} comparing, exactly (A vs B)?",
                "What is the real goal behind this comparison?",
            ],
            "Similarities": [
                "In what ways are the two options similar?",
                "What do they both do well?",
            ],
            "Differences": [
                "What are the biggest differences (features, cost, risk, complexity)?",
                "What difference matters most for your situation?",
            ],
            "Who Should Choose What": [
                "Who should choose option A, and who should choose option B?",
                "What’s the most common wrong choice people make here?",
            ],
            "Decision Rule": [
                "What simple rule can decide quickly?",
                "What’s the ‘good enough’ choice if you’re unsure?",
            ],
        }

    # default: concept
    return {
        "What": [
            f"What is {t} in plain language?",
            f"What are the key parts/components of {t}?",
            f"What problem does {t} exist to solve?",
            f"What are the main benefits of {t}?",
            f"What are the limitations or downsides of {t}?",
            f"What are common use cases for {t}?",
            f"What are the important topics to understand about {t}?",
            f"What terminology should I know related to {t}?",
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
        "Misconceptions": [
            f"What is a common misconception about {t}?",
            f"What is {t} often confused with?",
        ],
        "Examples": [
            f"What is a simple example that illustrates {t}?",
            f"What are some real-world examples of {t} in action?",
        ],
        "Related Topics": [
            f"What topics are closely related to {t}?",
            f"How does {t} connect to other important concepts?",
        ],
        "how to": [
            f"What are the first steps to get started with {t}?",
            f"What resources are best for learning {t}?",
        ],
        "Common Challenges": [
            f"What are common challenges people face when learning {t}?",
            f"What pitfalls should I avoid when studying {t}?",
        ],
        "who": [
            f"Who are the leading experts or influencers in the field of {t}?",
            f"Who created or discovered {t}?",
        ],
    }


def dedupe_questions(categories: dict) -> dict:
    """
    Remove duplicate / near-duplicate questions within each category.
    v0: simple normalization-based dedupe.
    """
    def norm(q: str) -> str:
        q = q.strip().lower()
        q = q.replace("?", "")
        q = " ".join(q.split())
        return q

    cleaned = {}
    for cat, qs in categories.items():
        seen = set()
        out = []
        for q in qs:
            k = norm(q)
            if k not in seen:
                seen.add(k)
                out.append(q)
        cleaned[cat] = out
    return cleaned


def dedupe_across_categories(categories: dict) -> dict:
    """
    Remove repeated questions across categories (global dedupe).
    Keeps the first occurrence and drops later duplicates.
    v0: normalization-based.
    """
    def norm(q: str) -> str:
        q = q.strip().lower()
        q = q.replace("?", "")
        q = " ".join(q.split())
        return q

    seen = set()
    out = {}
    for cat, qs in categories.items():
        kept = []
        for q in qs:
            k = norm(q)
            if k not in seen:
                seen.add(k)
                kept.append(q)
        out[cat] = kept
    return out


def clarification_for(topic: str, topic_type: str) -> str:
    t = topic
    if topic_type == "troubleshooting":
        return "Is this a technical error you're trying to fix? If yes, what exact error text do you see?"
    if topic_type == "decision":
        return f"Are you deciding between options related to {t}? If yes, what constraints matter most (cost, time, risk)?"
    if topic_type == "skill":
        return f"Do you want to learn {t} (a skill), or understand {t} as a concept?"
    # concept / fallback
    return f"Do you want a simple definition of {t}, or a deeper explanation with examples?"


def cap_categories(categories: dict, max_per_category: int = 5) -> dict:
    capped = {}
    for cat, qs in categories.items():
        capped[cat] = qs[:max_per_category]
    return capped


def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in s).strip("_")


# ==========================================================
# CORE ANSWER ENGINE (THIS IS WHAT YOUR APP USES)
# - Upgraded ORIENT + RISK (your requirement)
# - Everything else remains as before
# ==========================================================
def build_answer(topic, topic_type, category, question, archetype):
    topic = topic.strip()
    ql = (question or "").strip().lower()
    era_note = get_era_note(topic)

    # Topic-core lookup (v0: only a few topics; fallback works for all)
    core = TOPIC_CORE.get(topic.lower())

    # -------------------------
    # ORIENT (tuned, non-redundant)
    # -------------------------
    if archetype == "ORIENT":
        # Prefer topic-specific tuned answers when available
        if core:
            if "plain language" in ql or ql.startswith("what is"):
                ans = core.get("orient_plain") or core.get("one_liner", "")
            elif "problem" in ql or "exist to solve" in ql:
                ans = core.get("orient_problem") or core.get("one_liner", "")
            elif "benefit" in ql or "main benefits" in ql:
                ans = core.get("orient_benefits") or core.get("one_liner", "")
            elif "limit" in ql or "downside" in ql or "limitations" in ql:
                ans = core.get("orient_limits") or core.get("one_liner", "")
            else:
                ans = core.get("one_liner", "")
            if era_note and era_note not in ans:
                ans = ans + "\n\n" + era_note
            return ans

        # Generic tuned ORIENT (works for any topic)
        if "plain language" in ql or ql.startswith("what is"):
            parts = [
                f"{topic} refers to systems or methods that achieve useful outcomes by learning patterns from examples or data, rather than only following fixed rules.",
                "In practice, most real-world systems are narrow: excellent at specific tasks but not general human intelligence.",
                "A good mental model: it’s 'learn from examples + evaluate performance + improve'."
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        if "problem" in ql or "exist to solve" in ql:
            parts = [
                f"{topic} exists for situations where writing precise rules is too hard, too expensive, or too brittle.",
                "It’s useful when you can’t easily explain rules, but you can provide examples and define what 'good' looks like.",
                "It shifts effort from 'coding rules' to 'learning from data + measuring results'."
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        if "benefit" in ql:
            parts = [
                f"{topic} can increase speed and consistency on repetitive decisions, and improve accuracy on pattern-heavy tasks.",
                "It enables personalization at scale (different outputs for different users/situations).",
                "Used well, it augments human work; used blindly, it creates hidden risks."
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        if "confus" in ql:
            return (
                f"People get confused about {topic} because the term is used for many different things—from simple automation to advanced models.\n\n"
                "Media hype often blurs the line between narrow tools and general intelligence.\n\n"
                "A practical rule: ask what data it learns from and how performance is measured."
            )

        if "limit" in ql or "downside" in ql or "limitations" in ql:
            parts = [
                f"{topic} is limited by its data, objective, and evaluation setup.",
                "It can produce confident-but-wrong outputs, reflect biases, and fail when conditions change (data drift).",
                "It does not guarantee truth; it usually optimizes patterns/probabilities."
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        # ORIENT fallback
        base = (
            f"{topic} is a concept worth understanding clearly. "
            "Start by defining it simply, then connect it to real-world use and common pitfalls."
        )
        if era_note:
            base += " " + era_note
        return base

    # -------------------------
    # MECHANISM (unchanged)
    # -------------------------
    if archetype == "MECHANISM":
        base = (
            f"{topic} works by combining several components that interact with each other. "
            f"At a high level, inputs are processed through defined steps or models, "
            f"leading to outputs that improve decisions or actions. The exact mechanics "
            f"depend on the specific system or implementation."
        )

        if era_note:
            base += " " + era_note
        return base

    # -------------------------
    # APPLY (unchanged)
    # -------------------------
    if archetype == "APPLY":
        return (
            f"In real life, {topic} is used in practical scenarios such as workplaces, "
            f"products, or everyday tools. These applications help solve real problems, "
            f"improve efficiency, or enable new capabilities that were previously difficult."
        )

    # -------------------------
    # LEARN (unchanged)
    # -------------------------
    if archetype == "LEARN":
        base = (
            f"To learn {topic}, start with the fundamentals and build gradually. "
            f"Focus first on core concepts, then practice applying them through small exercises "
            f"or projects. Consistent practice and real-world exposure matter more than speed."
        )
        if era_note:
            base += " " + era_note
        return base

    # -------------------------
    # COMPARE (unchanged)
    # -------------------------
    if archetype == "COMPARE":
        return (
            f"When comparing options related to {topic}, the key differences usually involve "
            f"purpose, complexity, cost, and suitability for a given situation. "
            f"The better choice depends on what problem you are trying to solve."
        )

    # -------------------------
    # DECIDE (unchanged)
    # -------------------------
    if archetype == "DECIDE":
        return (
            f"Whether you should pursue or choose {topic} depends on your goals, constraints, "
            f"and current situation. Consider factors such as time investment, expected benefits, "
            f"and how it aligns with your long-term plans."
        )

    # -------------------------
    # RISK (TUNED, immediately after ORIENT as per your requirement)
    # -------------------------
    if archetype == "RISK":
        # Topic-specific risks when available
        if core and core.get("risk"):
            bullets = core["risk"]
            base = (
                f"Key risks/limits for {topic}:\n\n"
                f"- {bullets[0]}\n"
                f"- {bullets[1]}\n\n"
                "A practical safety habit: verify outputs, define success metrics, and monitor for drift."
            )
            if era_note and era_note not in base:
                base += "\n\n" + era_note
            return base

        # Generic tuned risk responses based on the question
        if "misconception" in ql:
            return (
                f"A common misconception is that {topic} 'understands' like a human.\n\n"
                "Most systems optimize patterns and can sound confident even when wrong.\n\n"
                "Treat outputs as suggestions unless verified."
            )

        if "challenge" in ql or "pitfall" in ql:
            return (
                f"Common pitfalls with {topic} include skipping fundamentals, overtrusting outputs, and ignoring edge cases.\n\n"
                "A good discipline is to test failure modes early and revise assumptions often.\n\n"
                "If it's high-stakes, require evidence, not vibes."
            )

        if "confus" in ql:
            return (
                f"People overtrust {topic} when it looks fluent, fast, or authoritative.\n\n"
                "The risk is accepting outputs without validation.\n\n"
                "A safe rule: ask 'what could make this wrong?' and test that first."
            )

        if "limit" in ql or "downside" in ql:
            return (
                f"Limitations include bias from data, brittleness outside training conditions, and silent performance decay.\n\n"
                "The most dangerous failure is confident wrong output.\n\n"
                "Mitigation: evaluation, monitoring, and human-in-the-loop review."
            )

        # RISK fallback (still tuned)
        return (
            f"Common mistakes with {topic} include misunderstanding its purpose, "
            f"overestimating what it can do, and using it without validation.\n\n"
            "Safe habit: test on edge cases, keep feedback loops, and monitor changes over time."
        )

    # -------------------------
    # NEXT (unchanged)
    # -------------------------
    if archetype == "NEXT":
        return (
            f"A good next step after understanding {topic} is to apply it in a small, "
            f"controlled way. This could mean experimenting, building something simple, "
            f"or deepening one specific area rather than trying to learn everything at once."
        )

    # fallback (should rarely hit)
    return f"This question relates to {topic}. Consider exploring it step by step for clarity."


def attach_answers(categories: dict, topic: str, topic_type: str) -> dict:
    """
    Convert category -> [question str] into category -> [{id, question, answer}]
    """
    out = {}
    for cat, qs in categories.items():
        items = []
        cat_id = _slug(cat)
        for i, q in enumerate(qs, start=1):
            archetype = ARCHETYPE_MAP.get(cat, "ORIENT")

            items.append({
                "id": f"{cat_id}_{i}",
                "archetype": archetype,
                "question": q,
                "answer": build_answer(topic, topic_type, cat, q, archetype)
            })
        out[cat] = items
    return out


def interrogate(topic: str) -> Dict[str, object]:
    """
    Return structured, relevant interrogative questions for a topic.
    v0 intelligence: templates + light normalization.
    """
    clean_topic = extract_topic(topic)
    if not clean_topic:
        return {"topic": topic, "categories": {}, "notes": ["Empty topic received."]}

    topic_type, confidence = detect_topic_type(clean_topic)
    summary = build_summary(clean_topic, topic_type, confidence)
    needs_clarification = confidence < 0.5
    clarifying_question = clarification_for(clean_topic, topic_type) if needs_clarification else ""

    categories = build_categories(clean_topic, topic_type)
    categories = dedupe_questions(categories)
    categories = dedupe_across_categories(categories)
    categories = cap_categories(categories, max_per_category=5)

    notes = [
        "v0: template-based interrogation (no external knowledge yet).",
        "v0: archetype-aware answers + ordered understanding flow.",
    ]

    quick_examples = build_quick_examples(clean_topic, topic_type, confidence)

    qa_categories = attach_answers(categories, clean_topic, topic_type)

    ordered_categories = {}
    seen = set()

    for arch in ARCHETYPE_ORDER:
        for cat, items in qa_categories.items():
            if items and items[0].get("archetype") == arch and cat not in seen:
                ordered_categories[cat] = items
                seen.add(cat)

    # Keep anything we didn't classify explicitly (so nothing disappears)
    for cat, items in qa_categories.items():
        if cat not in seen:
            ordered_categories[cat] = items

    qa_categories = ordered_categories

    return {
        "topic": clean_topic,
        "topic_type": topic_type,
        "categories": qa_categories,
        "notes": notes,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
        "clarifying_question": clarifying_question,
        "quick_examples": quick_examples,
        "summary": summary
    }

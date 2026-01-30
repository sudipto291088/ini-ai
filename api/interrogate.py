# api/interrogate.py

from __future__ import annotations

from typing import Dict, List


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
    "Understanding": "ORIENT",
    "Basics": "ORIENT",
    "How it works": "MECHANISM",
    "Mechanism": "MECHANISM",
    "Applications": "APPLY",
    "Use cases": "APPLY",
    "Learning": "LEARN",
    "Getting started": "LEARN",
    "Comparison": "COMPARE",
    "Decision": "DECIDE",
    "Risks": "RISK",
    "Misconceptions": "RISK",
    "Next steps": "NEXT",
}

ARCHETYPE_MAP.update({
    "What": "ORIENT",
    "Why": "ORIENT",
    "How": "MECHANISM",
    "Where": "APPLY",
    "When": "ORIENT",
    "Examples": "APPLY",
    "Related Topics": "NEXT",
    "Common Challenges": "RISK",
    "Common Traps": "RISK",
    "Decision Rule": "DECIDE",
    "Differences": "COMPARE",
    "Similarities": "COMPARE",
    "Who Should Choose What": "DECIDE",
})


ERA_HOOKS = {
    "Artificial Intelligence": {
        "keywords": ["agent", "agentic", "generative", "foundation model"],
        "notes": "Modern discussions often include generative models and agent-based systems."
    },
    "AI": {
        "keywords": ["agent", "agentic", "generative"],
        "notes": "Current AI focuses heavily on generative and agent-like capabilities."
    },
    "Machine Learning": {
        "keywords": ["deep learning", "transformers"],
        "notes": "Recent ML progress is driven largely by deep learning architectures."
    }
}


def get_era_note(topic):
    for key, data in ERA_HOOKS.items():
        if key.lower() in topic.lower():
            return data["notes"]
    return None


def extract_topic(user_text: str) -> str:
    """
    Extract a clean topic phrase from a natural language user prompt.
    v0: rule-based normalization.
    """
    t = user_text.strip().lower()

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
        "please explain",
        "could you tell me about",
        "give me an overview of",
        "overview of",
        "summary of",
        "explain to me",
        "could you explain to me",
        "please explain to me",
        "how do i",
        "how to",
    ]

    for p in sorted(prefixes, key=len, reverse=True):
        if t.startswith(p):
            t = t[len(p):].strip()
            break

    t = t.rstrip("?.!")
    t = " ".join(word.capitalize() for word in t.split())
    return t


def build_summary(topic: str, topic_type: str, confidence: float) -> list[str]:
    t = topic

    if topic_type == "skill":
        return [
            f"{t} is a skill you can build with practice.",
            "Progress comes from small drills, feedback loops, and clear milestones.",
            "We’ll outline a beginner path and common mistakes to avoid.",
        ]

    if confidence < 0.5 and len(topic.split()) <= 4:
        return [
            f"Topic: {t}.",
            "I might need a bit more context to be precise.",
            "Start with a simple overview, then we can go deeper.",
        ]

    if topic_type == "comparison":
        return [
            f"{t} is a comparison question (A vs B).",
            "The goal is to identify the key differences and what matters most for your situation.",
            "A good comparison ends with a simple decision rule.",
        ]

    if topic_type == "decision":
        return [
            f"{t} is a decision topic.",
            "Good decisions clarify constraints, tradeoffs, and risks.",
            "We’ll narrow down options and use a simple rule to choose.",
        ]

    if topic_type == "troubleshooting":
        return [
            f"{t} sounds like a troubleshooting problem.",
            "We’ll identify symptoms, reproduce the issue, and isolate the root cause.",
            "Then we’ll try the safest fix first and re-test.",
        ]

    return [
        f"{t} is a concept/topic to understand clearly.",
        "We’ll define it simply, break it into parts, and connect it to real-world use.",
        "Then we’ll test understanding using focused questions and examples.",
    ]


def detect_topic_type(topic: str) -> tuple[str, float]:
    t = topic.lower()

    troubleshooting_signals = [
        "error", "not working", "failed", "issue", "problem",
        "exception", "refused", "cannot", "can't"
    ]

    decision_signals = [
        "should i", "better", "which",
        "choose", "leasing", "buying"
    ]

    skill_signals = [
        "how to", "learn", "practice", "trading", "coding",
        "programming", "using", "develop"
    ]

    comparison_signals = [" vs ", " versus ", "compare", "comparison"]
    if any(s in t for s in comparison_signals):
        return "comparison", 0.67

    scores = {
        "troubleshooting": sum(s in t for s in troubleshooting_signals),
        "decision": sum(s in t for s in decision_signals),
        "skill": sum(s in t for s in skill_signals),
        "concept": 1,
    }

    topic_type = max(scores, key=scores.get)
    max_score = scores[topic_type]
    confidence = min(1.0, max_score / 3)

    if topic_type == "concept" and max_score <= 1:
        confidence = 0.67

    return topic_type, round(confidence, 2)


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

    return {
        "What": [
            f"What is {t} in plain language?",
            f"What are the key parts/components of {t}?",
            f"What problem does {t} exist to solve?",
            f"What are the main benefits of {t}?",
            f"What are the limitations or downsides of {t}?",
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
        "who": [
            f"Who are the leading experts or influencers in the field of {t}?",
            f"Who created or discovered {t}?",
        ],
    }


def dedupe_questions(categories: dict) -> dict:
    def norm(q: str) -> str:
        q = q.strip().lower().replace("?", "")
        return " ".join(q.split())

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


def cap_categories(categories: dict, max_per_category: int = 5) -> dict:
    return {cat: qs[:max_per_category] for cat, qs in categories.items()}


def clarification_for(topic: str, topic_type: str) -> str:
    t = topic
    if topic_type == "troubleshooting":
        return "Is this a technical error you're trying to fix? If yes, what exact error text do you see?"
    if topic_type == "decision":
        return f"Are you deciding between options related to {t}? If yes, what constraints matter most (cost, time, risk)?"
    if topic_type == "skill":
        return f"Do you want to learn {t} (a skill), or understand {t} as a concept?"
    return f"Do you want a simple definition of {t}, or a deeper explanation with examples?"


def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in s).strip("_")


# ----------------------------
# ORIENT: intent-aware answers
# ----------------------------

def _orient_answer(topic: str, question: str = "", category: str = "") -> str:
    """
    ORIENT answers must match the user's intent:
    definition vs components vs benefits vs limitations vs history vs confusion, etc.
    """
    t = (topic or "").strip()
    tl = t.lower()
    q = (question or "").strip().lower()
    c = (category or "").strip().lower()

    era_note = get_era_note(t)

    ai_signals = [
        "artificial intelligence", "machine learning", "deep learning", "neural network",
        "transformer", "llm", "large language model", "generative ai", "genai",
        "agentic", "foundation model"
    ]
    is_ai = ("ai" == tl) or (" ai" in f" {tl} ") or any(sig in tl for sig in ai_signals)

    if is_ai:
        # Definition / plain meaning
        if ("what is" in q) or ("plain language" in q) or (c == "what"):
            parts = [
                "Artificial Intelligence (AI) is a machine-based way to achieve human-defined goals by making predictions, recommendations, or decisions from data.",
                "In everyday terms: AI is software that learns patterns from examples and uses them to understand, generate, or decide.",
                "AI is not consciousness or human-like understanding by default; it is limited by its data, objective, and design.",
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        # Key parts/components
        if ("key parts" in q) or ("components" in q):
            parts = [
                "At a high level, modern AI systems usually include:",
                "• Data (examples the system learns from)\n• A model (the pattern-learning engine)\n• An objective (what it is optimized to do)\n• Training/evaluation (how it learns + is tested)\n• Deployment + monitoring (how it’s used and kept reliable).",
                "AI is not just 'the model'—it’s the full pipeline from data to behavior.",
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        # Problem it exists to solve
        if ("what problem" in q) or ("exist to solve" in q):
            parts = [
                "AI exists to automate or augment tasks where writing explicit step-by-step rules is too hard, too slow, or too brittle.",
                "It’s most useful for pattern-heavy problems (language, images, forecasting, ranking, anomaly detection).",
                "AI is not the best tool when you need guaranteed correctness, strict rules, or fully transparent logic.",
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        # Benefits
        if ("benefits" in q):
            return "\n\n".join([
                "AI can improve speed, scale, and consistency in tasks like classification, search, summarization, personalization, and prediction.",
                "It can also unlock capabilities (translation, drafting, detection of subtle patterns) that are difficult to do manually at scale.",
                "AI is not guaranteed to be correct—benefits depend on data quality, evaluation, and guardrails.",
            ])

        # Limitations / downsides
        if ("limitations" in q) or ("downsides" in q):
            return "\n\n".join([
                "AI can be wrong in confident ways, inherit bias from data, and break when the real world changes (data drift).",
                "It can be hard to explain, hard to audit, and risky when connected to tools or sensitive data without safeguards.",
                "AI is not a substitute for responsibility—high-stakes use needs testing, monitoring, and human oversight.",
            ])

        # Why it matters
        if (c == "why") or ("why does" in q):
            return "\n\n".join([
                "AI matters because it shifts work from manual effort to automated pattern recognition and decision support—changing productivity across industries.",
                "It also changes what skills are valuable (evaluation, tool use, data literacy, governance).",
                "AI is not 'just another app'—it’s becoming a general-purpose capability embedded into many products.",
            ])

        # History/context
        if ("history" in q) or ("become necessary" in q):
            return "\n\n".join([
                "AI became practical as computing power, data availability, and machine learning techniques improved.",
                "Recent breakthroughs came from deep learning and transformer-based models, enabling large-scale language and multimodal systems.",
                "AI is not new—but the recent jump is the scale and generality of modern models.",
            ])

        # Confusion
        if ("confused" in q):
            return "\n\n".join([
                "People get confused because 'AI' is an umbrella term for many things: rules, machine learning, deep learning, generative AI, and agents.",
                "A simple clarity rule: ML learns from data; deep learning is ML with neural nets; generative AI produces new content; agentic AI can plan/act toward goals.",
                "AI is not one single technology—it’s a family of approaches.",
            ])

        # When to use/avoid
        if (c == "when") or ("when should" in q):
            return "\n\n".join([
                "Use AI when the task is pattern-based, you can test it, and errors are manageable or can be caught.",
                "Avoid AI when you need guaranteed correctness, strict interpretability, or when errors cause high harm (unless you add strong controls).",
                "AI is not a silver bullet—use it where it measurably improves outcomes.",
            ])

        # Learning/resources
        if (c == "how to") or ("first steps" in q) or ("resources" in q):
            return "\n\n".join([
                "A good starting path is: (1) understand what machine learning is, (2) learn how models are trained/evaluated, (3) build tiny projects with real data.",
                "Then explore modern areas like generative AI and agentic systems as extensions of fundamentals, not replacements.",
                "AI is not learned by theory alone—small builds + evaluation habits matter.",
            ])

        # Who created / experts
        if (c == "who") or ("who created" in q) or ("who are" in q):
            return "\n\n".join([
                "AI has no single creator; it emerged from many researchers across computer science, math, and cognitive science over decades.",
                "If you want, we can later add a curated 'key contributors' list as a separate knowledge layer (v1), because names change by subfield (ML, NLP, vision, agents).",
                "AI is not one person’s invention—it’s a field.",
            ])

        # Fallback for AI topic
        parts = [
            "AI is a machine-based way to achieve human-defined objectives using data-driven models.",
            "Modern AI learns patterns from data to predict, generate, or decide.",
            "AI is not human-like understanding by default; it has limits and needs evaluation.",
        ]
        if era_note:
            parts.append(era_note)
        return "\n\n".join(parts)

    # Generic ORIENT fallback
    parts = [
        f"{t} is a clearly defined idea, system, or practice people use to achieve a goal or solve a problem.",
        "To orient yourself fast: define it, identify its purpose, and understand its limits.",
        f"{t} is not a vague buzzword; it has boundaries and tradeoffs in real use.",
    ]
    if era_note:
        parts.append(era_note)
    return "\n\n".join(parts)



def _mechanism_answer(topic: str, question: str = "", category: str = "", topic_type: str = "") -> str:
    """
    MECHANISM answers = how it works (mental model + steps + optional under-the-hood).
    v0: still template-based, but intent-aware and topic-aware for AI family.
    """
    t = (topic or "").strip()
    tl = t.lower()
    q = (question or "").strip().lower()

    era_note = get_era_note(t)

    ai_signals = [
        "artificial intelligence", "ai", "machine learning", "ml", "deep learning",
        "neural network", "transformer", "llm", "large language model", "generative ai",
        "genai", "agentic", "foundation model"
    ]
    is_ai = any(sig in tl for sig in ai_signals) or tl in {"ai", "ml"}

    # --------------------
    # AI / ML mechanism
    # --------------------
    if is_ai:
        # intent: "high level"
        if "high level" in q or "works" in q:
            parts = [
                "At a high level, modern AI works by learning patterns from data instead of following only hand-written rules.",
                "The core loop is: collect data → train a model → evaluate it → deploy it → monitor and improve it over time.",
                "Under the hood, many systems use neural networks that adjust parameters to minimize errors on training examples."
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        # intent: beginner learning steps (belongs to LEARN sometimes, but your MECHANISM question includes it)
        if "beginners" in q or "first 3 steps" in q or "start learning" in q:
            parts = [
                "A practical way to start is to understand the mechanism in this order:",
                "1) Learn what training data is and what a model predicts (inputs → outputs).",
                "2) Learn the training loop (loss → optimization → evaluation).",
                "3) Build a tiny project and measure results (accuracy, errors, failure cases).",
            ]
            if era_note:
                parts.append(era_note)
            return "\n\n".join(parts)

        # intent: test understanding
        if "tell if" in q or "truly understand" in q:
            return "\n\n".join([
                "You truly understand AI at a mechanism level when you can explain:",
                "• what the inputs/outputs are\n• what data it learns from\n• what objective it optimizes\n• what can make it fail (bias, drift, weak data).",
                "A quick test: describe how you would evaluate it and what metrics would prove it works."
            ])

        # fallback AI mechanism
        parts = [
            "AI works by learning statistical patterns from examples (data) and using those patterns to make predictions, generate outputs, or choose actions.",
            "Most systems follow a pipeline: data → model → training → evaluation → deployment → monitoring."
        ]
        if era_note:
            parts.append(era_note)
        return "\n\n".join(parts)

    # --------------------
    # Generic mechanism fallback
    # --------------------
    parts = [
        f"{t} works by taking inputs, applying a process or set of steps, and producing outputs that achieve a goal.",
        "A useful way to understand the mechanism is: inputs → transformation steps → outputs → feedback/iteration.",
        f"If you share the context (learning vs using vs building), the mechanism explanation can be made more exact for {t}."
    ]
    if era_note:
        parts.append(era_note)
    return "\n\n".join(parts)



def _apply_answer(topic: str, question: str = "", category: str = "", topic_type: str = "") -> str:
    """
    APPLY answers = where it's used + concrete examples.
    v0: topic-aware for AI family; generic fallback for everything else.
    """
    t = (topic or "").strip()
    tl = t.lower()
    q = (question or "").strip().lower()

    ai_signals = [
        "artificial intelligence", "ai", "machine learning", "ml", "deep learning",
        "neural network", "transformer", "llm", "large language model", "generative ai",
        "genai", "agentic", "foundation model"
    ]
    is_ai = any(sig in tl for sig in ai_signals) or tl in {"ai", "ml"}

    # --------------------
    # AI / ML examples
    # --------------------
    if is_ai:
        # If the question is explicitly "simple example"
        if "simple example" in q or "a simple example" in q:
            return "\n\n".join([
                "Simple example: email spam detection.",
                "The system learns patterns from labeled emails (spam/not spam) and predicts whether a new email is spam.",
                "Why it’s AI: it learns from examples rather than relying only on hard-coded rules."
            ])

        # If the question is "real-world examples"
        if "real-world" in q or "in action" in q or "examples" in q:
            return "\n\n".join([
                "Real-world examples of AI:",
                "• Search & ranking (Google/YouTube deciding what to show first)",
                "• Recommendations (Netflix/Amazon suggesting items)",
                "• Fraud detection (banks flagging unusual transactions)",
                "• Customer support (chatbots + ticket triage)",
                "• Generative AI (drafting text, code, images)."
            ])

        # If the question is "where used"
        if "where is" in q or "used in real life" in q:
            return "\n\n".join([
                "AI shows up anywhere decisions or predictions are made from data at scale:",
                "• Consumer apps (recommendations, translation, camera features)",
                "• Business systems (forecasting, quality checks, routing/logistics)",
                "• Security (fraud, anomaly detection, phishing filters)",
                "• Creation tools (writing/code assistance, image generation)."
            ])

        # If the question is "where it fails"
        if "fail" in q or "break" in q:
            return "\n\n".join([
                "AI often fails in practice when:",
                "• The real-world data changes (data drift) and the model isn’t retrained",
                "• Training data is biased or incomplete",
                "• The task requires strict correctness (math, legal/medical) without guardrails",
                "• The system is used outside the conditions it was tested for."
            ])

        # Fallback AI apply
        return "\n\n".join([
            "AI is applied when you need predictions/decisions at scale from patterns in data.",
            "Examples include recommendations, search ranking, detection (fraud/spam), forecasting, and generative tools."
        ])

    # --------------------
    # Generic fallback examples (non-AI)
    # --------------------
    if "simple example" in q:
        return "\n\n".join([
            f"Simple example of {t}:",
            f"• One everyday situation where {t} shows up.",
            "If you tell me your context (school/work/personal), I can make it more precise."
        ])

    if "real-world" in q or "in action" in q or "examples" in q:
        return "\n\n".join([
            f"Real-world examples of {t}:",
            "• Example in everyday life",
            "• Example in work/school",
            "• Example in a product/tool people use"
        ])

    if "fail" in q or "break" in q:
        return "\n\n".join([
            f"{t} usually fails when:",
            "• assumptions don’t hold",
            "• people skip fundamentals",
            "• the environment changes",
            "• the method is applied outside its intended use"
        ])

    return "\n\n".join([
        f"{t} is used in real situations where it helps achieve a goal or solve a recurring problem.",
        "If you share your use-case, I can tailor the examples to your life (student/work/project)."
    ])





def build_answer(topic, topic_type, category, question, archetype):
    topic = topic.strip()

    era_note = get_era_note(topic)

    if archetype == "ORIENT":
        return _orient_answer(topic, question=question, category=category)
    
    if archetype == "MECHANISM":
        return _mechanism_answer(topic, question=question, category=category, topic_type=topic_type)


    if archetype == "APPLY":
        return _apply_answer(topic, question=question, category=category, topic_type=topic_type)
       

    if archetype == "LEARN":
        base = (
            f"To learn {topic}, start with the fundamentals and build gradually. "
            f"Focus first on core concepts, then practice applying them through small exercises "
            f"or projects. Consistent practice and real-world exposure matter more than speed."
        )
        if era_note:
            base += " " + era_note
        return base

    if archetype == "COMPARE":
        return (
            f"When comparing options related to {topic}, the key differences usually involve "
            f"purpose, complexity, cost, and suitability for a given situation. "
            f"The better choice depends on what problem you are trying to solve."
        )

    if archetype == "DECIDE":
        return (
            f"Whether you should pursue or choose {topic} depends on your goals, constraints, "
            f"and current situation. Consider factors such as time investment, expected benefits, "
            f"and how it aligns with your long-term plans."
        )

    if archetype == "RISK":
        return (
            f"Common mistakes with {topic} include misunderstanding its purpose, "
            f"overestimating what it can do, or skipping fundamentals. "
            f"Avoid rushing ahead without building a solid base."
        )

    if archetype == "NEXT":
        return (
            f"A good next step after understanding {topic} is to apply it in a small, "
            f"controlled way. This could mean experimenting, building something simple, "
            f"or deepening one specific area rather than trying to learn everything at once."
        )

    return f"This question relates to {topic}. Consider exploring it step by step for clarity."


def attach_answers(categories: dict, topic: str, topic_type: str) -> dict:
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
    clean_topic = extract_topic(topic)
    if not clean_topic:
        return {"topic": topic, "categories": {}, "notes": ["Empty topic received."]}

    topic_type, confidence = detect_topic_type(clean_topic)
    summary = build_summary(clean_topic, topic_type, confidence)
    needs_clarification = confidence < 0.5
    clarifying_question = clarification_for(clean_topic, topic_type) if needs_clarification else ""

    categories = build_categories(clean_topic, topic_type)
    categories = dedupe_questions(categories)
    categories = cap_categories(categories, max_per_category=5)

    notes = [
        "v0: template-based interrogation (no external knowledge yet).",
        "v0: archetype-aware answers + ordered understanding flow.",
    ]

    quick_examples = build_quick_examples(clean_topic, topic_type, confidence)

    qa_categories = attach_answers(categories, clean_topic, topic_type)

    # Order categories by archetype flow
    ordered_categories = {}
    seen = set()
    for arch in ARCHETYPE_ORDER:
        for cat, items in qa_categories.items():
            if items and items[0].get("archetype") == arch and cat not in seen:
                ordered_categories[cat] = items
                seen.add(cat)

    for cat, items in qa_categories.items():
        if cat not in seen:
            ordered_categories[cat] = items

    return {
        "topic": clean_topic,
        "topic_type": topic_type,
        "categories": ordered_categories,
        "notes": notes,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
        "clarifying_question": clarifying_question,
        "quick_examples": quick_examples,
        "summary": summary
    }

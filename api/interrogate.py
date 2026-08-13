# api/interrogate.py
import os
import json
import re
from typing import Dict, List, Tuple, Any, Optional

from api.context_mode import build_carm_answer_prompt, classify_context
from api.conversation_engine import build_conversation_prompt
from api.intent_layer import detect_intent


# ------------------------------------------------------------
# OPTIONAL LLM HOOKS (safe import)
# ------------------------------------------------------------
# LLM is used ONLY for AI / ML topics in v0.
# Other topics use templates.
# ------------------------------------------------------------
try:
    from api.llm_answers import llm_enabled as _llm_enabled
    from api.llm_answers import generate_dynamic_answer_result
except Exception:
    _llm_enabled = None
    generate_dynamic_answer_result = None


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
    r"^help me decide between\s+",
    r"^help me choose between\s+",
    r"^quiz me (?:on|about)\s+",
    r"^compare\s+",
    r"^give me (?:a )?(?:worked |real-world |real world )?examples? (?:of|about|for)\s+",
    r"^show me (?:a )?(?:worked |real-world |real world )?examples? (?:of|about|for)\s+",
    r"^can you\s+",
    r"^could you please\s+",
    r"^could you explain\s+",
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

    # Discourse markers belong to the conversation, not to the learning topic.
    # Remove them before applying command-prefix extraction so natural turns
    # such as "alright, explain spatial AI" resolve to "Spatial AI".
    text = re.sub(
        r"^(?:(?:all\s*right|alright|okay|ok|well|sure|great|cool)\b[\s,;:!.-]*)+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # Remove trailing punctuation
    text = re.sub(r"[?.!]+$", "", text).strip()

    lowered = text.lower()

    # Normalize natural, imperfectly worded local MCP requests into a clear
    # subject while preserving the user's actual setup intent.
    mentions_mcp = "mcp" in lowered or "model context protocol" in lowered
    mentions_local = any(
        cue in lowered
        for cue in ("local", "on my computer", "on the computer", "local system")
    )
    mentions_setup = any(
        cue in lowered
        for cue in ("add", "install", "set up", "setup", "configure", "run")
    )
    if mentions_mcp and mentions_local and mentions_setup:
        integration_match = re.search(
            r"\b(?:add|expose|use)\s+(.+?)\s+as\s+(?:a\s+)?(?:local\s+)?(?:mcp|model context protocol)\s+(?:server|bridge)\b",
            text,
            flags=re.IGNORECASE,
        )
        if integration_match:
            target = re.sub(r"\s+", " ", integration_match.group(1)).strip(" ,.;:?!")
            if target:
                return f"{target} and local MCP integration"
        return "Setting up an MCP server locally"

    # Strip chained command phrases. Natural requests often stack them (for
    # example, "can you explain AI"), so stopping after "can you" leaves
    # "Explain AI" masquerading as the topic. Limit the passes defensively.
    for _ in range(4):
        matched_prefix = False
        for pat in PREFIX_PATTERNS:
            if re.search(pat, lowered):
                text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
                lowered = text.lower()
                matched_prefix = True
                break
        if not matched_prefix:
            break

    # Handle common "about X"
    m = re.search(r"\babout\s+(.+)$", text, flags=re.IGNORECASE)
    if m and len(m.group(1).strip()) >= 2:
        text = m.group(1).strip()

    # Normalize simple cases
    if text.lower() in {
        "quant artificial intelligence",
        "quant ai",
    }:
        return "Quantitative Artificial Intelligence"
    if text.lower() == "ai":
        return "Artificial Intelligence"
    if text.lower() in ["ml", "machine learning"]:
        return "Machine Learning"
    if text.lower() == "mcp":
        return "Model Context Protocol (MCP)"

    if len(text) <= 4 and text.isalpha():
        return text.upper()

    return text[:1].upper() + text[1:]


# ------------------------------------------------------------
# Topic type detection
# ------------------------------------------------------------
def detect_topic_type(topic: str) -> Tuple[str, float]:
    t = (topic or "").strip().lower()
    if not t:
        return "unknown", 0.0

    if any(x in t for x in [" vs ", "versus", "compare", "comparison", "difference between"]):
        return "comparison", 0.67

    if any(x in t for x in ["how to", "learn", "study", "become", "start with", "roadmap"]):
        return "how_to", 0.67

    if any(x in t for x in ["should i", "choose", "buy or", "pick", "decide"]):
        return "decision", 0.67

    return "concept", 0.67


# ------------------------------------------------------------
# Archetypes + category ordering
# ------------------------------------------------------------

ARCHETYPE_MAP = {
    "Orientation": "ORIENT",
    "Foundations": "ORIENT",
    "Mechanisms": "MECHANISM",
    "Methods & Tools": "MECHANISM",
    "Applications": "APPLY",
    "Pitfalls": "RISK",
    "Advanced / Future": "NEXT",
}

CATEGORY_ORDER = [
    "Orientation",
    "Foundations",
    "Mechanisms",
    "Methods & Tools",
    "Applications",
    "Pitfalls",
    "Advanced / Future"
]

SECTION_MIN_COUNTS = {
    "Orientation": 5,
    "Foundations": 4,
    "Mechanisms": 4,
    "Methods & Tools": 4,
    "Applications": 3,
    "Pitfalls": 3,
    "Advanced / Future": 3,
}

MIN_TOTAL_QUESTIONS = 26
MAX_TOTAL_QUESTIONS = 32
MAIN_LLM_ATTEMPTS = 2


def _question_map_counts_ok(categories: Dict[str, List[Dict[str, Any]]]) -> bool:
    total = 0
    for cat in CATEGORY_ORDER:
        items = categories.get(cat, []) or []
        total += len(items)
        if len(items) < SECTION_MIN_COUNTS.get(cat, 0):
            return False
    return MIN_TOTAL_QUESTIONS <= total <= MAX_TOTAL_QUESTIONS


def _normalize_question_map_terminology(
    categories: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Repair internally contradictory stage labels before UI rendering."""
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    for category, items in (categories or {}).items():
        normalized_items: List[Dict[str, Any]] = []
        for item in items or []:
            clean_item = dict(item)
            question = str(clean_item.get("question") or "")
            question = re.sub(
                r"\bmeiotic\s+i\s+(vs\.?|and|versus|or)\s+meiotic\s+i\b",
                lambda match: f"meiotic I {match.group(1)} meiotic II",
                question,
                flags=re.IGNORECASE,
            )
            question = re.sub(
                r"\bmeiosis\s+i\s+(vs\.?|and|versus|or)\s+(?:meiosis\s+)?i\b",
                lambda match: f"meiosis I {match.group(1)} meiosis II",
                question,
                flags=re.IGNORECASE,
            )
            question = re.sub(
                r"\bmeiosis\s+i\s*\+\s*meiosis\s+i\b",
                "meiosis I + meiosis II",
                question,
                flags=re.IGNORECASE,
            )
            question = re.sub(
                r"\b(i\s+vs\.?\s+)i\b",
                lambda match: f"{match.group(1)}II",
                question,
                flags=re.IGNORECASE,
            )
            question = re.sub(
                r"\b(prophase|metaphase|anaphase|telophase)\s+i\s+(vs\.?|and|versus|or)\s+(?:\1\s+)?i\b",
                lambda match: f"{match.group(1)} I {match.group(2)} {match.group(1)} II",
                question,
                flags=re.IGNORECASE,
            )
            clean_item["question"] = question
            normalized_items.append(clean_item)
        normalized[category] = normalized_items
    return normalized


def _top_up_question_map(
    categories: Dict[str, List[Dict[str, Any]]],
    topic: str,
    topic_type: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Preserve LLM-generated questions, but top up missing/underfilled sections
    from template questions so we avoid falling back to a fully templated map.
    """
    template_bank = build_categories(topic, topic_type)

    topped: Dict[str, List[Dict[str, Any]]] = {}
    for cat in CATEGORY_ORDER:
        topped[cat] = list(categories.get(cat, []) or [])

    # Fill missing questions per section
    for cat in CATEGORY_ORDER:
        existing_items = topped.get(cat, [])
        existing_qs = {
            ((it.get("question") or "").strip().lower())
            for it in existing_items
            if isinstance(it, dict)
        }

        archetype = ARCHETYPE_MAP.get(cat, "ORIENT")
        next_idx = len(existing_items) + 1

        for tq in template_bank.get(cat, []):
            if len(existing_items) >= SECTION_MIN_COUNTS.get(cat, 0):
                break

            key = tq.strip().lower()
            if not key or key in existing_qs:
                continue

            existing_items.append(
                {
                    "id": f"{cat.lower().replace(' ', '_')}_{next_idx}",
                    "archetype": archetype,
                    "question": tq,
                    "answer": "",
                    "collapsed": True,
                    "visible": False,
                }
            )
            existing_qs.add(key)
            next_idx += 1

        topped[cat] = existing_items

    # Recompute top-8 visible flags cleanly
    global_count = 0
    for cat in CATEGORY_ORDER:
        new_items: List[Dict[str, Any]] = []
        for it in topped.get(cat, []):
            global_count += 1
            it = dict(it)
            it["visible"] = global_count <= 8
            new_items.append(it)
        topped[cat] = new_items

    return topped


def build_categories(topic: str, topic_type: str) -> Dict[str, List[str]]:
    """Deterministic template question bank (non-AI topics in v0)."""
    T = topic
    categories: Dict[str, List[str]] = {}

    categories["Orientation"] = [
        f"What is {T} in plain language?",
        f"What is {T} for?",
        f"What problems does {T} solve?",
        f"What benefits does {T} provide?",
        f"What are the main classifications or types within {T}?",
        f"Why does {T} exist?",
        f"Why does {T} matter?",
    ]

    categories["Foundations"] = [
        f"What core ideas support {T}?",
        f"What terminology do I need before understanding {T} well?",
        f"What assumptions or principles sit underneath {T}?",
        f"What background knowledge makes {T} easier to understand?",
    ]

    categories["Mechanisms"] = [
        f"How does {T} work internally?",
        f"What are the key components inside {T}?",
        f"What internal process makes {T} effective?",
        f"How do the main parts of {T} interact with each other?",
    ]

    categories["Methods & Tools"] = [
        f"What methods are commonly used to build or apply {T}?",
        f"What tools, frameworks, or technologies are associated with {T}?",
        f"What practical workflow do practitioners follow when working with {T}?",
        f"What techniques are most useful when using {T} in practice?",
    ]

    categories["Applications"] = [
        f"Where is {T} used in real life?",
        f"What are important real-world examples of {T}?",
        f"In which industries or workflows does {T} deliver value?",
    ]

    categories["Pitfalls"] = [
        f"What are common misconceptions about {T}?",
        f"What common challenges appear when learning or applying {T}?",
        f"Where does {T} usually fail or break in practice?",
    ]

    categories["Advanced / Future"] = [
        f"What advanced topics are closely related to {T}?",
        f"What future developments or open problems matter for {T}?",
        f"What frontier questions are researchers or practitioners still exploring in {T}?",
    ]

    return categories


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
# Template answers (fallback)
# IMPORTANT: DO NOT shorten answers; keep full explanations.
# ------------------------------------------------------------
def _unsupported_topic_result(
    topic: str,
    topic_type: str,
    confidence: float,
    intent: Dict[str, Any],
    response_intent: str,
) -> Dict[str, Any]:
    """Stop cleanly when no topic-specific Question Map can be produced."""
    return {
        "topic": topic,
        "topic_type": topic_type,
        "categories": {},
        "summary": [],
        "confidence": confidence,
        "notes": [
            "No sufficiently specific Question Map was produced; generic fallback suppressed."
        ],
        "llm_used": False,
        "needs_clarification": False,
        "intent": "unsupported_learning_topic",
        "response_intent": response_intent,
        "response_mode": "conversation",
        "context_intent": "unsupported_learning_topic",
        "mode_hint": intent.get("mode_hint", "focused"),
        "followups": [],
        "should_answer_direct": False,
        "suppress_profile": True,
        "reply": (
            f"I cannot yet build a reliable, topic-specific Question Map for {topic}. "
            "I am stopping here instead of filling the response with generic questions."
        ),
    }


def _orient_answer(topic: str, question: str, cat: str) -> str:
    ql = (question or "").lower()

    if "plain language" in ql or ql.startswith("what is"):
        return (
            f"{topic} in plain language:\n"
            f"- It’s a way of thinking about and solving problems using structured concepts and methods.\n"
            f"- The key is being able to define it clearly, give an example, and describe where it fails.\n"
        )

    if "problem" in ql:
        return (
            f"{topic} exists to solve problems where simple rules are not enough.\n"
            f"It helps by introducing a structured way to represent the problem and evaluate outcomes."
        )

    if "benefit" in ql:
        return (
            f"Benefits of {topic} typically include:\n"
            f"- clearer structure\n"
            f"- faster or more consistent decisions\n"
            f"- better communication of ideas\n"
        )

    if "limitation" in ql:
        return (
            f"Limitations of {topic} usually come from:\n"
            f"- unclear goals\n"
            f"- missing context\n"
            f"- incorrect assumptions\n"
            f"- misuse (using it where it doesn’t apply)\n"
        )

    if "confused" in ql:
        return (
            f"People get confused about {topic} when definitions are mixed with buzzwords.\n"
            f"A good test: can you explain it simply and give one real example + one failure case?"
        )

    return (
        f"{topic} becomes clear when you can explain it simply, give an example, and state when it fails."
    )


def _mechanism_answer(topic: str, question: str) -> str:
    return (
        f"Mechanism (high level) for {topic}:\n"
        f"- Identify inputs and desired outputs.\n"
        f"- Apply a method/process that transforms inputs into outputs.\n"
        f"- Evaluate performance with a clear metric.\n"
        f"- Iterate based on errors and edge cases.\n"
    )


def _apply_answer(topic: str, question: str) -> str:
    ql = (question or "").lower()
    if "fail" in ql or "break" in ql:
        return (
            f"{topic} commonly fails when the real-world context violates assumptions.\n"
            f"Watch for edge cases, drift, misuse, and unclear success criteria."
        )
    return (
        f"{topic} is used wherever decisions repeat at scale and outcomes can be measured."
    )


def _risk_answer(topic: str, question: str) -> str:
    ql = (question or "").lower()
    if "misconception" in ql:
        return (
            f"A common misconception about {topic} is thinking the label explains the mechanism.\n"
            f"Always ask: what inputs, what method, what metric, what failure modes?"
        )
    return (
        f"Pitfalls with {topic} include skipping fundamentals, using it outside its scope, and overtrusting outputs."
    )


def _next_answer(topic: str) -> str:
    return (
        f"Next step: apply {topic} in a small project with a clear goal and a measurable metric."
    )


# ------------------------------------------------------------
# LLM routing (AI / ML only)
# ------------------------------------------------------------
def _is_llm_topic(topic: str) -> bool:
    tl = re.sub(r"[^a-z0-9]+", " ", (topic or "").lower()).strip()

    AI_KEYWORDS = [
        # AI / ML / Data Science
        "ai",
        "agi",
        "artificial intelligence",
        "artificial general intelligence",
        "machine learning",
        "ml",
        "deep learning",
        "neural",
        "neural network",
        "transformer",
        "llm",
        "large language model",
        "gpt",
        "computer vision",
        "nlp",
        "natural language",
        "reinforcement learning",
        "supervised learning",
        "unsupervised learning",
        "data science",
        "data scientist",
        "model training",
        "model inference",
        "feature engineering",
        "dataset",
        "prediction",
        "classification",
        "regression",
        "bayesian statistics",
        "time series",
        "time series forecasting",
        "principal component analysis",
        "pca",
        "gradient descent",
        "xgboost",

        # Computer Science / Software
        "computer science",
        "software engineering",
        "programming",
        "coding",
        "algorithm",
        "data structure",
        "operating system",
        "database",
        "sql",
        "networking",
        "cybersecurity",
        "cloud computing",
        "docker",
        "kubernetes",
        "mcp",
        "mcp server",
        "model context protocol",
        "local mcp server",
        "quantum computing",
        "qis",
        "quantum information science",
        "quantum physics",

        # Cognitive Science / Language and the Brain
        "bcbl",
        "basque center on cognition brain and language",
        "basque centre on cognition brain and language",
        "cognitive science",
        "cognitive neuroscience",
        "psycholinguistics",
        "neurolinguistics",
        "language and the brain",
        "bilingualism",
        "multilingualism",
        "language acquisition",

        # Computer Architecture / Hardware
        "computer architecture",
        "computer hardware",
        "cpu",
        "processor",
        "core",
        "dual core",
        "quad core",
        "hexa core",
        "octa core",
        "thread",
        "cache",
        "memory",
        "ram",
        "gpu",
        "intel",
        "amd",
        "ryzen",
    ]

    short_tokens = {
        "ai", "agi", "ml", "nlp", "gpt", "sql", "cpu", "gpu", "amd",
        "ram", "pca", "bcbl", "qis",
    }

    for keyword in AI_KEYWORDS:
        if keyword in short_tokens:
            if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", tl):
                return True
            continue

        if keyword in tl:
            return True

    return False


def _extract_json_object(text: str) -> Optional[dict]:
    if not isinstance(text, str) or not text.strip():
        return None

    text = text.strip()

    fenced = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        text = fenced.group(1).strip()

    start = text.find("{")
    if start < 0:
        return None

    candidate = text[start:].strip()

    # Prefer clean full object if available
    end = candidate.rfind("}")
    if end > 0:
        full_candidate = candidate[:end + 1].strip()
        try:
            return json.loads(full_candidate)
        except Exception:
            candidate = full_candidate

    # Repair common LLM JSON issues
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

    # Balance braces/brackets
    open_curly = candidate.count("{")
    close_curly = candidate.count("}")
    open_square = candidate.count("[")
    close_square = candidate.count("]")

    if open_square > close_square:
        candidate += "]" * (open_square - close_square)

    if open_curly > close_curly:
        candidate += "}" * (open_curly - close_curly)

    try:
        return json.loads(candidate)
    except Exception:
        return None


def _llm_generate_questions_only(
    topic: str,
    topic_type: str,
    response_intent: str = "explore",
) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """
    One LLM call (AI/ML only):
    - Generates a brief summary
    - Generates categories with QUESTIONS ONLY
    - Answers are fetched later via /answer on click (Streamlit session cache)
    """
    instruction = f"""
You are InI.ai — the world's first Question Engine.

Your job is NOT to explain the topic first.
Your job is to generate the RIGHT QUESTIONS that guide a learner
from beginner understanding to advanced insight.

TOPIC: {topic}
LEARNER INTENT: {response_intent}

INTENT ADAPTATION

- explain: emphasize definitions, mental models, causes, and mechanisms
- compare: contrast alternatives using shared criteria, trade-offs, and boundaries
- teach: scaffold from foundations to independent application
- quiz: progressively test recall, reasoning, and application
- example: prioritize concrete scenarios, worked cases, and transfer
- decide: surface decision criteria, evidence, risks, and context-dependent choices
- explore: use the balanced learning progression below

QUESTION DESIGN PRINCIPLES

The seven categories must form ONE coherent investigation of the exact topic,
not seven independent lists. Preserve the learner's wording and intent throughout.

- Every question must name the topic or refer to it unambiguously.
- Do not repeat the same learning objective within or across categories.
- Each category must deepen what came before it; never reset to generic background.
- Orientation defines scope, purpose, significance, and neighboring concepts.
- Foundations covers only genuinely required conceptual or mathematical prerequisites.
- Mechanisms decomposes the exact process, causal chain, calculation, or equation.
- Methods & Tools covers implementation, comparison, measurement, testing, and debugging.
- Do not assume programming intent merely because the topic is technical. Include coding,
  APIs, software implementation, or developer workflows only when the learner's wording
  explicitly requests them; otherwise keep Methods & Tools appropriate to the subject.
- Applications transfers the mechanism into distinct contexts and decision points.
- Pitfalls diagnoses failure modes, symptoms, trade-offs, and misconceptions.
- Advanced / Future examines alternatives, unresolved limitations, and open questions.
- For a precise advanced query, several Mechanisms questions must directly break down
  that exact query instead of retreating to generic background.
- The final question of each category should naturally prepare the next category.
- Do not insert a calendar year unless the topic explicitly requires time-sensitive facts.

If the topic concerns MCP or a local MCP server, ensure the learning path covers:
- what Model Context Protocol (MCP) is and the difference between an MCP host,
  client, and server
- what "running an MCP server locally" can mean in practical terms
- prerequisites and choosing an existing server versus building one
- local process/stdio and remote HTTP transport choices
- registering the server in the chosen MCP host's configuration
- environment variables, file and tool permissions, testing, logs, and security
- platform-specific configuration details without inventing universal paths or commands

Questions must follow a LEARNING LADDER:

1. Orientation
   – What the topic is
   – What the topic is for
   – What problems it solves
   – What benefits it provides
   – What are the main classifications or types within the topic
   – Why it exists
   – Why it matters

2. Foundations
   – Core ideas
   – Full definitions of each of the subtypes of the topic
   – Basic structure
   – Key terminology

3. Mechanisms
   – How it works
   – Internal processes
   – Key components

4. Methods & Tools
   – Techniques used
   – Technologies involved
   – Practical workflows

5. Applications
   – Real-world uses
   – Industry applications
   – Where it delivers value

6. Pitfalls & Misconceptions
   – Common misunderstandings
   – Failure modes
   – Limitations

7. Advanced & Future
   – Cutting-edge developments
   – Research directions
   – Open problems

QUESTION RULES

• Generate between 26 and 30 questions total.
• Respect these section minimums:
  - Orientation: 5 questions
  - Foundations: 4 to 5 questions
  - Mechanisms: 4 to 5 questions
  - Methods & Tools: 4 to 5 questions
  - Applications: 3 to 4 questions
  - Pitfalls: 3 to 4 questions
  - Advanced / Future: 3 to 4 questions
• Questions must progress from basic → advanced.
• Avoid duplicates.
• Avoid vague or generic questions.
• Questions should reveal gaps in understanding.
• Do NOT generate more than 5 Orientation questions.

STRUCTURE

Return STRICT JSON only.

{{
  "summary": [
    "short sentence about the topic",
    "short sentence about why it matters",
    "short sentence about how understanding will progress"
  ],

    "categories": {{
    "Orientation": [{{"question": "..."}}],
    "Foundations": [{{"question": "..."}}],
    "Mechanisms": [{{"question": "..."}}],
    "Methods & Tools": [{{"question": "..."}}],
    "Applications": [{{"question": "..."}}],
    "Pitfalls": [{{"question": "..."}}],
    "Advanced / Future": [{{"question": "..."}}]
  }}
}}

IMPORTANT

• You MUST return EXACTLY these category keys and no others:
  - Orientation
  - Foundations
  - Mechanisms
  - Methods & Tools
  - Applications
  - Pitfalls
  - Advanced / Future

• Do NOT rename categories.
• Do NOT add extra categories.
• Do NOT omit categories.
• Every category must contain questions.
• You must satisfy the section minimums listed above.
• The JSON schema must match exactly.

• First question in "Orientation" MUST clearly define the topic.
• Questions must feel technically relevant without inserting stale calendar years.
• Focus on learning progression.

Generate the questions now.
""".strip()

    res = generate_dynamic_answer_result(
    topic=topic,
    topic_type=topic_type,
    archetype="ORIENT",
    question=instruction,
    meta={"mode": "interrogate_questions_only", "expects": "json"},
)

    raw = (res.get("answer") or "").strip()

    data = _extract_json_object(raw or "")

    # 🔥 Attempt 2: clean and extract JSON substring manually
    if not isinstance(data, dict):
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                candidate = raw[start:end+1]
                data = json.loads(candidate)
            else:
                data = None
        except Exception:
            data = None

    # 🔥 FINAL fallback
    if not isinstance(data, dict):
        if os.getenv("INI_LLM_DEBUG", "0").lower() in ("1", "true", "yes"):
            return (
                ["DEBUG: LLM returned non-JSON. See categories.debug_raw."],
                {
                    "debug_raw": [
                        {
                            "id": "debug_raw_1",
                            "archetype": "DEBUG",
                            "question": "RAW_LLM_OUTPUT",
                            "answer": (raw or "")[:4000],
                            "collapsed": False,
                            "visible": True,
                        }
                    ]
                },
            )

        print("LLM RAW OUTPUT (FAILED PARSE):", (raw or "")[:1000])
        return (build_summary(topic, topic_type, 0.67), {})



    summary = data.get("summary") if isinstance(data.get("summary"), list) else []
    cats = _normalize_category_keys(
        data.get("categories") if isinstance(data.get("categories"), dict) else {}
    )

    cats = {key: cats.get(key, []) for key in CATEGORY_ORDER}

    categories_out: Dict[str, List[Dict[str, Any]]] = {}
    global_count = 0

    for cat in CATEGORY_ORDER:
        items = cats.get(cat, [])
        if not isinstance(items, list):
            items = []

        archetype = ARCHETYPE_MAP.get(cat, "ORIENT")
        out_items: List[Dict[str, Any]] = []

        for idx, it in enumerate(items, start=1):
            if not isinstance(it, dict):
                continue

            q = (it.get("question") or "").strip()
            if not q:
                continue

            global_count += 1
            out_items.append(
                {
                    "id": f"{cat.lower().replace(' ', '_')}_{idx}",
                    "archetype": archetype,
                    "question": q,
                    "answer": "",
                    "collapsed": True,
                    "visible": global_count <= 8,
                }
            )

        categories_out[cat] = out_items

    if not any(categories_out.get(c) for c in categories_out):
        return (build_summary(topic, topic_type, 0.67), {})

    return (summary, categories_out)


def _normalize_category_keys(cats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept small variations from the LLM and map them to the
    canonical CATEGORY_ORDER keys.
    """
    if not isinstance(cats, dict):
        return {}

    mapping = {
        "orientation": "Orientation",
        "foundations": "Foundations",
        "mechanisms": "Mechanisms",
        "methods and tools": "Methods & Tools",
        "methods & tools": "Methods & Tools",
        "methods/tools": "Methods & Tools",
        "applications": "Applications",
        "pitfalls": "Pitfalls",
        "pitfalls & misconceptions": "Pitfalls",
        "advanced": "Advanced / Future",
        "advanced & future": "Advanced / Future",
        "advanced/future": "Advanced / Future",
        "advanced / future": "Advanced / Future",
    }

    out = {k: [] for k in CATEGORY_ORDER}

    for key, val in cats.items():
        k = (key or "").strip().lower()
        mapped = mapping.get(k)
        if mapped:
            out[mapped] = val

    return out


def _llm_generate_questions_only_rescue(
    topic: str,
    topic_type: str,
    response_intent: str = "explore",
) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """
    Smaller rescue pass for AI/ML topics when the main JSON question-map fails.
    Keeps LLM-generated questions, but with a lighter prompt.
    """
    instruction = f"""
Return STRICT JSON only.

Topic: {topic}
Learner intent: {response_intent}

Adapt the questions to that intent: explain mechanisms, compare shared criteria,
teach progressively, quiz understanding, illustrate with cases, or support a decision.

Use EXACTLY these category keys:
- Orientation
- Foundations
- Mechanisms
- Methods & Tools
- Applications
- Pitfalls
- Advanced / Future

Rules:
- No prose outside JSON
- No markdown
- No code fences
- Generate between 26 and 30 questions total
- Respect these section minimums:
  - Orientation: 5 questions
  - Foundations: 4 to 5 questions
  - Mechanisms: 4 to 5 questions
  - Methods & Tools: 4 to 5 questions
  - Applications: 3 to 4 questions
  - Pitfalls: 3 to 4 questions
  - Advanced / Future: 3 to 4 questions
- Questions must be specific and technically relevant
- Treat the categories as one progressive investigation of the exact topic, not
  seven independent lists
- Every question must name the topic or refer to it unambiguously
- Do not repeat a learning objective within or across categories
- Orientation defines scope, purpose, neighboring concepts, and significance
- Foundations covers only genuinely required conceptual or mathematical prerequisites
- Mechanisms decomposes the exact process, causal chain, calculation, or equation
- Methods & Tools covers implementation, comparison, measurement, testing, and debugging
- Do not assume programming intent merely because the topic is technical. Include coding,
  APIs, software implementation, or developer workflows only when the learner's wording
  explicitly requests them; otherwise keep Methods & Tools appropriate to the subject
- Applications transfers the mechanism into distinct contexts and decision points
- Pitfalls diagnoses failure modes, symptoms, trade-offs, and misconceptions
- Advanced / Future examines alternatives, unresolved limitations, and open questions
- For a precise advanced query, several Mechanisms questions must directly break down
  that exact query instead of retreating to generic background
- The final question of each category should naturally prepare the next category
- Do not insert a calendar year unless the topic explicitly requires time-sensitive facts
- First question in "Orientation" must define the topic clearly
- Do not leave any category empty
- Do NOT generate more than 5 Orientation questions.

JSON shape:
{{
  "summary": [
    "short sentence about the topic",
    "short sentence about why it matters",
    "short sentence about how understanding will progress"
  ],
  "categories": {{
    "Orientation": [{{"question": "..."}}],
    "Foundations": [{{"question": "..."}}],
    "Mechanisms": [{{"question": "..."}}],
    "Methods & Tools": [{{"question": "..."}}],
    "Applications": [{{"question": "..."}}],
    "Pitfalls": [{{"question": "..."}}],
    "Advanced / Future": [{{"question": "..."}}]
  }}
}}
""".strip()

    res = generate_dynamic_answer_result(
    topic=topic,
    topic_type=topic_type,
    archetype="ORIENT",
    question=instruction,
    meta={"mode": "interrogate_questions_rescue", "expects": "json"},
)

    raw = (res.get("answer") or "").strip()

    data = _extract_json_object(raw or "")
    if not isinstance(data, dict):
        return (build_summary(topic, topic_type, 0.67), {})

    summary = data.get("summary") if isinstance(data.get("summary"), list) else []
    cats = _normalize_category_keys(
        data.get("categories") if isinstance(data.get("categories"), dict) else {}
    )
    cats = {key: cats.get(key, []) for key in CATEGORY_ORDER}

    categories_out: Dict[str, List[Dict[str, Any]]] = {}
    global_count = 0

    for cat in CATEGORY_ORDER:
        items = cats.get(cat, [])
        if not isinstance(items, list):
            items = []

        archetype = ARCHETYPE_MAP.get(cat, "ORIENT")
        out_items: List[Dict[str, Any]] = []

        for idx, it in enumerate(items, start=1):
            if not isinstance(it, dict):
                continue

            q = (it.get("question") or "").strip()
            if not q:
                continue

            global_count += 1
            out_items.append(
                {
                    "id": f"{cat.lower().replace(' ', '_')}_{idx}",
                    "archetype": archetype,
                    "question": q,
                    "answer": "",
                    "collapsed": True,
                    "visible": global_count <= 8,
                }
            )

        categories_out[cat] = out_items

    if not any(categories_out.get(c) for c in categories_out):
        return (build_summary(topic, topic_type, 0.67), {})

    return (summary, categories_out)


def attach_answers(categories: Dict[str, List[str]], topic: str, topic_type: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Non-AI topics: template questions + template answers.
    IMPORTANT: answers must NOT equal the question.
    """
    out: Dict[str, List[Dict[str, Any]]] = {}

    for cat in CATEGORY_ORDER:
        questions = categories.get(cat, [])
        items: List[Dict[str, Any]] = []
        archetype = ARCHETYPE_MAP.get(cat, "ORIENT")

        for idx, q in enumerate(questions, start=1):
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
                    "collapsed": True,
                    "visible": False,
                }
            )

        out[cat] = items

    return out


# ------------------------------------------------------------
# Main entry
# ------------------------------------------------------------
def interrogate(text: str) -> Dict[str, Any]:
    intent = detect_intent(text)
    response_intent = str(intent.get("response_intent") or "explore")

    if intent.get("intent") == "empty":
        return {
            "topic": "",
            "topic_type": "unknown",
            "categories": {},
            "notes": ["Empty topic received."],
            "summary": [],
            "confidence": 0.0,
            "needs_clarification": True,
            "clarifying_question": "Please provide a topic to explore.",
            "reply": intent.get("reply", ""),
            "followups": intent.get("followups", []),
            "llm_used": False,
            "intent": intent.get("intent", "empty"),
            "mode_hint": intent.get("mode_hint", "deep"),
        }

    # "Quan AI" is genuinely ambiguous: it can be a clipped/typo form of
    # either quantitative AI or quantum AI. Do not let the model silently
    # choose a domain and build an authoritative-looking response around it.
    normalized_query = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        (text or "").lower(),
    )
    normalized_query = re.sub(r"\s+", " ", normalized_query).strip()
    ambiguous_subject = re.sub(
        r"^(?:what is|what s|explain|define|tell me about)\s+",
        "",
        normalized_query,
    ).strip()
    if ambiguous_subject in {"quan ai", "quan artificial intelligence"}:
        return {
            "topic": "",
            "topic_type": "ambiguous_learning_topic",
            "categories": {},
            "notes": ["Clarification required between two plausible AI topics."],
            "summary": [],
            "confidence": 0.99,
            "needs_clarification": True,
            "clarifying_question": (
                "Did you mean Quantitative Artificial Intelligence or "
                "Quantum Artificial Intelligence?"
            ),
            "reply": (
                "Did you mean Quantitative Artificial Intelligence or "
                "Quantum Artificial Intelligence?"
            ),
            "followups": [
                "Quantitative Artificial Intelligence",
                "Quantum Artificial Intelligence",
            ],
            "llm_used": False,
            "intent": "clarify_topic_ambiguity",
            "response_mode": "conversation",
            "context_intent": "ambiguous_learning_topic",
            "clarification_title": "Choose the topic",
            "mode_hint": "focused",
            "should_answer_direct": False,
            "suppress_profile": True,
        }

    context = classify_context(text)
    if context.get("response_mode") == "carm":
        context_intent = context.get("context_intent", "practical")

        if context.get("clarification_required"):
            return {
                "topic": extract_topic(text),
                "topic_type": context_intent,
                "categories": {},
                "notes": ["CARM requested one material clarification before answering."],
                "summary": [],
                "confidence": 0.94,
                "needs_clarification": True,
                "clarifying_question": context.get("clarification_question", ""),
                "reply": context.get("clarification_question", ""),
                "followups": context.get("clarification_options", []),
                "llm_used": False,
                "intent": "clarify",
                "response_mode": "carm",
                "context_intent": context_intent,
                "mode_hint": "focused",
                "should_answer_direct": False,
            }

        return {
            "topic": extract_topic(text),
            "topic_type": context_intent,
            "categories": {},
            "notes": ["CARM selected an immediate-answer response."],
            "summary": [],
            "confidence": 0.92,
            "needs_clarification": False,
            "clarifying_question": "",
            "reply": "",
            "followups": [],
            "llm_used": False,
            "intent": "practical_request",
            "response_mode": "carm",
            "context_intent": context_intent,
            "direct_answer_prompt": build_carm_answer_prompt(text, context_intent),
            "mode_hint": "focused",
            "should_answer_direct": True,
        }

    # ------------------------------------------------------------
    # SAFER routing:
    # valid educational questions should still interrogate
    # ------------------------------------------------------------

    raw_text_lower = (text or "").strip().lower()

    EDUCATIONAL_SIGNALS = [
        "what",
        "why",
        "how",
        "difference",
        "compare",
        "explain",
        "define",
        "benefit",
        "problem",
        "classification",
        "types",
        "future",
        "applications",
        "limitations",
    ]

    looks_educational = (
        len(raw_text_lower) > 8
        and any(sig in raw_text_lower for sig in EDUCATIONAL_SIGNALS)
    )

    # Explicit conversational and direct-answer intents must win over the
    # educational-signal fallback. Otherwise words such as "how" in a natural
    # greeting can incorrectly create a Question Map.
    intent_name = str(intent.get("intent") or "").strip().lower()
    intent_is_explicitly_handled = intent_name not in {"", "clarify", "topic_explore"}

    if not intent.get("should_interrogate", False) and (
        intent_is_explicitly_handled or not looks_educational
    ):
        conversational_intents = {
            "greeting", "thanks", "farewell", "help", "affirmation",
            "negative", "smalltalk", "self_introduction", "clarify",
        }
        use_conversation_engine = intent_name in conversational_intents

        return {
            "topic": "",
            "topic_type": intent.get("intent", "conversation"),
            "categories": {},
            "notes": ["Intent layer handled without question map."],
            "summary": [],
            "confidence": float(intent.get("confidence", 0.8)),
            "needs_clarification": False,
            "clarifying_question": "",
            "reply": "" if use_conversation_engine else intent.get("reply", ""),
            "followups": [] if use_conversation_engine else intent.get("followups", []),
            "llm_used": False,
            "intent": intent.get("intent", "conversation"),
            "mode_hint": intent.get("mode_hint", "deep"),
            "should_answer_direct": (
                True if use_conversation_engine
                else bool(intent.get("should_answer_direct", False))
            ),
            "response_mode": "conversation" if use_conversation_engine else "standard",
            "suppress_profile": bool(use_conversation_engine),
            "direct_answer_prompt": (
                build_conversation_prompt(text, intent_name)
                if use_conversation_engine else ""
            ),
        }

    clean_topic = extract_topic(text)

    print("RAW TOPIC:", text)
    print("EXTRACTED TOPIC:", clean_topic)

    if not clean_topic:
        return {
            "topic": "",
            "topic_type": "unknown",
            "categories": {},
            "notes": ["Empty topic received after extraction."],
            "summary": [],
            "confidence": 0.0,
            "needs_clarification": True,
            "clarifying_question": "Please provide a topic to explore.",
            "reply": "",
            "followups": [],
            "llm_used": False,
            "intent": "empty",
            "mode_hint": intent.get("mode_hint", "deep"),
        }

    topic_type, confidence = detect_topic_type(clean_topic)
    intent_topic_types = {
        "compare": "comparison",
        "decide": "decision",
        "teach": "how_to",
    }
    topic_type = intent_topic_types.get(response_intent, topic_type)

    # Every supported learning topic must earn a topic-specific LLM map.
    # Generic template maps are intentionally forbidden.
    use_llm = (
        _llm_is_enabled()
        and (generate_dynamic_answer_result is not None)
    )

    if use_llm:
        summary, llm_categories = [], {}

        # STEP 1: Use full LLM generation FIRST (stronger output)
        print("USING FULL QUESTION GENERATOR")

        for _ in range(MAIN_LLM_ATTEMPTS):
            summary, llm_categories = _llm_generate_questions_only(
                clean_topic,
                topic_type,
                response_intent,
            )

            if _question_map_counts_ok(llm_categories):
                print("FULL QUESTION GENERATOR SUCCESS")
                break
            else:
                print("FULL QUESTION GENERATOR FAILED")
                llm_categories = {}

        # STEP 2: If full LLM fails → fallback to lighter rescue prompt
        if not (llm_categories and any(llm_categories.get(c) for c in llm_categories)):
            print("USING RESCUE QUESTION GENERATOR")

            summary, llm_categories = _llm_generate_questions_only_rescue(
                clean_topic,
                topic_type,
                response_intent,
            )

        # STEP 3: If we got a VALID full map → proceed normally
        if _question_map_counts_ok(llm_categories):

            validated_summary = (
                    summary
                    if isinstance(summary, list) and len(summary) >= 3
                    else build_summary(clean_topic, topic_type, confidence)
                )
            
            # Only top-up if an entire category is missing
            missing_category = any(
                len(llm_categories.get(cat, [])) == 0
                for cat in CATEGORY_ORDER
            )

            if missing_category:
                repair_summary, repair_categories = _llm_generate_questions_only_rescue(
                    clean_topic,
                    topic_type,
                    response_intent,
                )

                for cat in CATEGORY_ORDER:
                    if len(llm_categories.get(cat, [])) == 0 and repair_categories.get(cat):
                        llm_categories[cat] = repair_categories[cat]

            return {
                "topic": clean_topic,
                "topic_type": topic_type,
                "categories": _normalize_question_map_terminology(llm_categories),
                "summary": validated_summary,                
                "confidence": confidence,
                "notes": [
                    "v0: interrogation engine",
                    "v0: AI uses LLM for questions",
                    "v0: answers fetched on click via /answer (LLM)",
                    "v0: UI reveals answers on click (progressive disclosure)",
                    "v0: validated full LLM question-map",
                ],
                "llm_used": True,
                "intent": intent.get("intent", "topic_explore"),
                "response_intent": response_intent,
                "mode_hint": intent.get("mode_hint", "deep"),
                "followups": intent.get("followups", []),
                "reply": "",
            }

        # STEP 4: FINAL fallback → template only
        return _unsupported_topic_result(
            clean_topic, topic_type, confidence, intent, response_intent
        )

    return _unsupported_topic_result(
        clean_topic, topic_type, confidence, intent, response_intent
    )


__all__ = ["interrogate", "extract_topic", "detect_topic_type"]

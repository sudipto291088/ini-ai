# api/interrogate.py
import os
import json
import re
from typing import Dict, List, Tuple, Any, Optional

from api.intent_layer import detect_intent


# ------------------------------------------------------------
# OPTIONAL LLM HOOKS (safe import)
# ------------------------------------------------------------
# LLM is used ONLY for AI / ML topics in v0.
# Other topics use templates.
# ------------------------------------------------------------
try:
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

    # Normalize simple cases
    if text.lower() == "ai":
        return "Artificial Intelligence"
    if text.lower() in ["ml", "machine learning"]:
        return "Machine Learning"

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
    "Orientation": 7,
    "Foundations": 4,
    "Mechanisms": 4,
    "Methods & Tools": 4,
    "Applications": 3,
    "Pitfalls": 3,
    "Advanced / Future": 3,
}

MIN_TOTAL_QUESTIONS = 28
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
    tl = (topic or "").lower()

    AI_KEYWORDS = [
        "ai",
        "artificial intelligence",
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
    ]

    return any(k in tl for k in AI_KEYWORDS)


def _extract_json_object(text: str) -> Optional[dict]:
    """
    Pull a JSON object from an LLM response.
    Handles ```json fences and extra text.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start:end + 1].strip()
        try:
            return json.loads(candidate)
        except Exception:
            return None

    return None


def _llm_generate_questions_only(topic: str, topic_type: str) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
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

QUESTION DESIGN PRINCIPLES

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

• Generate between 28 and 32 questions total.
• Respect these section minimums:
  - Orientation: 7 to 9 questions
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
• Do NOT collapse Orientation into fewer than 7 questions.

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
• Questions must feel modern and relevant (2024–2025 context).
• Focus on learning progression.

Generate the questions now.
""".strip()

    raw = llm_answer_question(
        topic=topic,
        topic_type=topic_type,
        archetype="ORIENT",
        question=instruction,
        meta={"mode": "interrogate_questions_only", "expects": "json"},
    )

    data = _extract_json_object(raw or "")

    # 🔥 NEW: second attempt to parse raw JSON directly
    if not isinstance(data, dict):
        try:
            data = json.loads(raw.strip())
        except Exception:
            data = None

    # 🔥 FINAL fallback (with debug support)
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

        # 🔥 also print raw output for visibility (important)
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


def _llm_generate_questions_only_rescue(topic: str, topic_type: str) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """
    Smaller rescue pass for AI/ML topics when the main JSON question-map fails.
    Keeps LLM-generated questions, but with a lighter prompt.
    """
    instruction = f"""
Return STRICT JSON only.

Topic: {topic}

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
- Generate between 28 and 32 questions total
- Respect these section minimums:
  - Orientation: 7 to 9 questions
  - Foundations: 4 to 5 questions
  - Mechanisms: 4 to 5 questions
  - Methods & Tools: 4 to 5 questions
  - Applications: 3 to 4 questions
  - Pitfalls: 3 to 4 questions
  - Advanced / Future: 3 to 4 questions
- Questions must be specific and modern
- First question in "Orientation" must define the topic clearly
- Do not leave any category empty

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

    raw = llm_answer_question(
        topic=topic,
        topic_type=topic_type,
        archetype="ORIENT",
        question=instruction,
        meta={"mode": "interrogate_questions_rescue", "expects": "json"},
    )

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

    if not intent.get("should_interrogate", False):
        return {
            "topic": "",
            "topic_type": intent.get("intent", "conversation"),
            "categories": {},
            "notes": ["Intent layer handled without question map."],
            "summary": [],
            "confidence": float(intent.get("confidence", 0.8)),
            "needs_clarification": False,
            "clarifying_question": "",
            "reply": intent.get("reply", ""),
            "followups": intent.get("followups", []),
            "llm_used": False,
            "intent": intent.get("intent", "conversation"),
            "mode_hint": intent.get("mode_hint", "deep"),
            "should_answer_direct": bool(intent.get("should_answer_direct", False)),
        }

    clean_topic = extract_topic(text)

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

    # AI topic: LLM questions-only (answers on click via /answer)
    use_llm = _llm_is_enabled() and _is_llm_topic(clean_topic) and (llm_answer_question is not None)

    if use_llm:
        summary, llm_categories = [], {}

        # STEP 1: Use full LLM generation FIRST (stronger output)
        for _ in range(MAIN_LLM_ATTEMPTS):
            summary, llm_categories = _llm_generate_questions_only(clean_topic, topic_type)
            if llm_categories and any(llm_categories.get(c) for c in llm_categories):
                break

        # STEP 2: If full LLM fails → fallback to lighter rescue prompt
        if not (llm_categories and any(llm_categories.get(c) for c in llm_categories)):
            summary, llm_categories = _llm_generate_questions_only_rescue(clean_topic, topic_type)

        # STEP 3: If we got valid categories → proceed normally
        if llm_categories and any(llm_categories.get(c) for c in llm_categories):
            llm_categories = _top_up_question_map(llm_categories, clean_topic, topic_type)

            return {
                "topic": clean_topic,
                "topic_type": topic_type,
                "categories": llm_categories,
                "summary": summary or build_summary(clean_topic, topic_type, confidence),
                "confidence": confidence,
                "notes": [
                    "v0: interrogation engine",
                    "v0: AI uses LLM for questions",
                    "v0: answers fetched on click via /answer (LLM)",
                    "v0: UI reveals answers on click (progressive disclosure)",
                    "v0: underfilled sections are topped up from templates when needed",
                ],
                "llm_used": True,
                "intent": intent.get("intent", "topic_explore"),
                "mode_hint": intent.get("mode_hint", "deep"),
                "followups": intent.get("followups", []),
                "reply": "",
            }

        # STEP 4: FINAL fallback → template only
        fallback_categories = build_categories(clean_topic, topic_type)
        fallback_qa = attach_answers(fallback_categories, clean_topic, topic_type)

        return {
            "topic": clean_topic,
            "topic_type": topic_type,
            "categories": fallback_qa,
            "summary": build_summary(clean_topic, topic_type, confidence),
            "confidence": confidence,
            "notes": [
                "v0: interrogation engine",
                "v0: AI LLM question-map failed after retries; template fallback used",
            ],
            "llm_used": False,
            "needs_clarification": False,
            "intent": intent.get("intent", "topic_explore"),
            "mode_hint": intent.get("mode_hint", "deep"),
            "followups": intent.get("followups", []),
            "reply": "",
        }

    # Non-AI topics: templates
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
            "v0: templates for non-AI topics",
        ],
        "llm_used": False,
        "intent": intent.get("intent", "topic_explore"),
        "mode_hint": intent.get("mode_hint", "deep"),
        "followups": intent.get("followups", []),
        "reply": "",
    }


__all__ = ["interrogate", "extract_topic", "detect_topic_type"]
# api/interrogate.py
import os
import json
import re
from typing import Dict, List, Tuple, Any, Optional


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
    "What": "ORIENT",
    "Why": "ORIENT",

    # RISK immediately after ORIENT
    "Misconceptions": "RISK",
    "Common Challenges": "RISK",

    "How": "MECHANISM",
    "Where": "APPLY",
    "Examples": "APPLY",
    "Related Topics": "NEXT",
}

CATEGORY_ORDER = [
    "What",
    "Why",
    "Misconceptions",
    "Common Challenges",
    "How",
    "Where",
    "Examples",
    "Related Topics",
]


def build_categories(topic: str, topic_type: str) -> Dict[str, List[str]]:
    """Deterministic template question bank (non-AI topics in v0)."""
    T = topic
    categories: Dict[str, List[str]] = {}

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

    categories["Misconceptions"] = [
        f"What is a common misconception about {T}?",
    ]

    categories["Common Challenges"] = [
        f"What pitfalls should I avoid when learning or using {T}?",
    ]

    categories["How"] = [
        f"How does {T} work at a high level?",
        f"How can I tell if I truly understand {T}?",
    ]

    categories["Where"] = [
        f"Where is {T} used in real life?",
        f"Where does {T} usually fail or break in practice?",
    ]

    categories["Examples"] = [
        f"What is a simple example of {T}?",
        f"What are real-world examples of {T}?",
    ]

    categories["Related Topics"] = [
        f"What topics are closely related to {T}?",
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
    return any(x in tl for x in ["artificial intelligence", "ai", "machine learning", "ml"])


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
   – Why it exists
   – Why it matters

2. Foundations
   – Core ideas
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

• Generate between 22 and 28 questions total.
• Questions must progress from basic → advanced.
• Avoid duplicates.
• Avoid vague or generic questions.
• Questions should reveal gaps in understanding.

STRUCTURE

Return STRICT JSON only.

{{
  "summary": [
    "short sentence about the topic",
    "short sentence about why it matters",
    "short sentence about how understanding will progress"
  ],

  "categories": {{
    "What": [{{"question": "..."}}],
    "Why": [{{"question": "..."}}],
    "Misconceptions": [{{"question": "..."}}],
    "Common Challenges": [{{"question": "..."}}],
    "How": [{{"question": "..."}}],
    "Where": [{{"question": "..."}}],
    "Examples": [{{"question": "..."}}],
    "Related Topics": [{{"question": "..."}}]
  }}
}}

IMPORTANT

• You MUST return EXACTLY these category keys and no others:
  - What
  - Why
  - Misconceptions
  - Common Challenges
  - How
  - Where
  - Examples
  - Related Topics

• Do NOT rename categories.
• Do NOT add extra categories.
• Do NOT omit categories. If a category has fewer questions, return an empty list.
• The JSON schema must match exactly.

• First question in "What" MUST clearly define the topic.
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

    # === CHANGE: expose raw LLM output when debug is enabled ===
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
        return (build_summary(topic, topic_type, 0.67), {})

    summary = data.get("summary") if isinstance(data.get("summary"), list) else []
    cats = data.get("categories") if isinstance(data.get("categories"), dict) else {}
    
    # Force exact category schema so UI always stays stable
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
                    "answer": "",          # answers fetched later via /answer on click
                    "collapsed": True,
                    "visible": global_count <= 8,
                }
            )

        categories_out[cat] = out_items

    if not any(categories_out.get(c) for c in categories_out):
        return (build_summary(topic, topic_type, 0.67), {})

    return (summary, categories_out)


def _llm_generate_questions_only_rescue(topic: str, topic_type: str) -> Tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """
    Smaller rescue pass for AI/ML topics when the main JSON question-map fails.
    Keeps LLM-generated questions, but with a lighter prompt.
    """
    instruction = f"""
Return STRICT JSON only.

Topic: {topic}

Use EXACTLY these category keys:
- What
- Why
- Misconceptions
- Common Challenges
- How
- Where
- Examples
- Related Topics

Rules:
- No prose outside JSON
- No markdown
- No code fences
- 2 to 4 questions per category
- Questions must be specific and modern
- First question in "What" must define the topic clearly

JSON shape:
{{
  "summary": [
    "short sentence about the topic",
    "short sentence about why it matters",
    "short sentence about how understanding will progress"
  ],
  "categories": {{
    "What": [{{"question": "..."}}],
    "Why": [{{"question": "..."}}],
    "Misconceptions": [{{"question": "..."}}],
    "Common Challenges": [{{"question": "..."}}],
    "How": [{{"question": "..."}}],
    "Where": [{{"question": "..."}}],
    "Examples": [{{"question": "..."}}],
    "Related Topics": [{{"question": "..."}}]
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
    cats = data.get("categories") if isinstance(data.get("categories"), dict) else {}
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
                    "visible": False,  # Streamlit controls top-8 view globally
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

    # AI topic: LLM questions-only (answers on click via /answer)
    use_llm = _llm_is_enabled() and _is_llm_topic(clean_topic) and (llm_answer_question is not None)

    
    if use_llm:
        summary, llm_categories = _llm_generate_questions_only(clean_topic, topic_type)

        if not (llm_categories and any(llm_categories.get(c) for c in llm_categories)):
            summary, llm_categories = _llm_generate_questions_only_rescue(clean_topic, topic_type)

        if llm_categories and any(llm_categories.get(c) for c in llm_categories):
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
                ],
                "llm_used": True,
            }

        # AI fallback: only after main LLM pass + rescue pass both fail
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
                "v0: AI LLM question-map failed twice; template fallback used",
            ],
            "llm_used": False,
            "needs_clarification": False,
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
    }


__all__ = ["interrogate", "extract_topic", "detect_topic_type"]

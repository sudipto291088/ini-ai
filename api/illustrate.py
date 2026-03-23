from __future__ import annotations

import re
from typing import Dict, List

from api.topic_utils import detect_topic_type, extract_topic

try:
    from api.llm_answers import llm_enabled as _llm_enabled
    from api.llm_answers import generate_dynamic_answer as llm_answer_question
except Exception:
    _llm_enabled = None
    llm_answer_question = None


def _llm_is_enabled() -> bool:
    if _llm_enabled is None:
        return False
    try:
        return bool(_llm_enabled()) if callable(_llm_enabled) else bool(_llm_enabled)
    except Exception:
        return False


def _normalize_examples(text: str) -> str:
    if not text:
        return ""

    s = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    s = re.sub(r"\n{3,}", "\n\n", s)

    # Normalize headings like "Example 1:" -> "**Example 1 — ...**" only if already bold not present
    lines = s.splitlines()
    out: List[str] = []

    for ln in lines:
        stripped = ln.strip()

        # If model produced markdown heading markers, convert to bold section title
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
            if stripped and not stripped.startswith("**"):
                stripped = f"**{stripped}**"
            out.append(stripped)
            continue

        # If line looks like "Example 1: Healthcare"
        if re.match(r"^Example\s+\d+\s*[:\-–]", stripped, flags=re.IGNORECASE):
            title = re.sub(r"\s*[:\-–]\s*", " — ", stripped, count=1)
            if not title.startswith("**"):
                title = f"**{title}**"
            out.append(title)
            continue

        ln = re.sub(r"^(?:\t| {4,})", "", ln)    
        out.append(ln.rstrip())

    s = "\n".join(out).strip()
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def _build_illustrate_instruction(topic: str, topic_type: str) -> str:
    return f"""
You are InI.ai — an explanation engine for learning through examples.

TOPIC: {topic}
TOPIC TYPE: {topic_type}

Your task:
Generate 9 to 10 highly relevant examples that illustrate the topic clearly.

Output rules:
- Do NOT produce a question map.
- Do NOT produce generic bullets.
- Each example must start with a bold heading.
- Each heading should name the example clearly, such as a domain, scenario, or use case.
- Under each heading, write a properly indented explanatory write-up.
- Keep visible spacing between examples.
- Use horizontal separators like --- between major example blocks when helpful.
- Make the writing appealing, readable, and educational.
- Use concrete real-world examples whenever possible.
- If the topic is abstract, use strong analogies plus practical contexts.
- Maintain clarity and substance; avoid filler.
- Keep the formatting consistent from start to finish.

Preferred output pattern:

**Example 1 — Heading**

Explanation paragraph(s)...

---

**Example 2 — Heading**

Explanation paragraph(s)...

Now generate the examples.
""".strip()


def _build_template_examples(topic: str) -> str:
    return f"""**Example 1 — Everyday Life**

{topic} can often be understood through everyday choices, routines, or patterns people already recognize. This type of example helps make an abstract concept feel concrete and easier to remember.

---

**Example 2 — Workplace Use**

In professional settings, {topic} often appears in workflows, decision-making, automation, or analysis. Seeing the topic in a work context helps learners connect theory with real organizational value.

---

**Example 3 — Education Context**

A classroom or learning example of {topic} can show how the concept is taught, practiced, or applied step by step. This makes the topic more approachable for beginners.

---

**Example 4 — Technology Scenario**

Many modern tools and digital systems rely on ideas closely related to {topic}. A technology-focused illustration helps show how the topic works in current real-world systems.

---

**Example 5 — Business Application**

Businesses often use {topic} to improve efficiency, reduce uncertainty, or create better outcomes. This makes the concept easier to connect with value creation and practical decision-making.

---

**Example 6 — Failure Case**

A useful way to understand {topic} is to examine what happens when it is misunderstood, ignored, or badly applied. Failure cases sharpen understanding by showing limits and consequences.

---

**Example 7 — Analogy**

A strong analogy can explain {topic} by comparing it to something familiar. This helps learners build intuition before moving into technical detail.

---

**Example 8 — Beginner Perspective**

A beginner encountering {topic} for the first time usually benefits from a simple, concrete situation rather than theory alone. This kind of example lowers the entry barrier.

---

**Example 9 — Advanced Perspective**

At a more advanced level, {topic} can be illustrated through systems, trade-offs, and deeper practical implications. This helps learners move beyond surface familiarity.

---

**Example 10 — Why It Matters**

A final illustration should show why understanding {topic} matters in the real world. This ties the concept back to usefulness, judgment, and long-term learning value."""
    

def illustrate(topic: str) -> Dict[str, object]:
    clean_topic = extract_topic(topic)
    topic_type, confidence = detect_topic_type(clean_topic)

    used_llm = False
    examples_text = ""

    if clean_topic and _llm_is_enabled() and llm_answer_question is not None:
        try:
            raw = llm_answer_question(
                topic=clean_topic,
                topic_type=topic_type,
                archetype="APPLY",
                question=_build_illustrate_instruction(clean_topic, topic_type),
                meta={"mode": "illustrate_examples", "expects": "text"},
            )
            examples_text = _normalize_examples(raw or "")
            used_llm = bool(examples_text.strip())
        except Exception:
            examples_text = ""
            used_llm = False

    if not examples_text.strip():
        examples_text = _build_template_examples(clean_topic)
        used_llm = False

    return {
        "topic": clean_topic,
        "topic_type": topic_type,
        "confidence": confidence,
        "illustration_text": examples_text,
        "notes": [
            "v0: illustrate returns 9-10 formatted examples",
            "v0: LLM used when available; template fallback otherwise",
        ],
        "llm_used": used_llm,
    }
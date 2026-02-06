# api/llm_answers.py
import os
from typing import Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # allows app to run even if openai isn't installed


DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-5-mini")  # you can change later
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and (OpenAI is not None)


def _client() -> "OpenAI":
    return OpenAI(api_key=OPENAI_API_KEY)


def generate_dynamic_answer(
    *,
    topic: str,
    topic_type: str,
    archetype: str,
    question: str,
) -> Optional[str]:
    """
    Returns a dynamic answer string or None (if disabled / error).

    Design:
    - Only used for AI/ML in v0.
    - No hard length caps.
    - Structured, to-the-point, but can be long when needed.
    """
    if not llm_enabled():
        return None

    # Light era-awareness hints
    era_hint = ""
    if topic.lower() in {"artificial intelligence", "ai"}:
        era_hint = (
            "Modern AI should mention GenAI/LLMs, RAG, and agentic/tool-using systems when relevant."
        )
    elif topic.lower() in {"machine learning", "ml"}:
        era_hint = (
            "Modern ML should connect to deep learning, GenAI, and agents as a learning/progression map when asked."
        )

    system = (
        "You are InI.ai, a 'question engine' tutor.\n"
        "Answer the user's question clearly and accurately.\n"
        "Rules:\n"
        "- Be precise, not fluffy.\n"
        "- Do NOT artificially cap answer length; be as long as needed.\n"
        "- Use short paragraphs and occasional bullets when helpful.\n"
        "- If the question asks for examples, provide concrete examples.\n"
        "- If the archetype is RISK, include misconceptions/pitfalls and safe practice.\n"
        "- If the archetype is APPLY, include where-used and where-fails if relevant.\n"
        "- If the archetype is NEXT, give a learning map / next steps.\n"
        "- Avoid pretending you have live browsing; use stable knowledge.\n"
    )

    user = (
        f"Topic: {topic}\n"
        f"Topic type: {topic_type}\n"
        f"Archetype: {archetype}\n"
        f"Question: {question}\n\n"
        f"Era hints: {era_hint}\n"
    )

    try:
        c = _client()
        resp = c.responses.create(
            model=DEFAULT_MODEL,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        # Best-effort text extraction (SDK returns a rich object)
        # Many SDK versions provide resp.output_text
        text = getattr(resp, "output_text", None)
        if text and isinstance(text, str) and text.strip():
            return text.strip()

        # Fallback: try to dig through output blocks
        out = getattr(resp, "output", None)
        if isinstance(out, list):
            chunks = []
            for item in out:
                content = getattr(item, "content", None)
                if isinstance(content, list):
                    for c2 in content:
                        t = getattr(c2, "text", None)
                        if isinstance(t, str):
                            chunks.append(t)
            merged = "\n".join(x.strip() for x in chunks if x.strip()).strip()
            return merged or None

        return None
    except Exception:
        return None

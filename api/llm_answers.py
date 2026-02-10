# api/llm_answers.py
import os
from typing import Optional, Dict, Any

import requests


# ----------------------------
# Environment / Config
# ----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# IMPORTANT:
# gpt-4o-mini supports /v1/chat/completions
# gpt-4.1-mini does NOT
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-4o-mini").strip()

INI_LLM_TEMPERATURE = float(os.getenv("INI_LLM_TEMPERATURE", "0.4"))
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "1600"))

INI_LLM_DEBUG = os.getenv("INI_LLM_DEBUG", "").strip() in {
    "1", "true", "TRUE", "yes", "YES"
}


# ----------------------------
# Public helpers
# ----------------------------
def llm_enabled() -> bool:
    return bool(OPENAI_API_KEY)


def _era_hints(topic: str) -> str:
    t = (topic or "").strip().lower()

    if t in {"artificial intelligence", "ai"}:
        return (
            "Cover AI across layers and eras when relevant: "
            "symbolic/classical AI, machine learning, deep learning, "
            "foundation models, LLMs/GenAI, RAG, tool use, agentic systems, "
            "evaluation, alignment, and safety."
        )

    if t in {"machine learning", "ml"}:
        return (
            "Cover ML comprehensively: supervised, unsupervised, self-supervised learning, "
            "feature engineering, deep learning, evaluation (bias/variance, metrics), "
            "deployment, monitoring, and how ML connects to GenAI/LLMs."
        )

    return ""


# ----------------------------
# Core LLM function (v0)
# ----------------------------
def generate_dynamic_answer(
    *,
    topic: str,
    topic_type: str,
    archetype: str,
    question: str,
    meta: Optional[Dict[str, Any]] = None,
    **_ignored: Any,
) -> Optional[str]:
    """
    Generates a dynamic, uncapped-length answer using direct HTTP calls.

    Design guarantees:
    - NO artificial answer length restriction
    - Research-level depth allowed
    - Works reliably on Windows
    - Chat Completions compatible
    """

    if not llm_enabled():
        return None

    system_prompt = (
        "You are InI.ai — a teaching-first AI mentor.\n\n"
        "Non-negotiable rules:\n"
        "- Be precise, accurate, and thorough.\n"
        "- Do NOT artificially cap answer length.\n"
        "- Prefer clarity over brevity.\n"
        "- Use headings and bullets when helpful.\n"
        "- Include concrete examples where appropriate.\n"
        "- If archetype is RISK: include misconceptions, pitfalls, and limits.\n"
        "- If archetype is APPLY: include where-used AND where-it-fails.\n"
        "- If archetype is NEXT: include a clear learning roadmap.\n"
        "- Do NOT pretend to browse the internet.\n"
    )

    hints = _era_hints(topic)

    meta_txt = ""
    if isinstance(meta, dict) and meta:
        meta_txt = "Meta context: " + ", ".join(
            f"{k}={meta.get(k)}" for k in list(meta.keys())[:8]
        )

    user_prompt = (
        f"Topic: {topic}\n"
        f"Topic type: {topic_type}\n"
        f"Archetype: {archetype}\n"
        f"{meta_txt}\n"
        f"Era hints: {hints}\n\n"
        f"Instruction:\n{question}\n"
    )

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": INI_LLM_TEMPERATURE,
        "max_tokens": INI_LLM_MAX_TOKENS,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=90,
        )

        if response.status_code != 200:
            if INI_LLM_DEBUG:
                return (
                    f"[LLM DEBUG] HTTP {response.status_code}: "
                    f"{response.text[:2000]}"
                )
            return None

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        if isinstance(content, str) and content.strip():
            return content.strip()

        if INI_LLM_DEBUG:
            return "[LLM DEBUG] Empty content in response."

        return None

    except Exception as e:
        if INI_LLM_DEBUG:
            return f"[LLM DEBUG] requests exception: {type(e).__name__}: {e}"
        return None

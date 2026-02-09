import os
from typing import Optional, Dict, Any
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-4.1-mini").strip()
INI_LLM_TEMPERATURE = float(os.getenv("INI_LLM_TEMPERATURE", "0.4"))
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "1600"))
INI_LLM_DEBUG = os.getenv("INI_LLM_DEBUG", "").strip() in {"1","true","TRUE","yes","YES"}

# MARKER: REQUESTS_ONLY_V0

def llm_enabled() -> bool:
    return bool(OPENAI_API_KEY)

def _era_hints(topic: str) -> str:
    t = (topic or "").strip().lower()
    if t in {"artificial intelligence","ai"}:
        return ("Include modern layers: classical AI, ML, deep learning, GenAI/LLMs, "
                "RAG, tool-use, agentic systems, evaluation, safety.")
    if t in {"machine learning","ml"}:
        return ("Include ML fundamentals + modern practice: supervised/unsupervised/self-supervised, "
                "metrics, deployment, monitoring, connection to GenAI.")
    return ""

def generate_dynamic_answer(
    *,
    topic: str,
    topic_type: str,
    archetype: str,
    question: str,
    meta: Optional[Dict[str, Any]] = None,
    **_ignored: Any,
) -> Optional[str]:
    if not llm_enabled():
        return None

    system_prompt = (
        "You are InI.ai — a teaching-first AI mentor.\n"
        "Rules:\n"
        "- Be accurate, thorough, and clear.\n"
        "- Do NOT artificially cap length.\n"
        "- Use headings/bullets when helpful.\n"
        "- Include 1–2 examples when useful.\n"
        "- If RISK: misconceptions/pitfalls/limits.\n"
        "- If APPLY: where-used AND where-fails.\n"
        "- If NEXT: practical roadmap.\n"
        "- Do NOT pretend to browse.\n"
    )

    hints = _era_hints(topic)
    meta_txt = ""
    if isinstance(meta, dict) and meta:
        meta_txt = "Meta: " + ", ".join(f"{k}={meta.get(k)}" for k in list(meta.keys())[:8])

    user_prompt = (
        f"Topic: {topic}\n"
        f"Topic type: {topic_type}\n"
        f"Archetype: {archetype}\n"
        f"{meta_txt}\n"
        f"Era hints: {hints}\n\n"
        f"Instruction:\n{question}\n"
    )

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
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
        r = requests.post(url, headers=headers, json=payload, timeout=90)
        if r.status_code != 200:
            if INI_LLM_DEBUG:
                return f"[LLM DEBUG] HTTP {r.status_code}: {r.text[:500]}"
            return None
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return text.strip() if isinstance(text, str) and text.strip() else None
    except Exception as e:
        if INI_LLM_DEBUG:
            return f"[LLM DEBUG] requests exception: {type(e).__name__}: {e}"
        return None

# api/llm_answers.py
import os
from typing import Optional, Dict, Any

import requests


# ----------------------------
# Environment / Config
# ----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# IMPORTANT:
# gpt-4o-mini supports /v1/chat/completions and JSON mode.
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-4o-mini").strip()

INI_LLM_TEMPERATURE = float(os.getenv("INI_LLM_TEMPERATURE", "0.4"))
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "1600"))
INI_LLM_DEBUG = os.getenv("INI_LLM_DEBUG", "0").strip() in ("1", "true", "True", "YES", "yes")


def llm_enabled() -> bool:
    """LLM is enabled only if an API key exists."""
    return bool(OPENAI_API_KEY)


def _era_hints(topic: str) -> str:
    """Small hint helper (kept as-is)."""
    t = (topic or "").lower()
    if "artificial intelligence" in t or t == "ai":
        return "Include: Classical AI → ML → Deep Learning → Foundation Models → GenAI/LLMs → Tool-use/Agents."
    if "machine learning" in t or t == "ml":
        return "Include: supervised/unsupervised, features, evaluation, overfitting, deployment."
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
    """
    Generates a dynamic, uncapped-length answer using direct HTTP calls.

    Design guarantees:
    - NO artificial answer length restriction
    - Research-level depth allowed
    - Works reliably on Windows
    - Chat Completions compatible
    - JSON mode supported when meta expects JSON
    """

    if not llm_enabled():
        return None

    # If caller expects JSON, enforce JSON mode.
    expects_json = False
    if isinstance(meta, dict):
        expects = str(meta.get("expects", "")).lower().strip()
        expects_json = expects in ("json", "json_object", "strict_json")

    # System prompt (slightly strengthened for JSON mode)
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

    if expects_json:
        system_prompt += (
            "\nOUTPUT RULE (STRICT): Return a single valid JSON object only. "
            "No markdown, no commentary, no code fences.\n"
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

    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        # JSON mode is more reliable at lower temperature; keep your default otherwise.
        "temperature": 0.2 if expects_json else INI_LLM_TEMPERATURE,
        "max_tokens": INI_LLM_MAX_TOKENS,
    }

    # The key fix: enforce JSON object output when requested.
    if expects_json:
        payload["response_format"] = {"type": "json_object"}

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

        return None

    except Exception as e:
        if INI_LLM_DEBUG:
            return f"[LLM DEBUG] EXCEPTION: {type(e).__name__}: {e}"
        return None

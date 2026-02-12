# api/llm_answers.py
import os
from typing import Optional, Dict, Any

import requests


# ============================================================
# ENV / CONFIG
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Deep / research model (answers)
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-5-mini-2025-08-07").strip()

# Fast / reliable JSON model (interrogate questions-only)
# You can override via env if you want later.
INTERROGATE_JSON_MODEL = os.getenv("INI_INTERROGATE_JSON_MODEL", "gpt-4o-mini").strip()

# Token budgets (Responses API uses max_output_tokens)
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "2000"))

# Smaller budget for interrogate JSON (questions-only should be fast)
INI_INTERROGATE_MAX_TOKENS = int(os.getenv("INI_INTERROGATE_MAX_TOKENS", "900"))

INI_LLM_DEBUG = os.getenv("INI_LLM_DEBUG", "0").lower() in ("1", "true", "yes")


def llm_enabled() -> bool:
    return bool(OPENAI_API_KEY)


# ============================================================
# CONTEXT HELPERS
# ============================================================

def _era_hints(topic: str) -> str:
    t = (topic or "").lower()
    if "artificial intelligence" in t or t == "ai":
        return (
            "Cover: Classical AI → Machine Learning → Deep Learning → "
            "Foundation Models → Generative AI / LLMs → Tool use → Agentic AI."
        )
    if "machine learning" in t or t == "ml":
        return (
            "Cover: supervised vs unsupervised, features, training, "
            "evaluation, overfitting, deployment."
        )
    return ""


def _select_model_and_budget(meta: Optional[Dict[str, Any]], expects_json: bool) -> tuple[str, int]:
    """
    Routing rules:
    - Interrogate questions-only + JSON: use fast model + smaller token budget
      to avoid "reasoning-only" responses and long latency.
    - Everything else: use DEFAULT_MODEL + full budget.
    """
    mode = ""
    if isinstance(meta, dict):
        mode = str(meta.get("mode", "")).strip().lower()

    if expects_json and mode == "interrogate_questions_only":
        return INTERROGATE_JSON_MODEL, INI_INTERROGATE_MAX_TOKENS

    return DEFAULT_MODEL, INI_LLM_MAX_TOKENS


# ============================================================
# CORE LLM CALL (RESPONSES API)
# ============================================================

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
    Uses OpenAI Responses API.

    Key rules (compatibility):
    - Use /v1/responses
    - Use input[]
    - Use max_output_tokens
    - Do NOT send temperature (some models enforce default only)
    - If meta expects JSON, enable JSON mode via:
        payload["text"] = {"format": {"type": "json_object"}}
    """

    if not llm_enabled():
        return None

    # If caller expects JSON, enforce JSON mode.
    expects_json = False
    if isinstance(meta, dict):
        expects = str(meta.get("expects", "")).lower().strip()
        expects_json = expects in ("json", "json_object", "strict_json")

    # Choose model/budget based on task
    model, max_tokens = _select_model_and_budget(meta, expects_json)

    system_prompt = (
        "You are InI.ai — a teaching-first AI mentor.\n\n"
        "Rules:\n"
        "- Be conceptually clear and technically correct.\n"
        "- Avoid buzzwords unless explained.\n"
        "- Do not shorten answers artificially.\n"
        "- Use examples when helpful.\n"
        "- If archetype is RISK: include misconceptions and failure modes.\n"
        "- If archetype is APPLY: include where it works AND where it fails.\n"
        "- If archetype is NEXT: give concrete next learning steps.\n"
    )

    # IMPORTANT: when using JSON mode, we still instruct JSON (docs requirement).
    if expects_json:
        system_prompt += (
            "\nOUTPUT RULE (STRICT): Return ONE valid JSON object only. "
            "No markdown, no commentary, no code fences.\n"
        )

    era_hint = _era_hints(topic)

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
        f"Era hints: {era_hint}\n\n"
        f"Instruction:\n{question}\n"
    )

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": max_tokens,
    }

    # Responses API JSON mode
    if expects_json:
        payload["text"] = {"format": {"type": "json_object"}}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)

        if response.status_code != 200:
            if INI_LLM_DEBUG:
                return f"[LLM DEBUG] HTTP {response.status_code}: {response.text}"
            return None

        data = response.json()

        # Robust extraction for Responses API
        content = None
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text" and c.get("text"):
                        content = c["text"]
                        break

        if content and content.strip():
            return content.strip()

        if INI_LLM_DEBUG:
            return f"[LLM DEBUG] NO TEXT FOUND: {data}"

        return None

    except Exception as e:
        if INI_LLM_DEBUG:
            return f"[LLM DEBUG] EXCEPTION: {type(e).__name__}: {e}"
        return None

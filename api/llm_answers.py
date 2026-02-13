# api/llm_answers.py
import os
from typing import Optional, Dict, Any, Tuple

import requests


# ============================================================
# ENV / CONFIG
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Deep / research model (answers)
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-5-mini-2025-08-07").strip()

# Fast / reliable JSON model (interrogate questions-only)
INTERROGATE_JSON_MODEL = os.getenv("INI_INTERROGATE_JSON_MODEL", "gpt-4o-mini").strip()

# Token budgets (Responses API uses max_output_tokens)
# IMPORTANT: bigger = fewer truncations, but slower + more cost.
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "3300"))

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


def _select_model_and_budget(meta: Optional[Dict[str, Any]], expects_json: bool) -> Tuple[str, int]:
    """
    Routing rules:
    - Interrogate questions-only + JSON: use fast model + smaller token budget.
    - Everything else: use DEFAULT_MODEL + full budget.
    """
    mode = ""
    if isinstance(meta, dict):
        mode = str(meta.get("mode", "")).strip().lower()

    if expects_json and mode == "interrogate_questions_only":
        return INTERROGATE_JSON_MODEL, INI_INTERROGATE_MAX_TOKENS

    return DEFAULT_MODEL, INI_LLM_MAX_TOKENS


def _extract_output_text(data: Dict[str, Any]) -> str:
    """
    Extract best-effort text from Responses API result.
    We prefer message->content->output_text.
    """
    # Primary path
    for item in data.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text" and c.get("text"):
                    return str(c["text"])

    # Some incomplete responses may not include a message; return empty.
    return ""


def _debug_incomplete_info(data: Dict[str, Any]) -> str:
    status = str(data.get("status", "")).lower()
    inc = data.get("incomplete_details") or {}
    reason = inc.get("reason")
    model = data.get("model")
    usage = data.get("usage") or {}
    return f"status={status} reason={reason} model={model} usage={usage}"


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

    Rules (compatibility):
    - POST /v1/responses
    - Use input[] list of messages
    - Use max_output_tokens
    - Do NOT send temperature (some models enforce default only)
    - If meta expects JSON, enable JSON mode via:
        payload["text"] = {"format": {"type": "json_object"}}
    """

    if not llm_enabled():
        return None

    expects_json = False
    if isinstance(meta, dict):
        expects = str(meta.get("expects", "")).lower().strip()
        expects_json = expects in ("json", "json_object", "strict_json")

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

    if expects_json:
        payload["text"] = {"format": {"type": "json_object"}}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)

        if response.status_code != 200:
            if INI_LLM_DEBUG:
                return f"[LLM DEBUG] HTTP {response.status_code}: {response.text}"
            return None

        data = response.json()

        text = _extract_output_text(data).strip()
        if text:
            # If it was incomplete, we still return the partial text (NO shortening),
            # and the UI can fetch more via Continue.
            if INI_LLM_DEBUG and str(data.get("status", "")).lower() == "incomplete":
                return text + "\n\n" + f"[LLM DEBUG] INCOMPLETE: {_debug_incomplete_info(data)}"
            return text

        # No text found
        if INI_LLM_DEBUG:
            # Preserve the full payload for troubleshooting
            return f"[LLM DEBUG] NO TEXT FOUND: {data}"

        return None

    except Exception as e:
        if INI_LLM_DEBUG:
            return f"[LLM DEBUG] EXCEPTION: {type(e).__name__}: {e}"
        return None

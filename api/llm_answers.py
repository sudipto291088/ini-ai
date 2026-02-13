# api/llm_answers.py
import os
from typing import Optional, Dict, Any, Tuple

import requests


# ============================================================
# ENV / CONFIG
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Responses-compatible model
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-5-mini-2025-08-07").strip()

# Responses API uses max_output_tokens
# (You are overriding this via env var already, which is good.)
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "2000"))

# If True, we keep extra debug info internally in the returned dict,
# but we do NOT append it inside the user-visible answer.
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


def _extract_output_text(data: Dict[str, Any]) -> str:
    """
    Extract best-effort assistant text from Responses API output.
    """
    for item in data.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text" and c.get("text"):
                    return str(c["text"])
    return ""


def _is_incomplete(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Detect "incomplete" responses (most often max_output_tokens).
    Returns (incomplete, reason).
    """
    status = str(data.get("status", "")).lower().strip()
    if status == "incomplete":
        inc = data.get("incomplete_details") or {}
        reason = inc.get("reason")
        return True, str(reason) if reason else "unknown"

    # Some responses may not set status cleanly; keep a safety check
    inc = data.get("incomplete_details") or {}
    if inc:
        reason = inc.get("reason")
        return True, str(reason) if reason else "unknown"

    return False, None


# ============================================================
# CORE LLM CALL (RESPONSES API)
# ============================================================

def generate_dynamic_answer_result(
    *,
    topic: str,
    topic_type: str,
    archetype: str,
    question: str,
    meta: Optional[Dict[str, Any]] = None,
    timeout_s: int = 90,
    **_ignored: Any,
) -> Dict[str, Any]:
    """
    Returns a structured result:
      {
        "answer": "<text or ''>",
        "incomplete": <bool>,
        "stop_reason": "<reason or None>",
        "model": "<model>",
        "http_status": <int or None>,
        "error": "<string or None>",
        "raw": <full response json only when INI_LLM_DEBUG=1 else None>
      }

    IMPORTANT:
    - We NEVER append debug strings inside "answer".
    - "Continue" logic should be driven by result["incomplete"].
    """

    if not llm_enabled():
        return {
            "answer": "",
            "incomplete": False,
            "stop_reason": None,
            "model": DEFAULT_MODEL,
            "http_status": None,
            "error": "llm_disabled",
            "raw": None,
        }

    expects_json = False
    if isinstance(meta, dict):
        expects = str(meta.get("expects", "")).lower().strip()
        expects_json = expects in ("json", "json_object", "strict_json")

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
        "model": DEFAULT_MODEL,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": INI_LLM_MAX_TOKENS,
    }

    # Responses API JSON mode
    if expects_json:
        payload["text"] = {"format": {"type": "json_object"}}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)

        if resp.status_code != 200:
            return {
                "answer": "",
                "incomplete": False,
                "stop_reason": None,
                "model": DEFAULT_MODEL,
                "http_status": resp.status_code,
                "error": resp.text[:1200],
                "raw": None,
            }

        data = resp.json()

        text = _extract_output_text(data).strip()
        incomplete, reason = _is_incomplete(data)

        # Never leak debug strings into the answer.
        result = {
            "answer": text,
            "incomplete": bool(incomplete),
            "stop_reason": reason,
            "model": str(data.get("model") or DEFAULT_MODEL),
            "http_status": 200,
            "error": None,
            "raw": data if INI_LLM_DEBUG else None,
        }

        return result

    except Exception as e:
        return {
            "answer": "",
            "incomplete": False,
            "stop_reason": None,
            "model": DEFAULT_MODEL,
            "http_status": None,
            "error": f"{type(e).__name__}: {e}",
            "raw": None,
        }


def generate_dynamic_answer(
    *,
    topic: str,
    topic_type: str,
    archetype: str,
    question: str,
    meta: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Optional[str]:
    """
    Backward-compatible wrapper used by existing code:
    returns ONLY the answer text (no debug leakage).
    """
    res = generate_dynamic_answer_result(
        topic=topic,
        topic_type=topic_type,
        archetype=archetype,
        question=question,
        meta=meta,
        **kwargs,
    )
    ans = (res.get("answer") or "").strip()
    return ans if ans else None

import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import requests


# ============================================================
# Load .env from repo root (works no matter where uvicorn starts)
# ============================================================
try:
    from dotenv import load_dotenv  # type: ignore

    # api/llm_answers.py -> repo_root/.env
    REPO_ROOT = Path(__file__).resolve().parents[1]
    DOTENV_PATH = REPO_ROOT / ".env"
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
except Exception:
    # If python-dotenv isn't installed, rely on OS env vars
    pass


# ============================================================
# ENV / CONFIG
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Responses-compatible model
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-5-mini-2025-08-07").strip()

# Responses API uses max_output_tokens
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "3000"))

# If True, keep extra debug info in returned dict (not appended to answer text)
INI_LLM_DEBUG = os.getenv("INI_LLM_DEBUG", "0").lower() in ("1", "true", "yes")


def llm_enabled() -> bool:
    return bool(OPENAI_API_KEY)


# ============================================================
# TEXT CLEANUP (fix mojibake / weird characters)
# ============================================================

def _normalize_text(s: str) -> str:
    """
    Fix common mojibake sequences we keep seeing in Windows/PS/Streamlit renders.
    Example: “â€”” -> “—”, “â€™” -> “’”.
    """
    if not s:
        return ""

    # Fast path: only run replacements if we detect telltale mojibake markers
    if "â" not in s and "Â" not in s and "Ã" not in s:
        return s

    repl = {
        # dashes / ellipsis
        "â€”": "—",
        "â€“": "–",
        "â€•": "―",
        "â€¦": "…",

        # quotes
        "â€œ": "“",
        "â€�": "”",
        "â€˜": "‘",
        "â€™": "’",
        "â„¢": "™",

        # bullets / middots
        "â€¢": "•",
        "Â·": "·",

        # spaces / nbsp artifacts
        "Â ": " ",
        "Â ": " ",

        # common apostrophe variant
        "Ã¢â‚¬â„¢": "’",
        "Ã¢â‚¬â€œ": "–",
        "Ã¢â‚¬â€�": "—",
        "Ã¢â‚¬Â¦": "…",
        "Ã¢â‚¬Å“": "“",
        "Ã¢â‚¬Â": "”",
    }

    for k, v in repl.items():
        s = s.replace(k, v)

    return s


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


def _collect_text_from_content(content: Any) -> str:
    """
    Normalize different content shapes into a single concatenated text.

    Expected content items may look like:
      {"type":"output_text","text":"..."}
      {"type":"text","text":"..."}   (rare variants)
      {"type":"output_text","text":{"value":"..."}} (older/variant)
    """
    parts: List[str] = []

    if isinstance(content, list):
        for c in content:
            if not isinstance(c, dict):
                continue
            ctype = (c.get("type") or "").strip()
            txt = c.get("text")

            # Standard: output_text
            if ctype == "output_text" and isinstance(txt, str) and txt.strip():
                parts.append(txt)
                continue

            # Variant: type=text
            if ctype == "text":
                if isinstance(txt, str) and txt.strip():
                    parts.append(txt)
                    continue
                if isinstance(txt, dict) and isinstance(txt.get("value"), str) and txt["value"].strip():
                    parts.append(txt["value"])
                    continue

            # Variant: output_text with dict payload
            if ctype == "output_text" and isinstance(txt, dict) and isinstance(txt.get("value"), str) and txt["value"].strip():
                parts.append(txt["value"])
                continue

    return "\n".join([p for p in parts if p is not None]).strip()


def _extract_output_text(data: Dict[str, Any]) -> str:
    """
    Extract best-effort assistant text from Responses API output.

    Handles:
      - Standard Responses API: output -> message -> content -> output_text
      - Variants where message.content contains type "text"
      - Rare cases where text appears under output item "text"
      - Top-level content variants (rare)

    If nothing found, returns "".
    """
    # 1) Standard + variants: output items
    output = data.get("output") or []
    if isinstance(output, list):
        # Prefer message items first
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                text = _collect_text_from_content(item.get("content"))
                if text:
                    return text

        # 2) Fallback: sometimes content-like blocks appear in other output items
        for item in output:
            if not isinstance(item, dict):
                continue

            # Some variants may attach "content" even if type isn't message
            text = _collect_text_from_content(item.get("content"))
            if text:
                return text

            # Very rare: direct "text" field at the output item
            if isinstance(item.get("text"), str) and item["text"].strip():
                return str(item["text"]).strip()

            # Rare: item["text"] dict with value
            if isinstance(item.get("text"), dict) and isinstance(item["text"].get("value"), str) and item["text"]["value"].strip():
                return str(item["text"]["value"]).strip()

    # 3) Top-level variants (rare)
    top_content = data.get("content")
    text = _collect_text_from_content(top_content)
    if text:
        return text

    # 4) Last resort: some SDKs place output_text at top-level
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return str(data["output_text"]).strip()

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
    timeout_s: int = 120,
    previous_response_id: Optional[str] = None,
    **_ignored: Any,
) -> Dict[str, Any]:
    """
    Returns a structured result:
      {
        "answer": "<text or ''>",
        "incomplete": <bool>,
        "stop_reason": "<reason or None>",
        "status": "<responses status string or None>",
        "response_id": "<responses id or None>",
        "usage": <usage dict or None>,
        "model": "<model>",
        "http_status": <int or None>,
        "error": "<string or None>",
        "raw": <full response json only when INI_LLM_DEBUG=1 else None>
      }
    """

    if not llm_enabled():
        return {
            "answer": "",
            "incomplete": False,
            "stop_reason": None,
            "status": None,
            "response_id": None,
            "usage": None,
            "model": DEFAULT_MODEL,
            "http_status": None,
            "error": "llm_disabled_or_missing_key",
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
        "- Prefer structured sections with headings and bullet points when helpful.\n"
        "- Use concrete examples and failure modes when relevant.\n"
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
        "text": {"format": {"type": "text"}},
    }

    if expects_json:
        payload["text"] = {"format": {"type": "json_object"}}

    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)

        if resp.status_code != 200:
            return {
                "answer": "",
                "incomplete": False,
                "stop_reason": None,
                "status": None,
                "response_id": None,
                "usage": None,
                "model": DEFAULT_MODEL,
                "http_status": resp.status_code,
                "error": resp.text[:1200],
                "raw": None,
            }

        data = resp.json()

        text = _extract_output_text(data).strip()
        text = _normalize_text(text)

        incomplete, reason = _is_incomplete(data)

        return {
            "answer": text,
            "incomplete": bool(incomplete),
            "stop_reason": reason,
            "status": data.get("status"),
            "response_id": data.get("id"),
            "usage": data.get("usage"),
            "model": str(data.get("model") or DEFAULT_MODEL),
            "http_status": 200,
            "error": None,
            "raw": data if INI_LLM_DEBUG else None,
        }

    except Exception as e:
        return {
            "answer": "",
            "incomplete": False,
            "stop_reason": None,
            "status": None,
            "response_id": None,
            "usage": None,
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

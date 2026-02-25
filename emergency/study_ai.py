# api/study_ai.py
from typing import Dict, Any, Tuple, Optional
import re

from api.llm_answers import llm_enabled, generate_dynamic_answer_result


def _parse_llm_debug_error(text: str) -> Tuple[Optional[int], str]:
    """
    Legacy safety: if any old debug strings leak into answer text,
    detect them and suppress in UI.
    """
    if not isinstance(text, str):
        return None, "unknown"

    m = re.search(r"\[LLM DEBUG\]\s*HTTP\s+(\d+):", text)
    if m:
        return int(m.group(1)), "http_error"

    if "[LLM DEBUG]" in text:
        return None, "debug"

    return None, "unknown"


def _fallback_ai_lesson(user_message: str, level: str, goal: str, time_per_day: str) -> str:
    # Simple fallback (only used if LLM is disabled).
    return (
        "# AI Tutor (Fallback)\n\n"
        "LLM is currently disabled, so this is a safe fallback.\n\n"
        f"Your prompt: {user_message}\n\n"
        "Try again after setting OPENAI_API_KEY.\n"
    )


def study_ai(user_message: str) -> Dict[str, Any]:
    """
    v0 Study mode:
    - ONLY AI topic uses LLM.
    - Returns a stable schema so Streamlit can reliably detect truncation:
        { mode, topic, status, llm, answer, incomplete, stop_reason }
    """
    topic = "Artificial Intelligence"

    # Default knobs (you can later make these UI controls)
    level = "DEEP"
    goal = "learn"
    time_per_day = "30-60 min"

    if not llm_enabled():
        return {
            "mode": "study",
            "topic": topic,
            "status": "ok",
            "llm": {"enabled": False, "reason": "no_api_key"},
            "answer": _fallback_ai_lesson(user_message, level, goal, time_per_day),
            "incomplete": False,
            "stop_reason": None,
        }

    # IMPORTANT: Do NOT force “continue” unless the model actually truncates.
    # We request a deep answer; truncation is detected by the Responses API status fields.
    question = (
        "You are a deep technical AI tutor.\n"
        "Write a research-grade, well-structured answer.\n"
        "Use headings, bullets, and examples.\n"
        "Be specific, non-repetitive, and avoid filler.\n"
        "Do NOT ask the user meta-questions unless required.\n\n"
        f"User prompt: {user_message}\n"
    )

    result = generate_dynamic_answer_result(
        topic=topic,
        topic_type="concept",
        archetype="APPLY",
        question=question,
        meta={"mode": "study_ai", "expects": "text"},
        timeout_s=120,
    )

    ans = (result.get("answer") or "").strip()
    incomplete = bool(result.get("incomplete", False))
    stop_reason = result.get("stop_reason", None)

    # If the LLM returned no text (rare), expose a stable response
    if not ans:
        # If the LLM errored, preserve that in llm.reason
        err = result.get("error")
        http_status = result.get("http_status")
        return {
            "mode": "study",
            "topic": topic,
            "status": "ok",
            "llm": {
                "enabled": True,
                "reason": "empty_answer" if not err else "llm_error",
                "http_status": http_status,
                "error": err,
            },
            "answer": "No answer generated.",
            "incomplete": False,
            "stop_reason": None,
        }

    # Legacy safety: if debug strings leak into ans, suppress it (do not show raw debug)
    http_code, dbg_reason = _parse_llm_debug_error(ans)
    if dbg_reason in ("http_error", "debug"):
        return {
            "mode": "study",
            "topic": topic,
            "status": "ok",
            "llm": {"enabled": True, "reason": dbg_reason, "http_status": http_code},
            "answer": "No answer generated.",
            "incomplete": False,
            "stop_reason": None,
        }

    return {
        "mode": "study",
        "topic": topic,
        "status": "ok",
        "llm": {"enabled": True, "reason": "ok"},
        "answer": ans,
        "incomplete": incomplete,
        "stop_reason": stop_reason,
    }


__all__ = ["study_ai"]

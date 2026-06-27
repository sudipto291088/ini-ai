# api/study_ai.py
from typing import Dict, Any, Tuple, Optional, Union
import re

from api.llm_answers import llm_enabled, generate_dynamic_answer_result
from api.intent_layer import detect_intent


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


def _fallback_ai_lesson(user_message: str, level: str) -> str:
    # Simple fallback (only used if LLM is disabled).
    return (
        "# AI Tutor (Fallback)\n\n"
        "LLM is currently disabled, so this is a safe fallback.\n\n"
        f"Your prompt: {user_message}\n\n"
        "Try again after setting OPENAI_API_KEY.\n"
    )


def _normalize_mode(raw: Optional[str]) -> str:
    """
    Supported:
      - deep (default)
      - high (overview)
      - quiz
      - focused (FUQ-style direct deep bullets)
    Accept common aliases.
    """
    if not raw:
        return "deep"
    m = str(raw).strip().lower()

    alias = {
        "deep": "deep",
        "default": "deep",
        "d": "deep",
        "research": "deep",
        "apply": "deep",

        "overview": "high",
        "high": "high",
        "summary": "high",
        "brief": "high",

        "quiz": "quiz",
        "q": "quiz",
        "questions": "quiz",
        "test": "quiz",

        "focused": "focused",
        "focus": "focused",
        "fuq": "focused",
        "bullet": "focused",
        "bullets": "focused",
    }
    return alias.get(m, "deep")



def _build_instruction(mode: str) -> str:
    """
    Build the *style contract* for the tutor. This is where we make
    'high', 'quiz', and 'focused' visibly different from 'deep'.
    """
    if mode == "high":
        return (
            "You are InI, a clean and helpful AI tutor.\n"
            "Produce a HIGH-LEVEL overview.\n"
            "- Keep it short and crisp (8–12 bullets max).\n"
            "- Avoid deep dives; focus on the big picture.\n"
            "- Use bold headings.\n"
            "- End with 2 suggested follow-up questions.\n"
        )

    if mode == "quiz":
        return (
            "You are InI, an interactive AI tutor.\n"
            "Generate a QUIZ only (no answers unless user asks).\n"
            "- 7 questions total.\n"
            "- Mix: 3 conceptual, 2 scenario-based, 2 short definition.\n"
            "- Include difficulty tags: (Easy/Med/Hard).\n"
            "- Keep questions tight and unambiguous.\n"
            "- End with: 'Reply with your answers and I will grade you.'\n"
        )

    if mode == "focused":
        return (
            "You are InI, a thoughtful and visually clear AI tutor.\n"
            "Answer the user's question in a concise but pleasant-to-read way.\n"
            "\n"
            "Formatting rules:\n"
            "- Do NOT include an Introduction section.\n"
            "- Do NOT produce a Question Map.\n"
            "- Prefer 2 short readable paragraphs.\n"
            "- Target roughly 150 to 220 words total.\n"
            "- Avoid giant essays and avoid overly compressed bullets.\n"
            "- Use smooth educational flow and natural language.\n"
            "- Keep explanations beginner-friendly but intelligent.\n"
            "- Use examples only when they genuinely improve clarity.\n"
            "- Avoid numbered sections unless steps are necessary.\n"
            "- End naturally and cleanly.\n"
        )

    # deep (default)
    return (
        "You are InI, a deep technical AI tutor.\n"
        "Write a research-grade, well-structured answer.\n"
        "- Use bold headings, bullets, and concrete examples.\n"
        "- Maintain consistent hierarchy throughout the document.\n"
        "- Do NOT introduce abrupt top-level headings mid-answer.\n"
        "- Do NOT output standalone pseudo-code lines as headings.\n"
        "- Keep formatting clean and proportional (no oversized structural resets).\n"
        "- Add intuitions, failure modes, and practical trade-offs.\n"
        "- Be specific, cohesive, and avoid filler.\n"
        "- Do NOT ask meta-questions unless required.\n"
    )


def _archetype_for_mode(mode: str) -> str:
    if mode == "high":
        return "ORIENT"
    if mode == "focused":
        return "APPLY"
    if mode == "quiz":
        return "NEXT"
    return "APPLY"




def study_ai(payload: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    v0 Study mode:
    - ONLY AI topic uses LLM.
    - Accepts:
        1) str: user prompt
        2) dict: {"topic": "...", "mode": "deep|high|quiz", "continue_mode": bool, "previous_answer": str}
    - Returns stable schema:
        { mode, topic, domain, status, llm, answer, incomplete, stop_reason }
    """
    domain = "Artificial Intelligence"

    # ---- Parse input safely (string or dict) ----
    if isinstance(payload, dict):
        user_topic = (payload.get("topic") or payload.get("user_message") or "").strip()
        mode = _normalize_mode(payload.get("mode"))
        continue_mode = bool(payload.get("continue_mode", False))
        previous_answer = (payload.get("previous_answer") or "").strip()
    else:
        user_topic = str(payload).strip()
        mode = "deep"
        continue_mode = False
        previous_answer = ""

    if not user_topic:
        user_topic = "Explain Artificial Intelligence."

    # Focused mode = clicked Question Map / FUQ answer.
    # These are already educational questions and should bypass
    # conversational intent filtering.
    if mode == "focused":
        intent_name = "focused_question"
        should_interrogate = True
        should_answer_direct = False
    else:
        intent = detect_intent(user_topic)
        intent_name = (intent.get("intent") or "").strip().lower()
        should_interrogate = bool(intent.get("should_interrogate", False))
        should_answer_direct = bool(intent.get("should_answer_direct", False))

    # Normal conversational behavior: greeting / thanks / help / etc.
    if (
    mode != "focused"
    and not should_interrogate
    and not should_answer_direct
        ):
        reply = (intent.get("reply") or "").strip() or "Send a topic to explore."
        return {
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
            "status": "ok",
            "llm": {"enabled": bool(llm_enabled()), "reason": "intent_reply"},
            "answer": reply,
            "incomplete": False,
            "stop_reason": None,
            "intent": intent_name,
            "followups": intent.get("followups") or [],
            "should_answer_direct": False,
        }

    # ---- LLM disabled fallback ----
    if not llm_enabled():
        return {
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
            "status": "ok",
            "llm": {"enabled": False, "reason": "no_api_key"},
            "answer": _fallback_ai_lesson(user_topic, mode.upper()),
            "incomplete": False,
            "stop_reason": None,
        }

    # ---- Build prompt ----
    instruction = _build_instruction(mode)

    if continue_mode and previous_answer:

    # --- STRICT TOKEN CONTINUATION ---
    # Only send the tail of the previous answer
        tail = previous_answer[-1500:]

        question = (
        f"{instruction}\n"
        "STRICT CONTINUATION MODE:\n"
        "- Continue the text exactly from where it stopped.\n"
        "- Do NOT restart the topic.\n"
        "- Do NOT introduce new section headers.\n"
        "- Do NOT repeat earlier content.\n"
        "- Output ONLY the next portion of the same document.\n\n"
        "Text so far (ending segment only):\n"
        f"{tail}\n"
    )
    else:
        question = (
            f"{instruction}\n"
            f"User prompt: {user_topic}\n"
        )

    # ---- Call core LLM engine ----
    result = generate_dynamic_answer_result(
        topic=user_topic,
        topic_type="concept",
        archetype=_archetype_for_mode(mode),
        question=question,
        meta={
            "mode": "study_ai",
            "level": mode,
            "expects": "text",
            "continue_mode": continue_mode,
        },
        timeout_s=120,
    )

    ans = (result.get("answer") or "").strip()
    incomplete = bool(result.get("incomplete", False))
    stop_reason = result.get("stop_reason", None)

    # If the LLM returned no text (rare), expose a stable response
    if not ans:
        err = result.get("error")
        http_status = result.get("http_status")
        return {
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
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
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
            "status": "ok",
            "llm": {"enabled": True, "reason": dbg_reason, "http_status": http_code},
            "answer": "No answer generated.",
            "incomplete": False,
            "stop_reason": None,
        }

    return {
        "mode": mode,
        "topic": user_topic,
        "domain": domain,
        "status": "ok",
        "llm": {"enabled": True, "reason": "ok"},
        "answer": ans,
        "incomplete": incomplete,
        "stop_reason": stop_reason,
    }


__all__ = ["study_ai"]

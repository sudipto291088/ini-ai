# api/study_ai.py
from typing import Dict, Any, Tuple, Optional
import re

try:
    from api.llm_answers import llm_enabled, generate_dynamic_answer
except Exception:
    llm_enabled = lambda: False
    generate_dynamic_answer = None


def _parse_llm_debug_error(text: str) -> Tuple[Optional[int], str]:
    if not isinstance(text, str):
        return None, "unknown"

    m = re.search(r"\[LLM DEBUG\]\s+HTTP\s+(\d+)\s*:", text)
    if not m:
        return None, "unknown"

    code = int(m.group(1))
    if code == 401:
        return code, "invalid_api_key"
    if code == 429:
        return code, "rate_limited_or_quota"
    if 400 <= code < 500:
        return code, "bad_request"
    if 500 <= code < 600:
        return code, "provider_error"
    return code, "unknown"


def _fallback_ai_lesson(user_message: str, level: str, goal: str, time_per_day: str) -> str:
    return f"""# Study AI (Fallback Lesson)

**Status:** LLM unavailable right now — serving a built-in lesson instead.

## 1) Concept Map (big picture)
- **Artificial Intelligence (AI):** systems that perform tasks associated with “intelligence” (perception, language, decisions).
- **Machine Learning (ML):** AI where systems learn patterns from data instead of fixed rules.
- **Deep Learning (DL):** ML using neural networks with many layers; strong for vision, speech, language.
- **Generative AI (GenAI):** models that generate text/images/code (e.g., LLMs).
- **LLMs:** large language models that predict next tokens; great for language tasks, tutoring, and drafting.
- **Tool-use / Agents:** LLMs that call tools (search, code, DB) to do multi-step work.
- **Evaluation & Safety:** measuring correctness, bias, robustness, monitoring, guardrails.

## 2) What AI is NOT (common misconceptions)
- AI is not “human understanding.” It’s pattern + optimization.
- A confident answer is not necessarily a correct answer.
- “More data/model” doesn’t automatically mean “more trustworthy.”

**Your message (for context):**
{user_message}
""".strip()


def _detect_path_hint(user_message: str) -> str:
    txt = (user_message or "").upper()
    if "PATH=HIGH" in txt or "PATH:HIGH" in txt:
        return "HIGH"
    if "PATH=DEEP" in txt or "PATH:DEEP" in txt:
        return "DEEP"
    return "AUTO"


def study_ai(
    user_message: str,
    level: str = "beginner",
    goal: str = "learn",
    time_per_day: str = "30-60 min",
) -> Dict[str, Any]:
    topic = "Artificial Intelligence"

    if not (callable(llm_enabled) and llm_enabled() and generate_dynamic_answer):
        return {
            "mode": "study",
            "topic": topic,
            "status": "fallback",
            "llm": {"enabled": False, "reason": "llm_not_configured"},
            "answer": _fallback_ai_lesson(user_message, level, goal, time_per_day),
        }

    path_hint = _detect_path_hint(user_message)

    instruction = f"""
You are InI.ai in STUDY mode. Teach Artificial Intelligence like a calm, human tutor with machine-level precision.

User profile:
- level: {level}
- goal: {goal}
- time_per_day: {time_per_day}

User input:
{user_message}

ABSOLUTE QUALITY BAR:
- Research-grade explanations: correct, nuanced, and practical.
- NO artificial shortening. Depth is welcome.
- Be specific to the user's question; avoid generic filler.

STYLE (human + machine):
- Human tutor pacing: concept → intuition → example → boundary/failure mode → synthesis.
- Machine strengths: precise definitions, clear distinctions, honest limitations, tradeoffs.
- Include “math tidbits” ONLY when helpful and light (1–3 lines max), unless user explicitly asks for heavy math.

ANTI-CLICHÉ / ANTI-REPETITION:
- Do NOT always end with the same template.
- Only include week-by-week plans if the user explicitly requests them.
- Avoid stock closings like “Happy studying!” unless it fits naturally.

PATH BEHAVIOR (important):
- PATH={path_hint}

If PATH=HIGH:
- Explain for clarity and intuition first.
- Use examples, analogies, and practical framing.
- Keep technical depth moderate. Include light math tidbits only when they clarify.

If PATH=DEEP:
- This MUST be an elaborate technical answer (not brief).
- Do NOT be concise.
- Include the following minimum sections (use headings):
  ## 1) Precise definition (with scope)
  ## 2) Mechanisms (how it works internally)
  ## 3) Concrete examples (at least 2; one classical/ML, one modern LLM/agentic)
  ## 4) Evaluation (metrics, testing, failure analysis)
  ## 5) Failure modes + mitigations (specific, not generic)
  ## 6) Practical checklist (how to build / implement in real systems)
- Add “math tidbits” where relevant (loss, likelihood, gradient descent, attention) but keep them digestible.
- Avoid repetition: each section should add genuinely new information.

If PATH=AUTO:
- Choose HIGH vs DEEP based on the user’s question.
- If the user asks “explain” broadly, default to HIGH, unless they request deep details.

FORMAT RULES (non-negotiable):
- Output clean Markdown with stable structure:
  - Use headings (##, ###) and short paragraphs.
  - Use bullets only where they add clarity.
  - Keep indentation consistent.
- NEVER break a sentence across lines. Never split words across lines.
- Avoid orphan bullets (no 1–2 word bullets like "Support").
- Never leave a bullet unfinished (no trailing fragments like “AI will naturally …”).
- If you start a list, complete it before moving to the next section.

ENDING RULES (prevents weird Continue moments):
- Prefer a natural, clean ending (short synthesis / recap).
- Do NOT invite continuation automatically.
- If you ask the user a question, you MUST STOP immediately after that question.
  - Do NOT continue with more content after asking a question.
  - Do NOT ask a question near the end of the response where it could be followed by “Continue”.

CRITICAL CONTINUATION RULES:
- If the user input includes a CONTEXT block, treat it as the immediately preceding text shown to the user.
- Continue DIRECTLY from the end of that context.
- NEVER say "I don't have the previous part" or ask what the user saw.
- NEVER ask clarifying questions during continuation.
- Do NOT restart. Do NOT repeat earlier sections unless explicitly requested.
- If you are running out of space, end at a clean boundary (end of a paragraph or after finishing a list),
  NOT mid-bullet and NOT mid-sentence.
""".strip()

    ans = generate_dynamic_answer(
        topic=topic,
        topic_type="concept",
        archetype="STUDY",
        question=instruction,
    )

    if not ans:
        return {
            "mode": "study",
            "topic": topic,
            "status": "fallback",
            "llm": {"enabled": True, "reason": "empty_llm_output"},
            "answer": _fallback_ai_lesson(user_message, level, goal, time_per_day),
        }

    if isinstance(ans, str) and ans.startswith("[LLM DEBUG]"):
        http_code, reason = _parse_llm_debug_error(ans)
        return {
            "mode": "study",
            "topic": topic,
            "status": "fallback",
            "llm": {"enabled": True, "reason": reason, "http_status": http_code},
            "answer": _fallback_ai_lesson(user_message, level, goal, time_per_day),
        }

    return {
        "mode": "study",
        "topic": topic,
        "status": "ok",
        "llm": {"enabled": True, "reason": "ok"},
        "answer": ans,
    }


__all__ = ["study_ai"]

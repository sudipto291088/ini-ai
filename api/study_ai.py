# api/study_ai.py
from typing import Dict, Any, Tuple, Optional
import re

try:
    from api.llm_answers import llm_enabled, generate_dynamic_answer
except Exception:
    llm_enabled = lambda: False
    generate_dynamic_answer = None


def _parse_llm_debug_error(text: str) -> Tuple[Optional[int], str]:
    """
    Extract HTTP status from strings like:
    "[LLM DEBUG] HTTP 401: {...}"
    Returns (status_code, reason)
    """
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


def _fallback_ai_lesson(
    user_message: str,
    level: str,
    goal: str,
    time_per_day: str,
) -> str:
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

## 3) A simple working example
**Spam detection (classic ML):**
- Input: email text/features
- Output: spam/not spam
- Learn from labeled examples
- Evaluate using precision/recall

**LLM example (GenAI):**
- Input: prompt + context
- Output: explanation/summary/code
- Evaluate: factuality, consistency, usefulness; add checks/guardrails

## 4) A practical learning path (beginner → applied)
**Beginner**
- Understand: data, labels, features, train/test split
- Basic models: linear/logistic regression, decision trees
- Metrics: accuracy, precision/recall, F1

**Intermediate**
- Overfitting/regularization
- Cross-validation
- Feature engineering
- Model comparison & error analysis

**Applied / Modern**
- Deployment basics (APIs, monitoring)
- Data drift + retraining
- GenAI basics (prompting, constraints)
- Agents (tool-use), RAG (retrieval-augmented generation)

## 5) Daily plan ({time_per_day})
- **10 min:** read concept + summarize in 3 bullets
- **20–40 min:** do 1 exercise (below)
- **10 min:** reflect: “where does it fail?” + “how to evaluate?”

## 6) Exercises (pick one)
1) Define AI vs ML vs DL vs GenAI in your own words (4 lines each).
2) Pick a real problem and state: input, output, metric, failure mode.
3) Write 5 “gotcha” questions to test whether an AI claim is real.

## 7) Checkpoints (self-test)
- Can you explain AI in plain language without buzzwords?
- Can you name 3 failure modes and 3 evaluation metrics?
- Can you design a tiny project with clear input/output/metric?

## 8) Next actions (do these)
1) Choose one domain (finance, health, retail, education) and list 3 AI use-cases.
2) Build one tiny classifier in Python (spam/iris/penguins).
3) Write a 1-page “AI system checklist” (data, model, evaluation, monitoring, safety).

## 9) Mini-project idea
**AI Learning Tracker**
- Track topics learned, quizzes, and mini-projects.
- Include “mistakes I made” + “what I will do next.”
- Output as a simple Streamlit app.

**Your message (for context):**
{user_message}
""".strip()


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

    instruction = f"""
You are InI.ai in STUDY mode. Teach Artificial Intelligence like a mentor.

User profile:
- level: {level}
- goal: {goal}
- time_per_day: {time_per_day}

User input:
{user_message}

QUALITY BAR:
- Research-grade explanations. Prioritize correctness, nuance, and useful examples.
- Do NOT shorten answers artificially. Depth is welcome.

FORMAT RULES (very important):
- Write clean Markdown with stable structure:
  - Use headings (##, ###) for sections.
  - Use bullets with consistent indentation (2 spaces under a bullet for sub-bullets).
  - Keep blank line before a bullet block.
- NEVER break a sentence across lines.
  - Do not insert a newline in the middle of a paragraph or sentence.
  - Do not split words across lines.
- Avoid ultra-long “single-line” paragraphs. Prefer short paragraphs.

CONTENT COVERAGE:
- Classical AI → ML → Deep Learning → Foundation Models → GenAI/LLMs → Tool use → Agentic AI
- Include misconceptions + what AI is NOT
- Include 1–2 concrete examples
- End with:
  (1) 3 next actions
  (2) 3 practice prompts
  (3) 1 mini-project idea

CRITICAL CONTINUATION RULES:
- If the user input includes a CONTEXT block, treat it as the immediately preceding text shown to the user.
- Continue DIRECTLY from the end of that context.
- NEVER say "I don't have the previous part", "tell me the last heading", or ask what the user saw.
- NEVER ask clarifying questions during continuation.
- Do NOT restart. Do NOT repeat earlier sections unless explicitly requested.
- Write the next sections as a seamless continuation.
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
            "llm": {
                "enabled": True,
                "reason": reason,
                "http_status": http_code,
            },
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

# api/study_ai.py
from typing import Dict, Any

try:
    from api.llm_answers import llm_enabled, generate_dynamic_answer
except Exception:
    llm_enabled = lambda: False
    generate_dynamic_answer = None


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
            "status": "llm_disabled",
            "message": "LLM is not enabled. Set OPENAI_API_KEY and restart FastAPI.",
        }

    instruction = f"""
You are InI.ai in STUDY mode. Teach Artificial Intelligence like a mentor.

User profile:
- level: {level}
- goal: {goal}
- time_per_day: {time_per_day}

User message:
{user_message}

Deliver a HYBRID response:
- Clear headings + bullets where useful
- Warm tutor tone
- Go deep (no artificial length caps)
- Cover modern layers: Classical AI → ML → Deep Learning → GenAI/LLMs → Agentic/Tool-using AI
- Include misconceptions + what AI is NOT
- Include 1–2 examples
- End with: (1) 3 next actions, (2) 3 practice prompts, (3) 1 mini-project idea
""".strip()

    ans = generate_dynamic_answer(
        topic=topic,
        topic_type="concept",
        archetype="STUDY",
        question=instruction,
        
    )

    return {
        "mode": "study",
        "topic": topic,
        "status": "ok",
        "answer": ans or "LLM returned empty output. Please retry.",
    }


__all__ = ["study_ai"]

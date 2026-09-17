from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from api.interrogate import interrogate
from api.illustrate import illustrate as illustrate_logic
from api.resume import resume as resume_logic
from api.llm_answers import llm_enabled, generate_dynamic_answer
from api.study_ai import study_ai
from api.intent_layer import detect_intent
from api.subject_curriculum import (
    assess_subject,
    generate_subject_outline,
    generate_chapter_questions,
    answer_curriculum_question,
)
from api.wikidata_knowledge import wikidata_enabled
from api.wikipedia_knowledge import wikipedia_enabled
from api.wikibooks_knowledge import wikibooks_enabled


class TopicIn(BaseModel):
    topic: str


class QCChapterIn(BaseModel):
    outline: Dict
    chapter_id: str


class QCAnswerIn(BaseModel):
    subject: str
    chapter: Dict
    questions: List[Dict[str, str]]
    index: int = Field(..., ge=0)


class StudyAIIn(BaseModel):
    # v0 inputs
    topic: str = Field(..., description="User question/topic for the AI tutor")
    mode: str = Field("deep", description="deep | high | quiz | quiz_grade")

    # v0 continuation (optional; UI may wire later)
    continue_mode: bool = Field(False, description="If true, continue from previous_answer")
    previous_answer: Optional[str] = Field(None, description="Prior assistant answer to continue from")
    validation_feedback: List[str] = Field(
        default_factory=list,
        description="Structured-output defects to correct during one full regeneration",
    )
    profile_context: Dict[str, str] = Field(
        default_factory=dict,
        description="Canonical topic metadata shared by the Question Map and answer",
    )


def _warm_up_in_background() -> None:
    try:
        # Force a real LLM response so the model is ready
        generate_dynamic_answer(
            topic="Artificial Intelligence",
            topic_type="concept",
            archetype="ORIENT",
            question="What is artificial intelligence?",
            meta={"mode": "warmup"},
        )
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _warm_up_in_background()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "InI engine is alive"}


# @app.post("/interrogate")
# def interrogate_route(payload: TopicIn):
#     topic = (payload.topic or "").strip()

#     # Detect conversational intent
#     intent = detect_intent(topic)

#     # Only block interrogation for clearly conversational intents
#     conversational_intents = {"greeting", "thanks", "farewell", "help"}

#     if intent.get("intent") in conversational_intents:
#         return {
#             "topic": topic,
#             "topic_type": "intent",
#             "categories": {},
#             "summary": [],
#             "confidence": intent.get("confidence", 1.0),
#             "notes": ["v0: intent layer handled conversational input"],
#             "llm_used": False,
#             "intent": intent.get("intent"),
#             "reply": intent.get("reply", ""),
#             "followups": intent.get("followups", []),
#             "needs_clarification": False,
#         }

#     # Everything else should go through interrogation
#     return interrogate(topic)



@app.post("/interrogate")
def interrogate_route(payload: TopicIn):
    topic = (payload.topic or "").strip()
    return interrogate(topic)


@app.post("/qc/assess")
def qc_assess_route(payload: TopicIn):
    return assess_subject(payload.topic)


@app.post("/qc/outline")
def qc_outline_route(payload: TopicIn):
    return generate_subject_outline(payload.topic)


@app.post("/qc/chapter")
def qc_chapter_route(payload: QCChapterIn):
    try:
        return {"questions": generate_chapter_questions(payload.outline, payload.chapter_id)}
    except (KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/qc/answer")
def qc_answer_route(payload: QCAnswerIn):
    try:
        return {"answer": answer_curriculum_question(payload.subject, payload.chapter, payload.questions, payload.index)}
    except (KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/illustrate")
def illustrate_route(payload: TopicIn):
    return illustrate_logic(payload.topic)


@app.post("/resume")
def resume_route():
    return resume_logic()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "InI.ai",
        "version": "0.1",
        "components": ["interrogate", "illustrate", "resume", "study_ai", "wikidata", "wikipedia", "wikibooks"],
        "llm_enabled": llm_enabled(),
        "wikidata_enabled": wikidata_enabled(),
        "wikipedia_enabled": wikipedia_enabled(),
        "wikibooks_enabled": wikibooks_enabled(),
    }


@app.post("/study/ai")
def study_ai_route(payload: StudyAIIn):
    # Pass dict so study_ai can read mode + continuation fields
    return study_ai(payload.model_dump())

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

from api.interrogate import interrogate
from api.illustrate import illustrate as illustrate_logic
from api.resume import resume as resume_logic
from api.llm_answers import llm_enabled
from api.study_ai import study_ai
from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI


class TopicIn(BaseModel):
    topic: str


class StudyAIIn(BaseModel):
    # v0 inputs
    topic: str = Field(..., description="User question/topic for the AI tutor")
    mode: str = Field("deep", description="deep | high | quiz")

    # v0 continuation (optional; UI may wire later)
    continue_mode: bool = Field(False, description="If true, continue from previous_answer")
    previous_answer: Optional[str] = Field(None, description="Prior assistant answer to continue from")


from api.llm_answers import generate_dynamic_answer

def _warm_up_in_background() -> None:
    try:
        generate_dynamic_answer(
            topic="Artificial Intelligence",
            topic_type="concept",
            archetype="ORIENT",
            question="Warm up the model.",
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


@app.post("/interrogate")
def interrogate_route(payload: TopicIn):
    return interrogate(payload.topic)


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
        "components": ["interrogate", "illustrate", "resume", "study_ai"],
        "llm_enabled": llm_enabled(),
    }


@app.post("/study/ai")
def study_ai_route(payload: StudyAIIn):
    # Pass dict so study_ai can read mode + continuation fields
    return study_ai(payload.model_dump())
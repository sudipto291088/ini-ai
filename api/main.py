from fastapi import FastAPI
from pydantic import BaseModel
from api.interrogate import interrogate
from api.illustrate import illustrate as illustrate_logic
from api.resume import resume as resume_logic



app = FastAPI()

class TopicIn(BaseModel):
    topic: str

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
        "components": [
            "interrogate",
            "illustrate",
            "resume"
        ]
    }

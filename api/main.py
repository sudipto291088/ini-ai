from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TopicIn(BaseModel):
    topic: str

@app.get("/")
def root():
    return {"message": "InI engine is alive"}

@app.post("/interrogate")
def interrogate(payload: TopicIn):
    topic = payload.topic.strip()
    return {
        "topic": topic,
        "questions": [
            f"What is {topic}?",
            f"Why does {topic} matter?",
            f"How does {topic} work (at a high level)?"
        ]
    }

@app.post("/illustrate")
def illustrate(payload: TopicIn):
    topic = payload.topic.strip()
    return {
        "topic": topic,
        "examples": [
            f"Everyday example of {topic}: ...",
            f"Workplace example of {topic}: ...",
            f"Failure case (what happens without {topic}): ..."
        ]
    }

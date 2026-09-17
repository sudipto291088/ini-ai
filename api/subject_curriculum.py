"""Subject-scale learning, independent of the question-level Knowledge Map."""

import json
import re
from typing import Any

from api.llm_answers import generate_dynamic_answer_result


_LEARNING_START = re.compile(
    r"^\s*(?:(?:i\s+)?(?:want|would\s+like|wish|plan|need)\s+to\s+|"
    r"(?:can|could)\s+you\s+|please\s+)?"
    r"(?:learn|study|master|understand|teach\s+me|teach|take\s+me\s+through)\s+(.+?)\s*[.!?]*\s*$",
    re.IGNORECASE,
)


def learning_subject_candidate(text: str) -> str:
    """Only explicit learning requests can enter QC; a bare topic never can."""
    raw = (text or "").strip()
    if re.search(r"\b(?:do\s+not|don['’]t|not\s+interested)\b", raw, re.I):
        return ""
    match = _LEARNING_START.match(raw)
    if not match:
        return ""
    request = match.group(1).strip(" .?!")
    # A request for an introduction or a time-boxed plan is not a request to
    # traverse the entire field, even if it happens to name a broad subject.
    if re.match(r"^(?:about\s+)?the\s+basics\s+of\b", request, re.I):
        return ""
    if re.search(r"\b(?:in|over)\s+(?:a|one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:day|week|month)s?\b", request, re.I):
        return ""
    candidate = re.sub(
        r"^(?:about|all\s+of|everything\s+about|the\s+subject\s+of)\s+",
        "", request, flags=re.I,
    ).strip(" .?!")
    candidate = re.sub(r"\s+as\s+(?:an?\s+)?(?:entire\s+|whole\s+)?subject$", "", candidate, flags=re.I).strip()
    # A how/why/what question or a request to learn *how to do* one task is
    # not an entire subject, even when it contains the verb "learn".
    if not candidate or re.match(r"^(?:how|why|what|when|whether|to\s+)", candidate, re.I):
        return ""
    return candidate[:180]


def _json_result(subject: str, instruction: str, mode: str) -> dict[str, Any]:
    result = generate_dynamic_answer_result(
        topic=subject,
        topic_type="subject",
        archetype="SYSTEM",
        question=instruction,
        meta={"mode": mode, "expects": "json"},
        timeout_s=150,
    )
    raw = (result.get("answer") or "").strip()
    if result.get("error") or result.get("incomplete") or not raw:
        raise RuntimeError("Subject curriculum generation is unavailable or incomplete. Please try again.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("The generated curriculum was not valid structured data. Please retry.") from exc


def assess_subject(candidate: str) -> dict[str, Any]:
    data = _json_result(
        candidate,
        f"Assess whether '{candidate}' names an ENTIRE teachable subject/field, not a single "
        "topic, concept, method, task, question, or one chapter of a larger subject. "
        "Examples: Machine Learning and Operating Systems are subjects; gradient descent, "
        "regression, transformers, and CPU scheduling are topics. Ambiguous abbreviations "
        "or boundaries require clarification. Do not infer subject learning from a bare name. "
        "Return JSON only: {\"decision\":\"subject|topic|clarify\","
        "\"subject\":\"canonical name\",\"question\":\"one short clarification if needed\"}. ",
        "qc_subject_scope",
    )
    decision = str(data.get("decision") or "").lower()
    if decision not in {"subject", "topic", "clarify"}:
        raise ValueError("Subject scope could not be assessed reliably.")
    return {
        "decision": decision,
        "subject": str(data.get("subject") or candidate).strip()[:180],
        "question": str(data.get("question") or "").strip()[:250],
    }


def generate_subject_outline(subject: str) -> dict[str, Any]:
    data = _json_result(
        subject,
        f"Build a complete, coherent chapter outline for learning the ENTIRE subject '{subject}'. "
        "Determine chapters from the subject's natural knowledge structure; do not target a "
        "preset count. Include foundations, mechanisms, methods, applications, evaluation, "
        "limitations, and advanced areas where relevant. Order prerequisites before dependent "
        "chapters. Each chapter must have a distinct title and 2-6 concrete learning objectives. "
        "Return JSON only: {\"subject\":\"...\",\"chapters\":[{\"title\":\"...\","
        "\"objectives\":[\"...\"]}]}. No questions or answers yet.",
        "qc_outline",
    )
    raw_chapters = data.get("chapters")
    if not isinstance(raw_chapters, list) or len(raw_chapters) < 2:
        raise ValueError("The subject outline lacks a coherent chapter structure.")
    chapters = []
    seen = set()
    for index, item in enumerate(raw_chapters):
        if not isinstance(item, dict):
            raise ValueError("The subject outline contains an invalid chapter.")
        title = str(item.get("title") or "").strip()[:120]
        objectives = [str(value).strip()[:180] for value in (item.get("objectives") or []) if str(value).strip()]
        if not title or not objectives or title.casefold() in seen:
            raise ValueError("The subject outline has missing or duplicate chapter content.")
        seen.add(title.casefold())
        chapters.append({"id": f"chapter-{index + 1}", "title": title, "objectives": objectives, "questions": None})
    return {"version": 1, "subject": subject, "chapters": chapters}


def generate_chapter_questions(outline: dict[str, Any], chapter_id: str) -> list[dict[str, str]]:
    chapters = outline["chapters"]
    chapter = next((item for item in chapters if item["id"] == chapter_id), None)
    if not chapter:
        raise ValueError("Unknown curriculum chapter.")
    chapter_index = chapters.index(chapter)
    prior = [item["title"] for item in chapters[:chapter_index]]
    later = [item["title"] for item in chapters[chapter_index + 1:]]
    data = _json_result(
        outline["subject"],
        f"Create the COMPLETE pedagogically ordered QUESTION sequence for chapter '{chapter['title']}' "
        f"in the subject '{outline['subject']}'. Objectives: {json.dumps(chapter['objectives'])}. "
        f"Prior chapters: {json.dumps(prior)}. Later chapters: {json.dumps(later)}. "
        "Questions must cumulatively build understanding, not be independent FAQ entries. "
        "Cover every objective and its necessary foundations, mechanisms, relationships, "
        "applications, evaluation and limitations as appropriate. Let knowledge determine "
        "the number of questions: no fixed count or arbitrary cap. Do not duplicate another "
        "chapter. Audit sequence and coverage before returning. Every entry must be "
        "a distinct interrogative question ending in a question mark. Return JSON only: "
        "{\"questions\":[\"question 1?\",\"question 2?\",...]}. ",
        "qc_chapter_questions",
    )
    raw = data.get("questions")
    if not isinstance(raw, list) or not raw:
        raise ValueError("No usable chapter questions were generated.")
    questions = []
    seen = set()
    for item in raw:
        if isinstance(item, dict):
            item = item.get("question") or item.get("text") or ""
        if not isinstance(item, str):
            continue
        question = re.sub(r"^\s*(?:(?:\d+[.)]|[-*])\s+)", "", item).strip().strip('"“”')
        if not question or len(question) > 400:
            continue
        if not question.endswith("?"):
            if re.match(r"^(?:what|why|how|when|where|which|who|whom|whose|can|could|do|does|did|is|are|was|were|should|would|will|may|might)\b", question, re.I):
                question = question.rstrip(" .!:") + "?"
            else:
                continue
        key = re.sub(r"\s+", " ", question).casefold()
        if key in seen:
            continue
        seen.add(key)
        questions.append({"id": f"{chapter_id}-q{len(questions) + 1}", "text": question})
    if not questions:
        raise ValueError("No valid questions were generated for this chapter. Please retry.")
    return questions


def answer_curriculum_question(subject: str, chapter: dict[str, Any], questions: list[dict[str, str]], index: int) -> str:
    if not 0 <= index < len(questions):
        raise ValueError("Unknown curriculum question.")
    question = questions[index]["text"]
    previous = [item["text"] for item in questions[max(0, index - 3):index]]
    result = generate_dynamic_answer_result(
        topic=subject,
        topic_type="subject",
        archetype="MECHANISM",
        question=(
            f"You are teaching chapter '{chapter['title']}' of the Question Curriculum for "
            f"'{subject}'. The current question is: {question}\n"
            f"Earlier questions in this sequence: {json.dumps(previous)}.\n"
            "Answer THIS question directly and accurately. Build on earlier learning without "
            "repeating the whole curriculum. Keep the complete lesson to about 400-650 words; "
            "cover the specific concepts asked, explain important mechanisms and one useful "
            "example when appropriate, then end naturally. Do not generate a Knowledge Map "
            "or a new question list."
        ),
        meta={"mode": "qc_answer"},
        timeout_s=150,
    )
    answer = str(result.get("answer") or "").strip()
    if result.get("error") and not result.get("incomplete"):
        status = result.get("http_status")
        raise RuntimeError(f"The lesson service failed (HTTP {status}). Please retry." if status else "The lesson service failed. Please retry.")
    if result.get("incomplete"):
        reason = str(result.get("stop_reason") or "unknown")[:80]
        raise RuntimeError(f"The lesson stopped before completion ({reason}). Please retry.")
    if not answer:
        raise RuntimeError("The lesson returned no answer. Please retry.")
    return answer

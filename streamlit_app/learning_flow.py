"""Pure state helpers for the My New Learning conversation flow."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional


_QUIZ_PROMISE = re.compile(
    r"reply\s+with\s+your\s+answers\s+and\s+i\s+will\s+grade\s+you",
    flags=re.IGNORECASE,
)
_NUMBERED_ANSWER = re.compile(
    r"(?m)^\s*(\d{1,2})\s*[\).:\-]\s*\S+"
)


def is_quiz_response(message: Mapping[str, Any]) -> bool:
    """Return whether an assistant message is an unanswered generated quiz."""
    if str(message.get("role", "")).strip().lower() != "assistant":
        return False
    if str(message.get("mode", "")).strip().lower() != "quiz":
        return False
    return bool(_QUIZ_PROMISE.search(str(message.get("text", ""))))


def looks_like_quiz_answers(text: str, minimum_answers: int = 2) -> bool:
    """Recognize a numbered answer submission without relying on selected UI mode."""
    numbers = {int(value) for value in _NUMBERED_ANSWER.findall(text or "")}
    return len(numbers) >= minimum_answers


def find_active_quiz(
    messages: Iterable[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    """Return the latest assistant reply only when it is an ungraded quiz."""
    for message in reversed(list(messages)):
        role = str(message.get("role", "")).strip().lower()
        if role != "assistant":
            continue
        return message if is_quiz_response(message) else None
    return None


def resolve_learning_submission(
    messages: Iterable[Mapping[str, Any]],
    text: str,
    selected_mode: str,
) -> dict[str, Any]:
    """Route numbered replies to grading while preserving the visible Quiz mode."""
    mode = (selected_mode or "deep").strip().lower()
    active_quiz = find_active_quiz(messages)
    if active_quiz and looks_like_quiz_answers(text):
        return {
            "mode": "quiz_grade",
            "display_mode": "quiz",
            "previous_answer": str(active_quiz.get("text", "")).strip(),
            "quiz_root_id": active_quiz.get("id"),
        }
    return {
        "mode": mode,
        "display_mode": mode,
        "previous_answer": "",
        "quiz_root_id": None,
    }


def continuation_context(
    messages: Iterable[Mapping[str, Any]],
    message_id: str,
) -> str:
    """Return the complete answer chain for a continuation request."""
    materialized = list(messages)
    target = next(
        (message for message in materialized if message.get("id") == message_id),
        None,
    )
    if not target:
        return ""

    root_id = target.get("continued_root") or target.get("id")
    chunks: list[str] = []
    for message in materialized:
        if str(message.get("role", "")).strip().lower() != "assistant":
            continue
        candidate_root = message.get("continued_root") or message.get("id")
        if candidate_root != root_id:
            continue
        text = str(message.get("text", "")).strip()
        if text:
            chunks.append(text)
        if message.get("id") == message_id:
            break
    return "\n\n".join(chunks)


__all__ = [
    "continuation_context",
    "find_active_quiz",
    "is_quiz_response",
    "looks_like_quiz_answers",
    "resolve_learning_submission",
]

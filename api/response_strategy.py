"""Conversational-first response strategy built on InI's existing intent output.

This module does not classify user intent independently.  It receives the
result of the established intent/interrogation pipeline and decides only how
much of the already-available learning structure should be surfaced.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


NO_KS = "NO_KS"
CONDITIONAL_KS = "CONDITIONAL_KS"
KS_RECOMMENDED = "KS_RECOMMENDED"
KS_EXPLICIT = "KS_EXPLICIT"


_EXPLICIT_KS = re.compile(
    r"\b(?:show|open|display|reveal|give|render)\b.{0,40}"
    r"\b(?:complete|full|entire)?\s*(?:knowledge structure|ks)\b|"
    r"\bshow\s+me\s+everything\s+about\b",
    re.IGNORECASE,
)


def is_explicit_knowledge_structure_request(query: str) -> bool:
    """Return True only when the learner directly asks to reveal the KS."""
    text = query or ""
    if re.search(
        r"\b(?:do not|don['\u2019]?t|not|no|without)\b.{0,48}"
        r"\b(?:knowledge structure|ks)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return bool(_EXPLICIT_KS.search(text))


def extract_knowledge_structure_topic(query: str) -> str:
    """Extract the learning subject from an explicit KS command."""

    text = re.sub(r"\s+", " ", (query or "").strip())
    patterns = (
        r"^(?:please\s+)?(?:show|open|display|reveal|give|render)(?:\s+me)?\s+"
        r"(?:the\s+)?(?:complete\s+|full\s+|entire\s+)?"
        r"(?:knowledge structure|ks)(?:\s+(?:for|of|about))?\s+",
        r"^(?:please\s+)?show\s+me\s+everything\s+about\s+",
    )
    for pattern in patterns:
        candidate = re.sub(pattern, "", text, flags=re.IGNORECASE).strip(" .?!:;-")
        if candidate != text.strip(" .?!:;-"):
            return candidate
    return ""


def assess_ks_suitability(
    query: str,
    classified: Mapping[str, Any] | None = None,
) -> str:
    """Map existing classification output to a KS presentation decision."""

    if is_explicit_knowledge_structure_request(query):
        return KS_EXPLICIT

    info = classified or {}
    response_mode = str(info.get("response_mode") or "").casefold()
    intent = str(info.get("intent") or "").casefold()
    if response_mode in {"conversation", "carm"} or intent in {
        "greeting", "thanks", "farewell", "smalltalk", "clarify",
        "self_introduction", "affirmation", "negative",
    }:
        return NO_KS

    normalized = re.sub(r"\s+", " ", (query or "").casefold()).strip()
    broad_learning = bool(
        re.search(
            r"\b(?:teach me|learn (?:all|everything)|everything about|"
            r"understand .{0,50} deeply|complete guide|comprehensive|"
            r"research|from scratch|in depth|deep dive)\b",
            normalized,
        )
    )
    compound = bool(
        len(re.findall(r"\b(?:and|also|as well as|when|while)\b", normalized)) >= 2
        or normalized.count("?") >= 2
    )
    if broad_learning or compound:
        return KS_RECOMMENDED

    if info.get("categories"):
        return CONDITIONAL_KS
    return NO_KS


def select_lightweight_questions(
    query: str,
    categories: Mapping[str, Any] | None,
    limit: int = 3,
) -> list[str]:
    """Select a small, diverse set from the existing Question Map.

    At most one question is taken from a category during the first pass so the
    visible suggestions represent distinct intellectual directions.
    """

    if not isinstance(categories, Mapping) or limit <= 0:
        return []

    normalized = (query or "").casefold()
    if re.match(r"\s*how\b", normalized):
        preferred = ["Mechanisms", "Methods & Tools", "Foundations", "Applications", "Pitfalls"]
    elif re.match(r"\s*why\b", normalized):
        preferred = ["Foundations", "Mechanisms", "Pitfalls", "Applications", "Advanced / Future"]
    elif re.search(r"\b(?:compare|difference|versus|vs\.?|better)\b", normalized):
        preferred = ["Foundations", "Applications", "Pitfalls", "Mechanisms", "Advanced / Future"]
    else:
        preferred = ["Foundations", "Mechanisms", "Applications", "Pitfalls", "Advanced / Future", "Orientation"]

    def question_text(item: Any) -> str:
        if isinstance(item, Mapping):
            return str(item.get("question") or "").strip()
        return str(item or "").strip()

    selected: list[str] = []
    seen: set[str] = set()
    for category in preferred:
        for item in categories.get(category) or []:
            question = question_text(item)
            key = re.sub(r"[^a-z0-9]+", " ", question.casefold()).strip()
            if not question or not key or key in seen:
                continue
            selected.append(question)
            seen.add(key)
            break
        if len(selected) >= limit:
            return selected

    return selected


__all__ = [
    "NO_KS",
    "CONDITIONAL_KS",
    "KS_RECOMMENDED",
    "KS_EXPLICIT",
    "assess_ks_suitability",
    "extract_knowledge_structure_topic",
    "is_explicit_knowledge_structure_request",
    "select_lightweight_questions",
]

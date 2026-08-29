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
RESPONSE_STRATEGY_VERSION = 3


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


def question_intelligence_limit(query: str) -> int:
    """Choose a useful 3, 6, or 9-question budget for a substantive query."""

    normalized = re.sub(r"\s+", " ", (query or "").casefold()).strip()
    words = re.findall(r"[a-z0-9]+", normalized)
    deep_cue = bool(
        re.search(
            r"\b(?:from scratch|in depth|deep dive|comprehensive|research|"
            r"advanced|end-to-end|step by step|scientific and ethical|"
            r"compare and contrast)\b",
            normalized,
        )
    )
    clause_count = len(
        re.findall(r"(?:[,;:]|\b(?:and|also|as well as|while|whereas)\b)", normalized)
    )
    if deep_cue or normalized.count("?") >= 2 or (len(words) >= 16 and clause_count >= 2):
        return 9

    simple_definition = bool(
        len(words) <= 7
        and re.match(r"^(?:what is|what are|define|explain)\b", normalized)
        and clause_count == 0
    )
    if simple_definition:
        return 3
    return 6


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
        preferred = [
            "Mechanisms", "Methods & Tools", "Foundations", "Applications",
            "Pitfalls", "Orientation", "Advanced / Future",
        ]
    elif re.match(r"\s*why\b", normalized):
        preferred = [
            "Foundations", "Mechanisms", "Pitfalls", "Applications",
            "Methods & Tools", "Orientation", "Advanced / Future",
        ]
    elif re.search(r"\b(?:compare|difference|versus|vs\.?|better)\b", normalized):
        preferred = [
            "Foundations", "Applications", "Pitfalls", "Mechanisms",
            "Methods & Tools", "Orientation", "Advanced / Future",
        ]
    else:
        preferred = [
            "Foundations", "Mechanisms", "Applications", "Pitfalls",
            "Methods & Tools", "Advanced / Future", "Orientation",
        ]

    def question_text(item: Any) -> str:
        if isinstance(item, Mapping):
            return str(item.get("question") or "").strip()
        return str(item or "").strip()

    selected: list[str] = []
    seen: set[str] = set()

    # Compound questions often name dimensions that should not disappear from
    # the visible suggestions. Pull one strong candidate for each named
    # dimension before filling from the normal category order.
    dimension_terms: list[tuple[str, ...]] = []
    if re.search(r"\b(?:ethical|ethics|moral|consent|equity|fairness)\b", normalized):
        dimension_terms.append(
            ("ethical", "ethics", "moral", "consent", "equity", "fairness", "governance")
        )
    if re.search(r"\b(?:limitation|limitations|risk|risks|safety|scientific)\b", normalized):
        dimension_terms.append(
            ("limitation", "risk", "safety", "off-target", "delivery", "immune", "uncertainty")
        )

    all_candidates: list[tuple[str, str]] = []
    for category, items in categories.items():
        for item in items or []:
            question = question_text(item)
            if question:
                all_candidates.append((str(category), question))

    used_categories: set[str] = set()
    for terms in dimension_terms:
        match = next(
            (
                (category, question)
                for category, question in all_candidates
                if any(term in question.casefold() for term in terms)
                and re.sub(r"[^a-z0-9]+", " ", question.casefold()).strip() not in seen
            ),
            None,
        )
        if match:
            category, question = match
            selected.append(question)
            seen.add(re.sub(r"[^a-z0-9]+", " ", question.casefold()).strip())
            used_categories.add(category)

    for category in preferred:
        if category in used_categories:
            continue
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

    # Six categories provide the broad first tier. A genuinely deep topic may
    # earn questions 7–9 from the strongest remaining category candidates.
    for category in preferred:
        for item in categories.get(category) or []:
            question = question_text(item)
            key = re.sub(r"[^a-z0-9]+", " ", question.casefold()).strip()
            if not question or not key or key in seen:
                continue
            selected.append(question)
            seen.add(key)
            if len(selected) >= limit:
                return selected

    return selected


def fallback_learning_questions(query: str, limit: int = 6) -> list[str]:
    """Provide stable, diverse next directions when map generation is unavailable."""

    normalized = (query or "").casefold()
    questions: list[str] = []
    if re.search(r"\b(?:ethical|ethics|moral)\b", normalized):
        questions.append(
            "What ethical boundaries, consent concerns, and questions of fairness shape this topic?"
        )
    if re.search(r"\b(?:limitation|limitations|risk|risks|safety|scientific)\b", normalized):
        questions.append(
            "What scientific limitations, safety risks, and unresolved uncertainties matter most?"
        )
    if re.match(r"\s*why\b", normalized):
        questions.insert(0, "What underlying mechanisms and competing causes explain this?")
    elif re.match(r"\s*how\b", normalized):
        questions.insert(0, "How does the central mechanism work step by step?")
    else:
        questions.insert(0, "What are the foundational ideas needed to understand this clearly?")

    general = (
        "How does this appear in a concrete real-world example?",
        "What trade-offs, exceptions, or common misconceptions should be considered?",
        "How do researchers or practitioners evaluate whether it works as intended?",
        "Which assumptions does this explanation depend on?",
        "How does this relate to neighboring ideas or competing approaches?",
        "What evidence would strengthen or weaken the main claims?",
        "What consequences follow when this mechanism succeeds or fails?",
        "Which advanced or unresolved questions offer the most valuable next step?",
    )
    for question in general:
        if len(questions) >= limit:
            break
        if question not in questions:
            questions.append(question)
    return questions[:limit]


__all__ = [
    "NO_KS",
    "CONDITIONAL_KS",
    "KS_RECOMMENDED",
    "KS_EXPLICIT",
    "RESPONSE_STRATEGY_VERSION",
    "assess_ks_suitability",
    "extract_knowledge_structure_topic",
    "fallback_learning_questions",
    "is_explicit_knowledge_structure_request",
    "question_intelligence_limit",
    "select_lightweight_questions",
]

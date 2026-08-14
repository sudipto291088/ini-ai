"""Select the Question Map item that most directly answers a specific query."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Any, Mapping, Optional


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does",
    "for", "from", "how", "in", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "this", "to", "what", "when", "where",
    "which", "who", "why", "with",
}

_SPECIFIC_SIGNALS = re.compile(
    r"^(?:how|why|when|where|which|should)\b|"
    r"\b(?:compare|difference|different|relate|relationship|cause|causes|"
    r"advantages?|limitations?|pitfalls?|applications?|uses?|used|"
    r"prevent|prevented|avoid|avoided|mitigate|mitigated|main types?|classifications?|"
    r"when should|how should)\b",
    re.IGNORECASE,
)

_SPECIALIZATION_TERMS = {
    "automatic differentiation", "batch norm", "bptt", "convolutional",
    "frameworks", "recurrent", "reverse mode", "truncating",
}

FOCUS_MATCHER_VERSION = 6


@dataclass(frozen=True)
class DirectAnswerMatch:
    section: str
    question: str
    score: float
    part_index: int = 1
    total_parts: int = 1


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _normalized(text).split()
        if len(token) > 2 and token not in _STOP_WORDS
    }


def _intent_terms(text: str) -> set[str]:
    """Collapse common question wording into the learning intent it expresses."""
    normalized = _normalized(text)
    intents: set[str] = set()
    families = {
        "cause": ("why", "cause", "causes", "occur", "happen", "arise"),
        "prevention": (
            "prevent", "prevented", "avoid", "avoided", "mitigate", "mitigated",
            "reduce", "fix", "remedy", "address",
        ),
        "application": ("application", "applications", "use", "used", "uses", "real world"),
        "classification": ("type", "types", "classification", "classifications", "kinds"),
        "selection": ("when", "choose", "chosen", "select", "appropriate"),
        "decision": ("should", "adopt", "decision", "decide", "whether"),
        "mechanism": ("how", "work", "works", "working", "mechanism", "compute", "process"),
    }
    words = set(normalized.split())
    for intent, cues in families.items():
        if any((cue in words if " " not in cue else cue in normalized) for cue in cues):
            intents.add(intent)
    return intents


def is_specific_learning_question(prompt: str) -> bool:
    """Exclude bare subjects and ordinary definition-only prompts."""
    clean = re.sub(r"\s+", " ", (prompt or "").strip())
    normalized = _normalized(clean)
    if not normalized:
        return False

    if _SPECIFIC_SIGNALS.search(normalized):
        return True

    if "?" not in clean:
        return False

    return len(_query_parts(clean)) > 1


def _query_parts(prompt: str) -> list[str]:
    """Split explicit compound questions without fragmenting ordinary prose."""
    clean = re.sub(r"\s+", " ", (prompt or "").strip()).strip(" ?")
    if not clean:
        return []
    marked = re.sub(
        r"[,;]\s*(?:and\s+)?(?=(?:what|how|why|when|where|which)\b)",
        " ||| ",
        clean,
        flags=re.IGNORECASE,
    )
    marked = re.sub(
        r"\s+(?:and|also|then)\s+(?=(?:what|how|why|when|where|which)\b)",
        " ||| ",
        marked,
        flags=re.IGNORECASE,
    )
    parts = [part.strip(" ,;?") for part in marked.split("|||") if part.strip(" ,;?")]
    return parts if len(parts) > 1 else [clean]


def _find_best_match(
    prompt: str,
    categories: Mapping[str, Any],
    excluded_questions: set[str],
) -> Optional[DirectAnswerMatch]:
    prompt_norm = _normalized(prompt)
    prompt_tokens = _tokens(prompt)
    if not prompt_tokens:
        return None


    prompt_signals = {
        signal
        for signal in (
            "how", "why", "when", "where", "compare", "difference",
            "types", "classification", "relate", "relationship", "cause",
            "advantages", "limitations", "pitfalls",
        )
        if signal in prompt_norm
    }
    prompt_intents = _intent_terms(prompt)
    asks_application = bool(
        re.match(r"^how\s+(?:does|do|is|are|can)\b", prompt_norm)
        and re.search(r"\b(?:use|used|uses|apply|applied|application|applications)\b", prompt_norm)
    )
    asks_how_mechanism = bool(
        re.match(r"^how\s+(?:does|do|is|are|can)\b", prompt_norm)
        and not asks_application
    )
    asks_how_mechanism = asks_how_mechanism and not bool(
        prompt_intents & {"application", "prevention", "selection"}
    )
    preferred_sections: set[str] = set()
    if asks_application:
        preferred_sections.add("applications")
    elif prompt_norm.startswith("how "):
        preferred_sections.update({"mechanisms", "methods & tools"})
    if prompt_norm.startswith("why ") or " cause" in prompt_norm:
        preferred_sections.update({"mechanisms", "pitfalls"})
    if prompt_norm.startswith("when ") or "when should" in prompt_norm:
        preferred_sections.update({"methods & tools", "applications"})
    if "compare" in prompt_norm or "difference" in prompt_norm:
        preferred_sections.update({"foundations", "methods & tools"})
    if prompt_norm.startswith("what is "):
        preferred_sections.add("orientation")
    if "types" in prompt_norm or "classification" in prompt_norm:
        preferred_sections.update({"orientation", "foundations"})
    if "relate" in prompt_norm or "relationship" in prompt_norm:
        preferred_sections.update({"foundations", "applications"})
    if "prevention" in prompt_intents:
        preferred_sections.update({"methods & tools", "pitfalls"})
    if "application" in prompt_intents:
        preferred_sections.add("applications")
    if "decision" in prompt_intents:
        preferred_sections.update({"applications", "pitfalls"})

    best: Optional[DirectAnswerMatch] = None
    for section, items in categories.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            question = re.sub(r"\s+", " ", str(item.get("question") or "")).strip()
            if not question or question in excluded_questions:
                continue

            question_norm = _normalized(question)
            question_tokens = _tokens(question)
            if not question_tokens:
                continue
            overlap = prompt_tokens & question_tokens
            prompt_coverage = len(overlap) / len(prompt_tokens)
            question_coverage = len(overlap) / len(question_tokens)
            sequence = SequenceMatcher(None, prompt_norm, question_norm).ratio()
            signal_bonus = 0.0
            if any(signal in question_norm for signal in prompt_signals):
                signal_bonus = 0.12
            question_intents = _intent_terms(question)
            intent_overlap = prompt_intents & question_intents
            intent_bonus = min(0.36, 0.18 * len(intent_overlap))
            missing_intent_penalty = min(
                0.36,
                0.18 * len(prompt_intents - question_intents),
            )
            section_name = str(section).lower()
            section_intent_bonus = 0.0
            section_intent_penalty = 0.0
            if "cause" in prompt_intents and section_name == "mechanisms":
                section_intent_bonus += 0.34
            if "prevention" in prompt_intents and section_name in {
                "methods & tools", "pitfalls"
            }:
                section_intent_bonus += 0.34
            if "application" in prompt_intents and section_name == "applications":
                section_intent_bonus += 0.34
            if "decision" in prompt_intents and section_name in {
                "applications", "pitfalls"
            }:
                section_intent_bonus += 0.34
            if prompt_intents & {"cause", "prevention", "application", "selection"}:
                if section_name == "orientation":
                    section_intent_penalty += 0.32
            section_bonus = 0.18 if str(section).lower() in preferred_sections else 0.0
            core_mechanism_bonus = 0.0
            if asks_how_mechanism:
                if any(
                    phrase in question_norm
                    for phrase in ("step by step", "simple feedforward", "flow of gradients", "chain rule")
                ):
                    core_mechanism_bonus = 0.24
                elif any(
                    phrase in question_norm
                    for phrase in ("how does", "how do", "mechanism", "compute", "propagate")
                ):
                    core_mechanism_bonus = 0.14
            intent_mismatch_penalty = 0.0
            if asks_how_mechanism and question_norm.startswith(("what is ", "what are ")):
                intent_mismatch_penalty = 0.46
            if asks_how_mechanism and str(section).lower() == "orientation":
                intent_mismatch_penalty += 0.18
            specialization_penalty = 0.0
            for term in _SPECIALIZATION_TERMS:
                if term in question_norm and term not in prompt_norm:
                    specialization_penalty += 0.10

            score = (
                (0.46 * prompt_coverage)
                + (0.34 * question_coverage)
                + (0.20 * sequence)
                + signal_bonus
                + intent_bonus
                + section_intent_bonus
                + section_bonus
                + core_mechanism_bonus
                - intent_mismatch_penalty
                - missing_intent_penalty
                - section_intent_penalty
                - min(specialization_penalty, 0.34)
            )
            candidate = DirectAnswerMatch(str(section), question, score)
            if best is None or candidate.score > best.score:
                best = candidate

    return best if best and best.score >= 0.22 else None


def find_direct_answer_matches(
    prompt: str,
    categories: Mapping[str, Any],
) -> list[DirectAnswerMatch]:
    """Return one unique direct-answer match per substantive query part."""
    if not is_specific_learning_question(prompt) or not isinstance(categories, Mapping):
        return []

    parts = _query_parts(prompt)
    selected: list[DirectAnswerMatch] = []
    excluded: set[str] = set()
    for part in parts:
        match = _find_best_match(part, categories, excluded)
        if match:
            selected.append(match)
            excluded.add(match.question)

    total = len(selected)
    return [
        DirectAnswerMatch(
            match.section,
            match.question,
            match.score,
            part_index=index,
            total_parts=total,
        )
        for index, match in enumerate(selected, start=1)
    ]


def find_direct_answer_match(
    prompt: str,
    categories: Mapping[str, Any],
) -> Optional[DirectAnswerMatch]:
    """Backward-compatible accessor for the first direct-answer match."""
    matches = find_direct_answer_matches(prompt, categories)
    return matches[0] if matches else None


__all__ = [
    "DirectAnswerMatch",
    "find_direct_answer_match",
    "find_direct_answer_matches",
    "is_specific_learning_question",
]

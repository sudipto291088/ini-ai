"""Deterministic interpretation of a user's conversational turn.

The raw utterance is kept for history.  ``semantic_text`` is the same turn
with harmless discourse markers removed so downstream topic generation does
not mistake acknowledgements for part of the subject.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


CONVERSATION_INTERPRETER_VERSION = 5


_ACK_ONLY = re.compile(
    r"^(?:yes|yeah|yea|yep|yup|ok|okay|sure|right|correct|exactly|"
    r"alright|all\s+right|go\s+ahead|do\s+it|please|continue|proceed)$",
    re.IGNORECASE,
)
_DENIAL_ONLY = re.compile(
    r"^(?:no|nope|nah|not\s+that|incorrect|neither|cancel|stop)$",
    re.IGNORECASE,
)
_LEADING_DISCOURSE = re.compile(
    r"^(?:(?:yes|yeah|yea|yep|yup|ok|okay|sure|right|alright|all\s+right|"
    r"well|so|actually|please|fine|great|cool|then)\b[\s,;:!.\-]*)+",
    re.IGNORECASE,
)
_CORRECTION_PREFIX = re.compile(
    r"^(?:i\s+mean|i\s+meant|what\s+i\s+mean\s+is|rather)\b[\s,;:!.\-]*",
    re.IGNORECASE,
)
_TOPIC_SWITCH_PREFIX = re.compile(
    r"^(?:switch|change|move|moving)\s+(?:the\s+)?topics?\b[\s,;:!.\-]*",
    re.IGNORECASE,
)
_TRAILING_REPAIR = re.compile(
    r"[\s,;:!.\-\u2013\u2014]+(?:sorry|my\s+bad|apologies|pardon\s+me|excuse\s+me)"
    r"[\s.!?]*$",
    re.IGNORECASE,
)
_AMBIGUOUS_FOLLOWUPS = {
    "what else",
    "so what else",
    "anything else",
    "tell me more",
    "what more",
    "go on",
}


@dataclass(frozen=True)
class ConversationTurn:
    raw_text: str
    normalized_text: str
    semantic_text: str
    is_confirmation: bool
    is_denial: bool
    is_ambiguous_followup: bool
    has_substantive_text: bool


def _normalized(text: str) -> str:
    value = re.sub(r"\s+", " ", (text or "").strip())
    return re.sub(r"[!?.,;:]+$", "", value).strip().lower()


def interpret_turn(text: str) -> ConversationTurn:
    """Interpret one turn without guessing the user's topic or intent."""
    raw = re.sub(r"\s+", " ", (text or "").strip())
    normalized = _normalized(raw)
    confirmation = bool(_ACK_ONLY.fullmatch(normalized))
    denial = bool(_DENIAL_ONLY.fullmatch(normalized))

    semantic = raw
    if not confirmation and not denial:
        semantic = _LEADING_DISCOURSE.sub("", semantic).strip()
        semantic = _TOPIC_SWITCH_PREFIX.sub("", semantic).strip()
        semantic = _CORRECTION_PREFIX.sub("", semantic).strip()
        semantic = _TRAILING_REPAIR.sub("", semantic).strip()
        semantic = re.sub(r"\s+", " ", semantic)
        semantic = semantic or raw

    semantic_normalized = _normalized(semantic)
    return ConversationTurn(
        raw_text=raw,
        normalized_text=normalized,
        semantic_text=semantic,
        is_confirmation=confirmation,
        is_denial=denial,
        is_ambiguous_followup=normalized in _AMBIGUOUS_FOLLOWUPS,
        has_substantive_text=bool(semantic_normalized) and not confirmation and not denial,
    )


def should_preserve_conversation_context(
    *,
    user_text: str,
    prior_response_mode: str,
    study_mode_established: bool,
    requests_learning_map: bool,
    explicit_question_map_request: bool,
) -> bool:
    """Keep established casual conversation active across ordinary turns."""
    normalized = _normalized(user_text)
    explicit_learning_language = bool(
        re.search(
            r"\b(?:teach|explain|define|study|learn|understand|"
            r"walk me through|question map|qmap)\b",
            normalized,
        )
        or re.search(
            r"^(?:switch|change|move|moving)\s+(?:the\s+)?topics?\b",
            normalized,
        )
        or re.search(
            r"^(?:what|why)\s+(?:is|are|was|were)\s+"
            r"(?!(?:you|your|this|that|it|everything|anything|going)\b)",
            normalized,
        )
        or re.search(
            r"^how\s+(?:does|do|can)\s+"
            r"(?!(?:you|we|i|this|that|it)\b)",
            normalized,
        )
    )
    conversational_reference = bool(
        re.search(
            r"\b(?:i|im|me|my|mine|you|your|yours|we|our|ours|"
            r"this|that|it|something|anything|everything)\b",
            normalized,
        )
    )
    conversational_sentence = bool(
        re.search(
            r"\b(?:am|is|are|was|were|has|have|had|been|feel|feels|felt|"
            r"seem|seems|seemed|forgot|lost|found|went|came|made|liked|"
            r"loved|hated|enjoyed)\b",
            normalized,
        )
        or re.search(
            r"^(?:sometimes|often|usually|occasionally|recently|lately|"
            r"today|tonight|yesterday|this morning|this afternoon|this evening)\b",
            normalized,
        )
    )
    clear_learning_transition = bool(
        requests_learning_map
        and (
            explicit_learning_language
            or (not conversational_reference and not conversational_sentence)
        )
    )
    return bool(
        str(prior_response_mode or "").casefold() == "conversation"
        and not study_mode_established
        and not clear_learning_transition
        and not explicit_question_map_request
    )


def ensure_honest_ai_voice(user_text: str, reply: str) -> str:
    """Label invented first-person anecdotes instead of presenting them as memories."""
    text = (reply or "").strip()
    if not text:
        return text

    asks_for_story = bool(
        re.search(r"\b(?:story|anecdote|memory|something that happened)\b", user_text or "", re.I)
    )
    claims_personal_history = bool(
        re.search(
            r"\b(?:once|yesterday|last (?:night|week|month|year)|when I was)\s+I\b|"
            r"\bI\s+(?:once|was|did|remember|recalled|grew up|went|visited|met|tried|used to|had)\b",
            text,
            re.I,
        )
    )
    if asks_for_story and claims_personal_history:
        return (
            "I don't have personal experiences or memories, but here is a fictional story:\n\n"
            + text
        )
    return text


__all__ = [
    "CONVERSATION_INTERPRETER_VERSION",
    "ConversationTurn",
    "interpret_turn",
    "should_preserve_conversation_context",
    "ensure_honest_ai_voice",
]

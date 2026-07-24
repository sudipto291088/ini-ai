"""Deterministic interpretation of a user's conversational turn.

The raw utterance is kept for history.  ``semantic_text`` is the same turn
with harmless discourse markers removed so downstream topic generation does
not mistake acknowledgements for part of the subject.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


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


__all__ = ["ConversationTurn", "interpret_turn"]

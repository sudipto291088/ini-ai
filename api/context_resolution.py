"""Conservative context-aware correction for short learning-topic queries."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Optional


_CONTEXT_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "for", "from", "in", "is",
    "it", "of", "on", "or", "the", "this", "to", "with", "you", "your",
}


def should_continue_practical_context(
    query: str,
    *,
    original_request: str = "",
    resolved_request: str = "",
    last_answer: str = "",
) -> bool:
    """Return True only when a short turn is evidenced as a CARM follow-up."""
    raw = (query or "").strip()
    words = re.findall(r"[A-Za-z0-9+#.-]+", raw)
    if not 0 < len(words) <= 14:
        return False

    if re.match(
        r"^(what|who|why|when|where|how|explain|teach|compare|define|tell me|new topic)\b",
        raw,
        flags=re.IGNORECASE,
    ) or "?" in raw:
        return False

    normalized = re.sub(r"[^a-z0-9 ]+", " ", raw.lower()).strip()
    if re.match(
        r"^(?:yes|yeah|yep|no|nope|okay|ok|sure|maybe|probably|"
        r"i don t know|i do not know|not sure|go ahead|continue|do it)\b",
        normalized,
    ):
        return True

    context = " ".join(
        part for part in (original_request, resolved_request, last_answer) if part
    )
    query_terms = {
        token for token in _normalized_tokens(raw) if token not in _CONTEXT_STOPWORDS
    }
    context_terms = {
        token for token in _normalized_tokens(context) if token not in _CONTEXT_STOPWORDS
    }
    if query_terms & context_terms:
        return True

    return len(words) == 1 and "?" in (last_answer or "")


def _normalized_tokens(text: str) -> list[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
    return [token for token in normalized.split() if token]


def find_contextual_topic_match(
    query: str,
    candidates: Iterable[str],
) -> Optional[dict[str, object]]:
    """Return one strong, unambiguous near-match from the active topic context.

    Exact matches are ignored because they need no correction. The deliberately
    conservative thresholds prevent unrelated topics with one common word from
    being treated as corrections.
    """
    query_tokens = _normalized_tokens(query)
    if not 2 <= len(query_tokens) <= 6:
        return None

    query_normalized = " ".join(query_tokens)
    scored: list[tuple[float, str]] = []

    for candidate in candidates:
        candidate_text = str(candidate or "").strip()
        candidate_tokens = _normalized_tokens(candidate_text)
        if not 2 <= len(candidate_tokens) <= 6:
            continue

        candidate_normalized = " ".join(candidate_tokens)
        if candidate_normalized == query_normalized:
            continue

        # A longer query that contains the complete active topic is normally a
        # more specific subject, not a typo. For example, "quantum artificial
        # intelligence" and "sovereign artificial intelligence" must not be
        # collapsed back to "artificial intelligence".
        if (
            len(query_tokens) > len(candidate_tokens)
            and set(candidate_tokens).issubset(query_tokens)
        ):
            continue

        shared_tokens = len(set(query_tokens) & set(candidate_tokens))
        required_shared = max(1, min(len(query_tokens), len(candidate_tokens)) - 1)
        if shared_tokens < required_shared:
            continue

        score = SequenceMatcher(None, query_normalized, candidate_normalized).ratio()
        if score >= 0.72:
            scored.append((score, candidate_text))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_candidate = scored[0]
    if best_score < 0.82:
        return None
    if len(scored) > 1 and best_score - scored[1][0] < 0.08:
        return None

    return {
        "candidate": best_candidate,
        "confidence": round(best_score, 3),
    }

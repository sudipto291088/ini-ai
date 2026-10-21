"""Exact, conservative meaning checks for bare ambiguous abbreviations."""
import re

AMBIGUOUS_ABBREVIATIONS = {
    "ml": ("machine learning", "maximum likelihood", "millilitres"),
    "ai": ("artificial intelligence", "artificial insemination"),
    "os": ("an operating system", "another meaning"),
    "cv": ("computer vision", "a curriculum vitae", "cross-validation"),
    "rl": ("reinforcement learning", "something else"),
}


def clarification_choices(text: str) -> tuple[str, ...]:
    token = re.sub(r"[.?!]+$", "", str(text or "").strip()).strip().casefold()
    meanings = AMBIGUOUS_ABBREVIATIONS.get(token, ())
    return tuple(re.sub(r"^(?:an?|the) ", "", meaning).capitalize()
                 for meaning in meanings if meaning not in {"another meaning", "something else"})


def abbreviation_clarification(text: str) -> str:
    raw = str(text or "").strip()
    token = re.sub(r"[.?!]+$", "", raw).strip().casefold()
    meanings = AMBIGUOUS_ABBREVIATIONS.get(token)
    if not meanings:
        return ""
    options = ", ".join(meanings[:-1]) + " or " + meanings[-1]
    return f'By “{raw.rstrip(".?!")}”, do you mean {options}? Choose a meaning below, or write the full term.'

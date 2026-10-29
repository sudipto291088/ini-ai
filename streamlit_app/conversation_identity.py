"""Conservative self-introduction parsing; never an authentication signal."""
import re


_NON_NAMES = {
    "only", "just", "checking", "testing", "trying", "ready", "fine", "okay", "ok",
    "here", "back", "done", "tired", "happy", "sad", "going", "working", "learning",
    "asking", "wondering", "not", "very", "really", "good", "interested", "from",
}
_ROLES = {
    "founder", "cofounder", "co-founder", "creator", "developer", "engineer", "teacher",
    "student", "researcher", "owner", "administrator", "admin", "manager", "designer",
    "doctor", "scientist", "programmer", "learner", "ceo",
}


def parse_self_introduction(text: str) -> dict[str, str]:
    normalized = re.sub(r"\bi['’]m\b", "i am", str(text or ""), flags=re.I)
    normalized = re.sub(r"\s+", " ", normalized).strip().rstrip(".! ")
    match = re.fullmatch(r"(i am|im|my name is|you can call me|call me)\s+([a-z][a-z0-9 '-]{0,60})",
                         normalized, re.I)
    if not match:
        return {}
    prefix, value = match.groups()
    words = value.casefold().split()
    if not 1 <= len(words) <= 4 or set(words) & _NON_NAMES:
        return {}
    # Articles and possessives introduce descriptions, not personal names.
    descriptive = words[0] in {"a", "an", "the", "your", "my", "our"}
    implicit_role = prefix.casefold() in {"i am", "im"} and bool(set(words) & _ROLES)
    if descriptive or implicit_role:
        return {"kind": "role", "value": " ".join(words)}
    return {"kind": "name", "value": " ".join(part.capitalize() for part in value.split())}


def role_acknowledgement(value: str) -> str:
    """Acknowledge a claim without verifying it or granting privileges."""
    if value in {"your founder", "your creator", "your owner"}:
        role = value.split()[-1]
        return f"Got it—you’re telling me you’re InI’s {role}."
    return f"Got it—you’re describing yourself as {value}."

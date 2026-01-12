# api/illustrate.py

from __future__ import annotations

from typing import Dict, List


def illustrate(topic: str) -> Dict[str, object]:
    """
    Return structured illustrations/examples for a topic.
    v0 intelligence: templates + consistent example types.
    """
    t = " ".join(topic.strip().split())
    if not t:
        return {"topic": topic, "examples": [], "notes": ["Empty topic received."]}

    examples: List[str] = [
        f"Everyday example of {t}: (a simple real-life situation where {t} shows up).",
        f"Work/industry example of {t}: (how a professional uses {t} at work).",
        f"Failure case without {t}: (what goes wrong if {t} is ignored).",
        f"Analogy for {t}: (compare {t} to something familiar).",
    ]

    notes = [
        "v0: template-based illustration (no external knowledge yet).",
        "Next: generate examples based on topic-type (concept/skill/decision/problem).",
    ]

    return {"topic": t, "examples": examples, "notes": notes}

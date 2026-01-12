# api/interrogate.py

from __future__ import annotations

from typing import Dict, List


def interrogate(topic: str) -> Dict[str, object]:
    """
    Return structured, relevant interrogative questions for a topic.
    v0 intelligence: templates + light normalization.
    """
    t = " ".join(topic.strip().split())
    if not t:
        return {"topic": topic, "categories": {}, "notes": ["Empty topic received."]}

    categories: Dict[str, List[str]] = {
        "What": [
            f"What is {t} in plain language?",
            f"What are the key parts/components of {t}?",
            f"What problem does {t} exist to solve?",
        ],
        "Why": [
            f"Why does {t} matter?",
            f"Why did {t} become necessary (history/context)?",
            f"Why do people get confused about {t}?",
        ],
        "How": [
            f"How does {t} work at a high level?",
            f"How do beginners usually start learning {t} (first 3 steps)?",
            f"How can I tell if I truly understand {t}?",
        ],
        "When": [
            f"When should someone use {t} (and when should they avoid it)?",
            f"When did {t} become important/popular?",
            f"When does {t} become advanced or specialized?",
        ],
        "Where": [
            f"Where is {t} used in real life?",
            f"Where do people learn {t} effectively (paths/resources types)?",
            f"Where does {t} usually fail or break in practice?",
        ],
    }

    notes = [
        "v0: template-based interrogation (no external knowledge yet).",
        "Next: add topic-type detection (concept vs skill vs decision vs troubleshooting).",
    ]

    return {"topic": t, "categories": categories, "notes": notes}

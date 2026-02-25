# api/topic_utils.py

import re
from typing import Tuple

def extract_topic(user_text: str) -> str:
    text = (user_text or "").strip()
    if not text:
        return ""

    # remove common lead-in phrases
    prefixes = [
        "can you", "could you", "please", "tell me", "explain", "teach me",
        "what is", "what are", "how to", "how do i", "help me", "i want to learn",
        "i want to know", "give me", "show me"
    ]
    lowered = text.lower()
    for p in prefixes:
        if lowered.startswith(p + " "):
            text = text[len(p):].strip()
            break

    # cleanup punctuation
    text = re.sub(r"^[\s\-\:\,]+", "", text).strip()
    return text

def detect_topic_type(topic: str) -> Tuple[str, float]:
    t = (topic or "").lower().strip()

    # super-light heuristic; keep your existing rules if you already have better ones
    if any(x in t for x in [" vs ", "versus", "compare", "difference between"]):
        return "comparison", 0.67
    if any(x in t for x in ["how to", "learn", "tutorial", "guide", "steps"]):
        return "learning", 0.60
    return "concept", 0.50

"""Small, reviewed NASA Science fact catalogue, not live website retrieval.

Only paraphrased factual notes and official URLs are included. No images,
logos, third-party material, news, or entire articles are copied. Entries
expire after 180 days until reviewed again; user queries never leave the app.
"""

import os
import re
from copy import deepcopy
from datetime import date


REVIEWED_ON = date(2026, 10, 8)
MAX_AGE_DAYS = 180
TERMS_URL = "https://www.nasa.gov/nasa-brand-center/images-and-media/"

_RECORDS = (
    (
        r"\b(?:solar system|planetary science|astronomy)\b",
        {
            "title": "Solar System Exploration",
            "source_url": "https://science.nasa.gov/solar-system/",
            "facts": [
                "The solar system contains eight planets.",
                "Our solar system lies in the Orion Spur of the Milky Way.",
                "The Milky Way is a barred spiral galaxy.",
            ],
        },
    ),
    (
        r"\b(?:black holes?|event horizons?|astrophysics|astronomy)\b",
        {
            "title": "Black Holes",
            "source_url": "https://science.nasa.gov/universe/black-holes/",
            "facts": [
                "A black hole's event horizon is a boundary beyond which even light cannot escape.",
                "Astronomers study black holes through their effects on surrounding matter and light.",
                "At a sufficient distance, a black hole has the same gravitational effect as another object of the same mass.",
            ],
        },
    ),
    (
        r"\b(?:earth science|earth observation|climate change|climate science|remote sensing)\b",
        {
            "title": "Earth Science",
            "source_url": "https://science.nasa.gov/earth/",
            "facts": [
                "NASA satellites collect observations of Earth's land, water, atmosphere, temperature, and climate.",
                "NASA studies Earth as an interconnected system to understand how it changes.",
            ],
        },
    ),
)


def retrieve_nasa_context(topic: str) -> dict:
    """Return applicable reviewed notes, or nothing for unsupported queries."""
    if os.getenv("INI_NASA_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return {}
    age = (date.today() - REVIEWED_ON).days
    if age < 0 or age > MAX_AGE_DAYS:
        return {}
    if not isinstance(topic, str) or len(topic) > 300:
        return {}
    works = [deepcopy(record) for pattern, record in _RECORDS if re.search(pattern, topic, re.I)]
    if not works:
        return {}
    return {
        "source": "NASA Science",
        "attribution": "NASA Science, National Aeronautics and Space Administration",
        "terms_url": TERMS_URL,
        "license": "Paraphrased factual notes; no blanket licence asserted for NASA assets",
        "content_scope": "Reviewed factual summaries only; not live retrieval or full-site coverage",
        "reviewed_on": REVIEWED_ON.isoformat(),
        "works": works,
    }


def format_nasa_prompt_context(context: dict) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN REVIEWED NASA SCIENCE NOTES",
        "These are limited factual summaries checked on " + context["reviewed_on"] + ". Not live retrieval.",
    ]
    for work in context["works"]:
        lines.append(work["title"] + " | " + work["source_url"])
        lines.extend("- " + fact for fact in work["facts"])
    lines.extend([
        "Use only relevant supplied facts. Attribute NASA Science and link the supporting page when using these notes in explanatory prose. "
        "Do not imply NASA supports other claims, endorses InI, or supplies the entire curriculum. "
        "Do not treat this catalogue as current news or force it into unrelated answers. "
        "Preserve requested structured output schemas; do not add citation fields to them.",
        "END REVIEWED NASA SCIENCE NOTES",
    ])
    return "\n".join(lines)

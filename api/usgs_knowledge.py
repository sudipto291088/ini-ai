"""Reviewed USGS-authored science notes, not live retrieval or hazard advice.

Only short factual paraphrases and official links are included. No images,
logos, third-party contributions, or article copies. User queries stay local
to this adapter. Notes expire after 180 days unless reviewed again.
"""
import os
import re
from copy import deepcopy
from datetime import date


REVIEWED_ON = date(2026, 10, 28)
MAX_AGE_DAYS = 180
TERMS_URL = "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits"

_RECORDS = (
    (
        r"\b(?:earthquakes?|seismology|seismic waves?|tectonic plates?)\b",
        {
            "title": "The Science of Earthquakes",
            "source_url": "https://www.usgs.gov/programs/earthquake-hazards/science-earthquakes",
            "facts": [
                "Sudden movement between rock blocks along a fault can cause an earthquake.",
                "Energy released by fault movement travels through Earth as seismic waves.",
                "The hypocenter is the underground starting point; the epicenter is directly above it at the surface.",
                "Magnitude describes earthquake size; shaking intensity can differ between locations for the same event.",
            ],
        },
    ),
    (
        r"\b(?:volcanoes|volcano|volcanology|volcanic eruptions?|magma|lava)\b",
        {
            "title": "How Do Volcanoes Erupt?",
            "source_url": "https://www.usgs.gov/faqs/how-do-volcanoes-erupt",
            "facts": [
                "Molten rock beneath Earth's surface is magma; after reaching the surface it is called lava.",
                "Magma composition and the ability of gases to escape affect how explosive an eruption is.",
                "Explosive eruptions can fragment magma into tephra, including ash and larger pieces.",
            ],
        },
    ),
    (
        r"\b(?:groundwater|ground water|aquifers?|hydrogeology)\b",
        {
            "title": "Groundwater: What is Groundwater?",
            "source_url": "https://www.usgs.gov/water-science-school/science/groundwater-what-groundwater",
            "facts": [
                "Groundwater occupies water-filled pores and fractures in the saturated subsurface.",
                "Some precipitation infiltrates downward and replenishes groundwater through recharge.",
                "Groundwater can move through the subsurface and discharge into rivers, lakes, or the ocean.",
            ],
        },
    ),
)


def retrieve_usgs_context(topic: str) -> dict:
    """Return matching, unexpired factual notes without making network calls."""
    if os.getenv("INI_USGS_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return {}
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 300:
        return {}
    age = (date.today() - REVIEWED_ON).days
    if age < 0 or age > MAX_AGE_DAYS:
        return {}
    # This static catalogue cannot establish present conditions or personal risk.
    if re.search(r"\b(?:today|tonight|yesterday|latest|current|currently|now|live|recent|"
                 r"alerts?|warnings?|evacuate|evacuation|safe|safety|predict|prediction|"
                 r"forecast|near me|my home|my house|my location)\b", topic, re.I):
        return {}
    works = [deepcopy(record) for pattern, record in _RECORDS if re.search(pattern, topic, re.I)]
    if not works:
        return {}
    return {
        "source": "USGS",
        "attribution": "U.S. Geological Survey (USGS)",
        "terms_url": TERMS_URL,
        "license": "USGS-authored information is in the U.S. public domain; third-party material excluded",
        "content_scope": "Reviewed factual notes only; no live retrieval, alerts, forecasts, or full-site coverage",
        "reviewed_on": REVIEWED_ON.isoformat(),
        "works": works,
    }


def format_usgs_prompt_context(context: dict) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN REVIEWED USGS SCIENCE NOTES",
        "Limited factual paraphrases reviewed on " + context["reviewed_on"] + ". Not live retrieval.",
    ]
    for work in context["works"]:
        lines.append(work["title"] + " | " + work["source_url"])
        lines.extend("- " + fact for fact in work["facts"])
    lines.extend([
        "Use only relevant supplied facts. Credit the U.S. Geological Survey (USGS) and link the supporting page "
        "when using a note in explanatory prose. These notes do not establish current events, alerts, forecasts, "
        "earthquake predictions, drinking-water safety, or site-specific risk. Do not imply USGS endorsement "
        "of InI or of other generated claims. Do not claim to have fetched these pages live or read an entire textbook. "
        "Preserve requested structured output schemas; do not add extra source fields to them.",
        "END REVIEWED USGS SCIENCE NOTES",
    ])
    return "\n".join(lines)

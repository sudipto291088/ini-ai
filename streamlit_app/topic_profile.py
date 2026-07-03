import json
import re
from typing import Any


_PROFILE_BLOCK = re.compile(
    r"<TOPIC_PROFILE>\s*(.*?)\s*</TOPIC_PROFILE>",
    flags=re.IGNORECASE | re.DOTALL,
)


def extract_topic_profile(text: str) -> tuple[list[tuple[str, str]], str]:
    source = (text or "").strip()
    match = _PROFILE_BLOCK.search(source)
    if not match:
        return [], source

    body = _PROFILE_BLOCK.sub("", source, count=1).strip()
    raw_profile = match.group(1).strip()
    raw_profile = re.sub(r"^```(?:json)?\s*", "", raw_profile, flags=re.IGNORECASE)
    raw_profile = re.sub(r"\s*```$", "", raw_profile)

    try:
        parsed: Any = json.loads(raw_profile)
    except (TypeError, ValueError):
        return [], body

    if not isinstance(parsed, dict):
        return [], body

    rows: list[tuple[str, str]] = []
    for raw_label, raw_value in parsed.items():
        label = re.sub(r"\s+", " ", str(raw_label or "")).strip()
        value = re.sub(r"\s+", " ", str(raw_value or "")).strip()
        if not label or not value:
            continue
        if value.lower() in {"none", "unknown", "n/a", "not applicable"}:
            continue
        rows.append((label[:60], value[:300]))
        if len(rows) == 6:
            break

    return rows, body

"""Bounded, metadata-only DataCite grounding adapter for InI.ai.

DataCite makes its deposited DOI metadata available under a CC0 waiver. This
adapter intentionally retrieves only a small allowlist of citation fields. It
does not fetch descriptions, abstracts, files, or any resource linked by a DOI.
"""

from __future__ import annotations

import os
import re
import time
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import requests


API_URL = "https://api.datacite.org/dois"
SOURCE_NAME = "DataCite"
SOURCE_LICENSE = "CC0-1.0 metadata waiver"
SOURCE_TERMS_URL = "https://support.datacite.org/docs/datacite-data-file-use-policy"
DEFAULT_USER_AGENT = (
    "InI.ai/0.1.6 (educational metadata retrieval; "
    "+https://github.com/sudipto291088/ini-ai)"
)

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = Lock()


def datacite_enabled() -> bool:
    return os.getenv("INI_DATACITE_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _timeout_seconds() -> float:
    try:
        return max(1.0, min(float(os.getenv("INI_DATACITE_TIMEOUT", "4")), 10.0))
    except ValueError:
        return 4.0


def _cache_seconds() -> int:
    try:
        return max(60, min(int(os.getenv("INI_DATACITE_CACHE_SECONDS", "86400")), 604800))
    except ValueError:
        return 86400


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": os.getenv("INI_DATACITE_USER_AGENT", DEFAULT_USER_AGENT).strip()
        or DEFAULT_USER_AGENT,
        "Accept": "application/vnd.api+json",
    }


def _clean_text(value: Any, limit: int = 300) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _safe_topic(topic: str) -> str:
    text = _clean_text(topic, 180)
    text = re.sub(
        r"^(?:please\s+)?(?:explain|define|teach(?:\s+me)?|describe|introduce|"
        r"what\s+is|what\s+are)\s+",
        "",
        text,
        flags=re.I,
    )
    return text.strip(" ?.!:;")


def _is_public_research_query(query: str) -> bool:
    if not query or len(query) > 140 or len(query.split()) > 18:
        return False
    lowered = query.casefold()
    if re.search(r"https?://|www\.|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", lowered):
        return False
    if re.search(r"\b(?:i|i'm|i've|me|my|mine|we|our|ours)\b", lowered):
        return False
    if re.search(r"\b(?:password|api[_ -]?key|secret|token|address|phone)\b", lowered):
        return False
    return True


def _api_get(query: str) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(
            API_URL,
            params={"query": query, "page[size]": "3"},
            headers=_headers(),
            timeout=_timeout_seconds(),
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (requests.RequestException, ValueError):
        return None


def _first_title(attributes: Dict[str, Any]) -> str:
    for title in (attributes.get("titles") or [])[:3]:
        if isinstance(title, dict):
            cleaned = _clean_text(title.get("title"), 240)
            if cleaned:
                return cleaned
    return ""


def _creators(attributes: Dict[str, Any]) -> list[str]:
    names: list[str] = []
    for creator in (attributes.get("creators") or [])[:4]:
        if not isinstance(creator, dict):
            continue
        name = _clean_text(creator.get("name"), 160)
        if name:
            names.append(name)
    return names


def _subjects(attributes: Dict[str, Any]) -> list[str]:
    subjects: list[str] = []
    for subject in (attributes.get("subjects") or [])[:5]:
        if not isinstance(subject, dict):
            continue
        name = _clean_text(subject.get("subject"), 100)
        if name:
            subjects.append(name)
    return subjects


def _retrieve_uncached(topic: str) -> Dict[str, Any]:
    query = _safe_topic(topic)
    if len(query) < 3 or not _is_public_research_query(query):
        return {}
    data = _api_get(query)
    works: list[Dict[str, Any]] = []
    for record in ((data or {}).get("data") or [])[:3]:
        if not isinstance(record, dict):
            continue
        attributes = record.get("attributes") or {}
        if not isinstance(attributes, dict):
            continue
        title = _first_title(attributes)
        doi = _clean_text(attributes.get("doi") or record.get("id"), 180)
        if not title or not doi:
            continue
        year = attributes.get("publicationYear")
        try:
            year = int(year) if year is not None else None
        except (TypeError, ValueError):
            year = None
        if year is not None and not 1000 <= year <= 3000:
            year = None
        types = attributes.get("types") or {}
        works.append(
            {
                "title": title,
                "creators": _creators(attributes),
                "year": year,
                "publisher": _clean_text(attributes.get("publisher"), 180),
                "resource_type": _clean_text(
                    types.get("resourceTypeGeneral") if isinstance(types, dict) else "",
                    80,
                ),
                "subjects": _subjects(attributes),
                "doi": doi,
                "source_url": f"https://doi.org/{doi}",
            }
        )
    if not works:
        return {}
    return {
        "source": SOURCE_NAME,
        "license": SOURCE_LICENSE,
        "terms_url": SOURCE_TERMS_URL,
        "attribution": "DataCite DOI metadata",
        "retrieved_at": int(time.time()),
        "query": query,
        "works": works,
        "content_scope": "CC0 citation metadata only; no descriptions, abstracts, files, or linked content",
    }


def retrieve_datacite_context(topic: str) -> Dict[str, Any]:
    """Return bounded DataCite metadata, or {} on any failure."""
    if not datacite_enabled():
        return {}
    key = _safe_topic(topic).casefold()
    if not key or not _is_public_research_query(key):
        return {}
    now = time.time()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < _cache_seconds():
            return dict(cached[1])
    result = _retrieve_uncached(topic)
    if result:
        with _CACHE_LOCK:
            _CACHE[key] = (now, dict(result))
    return result


def format_datacite_prompt_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN TRUSTED RESEARCH-OUTPUT METADATA",
        "Source: DataCite DOI metadata (CC0-1.0)",
        "Scope: citation metadata only; no descriptions, abstracts, files, or linked content were retrieved",
    ]
    for index, work in enumerate((context.get("works") or [])[:3], start=1):
        if not isinstance(work, dict):
            continue
        creator_text = ", ".join(work.get("creators") or []) or "creators not supplied"
        subject_text = ", ".join(work.get("subjects") or []) or "subjects not supplied"
        lines.append(
            f"Record {index}: {_clean_text(work.get('title'), 240)} | "
            f"{_clean_text(creator_text, 240)} | {_clean_text(work.get('year'), 10)} | "
            f"{_clean_text(work.get('publisher'), 180)} | "
            f"{_clean_text(work.get('resource_type'), 80)} | {subject_text} | "
            f"DOI {_clean_text(work.get('doi'), 180)}"
        )
    lines.extend(
        [
            "Use these records only to identify relevant research outputs and directions. Metadata does not establish a work's findings or reliability. Do not invent, quote, or imply access to the linked resource.",
            "END TRUSTED RESEARCH-OUTPUT METADATA",
        ]
    )
    return "\n".join(lines)


def clear_datacite_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()

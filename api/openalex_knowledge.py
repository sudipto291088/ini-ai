"""Bounded, metadata-only OpenAlex grounding adapter for InI.ai.

OpenAlex indexes scholarly-work metadata and relationships. This adapter keeps
only a small allowlist of bibliographic, topical, citation-count, and
open-access indicator fields. It never forwards abstracts, full text, files,
or content from a work's landing page to the model.
"""

from __future__ import annotations

import os
import re
import time
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import requests


API_URL = "https://api.openalex.org/works"
SOURCE_NAME = "OpenAlex"
SOURCE_TERMS_URL = "https://openalex.org/OpenAlex_termsofservice.pdf"
SOURCE_LICENSE_URL = "https://help.openalex.org/data/licenses/"
DEFAULT_USER_AGENT = (
    "InI.ai/0.1.6 (metadata-only scholarly discovery; "
    "+https://github.com/sudipto291088/ini-ai)"
)

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = Lock()


def openalex_enabled() -> bool:
    return os.getenv("INI_OPENALEX_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _timeout_seconds() -> float:
    try:
        return max(1.0, min(float(os.getenv("INI_OPENALEX_TIMEOUT", "4")), 10.0))
    except ValueError:
        return 4.0


def _cache_seconds() -> int:
    try:
        return max(60, min(int(os.getenv("INI_OPENALEX_CACHE_SECONDS", "86400")), 604800))
    except ValueError:
        return 86400


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": os.getenv("INI_OPENALEX_USER_AGENT", DEFAULT_USER_AGENT).strip()
        or DEFAULT_USER_AGENT,
        "Accept": "application/json",
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
    params = {"search": query, "per-page": "3"}
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key
    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=_headers(),
            timeout=_timeout_seconds(),
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (requests.RequestException, ValueError):
        return None


def _authors(work: Dict[str, Any]) -> list[str]:
    names: list[str] = []
    for authorship in (work.get("authorships") or [])[:4]:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        name = _clean_text(author.get("display_name") if isinstance(author, dict) else "", 160)
        if name:
            names.append(name)
    return names


def _topics(work: Dict[str, Any]) -> list[str]:
    names: list[str] = []
    for topic in (work.get("topics") or [])[:5]:
        if not isinstance(topic, dict):
            continue
        name = _clean_text(topic.get("display_name"), 100)
        if name:
            names.append(name)
    return names


def _source_name(work: Dict[str, Any]) -> str:
    location = work.get("primary_location") or {}
    source = location.get("source") if isinstance(location, dict) else {}
    return _clean_text(source.get("display_name") if isinstance(source, dict) else "", 180)


def _retrieve_uncached(topic: str) -> Dict[str, Any]:
    query = _safe_topic(topic)
    if len(query) < 3 or not _is_public_research_query(query):
        return {}
    data = _api_get(query)
    works: list[Dict[str, Any]] = []
    for work in ((data or {}).get("results") or [])[:3]:
        if not isinstance(work, dict):
            continue
        title = _clean_text(work.get("display_name") or work.get("title"), 240)
        openalex_id = _clean_text(work.get("id"), 180)
        if not title or not openalex_id.startswith("https://openalex.org/"):
            continue
        year = work.get("publication_year")
        try:
            year = int(year) if year is not None else None
        except (TypeError, ValueError):
            year = None
        if year is not None and not 1000 <= year <= 3000:
            year = None
        open_access = work.get("open_access") or {}
        cited_by = work.get("cited_by_count")
        works.append(
            {
                "title": title,
                "authors": _authors(work),
                "year": year,
                "work_type": _clean_text(work.get("type"), 80),
                "source": _source_name(work),
                "topics": _topics(work),
                "doi": _clean_text(work.get("doi"), 180),
                "cited_by_count": cited_by if isinstance(cited_by, int) and cited_by >= 0 else None,
                "is_open_access": bool(open_access.get("is_oa")) if isinstance(open_access, dict) else False,
                "openalex_url": openalex_id,
            }
        )
    if not works:
        return {}
    return {
        "source": SOURCE_NAME,
        "terms_url": SOURCE_TERMS_URL,
        "license_guidance_url": SOURCE_LICENSE_URL,
        "attribution": "OpenAlex scholarly metadata",
        "retrieved_at": int(time.time()),
        "query": query,
        "works": works,
        "content_scope": "bibliographic, topical, citation-count, and access-status metadata only; no abstracts or full text",
    }


def retrieve_openalex_context(topic: str) -> Dict[str, Any]:
    """Return bounded OpenAlex metadata, or {} on any failure."""
    if not openalex_enabled():
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


def format_openalex_prompt_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN TRUSTED SCHOLARLY-DISCOVERY METADATA",
        "Source: OpenAlex scholarly metadata",
        "Scope: bibliographic, topical, citation-count, and access-status metadata only; no abstracts or full text were retrieved",
    ]
    for index, work in enumerate((context.get("works") or [])[:3], start=1):
        if not isinstance(work, dict):
            continue
        authors = ", ".join(work.get("authors") or []) or "authors not supplied"
        topics = ", ".join(work.get("topics") or []) or "topics not supplied"
        lines.append(
            f"Record {index}: {_clean_text(work.get('title'), 240)} | "
            f"{_clean_text(authors, 240)} | {_clean_text(work.get('year'), 10)} | "
            f"{_clean_text(work.get('work_type'), 80)} | {_clean_text(work.get('source'), 180)} | "
            f"topics: {_clean_text(topics, 240)} | citations: {_clean_text(work.get('cited_by_count'), 20)} | "
            f"open-access indicator: {bool(work.get('is_open_access'))} | DOI {_clean_text(work.get('doi'), 180)}"
        )
    lines.extend(
        [
            "Use these records only for scholarly discovery and topic orientation. Metadata, citation counts, and open-access indicators do not establish findings, quality, or permission to reproduce a work. Do not quote, summarize, or imply access to abstracts, full text, or linked content.",
            "END TRUSTED SCHOLARLY-DISCOVERY METADATA",
        ]
    )
    return "\n".join(lines)


def clear_openalex_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()

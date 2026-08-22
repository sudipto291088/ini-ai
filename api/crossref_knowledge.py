"""Bounded, metadata-only Crossref grounding adapter for InI.ai.

Crossref's public REST API makes bibliographic metadata openly reusable.  This
adapter deliberately excludes abstracts, full text, and publisher article
content because those materials can retain separate copyright.
"""

from __future__ import annotations

import os
import re
import time
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import requests


API_URL = "https://api.crossref.org/works"
SOURCE_NAME = "Crossref"
SOURCE_LICENSE = "Bibliographic facts / Crossref-generated CC0 data"
SOURCE_TERMS_URL = "https://www.crossref.org/documentation/retrieve-metadata/"
DEFAULT_USER_AGENT = (
    "InI.ai/0.1.6 (educational metadata retrieval; "
    "+https://github.com/sudipto291088/ini-ai)"
)

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = Lock()


def crossref_enabled() -> bool:
    return os.getenv("INI_CROSSREF_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _timeout_seconds() -> float:
    try:
        return max(1.0, min(float(os.getenv("INI_CROSSREF_TIMEOUT", "4")), 10.0))
    except ValueError:
        return 4.0


def _cache_seconds() -> int:
    try:
        return max(60, min(int(os.getenv("INI_CROSSREF_CACHE_SECONDS", "86400")), 604800))
    except ValueError:
        return 86400


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": os.getenv("INI_CROSSREF_USER_AGENT", DEFAULT_USER_AGENT).strip()
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


def _is_public_scholarly_query(query: str) -> bool:
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
            params={
                "query.bibliographic": query,
                "rows": "3",
                # Copyright-sensitive fields such as abstract and links to
                # full text are intentionally not requested.
                "select": "DOI,title,author,published,container-title,type,URL",
            },
            headers=_headers(),
            timeout=_timeout_seconds(),
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (requests.RequestException, ValueError):
        return None


def _published_year(item: Dict[str, Any]) -> Optional[int]:
    parts = ((item.get("published") or {}).get("date-parts") or [])
    if not parts or not isinstance(parts[0], list) or not parts[0]:
        return None
    try:
        year = int(parts[0][0])
    except (TypeError, ValueError):
        return None
    return year if 1000 <= year <= 3000 else None


def _authors(item: Dict[str, Any]) -> list[str]:
    names: list[str] = []
    for author in (item.get("author") or [])[:4]:
        if not isinstance(author, dict):
            continue
        name = _clean_text(
            " ".join(
                part for part in (
                    _clean_text(author.get("given"), 80),
                    _clean_text(author.get("family"), 80),
                ) if part
            ),
            160,
        )
        if name:
            names.append(name)
    return names


def _retrieve_uncached(topic: str) -> Dict[str, Any]:
    query = _safe_topic(topic)
    if len(query) < 3 or not _is_public_scholarly_query(query):
        return {}
    data = _api_get(query)
    items = (((data or {}).get("message") or {}).get("items") or [])
    works: list[Dict[str, Any]] = []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        titles = item.get("title") or []
        title = _clean_text(titles[0] if isinstance(titles, list) and titles else "", 240)
        doi = _clean_text(item.get("DOI"), 180)
        if not title or not doi:
            continue
        containers = item.get("container-title") or []
        works.append(
            {
                "title": title,
                "authors": _authors(item),
                "year": _published_year(item),
                "container": _clean_text(
                    containers[0] if isinstance(containers, list) and containers else "",
                    180,
                ),
                "type": _clean_text(item.get("type"), 80),
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
        "attribution": "Crossref bibliographic metadata",
        "retrieved_at": int(time.time()),
        "query": query,
        "works": works,
        "content_scope": "metadata only; no abstracts or full text",
    }


def retrieve_crossref_context(topic: str) -> Dict[str, Any]:
    """Return bounded scholarly metadata, or {} on any failure."""
    if not crossref_enabled():
        return {}
    key = _safe_topic(topic).casefold()
    if not key or not _is_public_scholarly_query(key):
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


def format_crossref_prompt_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN TRUSTED SCHOLARLY METADATA",
        "Source: Crossref public bibliographic metadata",
        "Scope: factual metadata only; no abstracts or full text were retrieved",
    ]
    for index, work in enumerate((context.get("works") or [])[:3], start=1):
        if not isinstance(work, dict):
            continue
        author_text = ", ".join(work.get("authors") or []) or "authors not supplied"
        lines.append(
            f"Work {index}: {_clean_text(work.get('title'), 240)} | "
            f"{_clean_text(author_text, 240)} | "
            f"{_clean_text(work.get('year'), 10)} | "
            f"{_clean_text(work.get('container'), 180)} | "
            f"DOI {_clean_text(work.get('doi'), 180)}"
        )
    lines.extend(
        [
            "Use these records only to identify relevant scholarly directions. Do not claim that metadata proves a paper's findings, and do not invent or quote article content.",
            "END TRUSTED SCHOLARLY METADATA",
        ]
    )
    return "\n".join(lines)


def clear_crossref_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()

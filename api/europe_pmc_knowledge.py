"""Bounded, metadata-only Europe PMC discovery adapter for InI.ai.

Europe PMC provides an official REST API for life-science publication records.
This adapter intentionally retains only a small bibliographic allowlist. It
does not retrieve abstracts, full text, supplementary files, annotations, or
content from publisher links.
"""

from __future__ import annotations

import os
import re
import time
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import requests


API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
SOURCE_NAME = "Europe PMC"
SOURCE_API_URL = "https://europepmc.org/RestfulWebService"
SOURCE_COPYRIGHT_URL = "https://europepmc.org/Copyright"
DEFAULT_USER_AGENT = (
    "InI.ai/0.1.6 (metadata-only life-science discovery; "
    "+https://github.com/sudipto291088/ini-ai)"
)

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = Lock()


def europe_pmc_enabled() -> bool:
    return os.getenv("INI_EUROPE_PMC_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _timeout_seconds() -> float:
    try:
        return max(1.0, min(float(os.getenv("INI_EUROPE_PMC_TIMEOUT", "4")), 10.0))
    except ValueError:
        return 4.0


def _cache_seconds() -> int:
    try:
        return max(60, min(int(os.getenv("INI_EUROPE_PMC_CACHE_SECONDS", "86400")), 604800))
    except ValueError:
        return 86400


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
            params={"query": query, "format": "json", "resultType": "lite", "pageSize": "3"},
            headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
            timeout=_timeout_seconds(),
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (requests.RequestException, ValueError):
        return None


def _authors(record: Dict[str, Any]) -> list[str]:
    author_list = record.get("authorList") or {}
    authors = author_list.get("author") if isinstance(author_list, dict) else []
    names: list[str] = []
    for author in (authors or [])[:4]:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("fullName"), 160)
        if name:
            names.append(name)
    return names


def _retrieve_uncached(topic: str) -> Dict[str, Any]:
    query = _safe_topic(topic)
    if len(query) < 3 or not _is_public_research_query(query):
        return {}
    data = _api_get(query)
    result_list = (data or {}).get("resultList") or {}
    records = result_list.get("result") if isinstance(result_list, dict) else []
    works: list[Dict[str, Any]] = []
    for record in (records or [])[:3]:
        if not isinstance(record, dict):
            continue
        title = _clean_text(record.get("title"), 240)
        identifier = _clean_text(record.get("pmid") or record.get("pmcid"), 40)
        source = "MED" if record.get("pmid") else "PMC"
        if not title or not identifier:
            continue
        works.append({
            "title": title,
            "authors": _authors(record),
            "year": _clean_text(record.get("pubYear"), 10),
            "journal": _clean_text(record.get("journalTitle"), 180),
            "publication_type": _clean_text(record.get("pubType"), 100),
            "doi": _clean_text(record.get("doi"), 180),
            "record_url": f"https://europepmc.org/article/{source}/{identifier}",
        })
    if not works:
        return {}
    return {
        "source": SOURCE_NAME,
        "api_url": SOURCE_API_URL,
        "copyright_url": SOURCE_COPYRIGHT_URL,
        "attribution": "Europe PMC bibliographic metadata",
        "retrieved_at": int(time.time()),
        "query": query,
        "works": works,
        "content_scope": "bibliographic metadata only; no abstracts, full text, supplementary files, annotations, or linked content",
    }


def retrieve_europe_pmc_context(topic: str) -> Dict[str, Any]:
    """Return bounded Europe PMC metadata, or {} on any failure."""
    if not europe_pmc_enabled():
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


def format_europe_pmc_prompt_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN TRUSTED LIFE-SCIENCE DISCOVERY METADATA",
        "Source: Europe PMC bibliographic metadata",
        "Scope: metadata only; no abstracts, full text, files, annotations, or linked content were retrieved",
    ]
    for index, work in enumerate((context.get("works") or [])[:3], start=1):
        if not isinstance(work, dict):
            continue
        lines.append(
            f"Record {index}: {_clean_text(work.get('title'), 240)} | "
            f"{_clean_text(', '.join(work.get('authors') or []), 240)} | "
            f"{_clean_text(work.get('year'), 10)} | {_clean_text(work.get('journal'), 180)} | "
            f"{_clean_text(work.get('publication_type'), 100)} | DOI {_clean_text(work.get('doi'), 180)}"
        )
    lines.extend([
        "Use these records only for life-science literature discovery and topic orientation. Metadata does not establish findings, clinical validity, reliability, or permission to reproduce a work. Do not quote, summarize, or imply access to abstracts, full text, or linked content.",
        "END TRUSTED LIFE-SCIENCE DISCOVERY METADATA",
    ])
    return "\n".join(lines)


def clear_europe_pmc_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()

"""Bounded, metadata-only DOAJ grounding adapter for InI.ai.

DOAJ exposes its journal and article metadata under a CC0 waiver. This adapter
keeps only a small citation allowlist and never downloads abstracts, article
text, files, or publisher-page content.
"""

from __future__ import annotations

import os
import re
import time
from threading import Lock
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import requests


API_URL = "https://doaj.org/api/search/articles"
SOURCE_NAME = "DOAJ"
SOURCE_LICENSE = "CC0 metadata waiver"
SOURCE_TERMS_URL = "https://doaj.org/terms/"
DEFAULT_USER_AGENT = (
    "InI.ai/0.1.6 (educational metadata retrieval; "
    "+https://github.com/sudipto291088/ini-ai)"
)

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = Lock()


def doaj_enabled() -> bool:
    return os.getenv("INI_DOAJ_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _timeout_seconds() -> float:
    try:
        return max(1.0, min(float(os.getenv("INI_DOAJ_TIMEOUT", "4")), 10.0))
    except ValueError:
        return 4.0


def _cache_seconds() -> int:
    try:
        return max(60, min(int(os.getenv("INI_DOAJ_CACHE_SECONDS", "86400")), 604800))
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
            f"{API_URL}/{quote(query, safe='')}",
            params={"pageSize": "3"},
            headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
            timeout=_timeout_seconds(),
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except (requests.RequestException, ValueError):
        return None


def _identifier(bibjson: Dict[str, Any], kind: str) -> str:
    for item in (bibjson.get("identifier") or [])[:8]:
        if isinstance(item, dict) and str(item.get("type") or "").casefold() == kind:
            value = _clean_text(item.get("id"), 180)
            if value:
                return value
    return ""


def _retrieve_uncached(topic: str) -> Dict[str, Any]:
    query = _safe_topic(topic)
    if len(query) < 3 or not _is_public_research_query(query):
        return {}
    data = _api_get(query)
    works: list[Dict[str, Any]] = []
    for record in ((data or {}).get("results") or [])[:3]:
        if not isinstance(record, dict):
            continue
        bibjson = record.get("bibjson") or {}
        if not isinstance(bibjson, dict):
            continue
        title = _clean_text(bibjson.get("title"), 240)
        if not title:
            continue
        authors = [
            _clean_text(author.get("name"), 160)
            for author in (bibjson.get("author") or [])[:4]
            if isinstance(author, dict) and _clean_text(author.get("name"), 160)
        ]
        subjects = [
            _clean_text(subject.get("term"), 100)
            for subject in (bibjson.get("subject") or [])[:5]
            if isinstance(subject, dict) and _clean_text(subject.get("term"), 100)
        ]
        journal = bibjson.get("journal") or {}
        journal_title = _clean_text(
            journal.get("title") if isinstance(journal, dict) else "", 180
        )
        doi = _identifier(bibjson, "doi")
        record_id = _clean_text(record.get("id"), 80)
        works.append(
            {
                "title": title,
                "authors": authors,
                "year": _clean_text(bibjson.get("year"), 10),
                "journal": journal_title,
                "subjects": subjects,
                "doi": doi,
                "source_url": f"https://doaj.org/article/{record_id}" if record_id else "",
            }
        )
    if not works:
        return {}
    return {
        "source": SOURCE_NAME,
        "license": SOURCE_LICENSE,
        "terms_url": SOURCE_TERMS_URL,
        "attribution": "Directory of Open Access Journals (DOAJ) metadata",
        "retrieved_at": int(time.time()),
        "query": query,
        "works": works,
        "content_scope": "CC0 citation metadata only; no abstracts, article text, files, or linked content",
    }


def retrieve_doaj_context(topic: str) -> Dict[str, Any]:
    """Return bounded DOAJ citation metadata, or {} on any failure."""
    if not doaj_enabled():
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


def format_doaj_prompt_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN TRUSTED OPEN-ACCESS ARTICLE METADATA",
        "Source: Directory of Open Access Journals (DOAJ), CC0 metadata",
        "Scope: citation metadata only; no abstracts, article text, files, or linked content were retrieved",
    ]
    for index, work in enumerate((context.get("works") or [])[:3], start=1):
        if not isinstance(work, dict):
            continue
        lines.append(
            f"Record {index}: {_clean_text(work.get('title'), 240)} | "
            f"{_clean_text(', '.join(work.get('authors') or []), 240)} | "
            f"{_clean_text(work.get('year'), 10)} | "
            f"{_clean_text(work.get('journal'), 180)} | "
            f"{_clean_text(', '.join(work.get('subjects') or []), 240)} | "
            f"DOI {_clean_text(work.get('doi'), 180)}"
        )
    lines.extend(
        [
            "Use these records only to identify potentially relevant open-access research. Metadata alone does not establish findings or reliability. Do not invent, quote, or imply access to article contents.",
            "END TRUSTED OPEN-ACCESS ARTICLE METADATA",
        ]
    )
    return "\n".join(lines)


def clear_doaj_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()

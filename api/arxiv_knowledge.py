"""Bounded arXiv metadata retrieval for InI.ai.

arXiv's API exposes descriptive metadata for scientific e-prints. This
adapter keeps a small discovery-focused allowlist, enforces arXiv's
one-request-per-three-seconds limit within the process, and never downloads
PDFs, source files, or linked-page content.
"""

from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from threading import Lock
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, urlencode

import requests


API_URL = "https://export.arxiv.org/api/query"
SOURCE_NAME = "arXiv"
SOURCE_TERMS_URL = "https://info.arxiv.org/help/api/tou.html"
SOURCE_MANUAL_URL = "https://info.arxiv.org/help/api/user-manual.html"
ACKNOWLEDGEMENT = "Thank you to arXiv for use of its open access interoperability."
DEFAULT_USER_AGENT = (
    "InI.ai/0.1.7 (educational research discovery; "
    "+https://github.com/sudipto291088/ini-ai)"
)

_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_LOCK = Lock()
_REQUEST_LOCK = Lock()
_LAST_REQUEST_AT = 0.0


def arxiv_enabled() -> bool:
    return os.getenv("INI_ARXIV_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }


def _timeout_seconds() -> float:
    try:
        return max(1.0, min(float(os.getenv("INI_ARXIV_TIMEOUT", "6")), 12.0))
    except ValueError:
        return 6.0


def _cache_seconds() -> int:
    try:
        return max(60, min(int(os.getenv("INI_ARXIV_CACHE_SECONDS", "86400")), 604800))
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


def _search_expression(query: str) -> str:
    # Keep only ordinary topic tokens so arXiv query operators cannot be
    # injected through a user's prompt. Requiring every token improves
    # relevance for short educational topics.
    tokens = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", query)[:12]
    return " AND ".join(f"all:{token}" for token in tokens)


def _api_get(query: str) -> Optional[str]:
    global _LAST_REQUEST_AT
    expression = _search_expression(query)
    if not expression:
        return None
    try:
        # arXiv requires legacy API clients to use a single connection and
        # make no more than one request every three seconds.
        with _REQUEST_LOCK:
            wait_seconds = 3.0 - (time.monotonic() - _LAST_REQUEST_AT)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            query_string = urlencode(
                {
                    "search_query": expression,
                    "start": "0",
                    "max_results": "2",
                    "sortBy": "relevance",
                },
                quote_via=quote,
            )
            response = requests.get(
                f"{API_URL}?{query_string}",
                headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/atom+xml"},
                timeout=_timeout_seconds(),
            )
            _LAST_REQUEST_AT = time.monotonic()
        if response.status_code != 200:
            return None
        return response.text
    except requests.RequestException:
        return None


def _entry_text(entry: ET.Element, name: str, limit: int) -> str:
    element = entry.find(f"{_ATOM}{name}")
    return _clean_text(element.text if element is not None else "", limit)


def _entry_url(entry: ET.Element) -> str:
    for link in entry.findall(f"{_ATOM}link"):
        if link.attrib.get("rel") == "alternate":
            url = _clean_text(link.attrib.get("href"), 220)
            if url.startswith("https://arxiv.org/abs/") or url.startswith("http://arxiv.org/abs/"):
                return url.replace("http://", "https://", 1)
    identifier = _entry_text(entry, "id", 220)
    if identifier.startswith("http://arxiv.org/abs/"):
        return identifier.replace("http://", "https://", 1)
    return identifier if identifier.startswith("https://arxiv.org/abs/") else ""


def _parse_feed(feed_text: str) -> list[Dict[str, Any]]:
    try:
        root = ET.fromstring(feed_text)
    except (ET.ParseError, TypeError):
        return []

    works: list[Dict[str, Any]] = []
    for entry in root.findall(f"{_ATOM}entry")[:2]:
        title = _entry_text(entry, "title", 240)
        record_url = _entry_url(entry)
        if not title or not record_url:
            continue
        authors = [
            _clean_text(author.findtext(f"{_ATOM}name"), 160)
            for author in entry.findall(f"{_ATOM}author")[:4]
        ]
        categories = [
            _clean_text(category.attrib.get("term"), 80)
            for category in entry.findall(f"{_ATOM}category")[:6]
        ]
        works.append(
            {
                "title": title,
                "authors": [name for name in authors if name],
                "published": _entry_text(entry, "published", 32),
                "updated": _entry_text(entry, "updated", 32),
                "categories": [category for category in categories if category],
                # arXiv explicitly classifies abstracts as reusable descriptive
                # metadata. Keep a strict bound to control prompt size.
                "abstract": _entry_text(entry, "summary", 900),
                "doi": _clean_text(entry.findtext(f"{_ARXIV}doi"), 180),
                "journal_reference": _clean_text(
                    entry.findtext(f"{_ARXIV}journal_ref"), 220
                ),
                "record_url": record_url,
            }
        )
    return works


def _retrieve_uncached(topic: str) -> Dict[str, Any]:
    query = _safe_topic(topic)
    if len(query) < 3 or not _is_public_research_query(query):
        return {}
    feed = _api_get(query)
    works = _parse_feed(feed or "")
    if not works:
        return {}
    return {
        "source": SOURCE_NAME,
        "terms_url": SOURCE_TERMS_URL,
        "manual_url": SOURCE_MANUAL_URL,
        "attribution": ACKNOWLEDGEMENT,
        "retrieved_at": int(time.time()),
        "query": query,
        "works": works,
        "content_scope": (
            "descriptive metadata for at most two e-prints; no PDFs, source files, "
            "attachments, or linked-page content"
        ),
        "review_status": (
            "arXiv records are e-prints and must not be represented as peer reviewed "
            "unless journal metadata independently establishes that status"
        ),
    }


def retrieve_arxiv_context(topic: str) -> Dict[str, Any]:
    """Return bounded arXiv discovery metadata, or {} on any failure."""
    if not arxiv_enabled():
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


def format_arxiv_prompt_context(context: Dict[str, Any]) -> str:
    if not context:
        return ""
    lines = [
        "BEGIN TRUSTED ARXIV DISCOVERY METADATA",
        f"Source acknowledgement: {ACKNOWLEDGEMENT}",
        "Scope: descriptive metadata for e-prints; no PDFs, source files, attachments, or linked pages were retrieved",
        "Review status: treat every record as a preprint/e-print, not as peer reviewed, unless supplied journal metadata establishes otherwise",
    ]
    for index, work in enumerate((context.get("works") or [])[:2], start=1):
        if not isinstance(work, dict):
            continue
        lines.append(
            f"Record {index}: {_clean_text(work.get('title'), 240)} | "
            f"authors: {_clean_text(', '.join(work.get('authors') or []), 260)} | "
            f"published: {_clean_text(work.get('published'), 32)} | "
            f"categories: {_clean_text(', '.join(work.get('categories') or []), 180)} | "
            f"DOI: {_clean_text(work.get('doi'), 180)} | "
            f"journal reference: {_clean_text(work.get('journal_reference'), 220)} | "
            f"abstract metadata: {_clean_text(work.get('abstract'), 900)} | "
            f"record: {_clean_text(work.get('record_url'), 220)}"
        )
    lines.extend(
        [
            "Use these records for research discovery and topic orientation. Clearly identify arXiv material as preprints/e-prints, do not imply peer review, and do not claim access to full text or linked content.",
            "END TRUSTED ARXIV DISCOVERY METADATA",
        ]
    )
    return "\n".join(lines)


def clear_arxiv_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()

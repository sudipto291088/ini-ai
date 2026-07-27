"""Explicit capability boundaries for topics InI cannot yet handle reliably."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CapabilityBoundary:
    domain: str
    reply: str


_TAX_PATTERN = re.compile(
    r"\b(?:tax|taxes|taxation|taxable|taxpayer|taxpayers|"
    r"income\s+tax|tax\s+return|tax\s+returns|tax\s+deduction|"
    r"gst|goods\s+and\s+services\s+tax|vat|value[-\s]+added\s+tax|"
    r"tds|tax\s+deducted\s+at\s+source)\b",
    flags=re.IGNORECASE,
)


def assess_capability(text: str) -> Optional[CapabilityBoundary]:
    """Return a refusal boundary when a query needs unverified expertise."""
    normalized = " ".join((text or "").split())
    if not normalized:
        return None

    if _TAX_PATTERN.search(normalized):
        return CapabilityBoundary(
            domain="tax",
            reply=(
                "I haven’t yet been equipped with verified tax knowledge, so I shouldn’t "
                "instruct you on taxation or generate a Question Map for it. InI is still "
                "being developed, and I would rather state that limitation clearly than "
                "give you unreliable guidance."
            ),
        )

    return None

"""Explicit capability boundaries for topics InI cannot yet handle reliably."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


CAPABILITY_BOUNDARY_VERSION = 2


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

_ACADEMIC_TAX_CONTEXT = re.compile(
    r"\b(?:supply\s+and\s+demand|market\s+equilibrium|price\s+controls?|"
    r"tax\s+incidence|deadweight\s+loss|microeconomics?|macroeconomics?|"
    r"economic\s+(?:theory|policy|effects?|impact))\b",
    flags=re.IGNORECASE,
)

_PERSONAL_OR_COMPLIANCE_TAX_CONTEXT = re.compile(
    r"\b(?:my|mine|we|our|file|filing|return|deduction|claim|owe|liability|"
    r"taxable\s+income|tax\s+bracket|accountant|irs|hmrc|income\s+tax|"
    r"in\s+(?:india|the\s+u\.s\.|the\s+us|canada|australia|the\s+uk))\b",
    flags=re.IGNORECASE,
)


def assess_capability(text: str) -> Optional[CapabilityBoundary]:
    """Return a refusal boundary when a query needs unverified expertise."""
    normalized = " ".join((text or "").split())
    if not normalized:
        return None

    tax_mentioned = bool(_TAX_PATTERN.search(normalized))
    academic_context = bool(_ACADEMIC_TAX_CONTEXT.search(normalized))
    personal_or_compliance = bool(_PERSONAL_OR_COMPLIANCE_TAX_CONTEXT.search(normalized))

    # Tax policy is also a legitimate economics subject. Keep conceptual
    # market questions in the learning pipeline while retaining the boundary
    # for personal, jurisdiction-specific, filing, and compliance guidance.
    if tax_mentioned and not (academic_context and not personal_or_compliance):
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

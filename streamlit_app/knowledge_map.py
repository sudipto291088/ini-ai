import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CompactKnowledgeMapProjection:
    anchor: str
    directions: tuple[str, ...]


_STAGE_DESCRIPTIONS = {
    "Orientation": "Defines its scope, purpose, and place within the wider subject.",
    "Foundations": "Establishes the concepts and terminology needed for what follows.",
    "Mechanisms": "Explains the process, relationships, and forces that make it work.",
    "Methods & Tools": "Covers the techniques used to apply, measure, test, or improve it.",
    "Applications": "Connects the concept to practical contexts, uses, and decisions.",
    "Pitfalls": "Surfaces limitations, failure modes, trade-offs, and common misconceptions.",
    "Advanced / Future": "Extends the path toward alternatives, research, and open questions.",
}


_QUESTION_PREFIXES = (
    r"what\s+(?:is|are)\s+",
    r"how\s+(?:does|do|is|are)\s+",
    r"why\s+(?:does|do|is|are)\s+",
    r"should\s+",
    r"can\s+",
)


def _clean_anchor(text: str) -> str:
    anchor = re.sub(r"\s+", " ", text).strip(" ,.;:?!\"'")
    anchor = re.sub(
        r"^what\s+(?:caused|causes|drives|drove|triggered|triggers)\s+",
        "",
        anchor,
        flags=re.IGNORECASE,
    ).strip()
    for prefix in _QUESTION_PREFIXES:
        anchor = re.sub(rf"^{prefix}", "", anchor, flags=re.IGNORECASE).strip()

    # Mechanism questions commonly end in a verb that is useful in the full
    # query but not in the map's central subject capsule.
    anchor = re.sub(
        r"\s+(?:work|works|working|operate|operates|function|functions)$",
        "",
        anchor,
        flags=re.IGNORECASE,
    ).strip()
    anchor = re.sub(r"^(?:a|an|the)\s+", "", anchor, flags=re.IGNORECASE).strip()
    return anchor


def compact_knowledge_map_projection(topic: str) -> CompactKnowledgeMapProjection:
    """Turn a user query into a compact-map subject and learning directions.

    The full query remains available elsewhere in the response. The compact
    map needs a short subject in its centre, especially when the query contains
    several questions.
    """
    query = re.sub(r"\s+", " ", str(topic or "")).strip()
    if not query:
        return CompactKnowledgeMapProjection("Topic", ())

    # Prefer the actual subject over the grammatical first clause for common
    # compound shapes. This keeps the narrow central capsule topic-led rather
    # than filling it with a partial question.
    subject_patterns = (
        r"^what\s+does\s+(?:the\s+)?research\s+show\s+about\s+how\s+(.+?)\s+affects?\b",
        r"^how\s+should\s+(.+?)\s+be\s+(?:evaluated|measured|assessed|tested)\b",
        r"^how\s+(?:do|does)\s+.+?\s+affect\s+(?:the\s+)?(?:rate\s+of\s+)?(.+?)\??$",
    )
    extracted_subject = ""
    for pattern in subject_patterns:
        match = re.match(pattern, query, flags=re.IGNORECASE)
        if match:
            extracted_subject = _clean_anchor(match.group(1))
            break

    # The first clause is the most reliable topic anchor after the response
    # pipeline has combined or rewritten a compound request.
    first_clause = re.split(
        r"\s*[,;]\s*|\s+and\s+(?=(?:what|how|why|where|when|which)\b)",
        query,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    anchor = extracted_subject or _clean_anchor(first_clause)
    anchor = re.sub(
        r"\s+(?:occur|occurs|happen|happens|arise|arises)$",
        "",
        anchor,
        flags=re.IGNORECASE,
    ).strip()

    # Fall back conservatively if a conversational clause did not expose a
    # usable noun phrase. Never place the entire compound query in the capsule.
    words = anchor.split()
    if not anchor:
        anchor = "Topic"
    elif len(words) > 5:
        anchor = " ".join(words[:5]).rstrip(" ,.;:?!")

    lowered = query.casefold()
    directions: list[str] = []

    def add(label: str) -> None:
        if label not in directions:
            directions.append(label)

    if re.search(r"\bwhat\s+(?:is|are)\b", lowered) or "," in query:
        add("Define the topic")
    if re.search(r"\b(?:main\s+)?types?\b|\bclassif(?:y|ication|ications)\b", lowered):
        add("Explore the main types")
    if re.search(r"\brelat(?:e|es|ed|ionship|ionships)\b|\bconnect(?:s|ed|ion|ions)?\b", lowered):
        add("Connect related fields")
    if re.search(r"\bhow\b|\bwork(?:s|ing)?\b|\bmechanis(?:m|ms)\b", lowered):
        add("See how it works")
    if re.search(r"\buse(?:d|s)?\b|\bapply|\bapplication", lowered):
        add("Apply and evaluate")

    return CompactKnowledgeMapProjection(anchor, tuple(directions[:3]))


def expanded_knowledge_map_entry(
    item: object,
    category: str,
) -> tuple[str, str]:
    """Return a topic-led title and description for one expanded-map leaf."""
    if isinstance(item, dict):
        question = re.sub(r"\s+", " ", str(item.get("question") or "")).strip()
        supplied_title = re.sub(
            r"\s+", " ", str(item.get("map_title") or "")
        ).strip(" ,.;:?!\"'")
        supplied_description = re.sub(
            r"\s+", " ", str(item.get("map_description") or "")
        ).strip()
    else:
        question = re.sub(r"\s+", " ", str(item or "")).strip()
        supplied_title = ""
        supplied_description = ""

    if supplied_title:
        title = supplied_title
    else:
        body = question.strip(" ,.;:?!\"'")
        lowered = body.casefold()
        classes_match = re.search(
            r"(?:classes|types)(?:\s+or\s+(?:classes|types))?\s+of\s+(.+?)(?:\s+exist|\s+are|$)",
            body,
            flags=re.IGNORECASE,
        )
        if classes_match:
            subject = re.split(r"\s*\(|\s+for\s+example\b", classes_match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
            subject = " ".join(subject.split()[:4]).strip()
            body = f"{subject} classifications"
        elif "major crispr subtypes" in lowered:
            body = "Major CRISPR subtypes"
        elif "guide rna" in lowered and category in {"Foundations", "Mechanisms"}:
            body = "Guide RNA function"
        elif "base editor" in lowered and category == "Mechanisms":
            body = "Base editing mechanisms"
        elif "experimental workflow" in lowered:
            body = "Experimental workflows"
        elif "delivery method" in lowered:
            body = "Delivery methods"
        elif "somatic gene therapy" in lowered:
            body = "Somatic gene therapy"
        elif "oncology" in lowered:
            body = "Oncology applications"
        elif "open research problem" in lowered:
            body = "Open research problems"
        elif "being developed" in lowered or "emerging" in lowered:
            body = "Emerging technical approaches"
        elif lowered.startswith("step-by-step"):
            body = "Step-by-step mechanism"
        body = re.sub(
            r"^(?:what|which)\s+(?:is|are|does|do|can|should)\s+",
            "",
            body,
            flags=re.IGNORECASE,
        )
        body = re.sub(
            r"^(?:define|describe|explain)(?:\s+and\s+(?:contrast|compare))?\s+",
            "",
            body,
            flags=re.IGNORECASE,
        )
        body = re.sub(
            r"^(?:how|why|when|where)\s+(?:does|do|is|are|can|should)\s+",
            "",
            body,
            flags=re.IGNORECASE,
        )
        body = re.split(
            r"\s+(?:and|but)\s+(?=(?:how|why|when|where|what|which)\b)|[,;—]",
            body,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        body = re.sub(
            r"\s+(?:work|works|differ|differs|relate|relates|matter|matters|"
            r"solve|solves|compute|computes|affect|affects|provide|provides)$",
            "",
            body,
            flags=re.IGNORECASE,
        ).strip()
        title = " ".join(body.split()[:7]).strip(" ,.;:?!") or category

    if len(title.split()) > 7:
        title = " ".join(title.split()[:7]).rstrip(" ,.;:?!")

    description = supplied_description or _STAGE_DESCRIPTIONS.get(
        category,
        "Shows how this idea continues the learning path.",
    )
    if description and description[-1] not in ".!?":
        description += "."
    return title, description

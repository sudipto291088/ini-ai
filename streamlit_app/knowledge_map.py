import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CompactKnowledgeMapProjection:
    anchor: str
    directions: tuple[str, ...]


_QUESTION_PREFIXES = (
    r"what\s+(?:is|are)\s+",
    r"how\s+(?:does|do|is|are)\s+",
    r"why\s+(?:does|do|is|are)\s+",
    r"should\s+",
    r"can\s+",
)


def _clean_anchor(text: str) -> str:
    anchor = re.sub(r"\s+", " ", text).strip(" ,.;:?!\"'")
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

    # The first clause is the most reliable topic anchor after the response
    # pipeline has combined or rewritten a compound request.
    first_clause = re.split(
        r"\s*[,;]\s*|\s+and\s+(?=(?:what|how|why|where|when|which)\b)",
        query,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    anchor = _clean_anchor(first_clause)

    # Fall back conservatively if a conversational clause did not expose a
    # usable noun phrase. Never place the entire compound query in the capsule.
    words = anchor.split()
    if not anchor:
        anchor = "Topic"
    elif len(words) > 7:
        anchor = " ".join(words[:7]).rstrip(" ,.;:?!")

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

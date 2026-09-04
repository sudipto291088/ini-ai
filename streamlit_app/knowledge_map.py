import re
from dataclasses import dataclass


KNOWLEDGE_MAP_VERSION = 9


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
    r"what\s+(?:can|could)\s+you\s+tell\s+me\s+about\s+",
    r"(?:can|could)\s+you\s+tell\s+me\s+about\s+",
    r"tell\s+me\s+about\s+",
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


def _concept_led_anchor(query: str) -> str:
    """Return a grammatical subject label for common relationship questions."""
    normalized = query.casefold()
    if re.search(r"\b(?:quantum error correction|qec)\b", normalized):
        return "Quantum error correction"
    if re.search(r"\b(?:mrna|messenger rna)\s+vaccines?\b", normalized):
        return "mRNA vaccines"
    if re.search(r"\b(?:database|dbms)\b.*\bindex(?:es|ing)?\b|\bindex(?:es|ing)?\b.*\b(?:database|query)\b", normalized):
        return "Database indexing and query performance"
    if re.search(r"\binflation\b", normalized):
        return "Inflation causes and effects"
    if re.search(r"\bbackpropagation\b", normalized):
        return "Neural-network backpropagation"
    if re.search(r"\bcarbon\s+(?:tax(?:es)?|pricing)\b", normalized) and re.search(
        r"\b(?:cap[- ]and[- ]trade|emissions?\s+trading)\b", normalized
    ):
        return "Carbon-pricing policies"

    privacy_match = re.match(
        r"^how\s+(?:does|do)\s+(.+?)\s+protect\s+privacy\b",
        query,
        flags=re.IGNORECASE,
    )
    if privacy_match:
        subject = _clean_anchor(privacy_match.group(1))
        if subject:
            return f"Privacy in {subject}"

    reliability_match = re.match(
        r"^how\s+(?:does|do)\s+(.+?)\s+(?:improve|increase|support)\s+"
        r"(?:the\s+)?(accuracy|reliability|safety)\b",
        query,
        flags=re.IGNORECASE,
    )
    if reliability_match:
        subject = _clean_anchor(reliability_match.group(1))
        if subject:
            return f"{reliability_match.group(2).capitalize()} of {subject}"
    return ""


def _qualify_map_description(description: str) -> str:
    """Correct known misleading claim patterns, including in saved maps.

    These guards supplement the generation contract; they are not a general
    factuality checker and deliberately leave formal mathematical claims alone.
    """
    value = re.sub(r"\s+", " ", str(description or "")).strip()
    value = re.sub(
        r"Place most selective and left-most columns matching query predicates; prefixing supports left-based equality and range patterns\.?",
        "Choose composite-index order from equality and range predicates, ordering needs, and the workload; usable prefixes begin with the leftmost indexed columns.",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"Secondary B-tree or hash indexes on join keys speed nested-loop/hash-join probes and support merge joins with ordered keys\.?",
        "Indexes on join keys can accelerate indexed nested-loop probes; ordered indexes may support merge joins, while hash joins commonly build their own hash table.",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"Bitmap encodes matches compactly for many-to-many filters; columnar indexes support vectorized scans and compression-aware reads\.?",
        "Bitmap indexes compactly represent low-cardinality predicates; column-oriented storage supports compressed, vectorized scans across selected columns.",
        value,
        flags=re.I,
    )
    if re.search(r"\b(?:staleness|hallucinations|privacy|reliability|bias)\b", value, re.I):
        value = re.sub(r"^Solves\b", "Helps address", value)
    value = re.sub(
        r"\bweak verification chains\b",
        "claim-to-source entailment checks",
        value,
        flags=re.I,
    )
    if "masks" in value.lower() and "decryptable" in value.lower():
        value = (
            "Clients send masked updates; pairwise masks cancel during summation, "
            "revealing only the aggregate under the protocol's trust assumptions."
        )
    if re.search(r"\bedge devices favor local DP\b", value, re.I):
        value = (
            "Local, central, or distributed DP choices depend on trust assumptions, "
            "privacy requirements, and utility—not deployment location alone."
        )
    if all(term in value.lower() for term in ("retrieve-then-generate,", "retrieve-and-read", "fusion-in-decoder")):
        value = (
            "Retrieve-and-generate pipelines may use reranking or Fusion-in-Decoder; "
            "these are overlapping design choices rather than mutually exclusive architecture classes."
        )
    value = re.sub(
        r"Cross-presentation on MHC I for CD8 priming; MHC I presentation to CD4 T cells",
        "MHC I presentation and cross-presentation for CD8 priming; MHC II presentation to CD4 T cells",
        value,
        flags=re.I,
    )
    if re.search(r"\bdetects and corrects bit/phase errors and leakage\b", value, re.I):
        value = (
            "Corrects encoded bit- and phase-type errors; leakage requires dedicated detection, "
            "reset, or leakage-reduction mechanisms, and correlated noise can lower thresholds."
        )
    if "guarantee logical operations below threshold rates" in value.casefold():
        value = (
            "Fault-tolerant designs limit error propagation; under explicit noise assumptions, "
            "logical error can be suppressed when physical error rates remain below a threshold."
        )
    if re.search(r"\brepetition codes reduce errors for VQE\b", value, re.I):
        value = (
            "Error mitigation and small logical demonstrations can support short-depth experiments; "
            "repetition codes protect only restricted error channels and are not general QEC for VQE."
        )
    return value


def compact_knowledge_map_projection(
    topic: str,
    context: object = "",
) -> CompactKnowledgeMapProjection:
    """Turn a user query into a compact-map subject and learning directions.

    The full query remains available elsewhere in the response. The compact
    map needs a short subject in its centre, especially when the query contains
    several questions.
    """
    query = re.sub(r"\s+", " ", str(topic or "")).strip()
    if not query:
        return CompactKnowledgeMapProjection("Topic", ())

    # Canonicalize common technical question shapes whose grammatical subject
    # is not a useful map title. These rules deliberately name the concept,
    # rather than retaining fragments such as "How should ... be".
    lowered_query = query.casefold()
    lowered_context = re.sub(r"\s+", " ", str(context or "")).casefold()
    canonical_subject = _concept_led_anchor(query)
    if not canonical_subject and re.search(r"\btime[- ]series\s+features?\s+be\s+engineered\b", lowered_query):
        canonical_subject = "Time-series feature engineering"
    elif re.search(r"\bcausal\s+effects?\s+be\s+estimated\b", lowered_query):
        canonical_subject = "Causal-effect estimation"
    elif all(
        marker in lowered_query
        for marker in ("batch", "stochastic", "mini-batch", "gradient descent")
    ):
        canonical_subject = "Gradient-descent optimization"
    elif re.search(
        r"\bself-attention\s+work\s+in\s+(?:a\s+)?transformer\b",
        lowered_query,
    ):
        canonical_subject = "Transformer self-attention"
    elif performance_match := re.match(
        r"^(?:why\s+(?:does|do)\s+)?(.+?)\s+"
        r"(?:perform|performs|behave|behaves|work|works|function|functions)\s+"
        r"(?:badly|poorly|worse|incorrectly|unreliably)\s+"
        r"(when|with|under|on|during|in)\s+(.+?)\??$",
        query,
        flags=re.IGNORECASE,
    ):
        subject = _clean_anchor(performance_match.group(1))
        relationship = performance_match.group(2).casefold()
        condition = _clean_anchor(performance_match.group(3))
        data_state = re.match(
            r"^(?:the\s+)?data\s+(?:is|are)\s+(.+)$",
            condition,
            flags=re.IGNORECASE,
        )
        if data_state:
            condition = f"{data_state.group(1).strip()} data"
        else:
            condition = re.sub(
                r"^there\s+(?:is|are|was|were)\s+",
                "",
                condition,
                flags=re.IGNORECASE,
            ).strip()
        if subject and condition:
            connector = "with" if relationship == "when" else relationship
            canonical_subject = f"Performance of {subject} {connector} {condition}"
    elif (
        lowered_query in {"convergence", "optimizer convergence"}
        and "gradient descent" in lowered_context
        and re.search(r"\b(?:optimizer|batch|stochastic|momentum)\b", lowered_context)
    ):
        canonical_subject = "Gradient-descent optimization"

    # Prefer the actual subject over the grammatical first clause for common
    # compound shapes. This keeps the narrow central capsule topic-led rather
    # than filling it with a partial question.
    subject_patterns = (
        r"^what\s+does\s+(?:the\s+)?research\s+show\s+about\s+how\s+(.+?)\s+affects?\b",
        r"^how\s+should\s+(.+?)\s+be\s+(?:evaluated|measured|assessed|tested)\b",
        r"^how\s+(?:do|does)\s+.+?\s+affect\s+(?:the\s+)?(?:rate\s+of\s+)?(.+?)\??$",
    )
    extracted_subject = canonical_subject
    if not extracted_subject:
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
    elif len(words) > 5 and not canonical_subject:
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

    description = _qualify_map_description(supplied_description) or _STAGE_DESCRIPTIONS.get(
        category,
        "Shows how this idea continues the learning path.",
    )
    if description and description[-1] not in ".!?":
        description += "."
    return title, description

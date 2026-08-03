import json
import re
from typing import Any


_PROFILE_BLOCK = re.compile(
    r"<TOPIC_PROFILE>\s*(.*?)\s*</TOPIC_PROFILE>",
    flags=re.IGNORECASE | re.DOTALL,
)

_LEARNING_PATHS_BLOCK = re.compile(
    r"<LEARNING_PATHS>\s*(.*?)\s*</LEARNING_PATHS>",
    flags=re.IGNORECASE | re.DOTALL,
)

_YOUR_QUESTION_BLOCK = re.compile(
    r"<YOUR_QUESTION>\s*(.*?)\s*</YOUR_QUESTION>",
    flags=re.IGNORECASE | re.DOTALL,
)

_CORE_EXPLANATION_BLOCK = re.compile(
    r"<CORE_EXPLANATION>\s*(.*?)\s*</CORE_EXPLANATION>",
    flags=re.IGNORECASE | re.DOTALL,
)

_LEARNING_LOOP_BLOCK = re.compile(
    r"<LEARNING_LOOP>\s*(.*?)\s*</LEARNING_LOOP>",
    flags=re.IGNORECASE | re.DOTALL,
)

_CONTINUE_JOURNEY_BLOCK = re.compile(
    r"<CONTINUE_JOURNEY>\s*(.*?)\s*</CONTINUE_JOURNEY>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _correct_difficulty(
    rows: list[tuple[str, str]],
    user_query: str = "",
) -> list[tuple[str, str]]:
    """Align difficulty with the depth requested, then with prerequisites."""
    fields = {label.casefold(): value for label, value in rows}
    current_difficulty = fields.get("difficulty", "").casefold()
    profile_text = " ".join(fields.values()).casefold()
    query = re.sub(r"\s+", " ", (user_query or "").strip().casefold())

    def set_difficulty(value: str) -> list[tuple[str, str]]:
        return [
            (label, value) if label.casefold() == "difficulty" else (label, item)
            for label, item in rows
        ]

    numbered_meiotic_stage = r"(?:meiosis|prophase|metaphase|anaphase|telophase)"
    if re.search(
        rf"\b({numbered_meiotic_stage})\s+(?:i|1)\b.*\b\1\s+(?:ii|2)\b",
        query,
        flags=re.IGNORECASE,
    ):
        # Comparing the two meiotic divisions or their corresponding stages
        # presupposes chromosome structure, homolog/sister distinction and the
        # meiotic sequence. It is therefore consistently intermediate.
        return set_difficulty("Intermediate")

    action_cues = re.compile(
        r"\b(explain|compare|calculate|derive|prove|show|teach|implement|how|why|what)\b"
    )
    is_bare_topic = bool(
        query
        and "?" not in query
        and len(query.split()) <= 8
        and not action_cues.search(query)
    )
    if is_bare_topic:
        specialized_bare_signals = (
            "crispr", "gene editing", "molecular cloning", "guide rna",
            "enzyme kinetics", "genome editing", "cell culture",
            "bayesian inference", "quantum mechanics", "compiler design",
            "distributed systems", "cryptography",
        )
        if any(signal in profile_text for signal in specialized_bare_signals):
            return set_difficulty("Intermediate")
        return set_difficulty("Beginner")

    advanced_query_cues = (
        "mathematically", "derive", "proof", "matrix calculus",
        "update uncertainty", "update weights", "gradient flow",
        "covariance update", "jacobian", "hessian",
    )
    advanced_foundations = (
        "matrix calculus", "partial derivatives", "multivariable calculus",
        "state-space", "covariance", "automatic differentiation", "jacobian",
    )
    if (
        any(cue in query for cue in advanced_query_cues)
        and any(foundation in profile_text for foundation in advanced_foundations)
    ):
        return set_difficulty("Advanced")

    advanced_topic_signals = (
        "backpropagation",
        "deep neural network",
        "neural network optimization",
        "automatic differentiation",
        "computational graph",
    )
    advanced_math_signals = (
        "partial derivatives",
        "multivariable calculus",
        "chain rule",
        "jacobian",
        "gradient derivation",
    )
    if (
        current_difficulty in {"beginner", "intermediate"}
        and any(signal in profile_text for signal in advanced_topic_signals)
        and any(signal in profile_text for signal in advanced_math_signals)
    ):
        return set_difficulty("Advanced")

    if current_difficulty != "beginner":
        return rows

    intermediate_signals = (
        "amdahl",
        "cache coherence",
        "concurrency",
        "undergraduate linear algebra",
        "quantum mechanics",
        "multivariable calculus",
        "chain rule",
        "gradient-based optimization",
        "pytorch",
        "tensorflow",
        "transfer learning",
        "cnn architectures",
        "throughput modelling",
        "throughput modeling",
        "numa",
        "parallel programming",
        "operating systems scheduling",
        "crispr",
        "gene editing",
        "dna repair",
        "nhej",
        "hdr",
        "bayesian",
        "frequentist",
        "statistical inference",
        "likelihood",
        "asymptotics",
    )
    prerequisites = fields.get("prerequisites", "")
    prerequisite_items = [
        item.strip()
        for item in re.split(r"[;,]", prerequisites)
        if len(item.strip().split()) >= 2
    ]
    substantial_foundations = (
        "calculus",
        "linear algebra",
        "probability theory",
        "conditional probability",
        "optimization",
        "molecular biology",
        "gene expression",
        "repair pathways",
    )
    requires_substantial_foundation = any(
        signal in profile_text for signal in substantial_foundations
    )
    has_layered_prerequisites = len(prerequisite_items) >= 3
    if not (
        any(signal in profile_text for signal in intermediate_signals)
        or requires_substantial_foundation
        or has_layered_prerequisites
    ):
        return rows

    return set_difficulty("Intermediate")


def split_intro_major_areas(value: str) -> tuple[list[str], str]:
    """Split numbered or lettered Introduction clauses into complete bullets."""
    source = re.sub(r"\s+", " ", str(value or "")).strip()
    marker_matches = list(
        re.finditer(r"\(([0-9]+|[a-z])\)\s*", source, flags=re.IGNORECASE)
    )
    if len(marker_matches) >= 2:
        lead = source[: marker_matches[0].start()].strip()
        lead = re.sub(r"[,:;â€”â€“-]+$", "", lead).strip()
        areas: list[str] = []
        for index, match in enumerate(marker_matches):
            end = marker_matches[index + 1].start() if index + 1 < len(marker_matches) else len(source)
            area = source[match.end() : end].strip()
            area = re.sub(r"^(?:and\s+)", "", area, flags=re.IGNORECASE)
            area = re.sub(r";?\s+and\s*$", "", area, flags=re.IGNORECASE)
            area = re.sub(r"[;,.\s]+$", "", area).strip()
            if area:
                areas.append(area[0].upper() + area[1:])
        if len(areas) >= 2:
            return areas, lead

    return [], source


def extract_topic_profile(
    text: str,
    user_query: str = "",
) -> tuple[list[tuple[str, str]], str]:
    source = (text or "").strip()
    match = _PROFILE_BLOCK.search(source)
    if not match:
        return [], source

    body = _PROFILE_BLOCK.sub("", source, count=1).strip()
    raw_profile = match.group(1).strip()
    raw_profile = re.sub(r"^```(?:json)?\s*", "", raw_profile, flags=re.IGNORECASE)
    raw_profile = re.sub(r"\s*```$", "", raw_profile)

    try:
        parsed: Any = json.loads(raw_profile)
    except (TypeError, ValueError):
        return [], body

    if not isinstance(parsed, dict):
        return [], body

    rows: list[tuple[str, str]] = []
    for raw_label, raw_value in parsed.items():
        label = re.sub(r"\s+", " ", str(raw_label or "")).strip()
        value = re.sub(r"\s+", " ", str(raw_value or "")).strip()
        if not label or not value:
            continue
        if value.lower() in {"none", "unknown", "n/a", "not applicable"}:
            continue
        rows.append((label[:60], value[:300]))
        if len(rows) == 10:
            break

    return _correct_difficulty(rows, user_query), body


def extract_learning_paths(
    text: str,
) -> tuple[list[tuple[str, list[str]]], str]:
    source = (text or "").strip()
    match = _LEARNING_PATHS_BLOCK.search(source)
    if not match:
        return [], source

    body = _LEARNING_PATHS_BLOCK.sub("", source, count=1).strip()
    raw_paths = match.group(1).strip()
    raw_paths = re.sub(r"^```(?:json)?\s*", "", raw_paths, flags=re.IGNORECASE)
    raw_paths = re.sub(r"\s*```$", "", raw_paths)

    try:
        parsed: Any = json.loads(raw_paths)
    except (TypeError, ValueError):
        return [], body

    if not isinstance(parsed, dict):
        return [], body

    groups: list[tuple[str, list[str]]] = []
    for raw_label, raw_questions in parsed.items():
        label = re.sub(r"\s+", " ", str(raw_label or "")).strip()
        if not label or not isinstance(raw_questions, list):
            continue

        questions: list[str] = []
        for raw_question in raw_questions:
            question = re.sub(r"\s+", " ", str(raw_question or "")).strip()
            if question:
                questions.append(question[:240])
            if len(questions) == 3:
                break

        if questions:
            groups.append((label[:60], questions))
        if len(groups) == 5:
            break

    return groups, body


def extract_your_question(text: str) -> tuple[dict[str, str], str]:
    """Extract InI's concise interpretation of the learner's exact question."""
    source = (text or "").strip()
    match = _YOUR_QUESTION_BLOCK.search(source)
    if not match:
        return {}, source

    body = _YOUR_QUESTION_BLOCK.sub("", source, count=1).strip()
    raw_question = match.group(1).strip()
    raw_question = re.sub(r"^```(?:json)?\s*", "", raw_question, flags=re.IGNORECASE)
    raw_question = re.sub(r"\s*```$", "", raw_question)

    try:
        parsed: Any = json.loads(raw_question)
    except (TypeError, ValueError):
        return {}, body

    if not isinstance(parsed, dict):
        return {}, body

    result: dict[str, str] = {}
    for field in ("Question", "Intent", "Learning goal"):
        value = re.sub(r"\s+", " ", str(parsed.get(field) or "")).strip()
        if value:
            result[field] = value[:500]

    return result, body


def extract_core_explanation(text: str) -> tuple[dict[str, Any], str]:
    """Extract a structured, progressively disclosed answer to the user's question."""
    source = (text or "").strip()
    match = _CORE_EXPLANATION_BLOCK.search(source)
    if match:
        body = _CORE_EXPLANATION_BLOCK.sub("", source, count=1).strip()
        raw_explanation = match.group(1).strip()
    else:
        opening = re.search(r"<CORE_EXPLANATION>\s*", source, re.IGNORECASE)
        if not opening:
            return {}, source

        tail = source[opening.end():]
        next_block = re.search(
            r"<(?:LEARNING_LOOP|CONTINUE_JOURNEY)>\s*",
            tail,
            re.IGNORECASE,
        )
        if next_block:
            raw_explanation = tail[:next_block.start()].strip()
            remainder = tail[next_block.start():]
            body = (source[:opening.start()] + remainder).strip()
        else:
            raw_explanation = tail.strip()
            body = source[:opening.start()].strip()
    raw_explanation = re.sub(
        r"^```(?:json)?\s*", "", raw_explanation, flags=re.IGNORECASE
    )
    raw_explanation = re.sub(r"\s*```$", "", raw_explanation)

    try:
        parsed: Any = json.loads(raw_explanation)
    except (TypeError, ValueError):
        parsed = None

    if not isinstance(parsed, dict):
        def tagged_value(tag: str) -> str:
            match = re.search(
                rf"<{tag}>\s*(.*?)(?:\s*</{tag}>|(?=\s*<[A-Z_]+>)|$)",
                raw_explanation,
                flags=re.IGNORECASE | re.DOTALL,
            )
            return match.group(1).strip() if match else ""

        parsed = {
            "Title": tagged_value("TITLE"),
            "Overview": tagged_value("OVERVIEW"),
            "Update rule": tagged_value("UPDATE_RULE"),
            "Key insight": tagged_value("KEY_INSIGHT"),
            "Worked example": tagged_value("WORKED_EXAMPLE"),
        }
        variables_block = tagged_value("VARIABLES")
        variables: dict[str, str] = {}
        for line in variables_block.splitlines():
            # Models occasionally place several ``symbol :: meaning`` pairs
            # on one semicolon-delimited line. Split those pairs first, while
            # retaining the final delimiter repair for symbols such as
            # ``L( :: ) :: loss``.
            entries = re.split(r";\s*(?=[^;\n]{1,60}\s*::)", line)
            for entry in entries:
                symbol, separator, meaning = entry.rpartition("::")
                if separator and symbol.strip() and meaning.strip():
                    clean_symbol = re.sub(r"\s*::\s*", "·", symbol.strip())
                    variables[clean_symbol] = meaning.strip()
        parsed["Variables"] = variables

        steps_block = tagged_value("STEPS")
        steps: list[dict[str, str]] = []
        for line in steps_block.splitlines():
            heading, separator, explanation = line.partition("::")
            if separator and heading.strip() and explanation.strip():
                steps.append(
                    {
                        "Heading": heading.strip(),
                        "Explanation": explanation.strip(),
                    }
                )
        parsed["Steps"] = steps

    result: dict[str, Any] = {}
    leaked_prompt_placeholders = {
        "two concise sentences",
        "the central equation or governing relationship",
        "a precise, topic-specific explanation title",
        "the single most important takeaway",
        "a compact numerical or concrete example",
    }
    for field, limit in (
        ("Title", 120),
        ("Overview", 900),
        ("Update rule", 240),
        ("Key insight", 500),
        ("Worked example", 1200),
    ):
        value = re.sub(r"\s+", " ", str(parsed.get(field) or "")).strip()
        if value.casefold() in leaked_prompt_placeholders:
            value = ""
        if field == "Update rule":
            for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
                missing = value.count(opening) - value.count(closing)
                if 0 < missing <= 2:
                    value += closing * missing
        if value:
            result[field] = value[:limit]

    raw_variables = parsed.get("Variables")
    if isinstance(raw_variables, dict):
        variables: list[tuple[str, str]] = []
        for raw_symbol, raw_meaning in raw_variables.items():
            symbol = re.sub(r"\s+", " ", str(raw_symbol or "")).strip()
            meaning = re.sub(r"\s+", " ", str(raw_meaning or "")).strip()
            if symbol and meaning:
                variables.append((symbol[:40], meaning[:240]))
            if len(variables) == 6:
                break
        if variables:
            result["Variables"] = variables

    raw_steps = parsed.get("Steps")
    if isinstance(raw_steps, list):
        steps: list[dict[str, str]] = []
        for raw_step in raw_steps:
            if not isinstance(raw_step, dict):
                continue
            heading = re.sub(
                r"\s+", " ", str(raw_step.get("Heading") or "")
            ).strip()
            explanation = re.sub(
                r"\s+", " ", str(raw_step.get("Explanation") or "")
            ).strip()
            if heading and explanation:
                steps.append(
                    {"Heading": heading[:100], "Explanation": explanation[:600]}
                )
            if len(steps) == 6:
                break
        if steps:
            result["Steps"] = steps

    return result, body


def extract_learning_loop(text: str) -> tuple[dict[str, Any], str]:
    """Extract a compact causal or operational sequence for visual rendering."""
    source = (text or "").strip()
    match = _LEARNING_LOOP_BLOCK.search(source)
    if not match:
        return {}, source

    body = _LEARNING_LOOP_BLOCK.sub("", source, count=1).strip()
    raw_loop = match.group(1).strip()

    def tagged_value(tag: str) -> str:
        tagged_match = re.search(
            rf"<{tag}>\s*(.*?)(?:\s*</{tag}>|(?=\s*<[A-Z_]+>)|$)",
            raw_loop,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return tagged_match.group(1).strip() if tagged_match else ""

    stages: list[dict[str, str]] = []
    for line in tagged_value("STAGES").splitlines():
        heading, separator, explanation = line.partition("::")
        heading = re.sub(r"\s+", " ", heading).strip()
        explanation = re.sub(r"\s+", " ", explanation).strip()
        if separator and heading and explanation:
            stages.append(
                {"Heading": heading[:90], "Explanation": explanation[:260]}
            )
        if len(stages) == 6:
            break

    outcome = re.sub(r"\s+", " ", tagged_value("OUTCOME")).strip()
    if not stages:
        return {}, body

    result: dict[str, Any] = {"Stages": stages}
    if outcome:
        result["Outcome"] = outcome[:500]
    return result, body


def extract_continue_journey(text: str) -> tuple[dict[str, Any], str]:
    """Extract the final three-step learning roadmap from an introduction response."""
    source = (text or "").strip()
    match = _CONTINUE_JOURNEY_BLOCK.search(source)
    if match:
        body = _CONTINUE_JOURNEY_BLOCK.sub("", source, count=1).strip()
        raw_journey = match.group(1).strip()
    else:
        opening = re.search(r"<CONTINUE_JOURNEY>\s*", source, re.IGNORECASE)
        if not opening:
            return {}, source

        tail = source[opening.end():]
        destination_line = re.search(
            r"<DESTINATION>\s*([^\r\n<]+)", tail, re.IGNORECASE
        )
        if destination_line:
            raw_journey = tail[:destination_line.end()].strip()
            remainder = tail[destination_line.end():].lstrip("\r\n ")
            body = (source[:opening.start()] + remainder).strip()
        else:
            raw_journey = tail.strip()
            body = source[:opening.start()].strip()

    def tagged_value(tag: str) -> str:
        tagged_match = re.search(
            rf"<{tag}>\s*(.*?)(?:\s*</{tag}>|(?=\s*<[A-Z_]+>)|$)",
            raw_journey,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return tagged_match.group(1).strip() if tagged_match else ""

    directions: list[dict[str, str]] = []
    for line in tagged_value("DIRECTIONS").splitlines():
        heading, separator, explanation = line.partition("::")
        heading = re.sub(r"^\s*\d+[.)]\s*", "", heading)
        heading = re.sub(r"\s+", " ", heading).strip()
        explanation = re.sub(r"\s+", " ", explanation).strip()
        if separator and heading and explanation:
            directions.append(
                {"Heading": heading[:140], "Explanation": explanation[:300]}
            )
        if len(directions) == 3:
            break

    destination = re.sub(r"\s+", " ", tagged_value("DESTINATION")).strip()
    destination = re.sub(r"\byou['’]?l\b", "you'll", destination, flags=re.IGNORECASE)
    if not directions:
        return {}, body

    result: dict[str, Any] = {"Directions": directions}
    if destination:
        result["Destination"] = destination[:500]
    return result, body


def split_prerequisites(
    rows: list[tuple[str, str]],
) -> tuple[list[tuple[str, str]], str]:
    """Remove prerequisite metadata from profile rows for separate rendering."""
    profile_rows: list[tuple[str, str]] = []
    prerequisite = ""
    prerequisite_labels = {
        "prerequisite",
        "prerequisites",
        "prior knowledge",
        "recommended background",
    }

    for label, value in rows or []:
        normalized_label = re.sub(r"\s+", " ", label.lower()).strip()
        if normalized_label in prerequisite_labels and not prerequisite:
            prerequisite = value.strip()
            continue
        profile_rows.append((label, value))

    return profile_rows, prerequisite


def split_prerequisite_items(value: str) -> list[str]:
    """Split compact prerequisite metadata without breaking parenthetical lists."""
    source = re.sub(r"\s+", " ", value or "").strip()
    if not source:
        return []

    items: list[str] = []
    buffer: list[str] = []
    depth = 0
    for character in source:
        if character in "([{" :
            depth += 1
        elif character in ")]}":
            depth = max(0, depth - 1)

        if depth == 0 and character in ";,":
            item = "".join(buffer).strip(" .")
            if item:
                items.append(item)
            buffer = []
            continue
        buffer.append(character)

    final_item = "".join(buffer).strip(" .")
    if final_item:
        items.append(final_item)

    return items if len(items) > 1 else ([source.strip(" .")] if source else [])

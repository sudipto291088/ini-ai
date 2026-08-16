from __future__ import annotations

import json
import re
from typing import Any


REQUIRED_BLOCKS = (
    "TOPIC_PROFILE",
    "LEARNING_PATHS",
    "YOUR_QUESTION",
    "CORE_EXPLANATION",
    "LEARNING_LOOP",
    "CONTINUE_JOURNEY",
)

KNOWN_TAGS = {
    *REQUIRED_BLOCKS,
    "TITLE",
    "OVERVIEW",
    "UPDATE_RULE",
    "VARIABLES",
    "STEPS",
    "KEY_INSIGHT",
    "WORKED_EXAMPLE",
    "STAGES",
    "OUTCOME",
    "DIRECTIONS",
    "DESTINATION",
}

PLACEHOLDER_TEXT = (
    "a precise, topic-specific explanation title",
    "two concise sentences",
    "the central equation or governing relationship",
    "a single presentation-ready equation or governing relationship",
    "symbol :: compact meaning",
    "one concise explanatory sentence",
    "the single most important takeaway",
    "a compact numerical or concrete example",
    "one concise sentence explaining what happens",
    "one concise sentence explaining what completing or repeating the sequence achieves",
)

GENERIC_LOOP_PHRASES = (
    "define the topic",
    "closest related concepts",
    "relate the main components",
    "representative scenario",
    "purpose, major trade-offs, and limitations",
    "explain the topic",
    "neighboring ideas",
    "define the two alternatives",
    "decision being examined",
    "which alternative fits",
    "decision boundaries",
)

GENERIC_JOURNEY_PHRASES = (
    "clarify the decision criteria",
    "examine representative scenarios",
    "explore boundaries and hybrids",
    "which alternative fits each one",
    "context-aware choice",
)


def _block(text: str, name: str) -> str:
    match = re.search(
        rf"<{name}>\s*(.*?)\s*</{name}>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _tag_value(text: str, name: str) -> str:
    return _block(text, name)


def _parse_json_block(text: str, name: str) -> Any:
    raw = _block(text, name)
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _repair_update_rule(text: str) -> tuple[str, bool]:
    pattern = re.compile(
        r"<UPDATE_RULE>\s*(.*?)\s*</UPDATE_RULE>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return text, False

    value = re.sub(r"\s+", " ", match.group(1)).strip()
    repaired = value
    for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
        missing = repaired.count(opening) - repaired.count(closing)
        if 0 < missing <= 2:
            repaired += closing * missing
    if repaired == value:
        return text, False
    replacement = f"<UPDATE_RULE>{repaired}</UPDATE_RULE>"
    return text[: match.start()] + replacement + text[match.end() :], True


def _repair_rag_relationship(text: str, subject: str) -> tuple[str, bool]:
    """Replace a common product-form RAG shortcut with marginalization."""
    evidence = f"{subject} {text}".casefold()
    if not any(
        marker in evidence
        for marker in ("retrieval-augmented", "retrieval augmented", " rag ")
    ):
        return text, False

    current = _tag_value(_block(text, "CORE_EXPLANATION"), "UPDATE_RULE")
    normalized = re.sub(r"\s+", " ", current).casefold()
    product_shortcut = (
        "p(answer | query, docs)" in normalized
        and "p(docs | query)" in normalized
    )
    weighted_shortcut = (
        ("pgen" in normalized or "p_generate" in normalized)
        and any(
            marker in normalized
            for marker in ("pret", "scoreretriever", "p_retrieve")
        )
        and ("∝" in current or "proportional" in normalized)
    )
    if not (product_shortcut or weighted_shortcut):
        return text, False

    if weighted_shortcut:
        corrected = (
            "P(answer | q) = sum_c [P_retrieve(c | q) * "
            "P_generate(answer | q, c)]"
        )
    else:
        corrected = (
            "p(answer | query) = sum_docs [p(docs | query) * "
            "p(answer | query, docs)]"
        )
    repaired = re.sub(
        r"<UPDATE_RULE>.*?</UPDATE_RULE>",
        f"<UPDATE_RULE>{corrected}</UPDATE_RULE>",
        text,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if weighted_shortcut:
        variables = _block(repaired, "VARIABLES")
        additions = {
            "answer": "generated answer",
            "q": "user query",
            "c": "retrieved context",
            "P_retrieve": "normalized retrieval probability",
            "P_generate": "generator probability conditioned on retrieved context",
        }
        existing = {
            line.split("::", 1)[0].strip().casefold()
            for line in variables.splitlines()
            if "::" in line
        }
        missing = [
            f"{name} :: {meaning}"
            for name, meaning in additions.items()
            if name.casefold() not in existing
        ]
        if missing:
            replacement = variables.rstrip() + "\n" + "\n".join(missing)
            repaired = re.sub(
                r"<VARIABLES>.*?</VARIABLES>",
                f"<VARIABLES>{replacement}</VARIABLES>",
                repaired,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            )
    return repaired, repaired != text


def _repair_quantum_entanglement_content(
    text: str,
    subject: str,
) -> tuple[str, list[str]]:
    if "entanglement" not in (subject or "").casefold():
        return text, []

    repaired = text
    repairs: list[str] = []
    if "bell" in repaired.casefold():
        bell_pattern = re.compile(
            r"\(\s*\|0(?P<ket0>>|⟩)\s*\+\s*\|1(?P<ket1>>|⟩)\s*\)"
            r"\s*/\s*(?:√\s*2|sqrt\s*\(?\s*2\s*\)?)",
            flags=re.IGNORECASE,
        )

        def replace_bell(match: re.Match[str]) -> str:
            ket = "⟩" if "⟩" in match.group(0) else ">"
            return f"(|00{ket} + |11{ket})/√2"

        repaired, count = bell_pattern.subn(replace_bell, repaired)
        if count:
            repairs.append("corrected Bell-pair basis states")

    loop = _block(repaired, "LEARNING_LOOP")
    generic_hits = [phrase for phrase in GENERIC_LOOP_PHRASES if phrase in loop.casefold()]
    if len(generic_hits) >= 2:
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Represent the joint state :: Write the composite system as one state that cannot be factored into independent subsystem states.
2. Choose measurement bases :: Specify which observable is measured on each subsystem and the outcomes each basis permits.
3. Compute joint probabilities :: Use amplitudes from the shared state to calculate correlated outcome probabilities.
4. Compare with classical bounds :: Test whether the correlations can be reproduced by shared classical variables, for example through a Bell inequality.
5. Interpret the result :: Separate nonclassical correlation from faster-than-light signalling and connect it to quantum-information tasks.
</STAGES>
<OUTCOME>The learner can recognize an entangled state, predict its measurement correlations, and explain why those correlations are nonclassical without implying controllable superluminal communication.</OUTCOME>
</LEARNING_LOOP>"""
        repaired = re.sub(
            r"<LEARNING_LOOP>.*?</LEARNING_LOOP>",
            replacement,
            repaired,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
        repairs.append("replaced generic entanglement learning loop")

    return repaired, repairs


def validate_structured_learning_answer(answer: str) -> dict[str, Any]:
    """Repair safe defects and reject incomplete structured learning output."""
    source = (answer or "").strip()
    issues: list[str] = []
    repairs: list[str] = []

    source = re.sub(r"^```(?:text|markdown)?\s*", "", source, flags=re.IGNORECASE)
    source = re.sub(r"\s*```$", "", source)
    source, formula_repaired = _repair_update_rule(source)
    if formula_repaired:
        repairs.append("balanced update-rule delimiters")
    source, leaked_rule_count = re.subn(
        r"(?<!<)(?<!</)\bUPDATE_RULE\b(?!>)",
        "governing relationship",
        source,
    )
    if leaked_rule_count:
        repairs.append("replaced leaked update-rule placeholder references")

    lowered = source.casefold()
    leaked = [item for item in PLACEHOLDER_TEXT if item in lowered]
    if leaked:
        issues.append("prompt placeholder text leaked into the response")

    unknown_tags = {
        match.group(1).upper()
        for match in re.finditer(r"</?([A-Z][A-Z_]{2,})>", source)
        if match.group(1).upper() not in KNOWN_TAGS
    }
    if unknown_tags:
        issues.append("unknown structured tags: " + ", ".join(sorted(unknown_tags)))

    for name in REQUIRED_BLOCKS:
        if not _block(source, name):
            issues.append(f"missing or empty {name} block")

    profile = _parse_json_block(source, "TOPIC_PROFILE")
    required_profile = {
        "entity type", "broad field", "subject", "prerequisites",
        "related topics", "difficulty",
    }
    if not isinstance(profile, dict):
        issues.append("TOPIC_PROFILE is not valid JSON")
    else:
        labels = {str(key).strip().casefold() for key in profile}
        missing = sorted(required_profile - labels)
        if missing:
            issues.append("TOPIC_PROFILE missing: " + ", ".join(missing))

    subject = str(profile.get("Subject") or "") if isinstance(profile, dict) else ""
    source, rag_repaired = _repair_rag_relationship(source, subject)
    if rag_repaired:
        repairs.append("corrected RAG marginalization relationship")
    source, semantic_repairs = _repair_quantum_entanglement_content(source, subject)
    repairs.extend(semantic_repairs)

    paths = _parse_json_block(source, "LEARNING_PATHS")
    if not isinstance(paths, dict) or len(paths) != 5:
        issues.append("LEARNING_PATHS must contain exactly five groups")
    elif any(not isinstance(value, list) or not 2 <= len(value) <= 3 for value in paths.values()):
        issues.append("each LEARNING_PATHS group must contain two or three questions")

    question = _parse_json_block(source, "YOUR_QUESTION")
    if not isinstance(question, dict) or any(
        not str(question.get(key) or "").strip()
        for key in ("Question", "Intent", "Learning goal")
    ):
        issues.append("YOUR_QUESTION is missing required content")

    core = _block(source, "CORE_EXPLANATION")
    for tag in ("TITLE", "OVERVIEW", "KEY_INSIGHT"):
        if not _tag_value(core, tag):
            issues.append(f"CORE_EXPLANATION missing {tag}")
    update_rule = _tag_value(core, "UPDATE_RULE")
    variables = _tag_value(core, "VARIABLES")
    if update_rule and "::" not in variables:
        issues.append("formula is present without variable definitions")
    variable_symbols = [
        line.split("::", 1)[0].strip()
        for line in variables.splitlines()
        if "::" in line
    ]
    compact_symbols = [
        symbol
        for symbol in variable_symbols
        if symbol and len(symbol) <= 24 and " " not in symbol
    ]
    if update_rule and len(compact_symbols) >= 2:
        represented = sum(
            bool(re.search(rf"(?<!\w){re.escape(symbol)}(?!\w)", update_rule))
            for symbol in compact_symbols
        )
        if represented * 2 < len(compact_symbols):
            issues.append("formula does not use its declared variables")
    steps = [line for line in _tag_value(core, "STEPS").splitlines() if "::" in line]
    if not 4 <= len(steps) <= 6:
        issues.append("CORE_EXPLANATION must contain four to six complete steps")

    loop = _block(source, "LEARNING_LOOP")
    stages = [line for line in _tag_value(loop, "STAGES").splitlines() if "::" in line]
    if not 5 <= len(stages) <= 6 or not _tag_value(loop, "OUTCOME"):
        issues.append("LEARNING_LOOP is incomplete")
    generic_hits = [phrase for phrase in GENERIC_LOOP_PHRASES if phrase in loop.casefold()]
    if len(generic_hits) >= 2:
        issues.append("LEARNING_LOOP uses a generic topic template")

    journey = _block(source, "CONTINUE_JOURNEY")
    directions = [
        line for line in _tag_value(journey, "DIRECTIONS").splitlines() if "::" in line
    ]
    if len(directions) != 3 or not _tag_value(journey, "DESTINATION"):
        issues.append("CONTINUE_JOURNEY is incomplete")
    journey_generic_hits = [
        phrase for phrase in GENERIC_JOURNEY_PHRASES if phrase in journey.casefold()
    ]
    if len(journey_generic_hits) >= 2:
        issues.append("CONTINUE_JOURNEY uses a generic comparison template")

    narrative = source
    for name in REQUIRED_BLOCKS:
        narrative = re.sub(
            rf"<{name}>.*?</{name}>",
            "",
            narrative,
            flags=re.IGNORECASE | re.DOTALL,
        )
    for heading in ("Purpose:", "Major areas:", "Who should study this next:"):
        if heading.casefold() not in narrative.casefold():
            issues.append(f"Introduction missing {heading[:-1]} heading")

    # A Bell pair must contain two-qubit basis states. A common malformed
    # generation drops one qubit and writes (|0> + |1>)/sqrt(2), which is a
    # single-qubit superposition rather than entanglement.
    if "entanglement" in subject.casefold() and "bell" in source.casefold():
        compact = re.sub(r"\s+", "", source)
        malformed_bell = re.search(
            r"\(\|0(?:>|⟩)[+]\|1(?:>|⟩)\)/(?:√2|sqrt\(?2\)?)",
            compact,
            flags=re.IGNORECASE,
        )
        if malformed_bell:
            issues.append("Bell-state formula contains single-qubit basis states")

    # The renderer can safely omit or simplify one malformed optional card.
    # Withholding the entire answer is reserved for genuinely incomplete
    # output: leaked prompt scaffolding or several absent structural blocks.
    present_required_blocks = sum(bool(_block(source, name)) for name in REQUIRED_BLOCKS)
    fatal_issues = [
        issue
        for issue in issues
        if issue.startswith("prompt placeholder text leaked")
    ]
    if present_required_blocks < 4:
        fatal_issues.extend(
            issue for issue in issues if issue.startswith("missing or empty ")
        )

    return {
        "answer": source,
        "valid": not issues,
        "displayable": not fatal_issues,
        "fatal_issues": fatal_issues,
        "issues": issues,
        "repairs": repairs,
    }


__all__ = ["validate_structured_learning_answer"]

"""Shared subject metadata and conservative profile normalization."""

import re


_QUESTION_OPENERS = re.compile(
    r"^(?:please\s+)?(?:tell me about|explain|describe|define|introduce|summarize|"
    r"give me (?:an? )?(?:overview|introduction) (?:of|to)|what (?:is|are)|"
    r"how (?:does|do|is|are)|why (?:does|do|is|are))\s+",
    flags=re.IGNORECASE,
)


def canonical_subject(text: str) -> str:
    """Turn a user request into a grammatical subject without inventing facts."""
    value = re.sub(r"\s+", " ", str(text or "")).strip(" \t\r\n?.!:")
    need_match = re.match(
        r"^why\s+(?:do|does)\s+(.+?)\s+need\s+(.+)$",
        value,
        flags=re.IGNORECASE,
    )
    if need_match:
        context, needed = (part.strip(" .?!") for part in need_match.groups())
        return f"{needed} in {context}"
    mechanism_match = re.match(
        r"^how\s+(?:do|does)\s+(.+?)\s+"
        r"(?:work|reduce|allow|enable|affect|improve|increase|decrease|differ|operate)\b",
        value,
        flags=re.IGNORECASE,
    )
    if mechanism_match:
        return mechanism_match.group(1).strip(" .?!")
    previous = None
    while value and value != previous:
        previous = value
        value = _QUESTION_OPENERS.sub("", value).strip(" \t\r\n?.!:")
    return value or "Requested topic"


def subject_metadata(text: str) -> dict[str, str]:
    text = text.casefold()
    entries = (
        (r"\bcrisp[\s-]?dm\b", {
            "Subject": "CRISP-DM",
            "Full form": "Cross-Industry Standard Process for Data Mining",
            "Entity type": "Data-mining process model",
            "Broad field": "Data Mining / Data Science",
            "Related topics": "Business Understanding; Data Understanding; Data Preparation; Modeling; Evaluation; Deployment",
            "Prerequisites": "No specialized prior knowledge is required; familiarity with basic data-project and business-goal terminology is helpful",
            "Difficulty": "Beginner",
        }),
        (r"\b(?:operating systems?|multitasking|cpu scheduling|process scheduling)\b", {
            "Subject": "Operating systems",
            "Entity type": "Operating-system mechanism",
            "Broad field": "Computer Science / Operating Systems",
            "Related topics": "Processes, threads, CPU scheduling, context switching, virtual memory, synchronization, and I/O",
            "Prerequisites": "CPU and memory basics; program execution; basic computer architecture; input/output",
        }),
        (r"\bactivation functions?\b", {
            "Subject": "Activation functions in neural networks",
            "Entity type": "Neural-network mathematical component",
            "Broad field": "Machine Learning / Deep Learning",
            "Related topics": "Nonlinearity, affine transformations, ReLU, sigmoid, tanh, GELU, backpropagation, and gradient flow",
            "Prerequisites": "Functions; vectors and matrices; weighted sums; derivatives for the mathematical explanation",
        }),
        (r"\b(?:quantum entanglement|entangled states?)\b", {
            "Subject": "Quantum entanglement",
            "Entity type": "Quantum phenomenon",
            "Broad field": "Physics / Quantum Information",
            "Related topics": "Separable states, density matrices, measurement, Bell inequalities, quantum steering, and decoherence",
            "Prerequisites": "Probability; vectors and complex numbers; quantum states; superposition; quantum measurement",
        }),
    )
    for pattern, fields in entries:
        if re.search(pattern, text):
            result = dict(fields)
            if result["Subject"] == "Operating systems" and re.search(
                r"multitask|multiple programs|scheduling|concurrent|same time", text
            ):
                result["Subject"] = "Operating-system multitasking"
            if result["Subject"] == "Quantum entanglement" and "correlation" in text:
                result["Subject"] = "Quantum entanglement and classical correlation"
            return result
    return {}


def fallback_subject_metadata(text: str) -> dict[str, str]:
    """Return useful, non-placeholder metadata for an arbitrary learning topic."""
    subject = canonical_subject(text)
    evidence = f" {subject.casefold()} "
    families = (
        (("machine learning", "neural", "data science", "regression", "classification",
          "principal component", " pca ", "transfer learning", "pretraining"),
         "Data-science concept", "Data Science / Machine Learning"),
        (("algorithm", "software", "database", "programming", "computer", "network",
          "distributed", "consensus"),
         "Technical concept", "Computer Science / Technology"),
        (("physics", "quantum", "energy", "force", "thermodynamic"),
         "Scientific concept", "Physics"),
        (("chemistry", "chemical", "molecule", "reaction", "polymer"),
         "Scientific concept", "Chemistry"),
        (("biology", "cell", "genetic", "gene", "ecology", "organism"),
         "Scientific concept", "Biology / Life Sciences"),
        (("economics", "inflation", "market", "finance", "accounting"),
         "Economic concept", "Economics / Finance"),
        (("history", "historical", "war", "empire", "revolution"),
         "Historical topic", "History"),
        (("law", "legal", "regulation", "policy"),
         "Legal or policy topic", "Law / Public Policy"),
        (("literature", "novel", "poetry", "language", "linguistic"),
         "Humanities topic", "Language / Humanities"),
        (("process", "method", "framework", "model", "methodology"),
         "Process or framework", "Interdisciplinary methods"),
    )
    entity_type, broad_field = "Topic or concept", "General knowledge"
    for markers, candidate_type, candidate_field in families:
        if any(marker in evidence for marker in markers):
            entity_type, broad_field = candidate_type, candidate_field
            break
    return {
        "Subject": subject,
        "Entity type": entity_type,
        "Broad field": broad_field,
        "Related topics": (
            f"Definitions of {subject}; core mechanisms; applications; evidence; limitations"
        ),
        "Prerequisites": "No specialized prior knowledge is assumed for an introductory overview",
        "Difficulty": "Beginner",
    }


def normalize_topic_profile(
    profile: dict[str, object] | None,
    user_query: str,
) -> dict[str, str]:
    """Reconcile generated metadata with shared defaults and verified overrides."""
    generated: dict[str, str] = {}
    canonical_labels = {
        "entity type": "Entity type",
        "broad field": "Broad field",
        "subject": "Subject",
        "full form": "Full form",
        "research area": "Research area",
        "mathematical foundation": "Mathematical foundation",
        "prerequisites": "Prerequisites",
        "related topics": "Related topics",
        "typical applications": "Typical applications",
        "difficulty": "Difficulty",
    }
    placeholders = {
        "learning inquiry", "learning question", "not yet classified",
        "knowledge and inquiry", "specific prerequisites have not yet been identified for this query.",
        "unknown", "n/a", "none identified", "include only when applicable",
        "specific type", "specific field", "complete noun phrase", "minimal prior knowledge",
        "specific neighboring topics", "beginner, intermediate, or advanced",
    }
    for raw_key, raw_value in (profile or {}).items():
        key = canonical_labels.get(str(raw_key).strip().casefold(), str(raw_key).strip())
        value = re.sub(r"\s+", " ", str(raw_value or "")).strip()
        if key and value and value.casefold() not in placeholders:
            generated[key] = value

    defaults = fallback_subject_metadata(user_query)
    for key, value in defaults.items():
        generated.setdefault(key, value)

    # Verified metadata takes precedence over both model output and inference.
    generated.update(subject_metadata(user_query))
    if generated.get("Difficulty", "").casefold() not in {
        "beginner", "intermediate", "advanced", "expert",
    }:
        generated["Difficulty"] = defaults["Difficulty"]
    return generated


__all__ = [
    "canonical_subject",
    "fallback_subject_metadata",
    "normalize_topic_profile",
    "subject_metadata",
]

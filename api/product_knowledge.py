"""Stable product knowledge for questions about InI.ai itself."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


PRODUCT_KNOWLEDGE_VERSION = 6


def _normalize(text: str) -> str:
    value = (text or "").lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9.']+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def answer_ini_product_query(
    text: str,
    user_profile: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Return a factual InI product answer, or ``None`` for non-product queries."""
    s = _normalize(text)
    profile = user_profile or {}
    full_name = str(profile.get("full_name") or "").strip()
    preferred_name = str(profile.get("preferred_name") or "").strip()

    if full_name and re.search(
        r"\b(?:do you (?:know|remember)|what(?:'s| is)|tell me)\s+my\s+(?:full\s+)?name\b",
        s,
    ):
        preferred_detail = (
            f", and you prefer to be called {preferred_name}" if preferred_name else ""
        )
        return (
            f"You identified yourself to me as {full_name}{preferred_detail}. "
            "I remember that within this conversation."
        )

    if preferred_name and re.search(r"\bi am\s+sid\b.*\bcreator\b", s):
        return (
            f"Yes, {preferred_name}. I remember that you identified yourself as my creator"
            f"{f', {full_name}' if full_name else ''}."
        )

    # A second-person pronoun inside an educational question does not make the
    # question about InI.  Require either an explicit InI reference or a
    # product-shaped form of address before any product answer can intercept
    # the normal learning pipeline.
    explicit_ini_reference = bool(re.search(r"\bini(?:\.ai)?\b", s))
    ini_response_term_reference = bool(
        re.search(
            r"\b(?:your|ini(?:\.ai)?(?:'s)?)\s+(?:initial answer|knowledge structure|ia|ks)\b",
            s,
        )
        or re.search(
            r"\b(?:initial answer|knowledge structure)\b.*\b(?:ini|your response|your answer)\b",
            s,
        )
        or re.fullmatch(
            r"(?:what (?:is|are)|explain|define|compare)\s+(?:the\s+)?(?:ia|ks|ia and ks|ia vs ks)",
            s,
        )
    )
    response_architecture_reference = bool(
        re.search(
            r"\b(?:how do you answer|ways? you answer|ways? (?:that )?you (?:can )?answer|"
            r"answer layers?|response layers?)\b",
            s,
        )
    )
    second_person_product_reference = bool(
        re.search(
            r"^(?:what (?:exactly )?(?:are|can) you\b|who are you\b|"
            r"how can you help\b|what should i call you\b|tell me about yourself\b|"
            r"(?:what all|which) (?:topics?|subjects?|areas?) (?:do you know|can you cover)\b|"
            r"who (?:created|built|made|designed) you\b|"
            r"why do you create question maps?\b)",
            s,
        )
        or re.search(
            r"\b(?:your (?:current )?(?:version|release|features?|capabilities|"
            r"roadmap|creator|founder|purpose)|(?:versions?|releases?) have you)\b",
            s,
        )
    )
    refers_to_ini = (
        explicit_ini_reference
        or second_person_product_reference
        or ini_response_term_reference
        or response_architecture_reference
    )
    if not s or not refers_to_ini:
        return None

    mentions_ia = bool(re.search(r"\b(?:initial answer|ia)\b", s))
    mentions_ks = bool(re.search(r"\b(?:knowledge structure|ks)\b", s))
    if response_architecture_reference:
        return (
            "I answer through two connected layers. The Initial Answer (IA) gives you the "
            "immediate, conversational explanation, its Topic Profile and prerequisites, and "
            "a focused set of related questions. The Knowledge Structure (KS) is the optional "
            "complete learning layer: it expands the topic into connected concepts, mechanisms, "
            "subtopics, maps, applications, limitations, and a progressive route through them. "
            "The IA helps you understand now; the KS helps you explore the full landscape when "
            "that additional depth is useful."
        )
    if mentions_ia and mentions_ks:
        return (
            "My Initial Answer (IA) is the concise, conversational first layer: it gives the "
            "direct answer, Topic Profile and prerequisites, a focused question set, and a route "
            "to continue. My Knowledge Structure (KS) is the complete learning layer: it expands "
            "the subject into connected concepts, mechanisms, subtopics, questions, maps, and a "
            "progressive path. IA helps you orient quickly; KS helps you study the full landscape."
        )
    if mentions_ia:
        return (
            "My Initial Answer (IA) is the first, conversational layer of a learning response. "
            "It combines a direct explanation with the Topic Profile and prerequisites, a small "
            "set of useful next questions, and an invitation to open the Knowledge Structure. "
            "It answers first without forcing the complete learning landscape on you."
        )
    if mentions_ks:
        return (
            "My Knowledge Structure (KS) is the complete structured learning layer for the active "
            "topic. It develops the subject progressively through its concepts, mechanisms, "
            "subtopics, relationships, questions, maps, applications, and limitations. You can "
            "open it from an Initial Answer when you want the full learning landscape."
        )

    if re.search(r"\b(who|what).*(created|creator|founder|built|made|designed)\b", s) or re.search(
        r"\b(created|creator|founder|built|made|designed).*(you|ini)\b", s
    ):
        return (
            "I was created by Sudipto, who prefers to be called Sid—the founder and product "
            "creator of InI.ai. "
            "He is shaping me as a Question Engine that helps people discover, organize, "
            "and pursue better questions—not merely collect isolated answers."
        )

    if re.search(r"\b(how many|which|previous|earlier|history).*(versions?|releases?)\b", s):
        return (
            "I am currently on v0.1.6. I have six documented releases, from v0.1.1 "
            "through v0.1.6; work before v0.1.1 belonged to the experimental v0 phase "
            "rather than the formal release history."
        )

    earlier_releases = {
        "v0.1.5": (
            "v0.1.5 deepened structured responses, strengthened conversation repair and "
            "capability boundaries, completed Illustrate, redesigned the Introduction, and "
            "improved desktop and mobile reliability."
        ),
        "v0.1.4": (
            "v0.1.4 strengthened conversational intelligence, context switching, guided "
            "discussion, persistent query history, generation states, the First Conversation "
            "Experience, and InI's visual identity."
        ),
        "v0.1.3": (
            "v0.1.3 refined New Chat, adaptive Topic Profiles, Question Map interactions, "
            "visitor privacy isolation, local timestamps, and My New Learning."
        ),
        "v0.1.2": (
            "v0.1.2 expanded technical coverage, strengthened topic recognition and ambiguity "
            "correction, preserved specific AI subjects, and clarified the interface."
        ),
        "v0.1.1": (
            "v0.1.1 established the stable public deployment, structured learning workflow, "
            "Question Maps, follow-ups, answer continuation, and session persistence."
        ),
    }
    for version, summary in earlier_releases.items():
        if version in s:
            return summary

    if re.search(r"\b(current|latest|new|special|update|changed|improved).*(versions?|releases?|v0.1.6)\b", s) or re.search(
        r"\b(versions?|releases?|v0.1.6).*(current|latest|new|special|update|changed|improved)\b", s
    ):
        return (
            "v0.1.6 is my current release. It expands trusted knowledge retrieval, strengthens "
            "topic and conversation routing, makes Knowledge Maps more meaningful, improves "
            "direct-answer navigation, and refines the New Chat, sidebar, mobile, and "
            "narrow-browser experiences."
        )

    if re.search(r"\b(plan|planned|planning|roadmap|future|coming|next)\b", s):
        return (
            "My planned direction includes stronger long-conversation memory, controlled "
            "internet research with sources, richer personal learning continuity, evolving "
            "Question Maps, and a curiosity graph that connects what a user explores over time. "
            "These are roadmap goals, not claims about features already available."
        )

    if re.search(r"\b(different|difference|compare|versus|vs).*(chatgpt|claude|other ai|ai assistant)\b", s) or re.search(
        r"\b(chatgpt|claude|other ai|ai assistant).*(different|difference|compare|versus|vs)\b", s
    ):
        return (
            "ChatGPT and Claude are broad general-purpose assistants. I am being designed around "
            "Question Intelligence: clarifying intent, profiling a subject, mapping its question "
            "space, and guiding a learner through useful directions. I still use language-model "
            "intelligence; my distinction is the learning experience and structure built around it."
        )

    if re.search(r"\bwhy.*(question maps?|qmaps?)\b", s) or re.search(
        r"\b(question maps?|qmaps?).*(purpose|reason|for)\b", s
    ):
        return (
            "I create Question Maps because understanding a subject requires more than one answer. "
            "A map exposes the foundations, mechanisms, applications, limitations, and advanced "
            "directions so you can see what to ask next and choose your own learning path."
        )

    if re.search(
        r"\b(what|which).*(topics?|subjects?|areas?).*(do you know|can you cover|can you help|support)\b",
        s,
    ) or re.search(
        r"\b(what all|which).*(do you know|can you cover).*(topics?|subjects?|areas?)\b",
        s,
    ):
        return (
            "I am strongest today at structured learning around artificial intelligence, machine "
            "learning, data science, computer science, software and cloud concepts such as "
            "Kubernetes, quantum computing, and cognitive science. I can discuss other educational "
            "topics too, but the depth and reliability may vary. I am still in active development, "
            "so I can occasionally misunderstand a request or produce an uneven result. I do not "
            "claim verified specialist support for medical, legal, or financial advice. Give me a "
            "topic and I will tell you honestly whether I can explain it or build a reliable "
            "Question Map."
        )

    if re.search(
        r"^(?:what (?:can|could) you (?:do|help me with)|"
        r"how (?:can|could) you help(?: me)?|"
        r"what are your (?:capabilities|features)|"
        r"how (?:do|should) i use you|what can you do for me)\??$",
        s,
    ):
        return (
            "I can hold a conversation, clarify ambiguous requests, explain topics directly, build "
            "Topic Profiles and structured Question Maps, suggest useful follow-ups, guide focused "
            "discussions, and preserve your query trail so an exploration remains navigable. I am "
            "still being improved, so these abilities are not equally reliable for every subject "
            "or every phrasing yet."
        )

    if re.search(
        r"^(?:what (?:exactly )?(?:is ini(?:\.ai)?|are you)|who are you|"
        r"describe (?:ini(?:\.ai)?|yourself)|define ini(?:\.ai)?)$",
        s,
    ) or s in {
        "what are you", "tell me about yourself", "tell me about ini",
    }:
        return (
            "I am InI.ai, a Question Engine built to turn curiosity into structured understanding. "
            "I can converse and answer directly, but my defining purpose is to reveal the larger "
            "question space around a subject and help you decide where to explore next."
        )

    return None

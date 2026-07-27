"""Stable product knowledge for questions about InI.ai itself."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


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

    refers_to_ini = bool(re.search(r"\b(ini|you|your|yourself)\b", s))
    if not s or not refers_to_ini:
        return None

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
            "I am currently on v0.1.4. This build has a documented product history for "
            "v0.1.3 and v0.1.4; earlier work belonged to the experimental v0 phase rather "
            "than a formal release history."
        )

    if re.search(r"\b(current|latest|new|special|update|changed|improved).*(versions?|releases?|v0.1.4)\b", s) or re.search(
        r"\b(versions?|releases?|v0.1.4).*(current|latest|new|special|update|changed|improved)\b", s
    ):
        return (
            "v0.1.4 is my current release. It adds stronger conversational intelligence, "
            "context-aware follow-ups and topic switching, guided Discussion Mode, persistent "
            "query history, clearer Thinking and generation states, a refined response-card "
            "experience, and broader branding and navigation polish."
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

    if re.search(r"\b(what can|how can|capabilities|features|help me|use you|do for me)\b", s):
        return (
            "I can hold a conversation, clarify ambiguous requests, explain topics directly, build "
            "Topic Profiles and structured Question Maps, suggest useful follow-ups, guide focused "
            "discussions, and preserve your query trail so an exploration remains navigable. I am "
            "still being improved, so these abilities are not equally reliable for every subject "
            "or every phrasing yet."
        )

    if re.search(r"\b(what exactly|what is|who are|describe|define).*(ini|you)\b", s) or s in {
        "what are you", "tell me about yourself", "tell me about ini",
    }:
        return (
            "I am InI.ai, a Question Engine built to turn curiosity into structured understanding. "
            "I can converse and answer directly, but my defining purpose is to reveal the larger "
            "question space around a subject and help you decide where to explore next."
        )

    return None

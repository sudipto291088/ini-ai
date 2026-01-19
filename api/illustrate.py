# api/illustrate.py

from __future__ import annotations

from typing import Dict, List
from api.interrogate import detect_topic_type, extract_topic








def illustration_support_map(topic_type: str) -> dict:
    if topic_type == "troubleshooting":
        return {
            "symptom": "Describe",
            "root_cause": "Isolate",
            "fix": "Fix",
            "prevention": "Fix",
        }

    if topic_type == "decision":
        return {
            "option_a": "Options",
            "option_b": "Options",
            "tradeoff": "Tradeoffs",
            "regret_case": "Risks",
        }

    if topic_type == "skill":
        return {
            "beginner": "Basics",
            "practice": "Practice",
            "mistake": "Common Mistakes",
            "progress": "Next Level",
        }

    if topic_type == "comparison":
        return {
            "side_by_side": "Differences",
            "winner_case": "Who Should Choose What",
            "loser_case": "Common Traps",
            "tie_case": "Decision Rule",
        }

    # concept
    return {
        "everyday": "What",
        "work": "Where",
        "analogy": "How",
        "failure": "Why",
    }




def build_illustrations(topic: str, topic_type: str) -> dict:
    t = topic

    if topic_type == "troubleshooting":
        return {
            "symptom": f"A real-world symptom where {t} appears.",
            "root_cause": "A common underlying cause for this issue.",
            "fix": "A safe first fix most people should try.",
            "prevention": "How to avoid this issue in the future.",
        }

    if topic_type == "decision":
        return {
            "option_a": f"Scenario where choosing one option in {t} makes sense.",
            "option_b": f"Scenario where the alternative is better.",
            "tradeoff": "What you gain vs what you give up.",
            "regret_case": "A common regret people report after deciding poorly.",
        }

    if topic_type == "skill":
        return {
            "beginner": f"A beginner practicing {t} for the first time.",
            "practice": "A concrete practice exercise.",
            "mistake": "A mistake beginners commonly make.",
            "progress": "What improvement looks like after consistent practice.",
        }

    if topic_type == "comparison":
        return {
            "side_by_side": f"A vs B comparison scenario for {t}.",
            "winner_case": "When option A clearly wins.",
            "loser_case": "When option B is the wrong choice.",
            "tie_case": "When both options are equally acceptable.",
        }

    # default: concept
    return {
        "everyday": f"An everyday example of {t}.",
        "work": f"A professional use of {t}.",
        "analogy": f"An analogy to explain {t} simply.",
        "failure": f"What goes wrong without understanding {t}.",
    }






def illustrate(topic: str) -> Dict[str, object]:
    clean_topic = extract_topic(topic)
    topic_type, confidence = detect_topic_type(clean_topic)
    supports = illustration_support_map(topic_type)

    illustrations = build_illustrations(clean_topic, topic_type)


    if confidence < 0.5:
        illustrations = dict(list(illustrations.items())[:2])






    return {
        "topic": clean_topic,
        "topic_type": topic_type,
        "confidence": confidence,
        "illustrations": illustrations,
        "notes": ["v0: illustration depth adapts to confidence"],
        "supports": supports,
    }



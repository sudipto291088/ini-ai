# api/interrogate.py

from __future__ import annotations

from typing import Dict, List





def extract_topic(user_text: str) -> str:
    """
    Extract a clean topic phrase from a natural language user prompt.
    v0: rule-based normalization.
    """
    t = user_text.strip().lower()

    # Common leading phrases to strip
    prefixes = [
        "can you teach me about",
        "about",
        "teach me about",
        "explain",
        "what is",
        "what are",
        "tell me about",
        "help me understand",
        "i want to learn about",
        "i would like to learn about",
        "could you explain",
        "hi there, explain",
        "hello, explain",
        "please explain",
        " hi, tell me about",
        " hello, tell me about",
        " please tell me about",
        "whats up with",
        "what's up with",
        "i want to know about",
        "i would like to know about",
        "i want to understand",
        "whats up",
        "what's up",
        "can you explain",
        "how do i",
        "how to",
        "give me information on",
        "give me details on",
        "provide insights on",
        "i need to know about",
        "information about",
        "details about",
        "insights about",
        "i'm interested in",
        "i am interested in",
        "looking for information on",
        "looking for details on",
        "looking for insights on",
        "could you tell me about",
        "would you explain",
        "please explain",
        "what do you know about",
        "what do you know about",
        "give me an overview of",
        "overview of",
        "summary of",
        "i want to understand",
        "help me with",
        "assist me with",
        "i have a question about",
        "my question is about",
        "teach me",
        "learn about",
        "information on",
        "details on",
        "insights on",
        "explanation of",
        "whose",
        "who is",
        "where is",
        "when is",
        "why is",
        "how is",
        "what's",
        "whats",
        "define",
        "definition of",
        "describe",
        "description of",
        "i want to know",
        "i would like to know",
        "could you tell me about",
        "would you tell me about",
        "please tell me about",
        "give me a brief on",
        "brief on",
        "i'm curious about",
        "i am curious about",
        "can you explain",        
        "would you explain",
        "please explain",
        "what are the basics of",
        "basics of",
        "fundamentals of",
        "introduction to",
        "intro to",
        "i need help with",
        "assist me in understanding",
        "help me in understanding",
        "i want assistance with",
        "i would like assistance with",
        "could you assist me with",
        "would you assist me with",
        "please assist me with",
        "what probably is",
        "what likely is",
        "what generally is",
        "what typically is",
        "what possibly is",
        "give me clarity on",
        "clarity on",
        "shed light on",
        "i seek knowledge on",
        "i am seeking knowledge on",
        "i would like to learn about",
        "i want to gain knowledge on",
        "i would like to gain knowledge on",
        "could you provide information on",
        "would you provide information on",
        "please provide information on",
        "i'm looking to understand",
        "i'm looking to explore",
        "i look forward to explore",
        "i am looking to understand",
        "i would like to understand",
        "i want to explore",
        "i would like to explore",
        "could you explore",
        "would you explore",
        "please explore",
        "give me insights into",
        "insights into",
        "i need insights into",
        "i would like insights into",
        "could you give me insights into",
        "would you give me insights into",
        "please give me insights into",
        "wish you could explain",
        "hope you can explain",
        "looking forward to understanding",
        "looking forward to exploring",
        "wish you could tell me about",
        "hope you can tell me about",
        'please shed light on',
        'could you shed light on',
        'would you shed light on',
        "please teach me about",
        "could you teach me about",
        "would you teach me about",
        "please help me understand",
        "could you help me understand",
        "would you help me understand",
        "i'm eager to learn about",
        "i am eager to learn about",
        "i would be eager to learn about",
        "i'm keen to learn about",
        "mind telling me about",
        "would you mind telling me about",
        "could you mind telling me about",
        "please mind telling me about",
        "i'm fascinated by",
        "i am fascinated by",
        "i would like to be fascinated by",
        "could you fascinate me with",
        "would you fascinate me with",
        "please fascinate me with",
        "i want to be fascinated by",
        "i would like to be fascinated by",
        "could you fascinate me with",
        "would you fascinate me with",
        "please fascinate me with",
        "explain to me",
        "could you explain to me",
        "could you explain to me about",
        "would you explain to me",
        "please explain to me",
        "what could we know about",
        "what can we know about",
        "what would we know about",
        "what should we know about",
        "what do we know about",
        "what is the current understanding of",
        "what is the latest information on",
        "what is the most recent update on",
        "what is the most up-to-date information on",
        "what is the most current knowledge on",
        "what is the most recent knowledge on",
        "what is the most up-to-date understanding of",
        "what is the most current understanding of",
        "what do experts say about",
        "what do specialists say about",
        "what do professionals say about",
        "what do authorities say about",
        "what do researchers say about",
        "what do scholars say about",
        "what do academics say about",
        "what do scientists say about",
        "what do analysts say about",
        "what do commentators say about",
        "what do critics say about",
        "what do reviewers say about",
        "what do observers say about",
        "what do insiders say about",
        "what do outsiders say about",
        "what do insiders say about",
        "what do outsiders say about",
        "could you provide insights on",
        "would you provide insights on",
        "please provide insights on",
        "what are the fundamentals of",
        "fundamentals of",
        "what could possibly be",
        "what can possibly be",
        "what would possibly be",
        "what should possibly be",
        "what might possibly be",
        "what may possibly be",
        "what is possibly be",
        "what are possibly be",
        "what could probably be",
        "what can probably be",
        "what would probably be",
        "what should probably be",
        "what might probably be",
        "what may probably be",
        "what is probably be",
        "what are probably be",
        "what could generally be",
        "what can generally be",
        "what would generally be",
        "what should generally be",
        "what might generally be",
        "what may generally be",
        "what is generally be",
        "what are generally be",
        "what could typically be",
        "what can typically be",
        "what would typically be",
        "what should typically be",
        "what might typically be",
        "what may typically be",
        "what is typically be",
        "what are typically be",    
        "what could likely be",
        "what can likely be",
        "what would likely be",
        "what should likely be",
        "what might likely be",
        "what may likely be",
        "what is likely be",
        "what are likely be",
        "what are the chances of",
        "what is the likelihood of",
        "what are teh topics on",
        "what topics are on",
        "topics on",
        "topics about",
        "could you give me an overview of",
        "would you give me an overview of",
        "please give me an overview of",
        "give me an overview of",
        "overview of",
        "summary of",
        "could you give me a brief on",
        "would you give me a brief on",
        "please give me a brief on",
        "give me a brief on",
        "brief on",
        "explain like i'm five",
        "explain like im five",
        "explain like i'm 5",
        "explain like im 5",
        "explain like a beginner",
        "explain like beginner",
        "explain like a novice",
        "explain like novice",
        "in simple terms",
        "in layman's terms",
        "in laymans terms",
        "in simple language",
        "in easy terms",
        "in easy language",
        "for dummies",
        "for beginners",
        "for novices",
        "for newbies",
        "for newbs",
        "for starters",
        "I want to understand",
        "i would like to understand",
        "i need to understand",
        "could you help me understand",
        "would you help me understand",
        "please help me understand",
        "i wish to understand",
        "i would wish to understand",
        "i desire to understand",
        "i would desire to understand",
        "i want to learn"
        "i would like to learn",
        "i need to learn",
        "could you help me learn",
        "would you help me learn",
        "please help me learn",
        "i want to learn",
        "i would like to learn",
        "i need to learn",
        "could you help me learn",
        "would you help me learn",
        
        



    ]

    for p in sorted(prefixes, key=len, reverse=True):
        if t.startswith(p):
            t = t[len(p):].strip()
            break

    # Remove trailing punctuation
    t = t.rstrip("?.!")

    # Capitalize nicely (simple heuristic)
    t = " ".join(word.capitalize() for word in t.split())

    return t


def build_summary(topic: str, topic_type: str, confidence: float) -> list[str]:
    t = topic

        # v0 override: "how to learn/..." is clear intent even if confidence is low
    if topic_type == "skill":
        return [
            f"{t} is a skill you can build with practice.",
            "Progress comes from small drills, feedback loops, and clear milestones.",
            "We’ll outline a beginner path and common mistakes to avoid.",
        ]


    if confidence < 0.5 and len(topic.split()) <= 4:
        return [
            f"Topic: {t}.",
            "I might need a bit more context to be precise.",
            "Start with a simple overview, then we can go deeper.",
        ]

    if topic_type == "comparison":
        return [
            f"{t} is a comparison question (A vs B).",
            "The goal is to identify the key differences and what matters most for your situation.",
            "A good comparison ends with a simple decision rule.",
        ]

    if topic_type == "decision":
        return [
            f"{t} is a decision topic.",
            "Good decisions clarify constraints, tradeoffs, and risks.",
            "We’ll narrow down options and use a simple rule to choose.",
        ]

    if topic_type == "troubleshooting":
        return [
            f"{t} sounds like a troubleshooting problem.",
            "We’ll identify symptoms, reproduce the issue, and isolate the root cause.",
            "Then we’ll try the safest fix first and re-test.",
        ]

    if topic_type == "skill":
        return [
            f"{t} is a skill you can build with practice.",
            "Progress comes from small drills, feedback loops, and clear milestones.",
            "We’ll outline a beginner path and common mistakes to avoid.",
        ]

    # concept default
    return [
        f"{t} is a concept/topic to understand clearly.",
        "We’ll define it simply, break it into parts, and connect it to real-world use.",
        "Then we’ll test understanding using focused questions and examples.",
    ]



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


def detect_topic_type(topic: str) -> tuple[str, float]:
    t = topic.lower()

    troubleshooting_signals = [
        "error", "not working", "failed", "issue", "problem",
        "exception", "refused", "cannot", "can't"
    ]

    decision_signals = [
        "should i", "or", "better", "which",
        "choose", "leasing", "buying"
    ]

    skill_signals = [
        "how to", "learn", "practice", "trading", "coding",
        "programming", "using", "develop"
    ]

    comparison_signals = [" vs ", " vs", "vs ", "vs", " versus ", "versus", "compare", "comparison"]
    if any(s in t for s in comparison_signals):
        # treat explicit comparisons as their own type
        return "comparison", 0.67


    scores = {
        "troubleshooting": sum(s in t for s in troubleshooting_signals),
        "decision": sum(s in t for s in decision_signals),
        "skill": sum(s in t for s in skill_signals),
        "concept": 1,  # default baseline
        "comparison": sum(s in t for s in comparison_signals),
    }

    

    topic_type = max(scores, key=scores.get)
    max_score = scores[topic_type]

    confidence = min(1.0, max_score / 3)

    # v0: avoid under-confident "concept" for clean topic phrases
    if topic_type == "concept" and max_score <= 1:
        confidence = 0.67


    return topic_type, round(confidence, 2)





def build_quick_examples(topic: str, topic_type: str, confidence: float) -> list[str]:
    t = topic

    # If we're uncertain, keep it extra short + safe
    if confidence < 0.5:
        return [
            f"Everyday: a simple place you might notice {t}.",
            f"Work/real-life: one practical situation involving {t}.",
        ]

    if topic_type == "comparison":
        return [
            f"Scenario: choosing between two options related to {t}.",
            "Quick rule: pick A when speed/short-term matters; pick B when long-term stability matters.",
            "Common mistake: comparing prices only, ignoring total cost/constraints.",
        ]

    if topic_type == "decision":
        return [
            f"Scenario: you must decide something involving {t} this week.",
            "Tradeoff example: saving money vs saving time/effort.",
            "Regret case: choosing quickly without checking constraints.",
        ]

    if topic_type == "troubleshooting":
        return [
            f"Symptom: something goes wrong related to {t}.",
            "First check: confirm the simplest cause before deeper steps.",
            "Fix example: apply one safe change, then re-test.",
        ]

    if topic_type == "skill":
        return [
            f"Practice: spend 20 minutes/day doing one small task in {t}.",
            "Beginner mistake: trying advanced stuff before basics.",
            "Progress sign: you can explain it in 2 sentences + do a tiny demo.",
        ]

    # default: concept
    return [
        f"Everyday: a simple example of {t}.",
        f"Work: how {t} shows up in a job or project.",
        f"Without it: what becomes confusing or fails when you ignore {t}.",
    ]




def build_categories(topic: str, topic_type: str) -> dict:
    t = topic

   
    if topic_type == "troubleshooting":
        return {
            "Describe": [
                "What exactly is happening (symptoms) in one sentence?",
                "What is the exact error message (copy/paste if possible)?",
            ],
            "Reproduce": [
                "What steps reliably reproduce the issue?",
                "What changed right before it started (code, install, settings, update)?",
            ],
            "Environment": [
                "What OS, Python version, and dependency versions are you using?",
                "Are you using a virtual environment? If yes, which one?",
            ],
            "Isolate": [
                f"What is the smallest example where {t} fails?",
                "Does it fail for everyone or only in a specific case?",
            ],
            "Fix": [
                "What are the top 3 most likely causes?",
                "What is the safest next fix to try first (lowest risk)?",
            ],
        }

    if topic_type == "decision":
        return {
            "Goal": [
                f"What outcome are you trying to achieve with {t}?",
                "What constraints matter most (budget, time, risk, convenience)?",
            ],
            "Options": [
                f"What are the main options/choices within {t}?",
                "What are viable alternatives you should compare against?",
            ],
            "Tradeoffs": [
                "What are the biggest pros/cons of each option?",
                "What hidden costs or downsides do people miss?",
            ],
            "Risks": [
                "What can go wrong, and how likely is it?",
                "What are the red flags that indicate a bad choice?",
            ],
            "Decision": [
                "What simple decision rule can you use to decide?",
                "What would a 'good enough' decision look like?",
            ],
        }

    if topic_type == "skill":
        return {
            "Basics": [
                f"What does 'good' look like in {t} (skills/behaviors)?",
                f"What are the core sub-skills inside {t}?",
            ],
            "Learning Path": [
                f"What should a beginner learn first in {t} (3-step path)?",
                "What are common beginner mistakes to avoid?",
            ],
            "Practice": [
                "What drills/practice tasks build the skill fastest?",
                "How much practice per day/week is realistic and effective?",
            ],
            "Feedback": [
                "How do you measure progress (metrics or checkpoints)?",
                "How do you get feedback quickly (tests, mentors, reviews)?",
            ],
            "Next Level": [
                "What does intermediate/advanced look like?",
                "What projects prove competence?",
            ],

            "Common Mistakes": [
    f"What are the top 3 beginner mistakes in {t}?",
    "What habit causes most people to plateau?",
],

            "Resources": [
    f"What are the best resources to learn {t} effectively?",
    f"What communities or groups focus on {t}?",
],

"who": [
    f"Who are the top experts or influencers in {t}?",
    f"Who created or pioneered {t}?",
],

"Common Traps": [
    f"What do people commonly overlook when deciding about {t}?",
    "What terms/conditions should be read carefully?",
],

        }
    

    if topic_type == "comparison":
        return {
                    "Define": [
                                    f"What is {t} comparing, exactly (A vs B)?",
                                     "What is the real goal behind this comparison?",
        ],
        "Similarities": [
            "In what ways are the two options similar?",
            "What do they both do well?",
        ],
        "Differences": [
            "What are the biggest differences (features, cost, risk, complexity)?",
            "What difference matters most for your situation?",
        ],
        "Who Should Choose What": [
            "Who should choose option A, and who should choose option B?",
            "What’s the most common wrong choice people make here?",
        ],
        "Decision Rule": [
            "What simple rule can decide quickly?",
            "What’s the ‘good enough’ choice if you’re unsure?",
        ],
    }


    # default: concept
    return {
        "What": [
            f"What is {t} in plain language?",
            f"What are the key parts/components of {t}?",
            f"What problem does {t} exist to solve?",
            f"What are the main benefits of {t}?",
            f"What are the limitations or downsides of {t}?",
            f"What are common use cases for {t}?",
            f"What are the important topics to understand about {t}?",
            f"What terminology should I know related to {t}?",
        ],
        "Why": [
            f"Why does {t} matter?",
            f"Why did {t} become necessary (history/context)?",
            f"Why do people get confused about {t}?",
        ],
        "How": [
            f"How does {t} work at a high level?",
            f"How do beginners start learning {t} (first 3 steps)?",
            f"How can I tell if I truly understand {t}?",
        ],
        "When": [
            f"When should someone use {t} (and when should they avoid it)?",
            f"When did {t} become important/popular?",
        ],
        "Where": [
            f"Where is {t} used in real life?",
            f"Where does {t} usually fail or break in practice?",
        ],
        "Misconceptions": [
    f"What is a common misconception about {t}?",
    f"What is {t} often confused with?",
],
        "Examples": [
    f"What is a simple example that illustrates {t}?",
    f"What are some real-world examples of {t} in action?",
],
        "Related Topics": [
    f"What topics are closely related to {t}?",
    f"How does {t} connect to other important concepts?",
],
    "how to": [
    f"What are the first steps to get started with {t}?",
    f"What resources are best for learning {t}?",
],

    "Common Challenges": [
    f"What are common challenges people face when learning {t}?",
    f"What pitfalls should I avoid when studying {t}?",
],
    "who": [
    f"Who are the leading experts or influencers in the field of {t}?",
    f"Who created or discovered {t}?",
],



    }


def dedupe_questions(categories: dict) -> dict:
    """
    Remove duplicate / near-duplicate questions within each category.
    v0: simple normalization-based dedupe.
    """
    def norm(q: str) -> str:
        q = q.strip().lower()
        q = q.replace("?", "")
        q = " ".join(q.split())
        return q

    cleaned = {}
    for cat, qs in categories.items():
        seen = set()
        out = []
        for q in qs:
            k = norm(q)
            if k not in seen:
                seen.add(k)
                out.append(q)
        cleaned[cat] = out
    return cleaned



def dedupe_across_categories(categories: dict) -> dict:
    """
    Remove repeated questions across categories (global dedupe).
    Keeps the first occurrence and drops later duplicates.
    v0: normalization-based.
    """
    def norm(q: str) -> str:
        q = q.strip().lower()
        q = q.replace("?", "")
        q = " ".join(q.split())
        return q

    seen = set()
    out = {}
    for cat, qs in categories.items():
        kept = []
        for q in qs:
            k = norm(q)
            if k not in seen:
                seen.add(k)
                kept.append(q)
        out[cat] = kept
    return out





def clarification_for(topic: str, topic_type: str) -> str:
    t = topic
    if topic_type == "troubleshooting":
        return "Is this a technical error you're trying to fix? If yes, what exact error text do you see?"
    if topic_type == "decision":
        return f"Are you deciding between options related to {t}? If yes, what constraints matter most (cost, time, risk)?"
    if topic_type == "skill":
        return f"Do you want to learn {t} (a skill), or understand {t} as a concept?"
    # concept / fallback
    return f"Do you want a simple definition of {t}, or a deeper explanation with examples?"




def cap_categories(categories: dict, max_per_category: int = 5) -> dict:
    capped = {}
    for cat, qs in categories.items():
        capped[cat] = qs[:max_per_category]
    return capped


def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in s).strip("_")


def build_answer(topic: str, topic_type: str, category: str, question: str) -> str:
    """
    v0: template-based answers (short, non-dumpy).
    Goal: every question has an answer that is at least directionally useful.
    """
    t = topic
    c = category.lower()

    # Decision/comparison oriented
    if topic_type in ("decision", "comparison"):
        if "cost" in question.lower() or "money" in question.lower():
            return f"For {t}, compare total cost over time (upfront + ongoing + hidden fees). The best choice depends on your time horizon and risk tolerance."
        if "risk" in question.lower() or "trap" in question.lower():
            return f"Common risks in {t} include hidden assumptions, one-sided comparisons, and ignoring second-order effects. List constraints first, then evaluate trade-offs."
        return f"A good way to answer this for {t} is to list 2–3 options, compare trade-offs (cost/time/risk), and pick based on your constraints."

    # Skill / learning oriented
    if topic_type == "skill" or "learn" in question.lower():
        if "prereq" in question.lower() or "prerequisite" in question.lower():
            return f"For learning {t}, start with fundamentals first, then practice with small projects. Fill gaps only when they block progress."
        if "how" in question.lower() or "steps" in question.lower():
            return f"To learn {t}, follow: basics → guided exercises → small projects → feedback → repeat. Consistency beats intensity."
        return f"The practical answer for {t} is to define your goal, choose a learning path, and validate with hands-on practice."

    # Troubleshooting oriented
    if topic_type == "troubleshooting":
        return f"For {t}, first reproduce the issue, capture the exact error text, then isolate the smallest failing case. That usually reveals the root cause."

    # Concept / general
    if "why" in question.lower():
        return f"{t} matters because it affects outcomes and decisions in real life. The ‘why’ is usually impact: efficiency, cost, safety, or capability."
    if "how" in question.lower():
        return f"At a high level, {t} works through inputs → process → output. Understand the moving parts, then look at real examples."
    if "when" in question.lower() or "where" in question.lower():
        return f"{t} applies when it helps you achieve a goal under constraints. Look for real-world contexts where it changes results measurably."

    # Fallback
    return f"A useful way to answer this about {t} is to define it in one sentence, identify key parts, then test the idea with one example."
    

def attach_answers(categories: dict, topic: str, topic_type: str) -> dict:
    """
    Convert category -> [question str] into category -> [{id, question, answer}]
    """
    out = {}
    for cat, qs in categories.items():
        items = []
        cat_id = _slug(cat)
        for i, q in enumerate(qs, start=1):
            items.append({
                "id": f"{cat_id}_{i}",
                "question": q,
                "answer": build_answer(topic, topic_type, cat, q)
            })
        out[cat] = items
    return out















def interrogate(topic: str) -> Dict[str, object]:
    """
    Return structured, relevant interrogative questions for a topic.
    v0 intelligence: templates + light normalization.
    """
    clean_topic = extract_topic(topic)
    if not clean_topic:
        return {"topic": topic, "categories": {}, "notes": ["Empty topic received."]}
    
    topic_type, confidence = detect_topic_type(clean_topic)
    summary = build_summary(clean_topic, topic_type, confidence)
    needs_clarification = confidence < 0.5
    clarifying_question = clarification_for(clean_topic, topic_type) if needs_clarification else ""

    categories = build_categories(clean_topic, topic_type)
    categories = dedupe_questions(categories)
    categories = dedupe_across_categories(categories)
    categories = cap_categories(categories, max_per_category=5)


    notes = [
        "v0: template-based interrogation (no external knowledge yet).",
        "Next: add topic-type detection (concept vs skill vs decision vs troubleshooting).",
    ]

    quick_examples = build_quick_examples(clean_topic, topic_type, confidence)

    qa_categories = attach_answers(categories, clean_topic, topic_type)




    return {
    "topic": clean_topic,
    "topic_type": topic_type,
    "categories": qa_categories,
    "notes": notes,
    "confidence": confidence,
    "needs_clarification": needs_clarification,
    "clarifying_question": clarifying_question,
    "quick_examples": quick_examples,
    "summary": summary

}



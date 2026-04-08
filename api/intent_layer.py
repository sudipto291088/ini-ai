from __future__ import annotations

import re
from typing import Any, Dict, Iterable


# ============================================================
# Normalization
# ============================================================
def _normalize(text: str) -> str:
    s = (text or "").strip().lower()
    s = s.replace("’", "'")
    s = re.sub(r"[ \t\r\n]+", " ", s)
    s = re.sub(r"[!?.,;:]+$", "", s)
    return s.strip()


def _normalize_compact(text: str) -> str:
    s = _normalize(text)
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _contains_phrase(text: str, phrases: Iterable[str]) -> bool:
    s = _normalize_compact(text)
    return s in {_normalize_compact(p) for p in phrases}


def _contains_any_substring(text: str, phrases: Iterable[str]) -> bool:
    s = _normalize_compact(text)
    phrase_set = {_normalize_compact(p) for p in phrases}
    return any(p and p in s for p in phrase_set)


# ============================================================
# Production-grade phrase banks
# ============================================================

GREETING_PHRASES = {
    "hi", "hello", "hey", "yo", "sup", "hiya", "greetings", "namaste", "hola",
    "bonjour", "hey there", "hello there", "hi there", "good morning",
    "good afternoon", "good evening", "hey cg", "hello cg", "hi cg",
    "hey ini", "hello ini", "hi ini", "yo cg", "yo ini", "sup cg", "sup ini",
    "hey buddy", "hello buddy", "hi buddy", "hey bro", "hi bro", "hello bro",
    "hey man", "hello man", "hi man", "hey friend", "hello friend", "hi friend",
    "hey boss", "hello boss", "hi boss", "hey chief", "hello chief", "hi chief",
    "hey dude", "hello dude", "hi dude", "hey mate", "hello mate", "hi mate",
    "hey pal", "hello pal", "hi pal", "hey partner", "hello partner", "hi partner",
    "hey again", "hello again", "hi again", "long time no see", "good to see you",
    "nice to see you", "nice seeing you", "whats up", "what's up",
    "how are you", "how are you doing", "how you doing", "how r u",
    "how are things", "hows it going", "how's it going", "how is it going",
    "hows life", "how's life", "how is life", "whats going on", "what's going on",
    "anything new", "hey whats up", "hello whats up", "hey whats going on",
    "hello whats going on", "hey there cg", "hello there cg", "hi there cg",
    "hey there ini", "hello there ini", "hi there ini", "morning", "evening",
    "afternoon", "good day", "hey you", "hello you", "are you there",
    "you there", "yo there", "hey assistant", "hello assistant", "hi assistant",
    "hey ai", "hello ai", "hi ai", "what up", "wassup", "wsup",
    "hru", "how u doing", "how are ya", "how ya doing", "how you been",
}

THANKS_PHRASES = {
    "thanks", "thank you", "thx", "ty", "tysm", "thanks a lot", "thanks so much",
    "thank you so much", "many thanks", "much appreciated", "appreciate it",
    "really appreciate it", "thanks cg", "thank you cg", "thanks ini",
    "thank you ini", "awesome thanks", "great thanks", "cool thanks",
    "okay thanks", "ok thanks", "alright thanks", "got it thanks",
    "thanks buddy", "thanks bro", "thanks man", "thanks friend", "thanks boss",
    "thanks chief", "thank you very much", "big thanks", "super thanks",
    "perfect thanks", "beautiful thanks", "nice thanks", "thanks again",
    "thank you again", "appreciated", "grateful", "i appreciate that",
    "i appreciate this", "thanks for that", "thanks for your help",
    "thank you for your help", "thanks a ton", "thanks a bunch",
    "thanks a million", "many many thanks", "cheers", "cheers mate",
}

FAREWELL_PHRASES = {
    "bye", "goodbye", "bye bye", "see you", "see ya", "see you later",
    "catch you later", "talk to you later", "talk later", "later", "peace",
    "good night", "gn", "night", "take care", "have a good day",
    "have a nice day", "until next time", "see you soon", "cya", "farewell",
    "alright bye", "ok bye", "okay bye", "thanks bye", "bye cg", "bye ini",
    "im leaving", "i am leaving", "gotta go", "got to go", "need to go",
    "i have to go", "signing off", "logging off", "wrap it up", "thats all bye",
}

HELP_PHRASES = {
    "help", "help me", "can you help", "can you help me", "need help",
    "i need help", "what can you do", "how does this work", "how do i use this",
    "what should i do here", "what is this", "how can you help",
    "show me how this works", "how does ini work", "how do i use ini",
    "what are you for", "what can ini do", "what can you help with",
    "what can i ask you", "how should i start", "where do i start",
    "how do i begin", "how can i begin", "guide me", "assist me",
    "tell me how to use this", "show capabilities", "show features",
    "what features do you have", "how do i use your features",
    "what modes do you have", "how do your modes work", "explain your features",
}

AFFIRM_PHRASES = {
    "yes", "yeah", "yep", "yup", "sure", "okay", "ok", "alright", "fine",
    "go ahead", "continue", "carry on", "please continue", "sounds good",
    "works for me", "lets do it", "let's do it", "do it", "proceed",
    "move ahead", "keep going", "go on", "yes please", "sure thing",
    "absolutely", "definitely", "exactly", "correct", "right", "indeed",
    "ok go ahead", "okay go ahead", "yes go ahead", "continue please",
    "please go ahead", "yeah go ahead", "sure go ahead", "lets proceed",
    "let's proceed", "that works", "perfect", "great", "fine go ahead",
}

NEGATIVE_PHRASES = {
    "no", "nope", "nah", "not now", "stop", "cancel", "never mind",
    "nevermind", "forget it", "not interested", "dont", "don't", "do not",
    "leave it", "skip it", "no thanks", "not really", "no thank you",
    "dont continue", "don't continue", "stop here", "thats enough",
    "that's enough", "no need", "not this", "not that", "not yet",
    "maybe later", "hold on", "wait", "pause", "drop it",
}

SMALLTALK_PHRASES = {
    "how is your day", "hows your day", "how's your day",
    "what are you doing", "whatre you doing", "what are you up to",
    "who are you", "tell me about yourself", "introduce yourself",
    "are you real", "are you an ai", "are you chatgpt", "who made you",
    "what are you", "how old are you", "where are you from",
}

# direct factual query cues
DIRECT_FACTUAL_PREFIXES = (
    "what is",
    "what are",
    "who is",
    "who are",
    "when is",
    "when are",
    "where is",
    "where are",
    "how much",
    "how many",
    "how old",
    "which is",
    "which are",
    "latest",
    "current",
    "today",
    "price of",
    "rate of",
    "cost of",
)

DIRECT_FACTUAL_KEYWORDS = {
    "today", "current", "latest", "price", "rate", "weather", "temperature",
    "stock", "gas", "diesel", "petrol", "time", "date", "news", "score",
    "president", "ceo", "population", "salary", "exchange rate", "bitcoin",
    "gold price", "silver price", "fuel price", "live", "now", "currently",
}

QUIZ_CUES = {
    "quiz", "test me", "practice questions", "mcq", "multiple choice",
    "ask me questions", "challenge me", "give me a quiz",
}

OVERVIEW_CUES = {
    "overview", "high level", "summary", "briefly", "quick intro",
    "introduction", "birds eye", "big picture", "in short",
}

TOPIC_CUES = {
    "explain", "tell", "teach", "learn", "why", "how", "compare",
    "difference", "versus", "vs", "roadmap", "guide", "steps", "deep",
    "architecture", "system", "model", "algorithm", "concept", "theory",
    "workflow", "pipeline", "framework", "fundamentals", "basics",
    "beginner", "advanced", "mechanism", "working", "internals","so teach me", "i want to learn", "i want to understand", "i want to know about", "can you explain", "can you tell me about", "can you teach me", "can you help me understand", "i want to learn about", 
    "i want to understand", "i want to know about", "explain to me", "tell me about", "teach me about", "help me understand", "what is", "what are", "who is", "who are", "when is", "when are", "where is", "where are", "how much", "how many", "how old", "which is", "which are",
    "give me a roadmap for", "give me a guide for", "what are the steps to learn", "what is the workflow for", "what is the pipeline for", "what is the framework for", "what are the fundamentals of", "what are the basics of", "how does X work", 
    "how does X actually work", "how does X internally work", "how does X mechanism work", "how does X architecture look like", "how does X system look like", "what is the internals of", "what is the architecture of", "what is the system of", "what is the model of", "what is the algorithm of", 
    "what is the concept of", "what is the theory of",

}


# ============================================================
# Intent helpers
# ============================================================
def _detect_mode(text: str) -> str:
    s = _normalize_compact(text)

    if any(_normalize_compact(p) in s for p in QUIZ_CUES):
        return "quiz"

    if any(_normalize_compact(p) in s for p in OVERVIEW_CUES):
        return "high"

    return "deep"


def _is_greeting(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, GREETING_PHRASES)


def _is_thanks(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, THANKS_PHRASES)


def _is_farewell(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, FAREWELL_PHRASES)


def _is_help(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, HELP_PHRASES)


def _is_affirmation(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, AFFIRM_PHRASES)


def _is_negative(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, NEGATIVE_PHRASES)


def _is_smalltalk(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, SMALLTALK_PHRASES)


def _looks_like_direct_factual_query(text: str) -> bool:
    s = _normalize_compact(text)

    if not s:
        return False

    # classic structured questions
    if any(s.startswith(prefix) for prefix in DIRECT_FACTUAL_PREFIXES):
        return True

    # keyword based factual query
    if any(word in s for word in DIRECT_FACTUAL_KEYWORDS):
        return True

    # short fragment queries
    words = s.split()

    if len(words) <= 5 and "?" in text:
        return True

    # things like: "gas rate today"
    factual_markers = {
        "rate",
        "price",
        "cost",
        "weather",
        "temperature",
        "population",
        "age",
        "salary",
        "stock",
        "bitcoin",
        "date",
        "time",
    }

    if any(marker in words for marker in factual_markers):
        return True

    return False


def _looks_like_topic(text: str) -> bool:
    s = _normalize_compact(text)
    if not s:
        return False

    if _looks_like_direct_factual_query(s):
        return False

    if any(_normalize_compact(p) in s for p in QUIZ_CUES):
        return True

    if any(_normalize_compact(p) in s for p in OVERVIEW_CUES):
        return True

    if any(_normalize_compact(tok) in s for tok in TOPIC_CUES):
        return True

    # clean noun phrase topic: "artificial intelligence", "neural networks"
    if 2 <= len(s.split()) <= 8 and "?" not in s:
        banned_smalltalk_starts = {
            "how are", "how you", "how r", "whats up", "what's up",
            "good morning", "good evening", "good afternoon",
        }
        if not any(s.startswith(x) for x in banned_smalltalk_starts):
            return True

    if "?" in s and any(tok in s for tok in {"what", "why", "how", "explain", "compare"}):
        smalltalk_question_starts = {
            "how are you", "how are things", "how you doing", "how r u",
            "who are you", "what are you",
        }
        if not any(s.startswith(x) for x in smalltalk_question_starts):
            return True

    return False


# ============================================================
# Main detector
# ============================================================
def detect_intent(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    s = _normalize_compact(raw)
    mode = _detect_mode(raw)

    if not s:
        return {
            "intent": "empty",
            "reply": "Give me a topic to explore and I will build a question map for it.",
            "followups": [
                "Artificial Intelligence",
                "Neural Networks",
                "Transformers",
            ],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.99,
        }

    if _is_greeting(raw):
        return {
            "intent": "greeting",
            "reply": "Hey. I am ready. Give me a topic and I will either build a structured question map or answer it directly if it is a simple factual query.",
            "followups": [
                "Artificial Intelligence",
                "Explain transformers",
                "What is the gas rate today?",
            ],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.98,
        }

    if _is_thanks(raw):
        return {
            "intent": "thanks",
            "reply": "Always. Drop the next topic whenever you are ready.",
            "followups": [
                "Artificial Intelligence",
                "Prompt Engineering",
                "What is machine learning?",
            ],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.97,
        }

    if _is_farewell(raw):
        return {
            "intent": "farewell",
            "reply": "Alright. We can pick this up anytime. Bring the next topic when you return.",
            "followups": [],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.97,
        }

    if _is_help(raw):
        return {
            "intent": "help",
            "reply": "Use Interrogate when you want a structured question ladder. Use Illustrate when you want a direct explanation. Simple factual queries can be answered directly without a question map.",
            "followups": [
                "Artificial Intelligence",
                "Explain neural networks",
                "What is the gas rate today?",
            ],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.97,
        }

    if _is_affirmation(raw):
        return {
            "intent": "affirmation",
            "reply": "Got it. Send the topic or question you want to explore next.",
            "followups": [
                "Artificial Intelligence",
                "Explain transformers",
            ],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.93,
        }

    if _is_negative(raw):
        return {
            "intent": "negative",
            "reply": "No problem. Send a different topic whenever you want.",
            "followups": [],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.93,
        }

    if _is_smalltalk(raw):
        return {
            "intent": "smalltalk",
            "reply": "I am here and ready. Ask me a topic to learn, a concept to explain, or a direct factual question.",
            "followups": [
                "Artificial Intelligence",
                "Explain transformers",
                "What is the gas rate today?",
            ],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "deep",
            "confidence": 0.92,
        }

    if _looks_like_direct_factual_query(raw):
        return {
            "intent": "direct_factual_query",
            "reply": "",
            "followups": [],
            "should_interrogate": False,
            "should_answer_direct": True,
            "mode_hint": "high",
            "confidence": 0.88,
        }

    if _looks_like_topic(raw):
        return {
            "intent": "topic_explore",
            "reply": "",
            "followups": [],
            "should_interrogate": True,
            "should_answer_direct": False,
            "mode_hint": mode,
            "confidence": 0.82,
        }

    return {
        "intent": "clarify",
        "reply": "I can help, but that looks more like a conversational message than a topic. Send a topic, a concept, or a direct factual question.",
        "followups": [
            "Artificial Intelligence",
            "What is a neural network?",
            "What is the gas rate today?",
        ],
        "should_interrogate": False,
        "should_answer_direct": False,
        "mode_hint": "deep",
        "confidence": 0.70,
    }
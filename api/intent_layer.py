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


def _normalize_expressive(text: str) -> str:
    """Normalize casual emphasis (heyyy/hellooo/noooo) for intent matching."""
    s = _normalize_compact(text)
    return re.sub(r"([a-z])\1{2,}", r"\1", s)


def _strip_social_address(text: str) -> str:
    """Remove a harmless trailing vocative from an already-normalized turn."""
    return re.sub(
        r"\s+(?:ini|cd|cg|man|buddy|bro|friend|mate)$", "", text
    ).strip()


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
    "hows everything going", "how's everything going", "how is everything going",
    "how are things going", "how is everything", "hows everything",
    "hows life", "how's life", "how is life", "whats going on", "what's going on",
    "so whats going on", "so what's going on", "so what is going on",
    "so whats up", "so what's up", "so what is up",
    "anything new", "hey whats up", "hello whats up", "hey whats going on",
    "hello whats going on", "hey there cg", "hello there cg", "hi there cg",
    "hey there ini", "hello there ini", "hi there ini", "morning", "evening",
    "afternoon", "good day", "hey you", "hello you", "are you there",
    "you there", "yo there", "hey assistant", "hello assistant", "hi assistant",
    "hey ai", "hello ai", "hi ai", "what up", "wassup", "wsup",
    "hru", "how u doing", "how are ya", "how ya doing", "how you been",
}

GREETING_OPENERS = {
    "hi", "hello", "hey", "hiya", "greetings", "namaste", "hola",
    "bonjour", "good morning", "good afternoon", "good evening",
    "hi there", "hello there", "hey there",
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
    "rest for today", "let us rest for today", "lets rest for today",
    "done for today", "that is all for today", "thats all for today",
    "we are done for today", "call it a day",
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
    "cool", "nice", "awesome", "wonderful", "all good",
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
    "today", "current", "latest", "price", "weather", "temperature",
    "stock", "gas", "diesel", "petrol", "time", "date", "news", "score",
    "president", "ceo", "population", "salary", "exchange rate", "bitcoin",
    "gold price", "silver price", "fuel price", "live", "now", "currently",
}

TECHNICAL_TOPIC_PHRASES = {
    "ai",
    "agi",
    "ml",
    "pca",
    "gpu",
    "cpu",
    "amd",
    "ryzen",
    "processor",
    "xgboost",
    "docker",
    "kubernetes",
    "mcp",
    "mcp server",
    "model context protocol",
    "local mcp server",
    "mcp server in local system",
    "mcp server on my computer",
    "sql",
    "time series",
    "time series forecasting",
    "bayesian statistics",
    "principal component analysis",
    "gradient descent",
    "gradient descent variations",
    "constitutional ai",
    "spatial ai",
    "quant artificial intelligence",
    "quantitative artificial intelligence",
    "artificial general intelligence",
    "bcbl",
    "basque center on cognition brain and language",
    "basque centre on cognition brain and language",
    "cognitive science",
    "cognitive neuroscience",
    "psycholinguistics",
    "neurolinguistics",
    "bilingualism",
    "multilingualism",
    "language acquisition",
    "computer science",
    "quantum computing",
    "qis",
    "quantum information science",
    "quantum physics",
}

QUIZ_CUES = {
    "quiz", "test me", "practice questions", "mcq", "multiple choice",
    "ask me questions", "challenge me", "give me a quiz",
}

COMPARE_CUES = {
    "compare", "comparison", "difference between", "differences between",
    "versus", "vs", "pros and cons", "trade-offs", "tradeoffs",
}

DECIDE_CUES = {
    "help me decide", "help me choose", "which should i", "should i choose",
    "should i use", "which is better", "recommend between", "pick between",
}

EXAMPLE_CUES = {
    "give me an example", "give me examples", "show me an example",
    "show me examples", "worked example", "real world example",
    "real-world example", "use case", "use cases",
}

TEACH_CUES = {
    "teach me", "teach me about", "help me learn", "i want to learn",
    "lesson on", "walk me through", "from scratch", "step by step",
}

EXPLAIN_CUES = {
    "explain", "explain to me", "help me understand", "how does",
    "how do", "why does", "why do", "what is", "what are",
}

OVERVIEW_CUES = {
    "overview", "high level", "summary", "briefly", "quick intro",
    "introduction", "birds eye", "big picture", "in short",
}

TOPIC_CUES = {
    "explain", "tell", "teach", "learn", "why", "how", "compare",
    "difference", "versus", "vs", "roadmap", "guide", "steps", "deep",
    "architecture", "system", "model", "algorithm", "concept", "theory",
    "install", "installation", "setup", "set up", "configure", "configuration",
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


def _detect_response_intent(text: str) -> str:
    """Detect how the learner wants the topic handled, not only what it is."""
    compact = _normalize_compact(text)
    s = f" {compact} "

    # Normative questions can request a decision without using the literal
    # phrase "help me decide". Keep this structural so it covers unfamiliar
    # subjects rather than relying on a list of topic names.
    if re.match(r"^should\b", compact) or re.match(
        r"^(?:is|are|would|can)\b.+\b(?:responsible|appropriate|ethical|"
        r"acceptable|advisable|worthwhile|a good idea|the right choice|"
        r"a better option)\b",
        compact,
    ):
        return "decide"

    ordered_cues = (
        ("quiz", QUIZ_CUES),
        ("decide", DECIDE_CUES),
        ("compare", COMPARE_CUES),
        ("example", EXAMPLE_CUES),
        ("teach", TEACH_CUES),
        ("explain", EXPLAIN_CUES),
    )
    for intent_name, cues in ordered_cues:
        if any(f" {_normalize_compact(cue)} " in s for cue in cues):
            return intent_name
    return "explore"


def _is_greeting(text: str) -> bool:
    s = _strip_social_address(_normalize_expressive(text))
    if _contains_phrase(s, GREETING_PHRASES):
        return True

    # Natural wellbeing questions often carry harmless time modifiers. Treat
    # them as conversation rather than mistaking "today" for a live-data cue.
    wellbeing_starts = {
        "how are you", "how are you doing", "how you doing", "how r u",
        "how are things", "hows it going", "how is it going",
        "hows everything going", "how is everything going", "how are things going",
        "how have you been", "how you been",
    }
    benign_suffix_words = {
        "today", "now", "lately", "this", "morning", "afternoon", "evening",
        "ini", "friend", "buddy",
    }
    for phrase in wellbeing_starts:
        if s.startswith(phrase + " "):
            suffix_words = set(s[len(phrase):].strip().split())
            if suffix_words and suffix_words <= benign_suffix_words:
                return True

    # Accept natural compound greetings such as "Hello, how are you doing?"
    # without swallowing educational requests such as "Hello, explain AI".
    normalized_greetings = {_normalize_compact(p) for p in GREETING_PHRASES}
    for opener in sorted(GREETING_OPENERS, key=len, reverse=True):
        normalized_opener = _normalize_compact(opener)
        if s.startswith(normalized_opener + " "):
            remainder = s[len(normalized_opener):].strip()
            remainder = re.sub(r"^(ini|cg|friend|buddy)\s+", "", remainder)
            if remainder in normalized_greetings:
                return True

    return False


def _is_thanks(text: str) -> bool:
    s = _normalize_compact(text)
    return (
        _contains_phrase(s, THANKS_PHRASES)
        or bool(re.match(r"^(thanks|thank you|thx|ty)\b", s))
    )


def _is_farewell(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, FAREWELL_PHRASES)


def _is_help(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, HELP_PHRASES)


def _is_affirmation(text: str) -> bool:
    s = _normalize_compact(text)
    if _contains_phrase(s, AFFIRM_PHRASES):
        return True

    # Praise addressed to InI is a conversational acknowledgement, not a
    # learning topic that should generate a Question Map.
    if re.match(
        r"^(?:(?:well done)|(?:(?:amazing|great|good|excellent|fantastic|"
        r"awesome|nice|wonderful|brilliant|perfect)\s+(?:job|work)))"
        r"(?:\s+(?:ini|inl|buddy|bro|man|friend))?$",
        s,
    ):
        return True

    # Natural acknowledgements are conversation, not learning topics.
    return bool(
        re.match(
            r"^(?:(?:it is|its|that is|thats|this is|thiss)\s+)?"
            r"(?:ok|okay|fine|alright|all good|no problem|not a problem)"
            r"(?:\s+(?:thanks|thank you))?$",
            s,
        )
    )


def _is_negative(text: str) -> bool:
    s = _normalize_compact(text)
    return _contains_phrase(s, NEGATIVE_PHRASES)


def _is_self_introduction(text: str) -> bool:
    """Recognize a person introducing how they want to be addressed."""
    s = _normalize_compact(text)
    match = re.match(
        r"^(?:i am|im|my name is|you can call me|call me)\s+"
        r"([a-z][a-z0-9 -]{0,39})$",
        s,
    )
    if not match:
        return False
    candidate_words = match.group(1).split()
    non_name_words = {
        "only", "just", "checking", "testing", "trying", "ready", "fine",
        "okay", "ok", "here", "back", "done", "tired", "happy", "sad",
        "going", "working", "learning", "asking", "wondering",
    }
    return 1 <= len(candidate_words) <= 4 and not (set(candidate_words) & non_name_words)


def _is_smalltalk(text: str) -> bool:
    s = _normalize_expressive(text)
    # A harmless form of address does not turn casual speech into a learning
    # subject.  Keep the gate structural so natural variants such as
    # "what's going on, man?" cannot fall through to Question Map generation.
    s = _strip_social_address(s)
    if _contains_phrase(s, SMALLTALK_PHRASES):
        return True

    # Everyday observations are conversation, not requests for live data or
    # standalone learning subjects. Location-specific weather questions remain
    # eligible for the live-data route; personal remarks do not.
    if re.match(
        r"^(?:it(?: is|s)?\s+)?(?:so|too|very|really|quite|pretty)?\s*"
        r"(?:hot|cold|warm|chilly|humid|windy|rainy|uncomfortable)"
        r"(?:\s+(?:today|tonight|outside|here))?$",
        s,
    ):
        return True

    words = set(s.split())
    if len(s.split()) <= 18:
        testing_words = {"test", "testing", "check", "checking", "trying"}
        conversational_targets = {"you", "this", "it", "things"}
        if words & testing_words and words & conversational_targets:
            return True

    # Relational/identity and capability questions are conversation turns,
    # not educational subjects that need a Question Map.
    relational_patterns = (
        r"^(can|may|should|could) i call you\b",
        r"^(what|which) (can|could|do) you (help|do)\b",
        r"^how can you help\b",
        r"^what should i call you\b",
        r"^who are you\b",
        r"^(nothing|nothin|nothing much|nothin much)?\s*(lets|let us) just talk\b",
        r"^(nothing|nothin|nothing much|nothin much)\b",
        r"^why are you (going to|trying to|offering to|asking to)\b",
        r"^(are you|you are) (ok|okay|alright|fine|still not perfect)\b",
    )
    return any(re.match(pattern, s) for pattern in relational_patterns)


def _is_conversation_only_turn(text: str) -> bool:
    """Gate social speech acts that do not name a subject to learn.

    This is deliberately structural rather than a list of one-off spellings.
    A conversational invitation is routed to dialogue only when the complete
    turn contains no ``about/on + subject`` complement. Consequently, "let's
    chat" is conversation while "let's talk about machine learning" remains a
    legitimate learning request.
    """
    s = _normalize_expressive(text)
    if not s or len(s.split()) > 18:
        return False

    # A named complement makes this substantive rather than a pure social
    # invitation: "talk about machine learning" must remain a learning query.
    if re.search(r"(?:^| )(?:about|on|regarding|concerning) +[a-z0-9]", s):
        return False

    social_action = (
        r"(?:chat|talk|converse|have +(?:a +)?chat|"
        r"have +(?:a +)?conversation)"
    )
    social_tail = (
        r"(?: +(?:with +(?:me|you)|to +(?:me|you)|"
        r"for +(?:a +)?(?:bit|while|moment)|now|please|casually|"
        r"a +little))*"
    )
    invitation_patterns = (
        rf"^(?:lets|let +us) +(?:just +)?{social_action}{social_tail}$",
        rf"^(?:can|could|may|shall|should|would) +(?:we|i|you) +"
        rf"(?:just +)?{social_action}{social_tail}$",
        rf"^i +(?:want|would +like|need) +to +(?:just +)?"
        rf"{social_action}{social_tail}$",
        rf"^(?:please +)?{social_action}{social_tail}$",
    )
    return any(re.fullmatch(pattern, s) is not None for pattern in invitation_patterns)


def _looks_like_contextual_utterance(text: str) -> bool:
    """Recognize short human continuation/correction language, not exact phrases."""
    s = _normalize_compact(text)
    words = set(s.split())
    if not s or len(s.split()) > 18:
        return False

    # These phrases have no stable meaning without the immediately preceding
    # answer. Treating them as fresh subjects creates nonsensical Question Maps.
    contextual_followups = {
        "what else",
        "anything else",
        "tell me more",
        "what more",
        "go on",
        "continue",
    }
    continuation = re.sub(r"^(?:so|and|okay|ok|well|then)\s+", "", s).strip()
    if continuation in contextual_followups or re.match(
        r"^(more|what|how) (about|on) (it|this|that|the topic)$", s
    ):
        return True

    deictic_words = {"it", "this", "that", "those", "there", "thing"}
    continuation_words = {
        "again", "still", "already", "doing", "happening", "working",
        "meant", "mean", "same", "wrong", "right", "instead",
    }
    return bool(words & deictic_words) and bool(words & continuation_words)


def _is_known_technical_topic(text: str) -> bool:
    s = _normalize_compact(text)
    if not s:
        return False

    normalized_topics = {_normalize_compact(p) for p in TECHNICAL_TOPIC_PHRASES}
    if s in normalized_topics:
        return True

    # A definition-style question about a known learning subject is still a
    # learning request. Classify the subject after removing the interrogative
    # wrapper instead of sending every "what is ..." turn to the factual path.
    subject = re.sub(
        r"^(?:what|who|where|when|which)\s+(?:is|are)\s+",
        "",
        s,
    ).strip()
    return subject in normalized_topics


def _looks_like_direct_factual_query(text: str) -> bool:
    s = _normalize_compact(text)

    if not s:
        return False

    if _is_known_technical_topic(text):
        return False

    # "Where is X used?" asks for the applications of a subject. It is a
    # learning request, not a location lookup, even though it begins with
    # the otherwise factual-looking word "where".
    if re.match(r"^where\s+(?:is|are|does|do)\b.*\b(?:used|use|applied|apply)\b", s):
        return False

    # A definition request is usually a learning request, even when the
    # subject has not yet been added to our small known-topic vocabulary.
    # Reserve the direct-fact path for genuinely time-sensitive or lookup-like
    # wording (price, date, office holder, population, and similar cues).
    if re.match(r"^what\s+(?:is|are)\s+", s) and not any(
        (keyword in set(s.split()) if " " not in keyword else keyword in s)
        for keyword in DIRECT_FACTUAL_KEYWORDS
    ):
        return False

    # Educational questions should NOT be treated as factual lookups
    EDUCATIONAL_QUESTION_PREFIXES = (
        "what terminology",
        "what methods",
        "what techniques",
        "what assumptions",
        "what principles",
        "what future developments",
        "what frontier questions",
        "what challenges",
        "what limitations",
        "what misconceptions",
        "what pitfalls",
        "what applications",
        "why does",
        "why do",
        "how does",
        "how do",
    )

    if any(s.startswith(prefix) for prefix in EDUCATIONAL_QUESTION_PREFIXES):
        return False

    # classic structured factual questions
    if any(s.startswith(prefix) for prefix in DIRECT_FACTUAL_PREFIXES):
        return True

    # keyword based factual query
    factual_words = set(s.split())
    if any(
        (keyword in factual_words if " " not in keyword else keyword in s)
        for keyword in DIRECT_FACTUAL_KEYWORDS
    ):
        return True

    # short fragment queries
    words = s.split()

    if len(words) <= 5 and "?" in text:
        return True

    # things like: "gas rate today"
    factual_markers = {
        "price",
        "cost",
        "weather",
        "temperature",
        "population",
        "agelet me ",
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

    # Explicit learning instructions remain valid even when the user adds
    # substantial context and the request is longer than a short noun phrase.
    if _detect_response_intent(text) != "explore":
        return True

    if _is_known_technical_topic(text):
        return True

    if _looks_like_direct_factual_query(s):
        return False

    if any(_normalize_compact(p) in s for p in QUIZ_CUES):
        return True

    if any(_normalize_compact(p) in s for p in OVERVIEW_CUES):
        return True

    if any(_normalize_compact(tok) in s for tok in TOPIC_CUES):
        return True

    # A learner will often enter a single subject name ("photosynthesis",
    # "mitosis", "thermodynamics") without an instruction. Earlier this was
    # rejected merely because it was one word. Conversation primitives are
    # handled before this function, so a substantial alphabetic term is a
    # valid learning topic unless it is clearly generic dialogue language.
    # Technical subject names are not necessarily alphabetic: learners also
    # enter compact names such as "web3", "oauth2", "ipv6", and "5g".
    words = s.split()
    generic_single_words = {
        "again", "anything", "buddy", "continue", "different", "else",
        "fine", "friend", "good", "great", "help", "later", "maybe",
        "more", "next", "nothing", "okay", "please", "right", "same",
        "something", "sorry", "thanks", "today", "tomorrow", "wrong",
    }
    if (
        len(words) == 1
        and len(words[0]) >= 2
        and re.fullmatch(r"[a-z0-9][a-z0-9+#./-]*", words[0]) is not None
        and any(char.isalpha() for char in words[0])
        and words[0] not in generic_single_words
    ):
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
            "reply": "Hello. Good to see you. What would you like to understand today?",
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

    if _is_self_introduction(raw):
        return {
            "intent": "self_introduction",
            "reply": "Nice to meet you. I will remember how you introduced yourself in this conversation.",
            "followups": [],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "focused",
            "confidence": 0.98,
        }

    if _is_smalltalk(raw) or _is_conversation_only_turn(raw):
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

    if re.search(r"\b(generate|create|build|make)\b.*\b(question map|qmap)\b", s):
        return {
            "intent": "topic_explore",
            "response_intent": "explore",
            "reply": "",
            "followups": [],
            "should_interrogate": True,
            "should_answer_direct": False,
            "mode_hint": mode,
            "confidence": 0.99,
        }

    if _looks_like_contextual_utterance(raw):
        return {
            "intent": "clarify",
            "reply": "",
            "followups": [],
            "should_interrogate": False,
            "should_answer_direct": False,
            "mode_hint": "focused",
            "confidence": 0.84,
        }

    if _looks_like_direct_factual_query(raw):
        return {
            "intent": "direct_factual_query",
            "response_intent": _detect_response_intent(raw),
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
            "response_intent": _detect_response_intent(raw),
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

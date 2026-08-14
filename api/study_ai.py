# api/study_ai.py
from typing import Dict, Any, Tuple, Optional, Union
import re

from api.llm_answers import llm_enabled, generate_dynamic_answer_result
from api.intent_layer import detect_intent


def _parse_llm_debug_error(text: str) -> Tuple[Optional[int], str]:
    """
    Legacy safety: if any old debug strings leak into answer text,
    detect them and suppress in UI.
    """
    if not isinstance(text, str):
        return None, "unknown"

    m = re.search(r"\[LLM DEBUG\]\s*HTTP\s+(\d+):", text)
    if m:
        return int(m.group(1)), "http_error"

    if "[LLM DEBUG]" in text:
        return None, "debug"

    return None, "unknown"


def _fallback_ai_lesson(user_message: str, level: str) -> str:
    # Simple fallback (only used if LLM is disabled).
    return (
        "# AI Tutor (Fallback)\n\n"
        "LLM is currently disabled, so this is a safe fallback.\n\n"
        f"Your prompt: {user_message}\n\n"
        "Try again after setting OPENAI_API_KEY.\n"
    )


def _normalize_mode(raw: Optional[str]) -> str:
    """
    Supported:
      - deep (default)
      - intro (New Chat topic introduction)
      - high (overview)
      - quiz
      - focused (FUQ-style direct deep bullets)
      - carm (context-aware immediate practical answer)
      - conversation (short natural conversational turn)
    Accept common aliases.
    """
    if not raw:
        return "deep"
    m = str(raw).strip().lower()

    alias = {
        "deep": "deep",
        "default": "deep",
        "d": "deep",
        "research": "deep",
        "apply": "deep",

        "intro": "intro",
        "introduction": "intro",

        "overview": "high",
        "high": "high",
        "summary": "high",
        "brief": "high",

        "quiz": "quiz",
        "q": "quiz",
        "questions": "quiz",
        "test": "quiz",

        "focused": "focused",
        "focus": "focused",
        "fuq": "focused",
        "bullet": "focused",
        "bullets": "focused",
        "carm": "carm",
        "context": "carm",
        "conversation": "conversation",
        "chat": "conversation",
    }
    return alias.get(m, "deep")



def _build_instruction(mode: str) -> str:
    """
    Build the *style contract* for the tutor. This is where we make
    'intro', 'high', 'quiz', and 'focused' visibly different from 'deep'.
    """
    if mode == "intro":
        return (
            "You are InI, a clear and thoughtful AI tutor.\n"
            "Write a descriptive INTRODUCTION that prepares the learner for a structured Question Map.\n"
            "- Preserve and address the user's exact topic; never replace it with a broader parent topic.\n"
            "- Start with this exact machine-readable structure, using valid JSON between the tags:\n"
            "<TOPIC_PROFILE>\n"
            '{"Entity type":"...", "Broad field":"...", "Subject":"...", "Research area":"...", "Mathematical foundation":"...", "Prerequisites":"...", "Related topics":"...", "Typical applications":"...", "Difficulty":"..."}\n'
            "</TOPIC_PROFILE>\n"
            "- Include 6–9 concise profile fields that locate the user's exact topic within its wider learning landscape.\n"
            "- Always include Entity type, Broad field, Subject, Prerequisites, Related topics, and Difficulty.\n"
            "- Set Difficulty to Beginner, Intermediate, or Advanced by judging the exact question and the depth of reasoning it requests—not merely the broad subject.\n"
            "- For mathematical, scientific, or technical topics, include relevant fields such as Research area, Mathematical foundation, Typical applications, or Subfield.\n"
            "- For products, people, organizations, places, or other non-technical subjects, replace technical-only fields with accurate topic-specific labels such as Organization type, Manufacturer, Parent domain, Full form, Name type, Era, Region, or Primary significance.\n"
            "- Always include a Prerequisites field with 3–6 distinct, concise foundations a learner should have before beginning this topic; separate the items with semicolons.\n"
            "- Omit irrelevant labels instead of writing unknown, none, or not applicable.\n"
            "- Keep profile values factual and compact; do not use Markdown inside the JSON.\n"
            "- Immediately after the closing TOPIC_PROFILE tag, output this exact machine-readable block using valid JSON:\n"
            "<LEARNING_PATHS>\n"
            '{"Foundation area":["Question?", "Question?"], "Second area":["Question?", "Question?"]}\n'
            "</LEARNING_PATHS>\n"
            "- Create exactly 5 topic-specific learning-path groups with 2–3 concise questions in each group.\n"
            "- The groups must reveal distinct foundations, mechanisms or mathematics, methods or optimization, applications, and advanced implications appropriate to the exact query.\n"
            "- Do not repeat Question Map questions verbatim and do not add a Suggested Follow-ups heading outside this block.\n"
            "- Immediately after the closing LEARNING_PATHS tag, output this exact machine-readable block using valid JSON:\n"
            "<YOUR_QUESTION>\n"
            '{"Question":"...", "Intent":"...", "Learning goal":"..."}\n'
            "</YOUR_QUESTION>\n"
            "- Question must preserve the user's exact substantive question without conversational filler.\n"
            "- Intent must explain in one concise sentence what the learner is really trying to understand.\n"
            "- Learning goal must state in one concise sentence what the learner should be able to explain after the answer.\n"
            "- Do not infer that the learner wants programming, coding, implementation, APIs, or developer workflows merely because the subject is technical. Include that intent only when the user's wording or established conversation context explicitly supports it.\n"
            "- Do not answer the question inside this block.\n"
            "- Immediately after the closing YOUR_QUESTION tag, output this exact machine-readable block:\n"
            "<CORE_EXPLANATION>\n"
            "<TITLE>A precise, topic-specific explanation title</TITLE>\n"
            "<OVERVIEW>Two concise sentences</OVERVIEW>\n"
            "<UPDATE_RULE>A single presentation-ready equation or governing relationship</UPDATE_RULE>\n"
            "<VARIABLES>\n"
            "symbol :: compact meaning\n"
            "</VARIABLES>\n"
            "<STEPS>\n"
            "1. Step name :: One concise explanatory sentence\n"
            "</STEPS>\n"
            "<KEY_INSIGHT>The single most important takeaway</KEY_INSIGHT>\n"
            "<WORKED_EXAMPLE>A compact numerical or concrete example</WORKED_EXAMPLE>\n"
            "</CORE_EXPLANATION>\n"
            "- Directly answer the user's exact question in this block.\n"
            "- Create 4â€“6 logically ordered steps with properly indented, concise explanations.\n"
            "- Use a precise central equation when the subject is mathematical; otherwise use the most important governing relationship.\n"
            "- Make UPDATE_RULE display-ready: output one equation only, without a label, prose, Markdown, code fences, or surrounding dollar signs. Prefer conventional mathematical symbols such as ×, −, →, ∑, ∂, √, subscripts, and superscripts over programming notation such as *, ->, sum(), or **.\n"
            "- Define every symbol used in the update rule and keep variable meanings compact.\n"
            "- Use the exact same symbols in UPDATE_RULE and VARIABLES; never provide variable definitions for symbols that do not appear in the displayed relationship.\n"
            "- Make headings and the Key insight carry the important emphasis; do not use Markdown inside the block.\n"
            "- Include a concrete worked example when one improves understanding; otherwise use a realistic conceptual example.\n"
            "- Immediately after the closing CORE_EXPLANATION tag, output this exact machine-readable block:\n"
            "<LEARNING_LOOP>\n"
            "<STAGES>\n"
            "1. Stage name :: One concise sentence explaining what happens\n"
            "</STAGES>\n"
            "<OUTCOME>One concise sentence explaining what completing or repeating the sequence achieves</OUTCOME>\n"
            "</LEARNING_LOOP>\n"
            "- Create 5 to 6 causal or operational stages specific to the user's exact question.\n"
            "- Never use placeholder-like stages such as Define the topic, closest related concepts, relate the main components, use a representative scenario, or summarize purpose and trade-offs. Name the actual concepts, mechanisms, or processes from the user's question in every stage.\n"
            "- Match the loop to the depth and form of the user's request: for a broad or introductory topic, use a conceptual learning progression; for a precise advanced question, use the technical reasoning or mechanism sequence; for an explicit practical request, use an actionable workflow.\n"
            "- Do not turn a broad topic into an advanced optimization, implementation, measurement, or troubleshooting workflow unless the user's wording or established context supports that depth.\n"
            "- Treat a bare topic or short noun phrase with no action verb as introductory. Use exactly 5 stagesâ€”identify, distinguish, connect, apply conceptually, and reviewâ€”then stop; do not append a refine or optimization stage. Such a loop must not instruct the learner to code, benchmark, measure, profile, optimize, debug, configure, deploy, or select replacement hardware.\n"
            "- For a cyclical process, the final stage must naturally lead back to the next cycle; for a non-cyclical subject, show the complete reasoning sequence toward a practical outcome.\n"
            "- Keep each stage compact, distinct, and free of Markdown.\n"
            "- Immediately after the closing LEARNING_LOOP tag, output this exact machine-readable block:\n"
            "<CONTINUE_JOURNEY>\n"
            "<DIRECTIONS>\n"
            "1. A short, topic-specific direction :: One concise sentence explaining the learner's immediate next step\n"
            "2. A short, topic-specific direction :: One concise sentence describing a practical way to apply or verify the idea\n"
            "3. A short, topic-specific direction :: One concise sentence identifying the deeper concept to explore afterward\n"
            "</DIRECTIONS>\n"
            "<DESTINATION>One concise sentence stating what the learner will be able to understand or do after following this path</DESTINATION>\n"
            "</CONTINUE_JOURNEY>\n"
            "- Create exactly 3 distinct directions: strengthen understanding, practise or verify it, then advance beyond it.\n"
            "- Make every direction specific to the user's exact question; never use generic labels such as Learn more or Explore further.\n"
            "- A practical verification step need not involve code. Recommend programming or implementation only when the user's wording or established context calls for it.\n"
            "- Do not repeat questions from Related Learning Paths or the Question Map.\n"
            "- Keep the directions non-interactive in wording: no invitations to click, choose, or select.\n"
            "- After the closing CONTINUE_JOURNEY tag, write the narrative introduction.\n"
            "- Target roughly 250–400 words.\n"
            "- Give every card one distinct job: Topic Profile classifies, Your Question interprets intent, Core Explanation answers, and Introduction supplies context.\n"
            "- Do not repeat the definition, governing relationship, worked example, learning goal, or step sequence already present in the structured blocks.\n"
            "- Do not preview the Learning Loop or explain how to use the Question Map; those cards must speak for themselves.\n"
            "- Structure the introduction as exactly three short paragraphs beginning with Purpose:, Major areas:, and Who should study this next:.\n"
            "- Keep those labels concise; the paragraphs should provide wider context rather than repeat the Core Explanation.\n"
            "- For a named institution or organization, explain its identity, research focus, and relationship to the wider field without inventing current details.\n"
            "- Keep a natural educational flow across those three compact sections.\n"
            "- Do not produce the Question Map itself, a quiz, or an exhaustive technical deep dive.\n"
            "- Avoid repetitive summaries and do not compress the introduction into only a few bullets.\n"
            "- Never invent current, local, or live facts.\n"
            "- End cleanly without repeating the opening definition.\n"
        )

    if mode == "high":
        return (
            "You are InI, a clean and helpful AI tutor.\n"
            "Produce a HIGH-LEVEL overview.\n"
            "- Answer the user's exact question before adding context.\n"
            "- Keep it short and crisp (4–7 bullets maximum).\n"
            "- Avoid deep dives; focus on the big picture.\n"
            "- Do not repeat an idea in a summary or conclusion.\n"
            "- If essential context is missing, ask one precise clarification instead of guessing.\n"
            "- When clarification is required, use no more than 60 words and stop after the question.\n"
            "- Never invent current, local, or live facts.\n"
            "- End with 2 suggested follow-up questions.\n"
        )

    if mode == "carm":
        return (
            "You are InI in Context-Aware Response Mode.\n"
            "Answer the practical request immediately and obey the response contract embedded in the user input.\n"
            "- Accuracy is more important than appearing comprehensive.\n"
            "- Never invent commands, flags, packages, paths, URLs, or system requirements.\n"
            "- Keep the complete response under 400 words.\n"
            "- Do not create a Question Map.\n"
            "- Do not add a conclusion or Suggested Follow-ups after the requested final section.\n"
        )

    if mode == "conversation":
        return (
            "You are InI holding a natural conversation.\n"
            "- Return only the next conversational turn.\n"
            "- Keep it under 70 words with no headings, bullets, or Question Map.\n"
            "- Ask at most one cross-question.\n"
            "- Explain uncertainty naturally instead of using a generic rejection.\n"
            "- Do not repeat stock wording.\n"
        )

    if mode == "quiz":
        return (
            "You are InI, an interactive AI tutor.\n"
            "Generate a QUIZ only (no answers unless user asks).\n"
            "- 7 questions total.\n"
            "- Mix: 3 conceptual, 2 scenario-based, 2 short definition.\n"
            "- Include difficulty tags: (Easy/Med/Hard).\n"
            "- Keep questions tight and unambiguous.\n"
            "- End with: 'Reply with your answers and I will grade you.'\n"
        )

    if mode == "focused":
        return (
            "You are InI, a thoughtful and visually clear AI tutor.\n"
            "Answer the user's question in a concise but pleasant-to-read way.\n"
            "\n"
            "Formatting rules:\n"
            "- Do NOT include an Introduction section.\n"
            "- Do NOT produce a Question Map.\n"
            "- Prefer 2 short readable paragraphs.\n"
            "- Target roughly 150 to 220 words total.\n"
            "- Avoid giant essays and avoid overly compressed bullets.\n"
            "- Use smooth educational flow and natural language.\n"
            "- Keep explanations beginner-friendly but intelligent.\n"
            "- Use examples only when they genuinely improve clarity.\n"
            "- Avoid numbered sections unless steps are necessary.\n"
            "- End naturally and cleanly.\n"
        )

    # deep (default)
    return (
        "You are InI, a deep technical AI tutor.\n"
        "Give the deepest useful answer for the question actually asked, not the longest possible answer.\n"
        "- Start with a direct answer to the user's exact question.\n"
        "- Match depth and length to the query. A simple or underspecified query should stay concise.\n"
        "- For genuinely complex technical questions, add mechanisms, examples, trade-offs, or failure modes only when they improve understanding.\n"
        "- Treat generic section templates as optional. Use at most 2–5 sections, each with a distinct purpose.\n"
        "- Never restate the same idea under different headings, in a checklist, or in a concluding recap.\n"
        "- Do not add both a detailed failure-modes section and a second short-checks section.\n"
        "- Avoid exhaustive checklists unless the user explicitly requests one.\n"
        "- If the query is ambiguous and the missing detail changes the answer, briefly explain the ambiguity and ask one targeted clarification.\n"
        "- When clarification is required, use no more than 80 words, ask one question, and stop. Do not add a generic guide, checklist, or hypothetical answer first.\n"
        "- For current, local, price, rate, weather, legal, medical, or other time-sensitive questions, never invent a present-day value. State what detail or live source is needed.\n"
        "- Use clean proportional formatting and concrete examples only when they are factual or clearly labelled as hypothetical.\n"
        "- Prefer roughly 250–600 words; exceed that only when the user clearly requests advanced depth.\n"
        "- End cleanly without repeating the answer.\n"
    )


def _archetype_for_mode(mode: str) -> str:
    if mode in {"intro", "high"}:
        return "ORIENT"
    if mode == "focused":
        return "APPLY"
    if mode == "quiz":
        return "NEXT"
    return "APPLY"


def _requires_current_context(topic: str) -> bool:
    """Identify requests whose answer depends on information that can change."""
    text = (topic or "").strip().lower()
    if not text:
        return False

    patterns = (
        r"\btoday\b",
        r"\bright now\b",
        r"\bcurrently\b",
        r"\blatest\b",
        r"\blive (?:price|rate|score|status|data|weather)\b",
        r"\bcurrent (?:price|rate|score|status|law|version|weather|temperature)\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _processor_accuracy_contract(topic: str) -> str:
    """Add terminology constraints only when the query concerns CPU cores."""
    text = (topic or "").lower()
    if not re.search(
        r"\b(?:cpu|processor|microarchitecture|multicore|multi-core|"
        r"dual[ -]core|quad[ -]core|hexa[ -]core|octa[ -]core|"
        r"physical cores?|logical processors?|hyper[ -]?threading|smt)\b",
        text,
    ):
        return ""
    return (
        "\nPROCESSOR TERMINOLOGY ACCURACY:\n"
        "- A core count describes physical processing cores, not a guaranteed thread count.\n"
        "- Distinguish physical cores, logical processors, hardware threads, and software threads.\n"
        "- Never infer logical-processor or thread count unless SMT/Hyper-Threading support is explicitly known.\n"
        "- For example, a hexa-core CPU has six physical cores; it may expose six logical processors without SMT or commonly twelve with two-way SMT.\n"
        "- Do not use the imprecise phrase native threads.\n"
    )


def _normalize_processor_terminology(answer: str, topic: str) -> str:
    """Repair the known core/thread conflation if it escapes generation."""
    if not _processor_accuracy_contract(topic):
        return answer
    return re.sub(
        r"\bsix\s+native\s+threads\b",
        "six physical processing cores",
        answer,
        flags=re.IGNORECASE,
    )


def _resolve_topic_context(topic: str) -> str:
    """Add context only for exact acronyms already routed as technical topics."""
    if topic.strip().lower() == "amd":
        return "AMD (Advanced Micro Devices)"
    return topic


def _continuation_context(previous_answer: str, max_chars: int = 6000) -> str:
    """Keep both the established outline and the latest unfinished passage."""
    text = (previous_answer or "").strip()
    if len(text) <= max_chars:
        return text

    opening_chars = min(1500, max_chars // 3)
    ending_chars = max_chars - opening_chars
    return (
        text[:opening_chars].rstrip()
        + "\n\n[...middle omitted...]\n\n"
        + text[-ending_chars:].lstrip()
    )


_LEARNING_LOOP_BLOCK = re.compile(
    r"<LEARNING_LOOP>.*?</LEARNING_LOOP>",
    flags=re.IGNORECASE | re.DOTALL,
)

_CONTINUE_JOURNEY_BLOCK = re.compile(
    r"<CONTINUE_JOURNEY>.*?</CONTINUE_JOURNEY>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _is_bare_learning_topic(user_topic: str) -> bool:
    """Return True for a short topic label with no requested action."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    if not topic or "?" in topic or len(topic.split()) > 8:
        return False

    action_cues = (
        "explain", "compare", "calculate", "derive", "prove", "show", "teach",
        "implement", "build", "create", "code", "program", "debug", "configure",
        "install", "deploy", "measure", "profile", "optimize", "evaluate", "design",
        "how", "why", "what", "when", "where", "which", "can", "should",
    )
    return not any(re.search(rf"\b{re.escape(cue)}\b", topic) for cue in action_cues)


def _adapt_intro_learning_loop(answer: str, user_topic: str) -> str:
    """Enforce a conceptual five-stage loop for an unqualified topic label."""
    if not _is_bare_learning_topic(user_topic) or not _LEARNING_LOOP_BLOCK.search(answer):
        return answer

    topic = re.sub(r"[<>]", "", re.sub(r"\s+", " ", user_topic.strip()))
    replacement = f"""<LEARNING_LOOP>
<STAGES>
1. Identify :: Define the topic and recognize its essential components.
2. Distinguish :: Separate the topic from its closest related concepts and common misconceptions.
3. Connect :: Relate the main components to understand how the topic works as a whole.
4. Apply conceptually :: Use a representative scenario to predict where the topic matters and what behavior to expect.
5. Review :: Summarize its purpose, major trade-offs, and limitations.
</STAGES>
<OUTCOME>The learner can explain the topic, distinguish it from neighboring ideas, and reason about it in context.</OUTCOME>
</LEARNING_LOOP>"""
    return _LEARNING_LOOP_BLOCK.sub(replacement, answer, count=1)


def _is_compare_request(user_topic: str) -> bool:
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    return bool(
        re.search(r"\b(compare|comparison|contrast|difference between|versus|vs\.? )\b", topic)
        or topic.startswith("compare ")
    )


def _comparison_pair(user_topic: str) -> tuple[str, str] | None:
    """Extract two compact comparison labels for deterministic adaptations."""
    topic = re.sub(r"[?.!]+$", "", re.sub(r"\s+", " ", user_topic.strip()))
    topic = re.sub(
        r"^(?:compare|contrast)\s+",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    parts = re.split(
        r"\s+(?:and|versus|vs\.?)\s+|\s+difference\s+between\s+",
        topic,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    if len(parts) != 2:
        return None
    first, second = (part.strip(" ,:;-") for part in parts)
    if not first or not second or len(first.split()) > 8 or len(second.split()) > 8:
        return None
    return first, second


def _is_scientific_process_comparison(user_topic: str) -> bool:
    """Return True when a comparison asks how natural processes differ."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    process_terms = (
        "mitosis", "meiosis", "photosynthesis", "cellular respiration",
        "aerobic respiration", "anaerobic respiration", "fermentation",
        "transcription", "translation", "dna replication", "diffusion",
        "osmosis", "evaporation", "condensation", "conduction",
        "convection", "radiation",
    )
    return _is_compare_request(topic) and sum(term in topic for term in process_terms) >= 2


def _is_conceptual_comparison(user_topic: str) -> bool:
    """Return True for comparisons intended to clarify concepts, not choose tools."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    conceptual_pairs = (
        ("deductive", "inductive"),
        ("accuracy", "precision"),
        ("validity", "reliability"),
        ("necessary", "sufficient"),
    )
    return _is_compare_request(topic) and any(
        first in topic and second in topic for first, second in conceptual_pairs
    )


def _is_causal_inference_comparison(user_topic: str) -> bool:
    """Return True when association is being contrasted with causal evidence."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    return (
        _is_compare_request(topic)
        and "correlation" in topic
        and ("causation" in topic or "causal" in topic)
    )


def _is_research_method_comparison(user_topic: str) -> bool:
    """Return True for comparisons between qualitative and quantitative methods."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    return (
        _is_compare_request(topic)
        and "qualitative" in topic
        and "quantitative" in topic
    )


def _is_learning_theory_comparison(user_topic: str) -> bool:
    """Return True for the classical/operant conditioning distinction."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    return (
        _is_compare_request(topic)
        and "classical" in topic
        and "operant" in topic
        and "conditioning" in topic
    )


def _is_stack_queue_comparison(user_topic: str) -> bool:
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    return _is_compare_request(topic) and "stack" in topic and "queue" in topic


def _is_graph_search_comparison(user_topic: str) -> bool:
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    breadth = "breadth-first" in topic or "breadth first" in topic or "bfs" in topic
    depth = "depth-first" in topic or "depth first" in topic or "dfs" in topic
    return _is_compare_request(topic) and breadth and depth


def _is_metric_comparison(user_topic: str) -> bool:
    """Return True when the user compares evaluation or statistical metrics."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    metric_pairs = (
        ("precision", "recall"),
        ("sensitivity", "specificity"),
        ("precision", "accuracy"),
        ("roc", "auc"),
        ("f1", "accuracy"),
    )
    return _is_compare_request(topic) and any(
        first in topic and second in topic for first, second in metric_pairs
    )


def _metric_comparison_pair(user_topic: str) -> tuple[str, str] | None:
    """Return the actual metric pair named by the learner, when recognized."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip().lower())
    metric_pairs = (
        ("precision", "recall"),
        ("sensitivity", "specificity"),
        ("precision", "accuracy"),
        ("roc", "auc"),
        ("f1", "accuracy"),
    )
    return next(
        (pair for pair in metric_pairs if pair[0] in topic and pair[1] in topic),
        None,
    )


def _adapt_compare_learning_loop(answer: str, user_topic: str) -> str:
    """Keep comparison requests analytical unless implementation was requested."""
    if not _is_compare_request(user_topic) or not _LEARNING_LOOP_BLOCK.search(answer):
        return answer

    pair = _comparison_pair(user_topic)
    normalized_pair = {item.casefold() for item in pair} if pair else set()

    if normalized_pair == {"tcp", "udp"}:
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Establish transport requirements :: Identify whether the application needs ordered delivery, retransmission, congestion control, low latency, or message boundaries.
2. Trace TCP delivery :: Follow connection setup, sequencing, acknowledgements, retransmission, flow control, and congestion control from sender to receiver.
3. Trace UDP delivery :: Follow independent datagrams without connection setup, built-in ordering, retransmission, or congestion control.
4. Compare network conditions :: Evaluate how TCP and UDP behave under packet loss, delay, reordering, and changing available bandwidth.
5. Match protocol to application :: Select TCP, UDP, or an application-layer design such as QUIC according to the required reliability and latency behavior.
</STAGES>
<OUTCOME>The learner can explain the mechanisms of TCP and UDP and justify a transport choice from an application's delivery, latency, and congestion requirements.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_stack_queue_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Trace insertion and removal :: Follow the same sequence of items through stack push/pop and queue enqueue/dequeue operations.
2. Connect order to structure :: Relate LIFO behavior to the stack top and FIFO behavior to queue front and rear positions.
3. Compare implementations :: Examine dynamic arrays, linked lists, and circular buffers through operation cost and memory behavior.
4. Match algorithms to access order :: Use stacks for recursion, undo, and depth-first search; use queues for scheduling, buffering, and breadth-first search.
5. Test boundary conditions :: Check underflow, overflow, resizing, and concurrent-access cases without confusing queues with priority queues or deques.
</STAGES>
<OUTCOME>The learner can trace stack and queue operations, explain why their service orders differ, and select the correct structure for an algorithm.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_graph_search_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Build the same graph frontier :: Start BFS and DFS from the same node with an explicit visited set.
2. Trace traversal order :: Follow FIFO queue expansion for BFS and LIFO stack or recursion expansion for DFS.
3. Compare guarantees :: Determine completeness, shortest-path behavior, and time and space costs under the same graph assumptions.
4. Match search to problem shape :: Apply BFS to level distance and unweighted shortest paths, and DFS to backtracking, cycle analysis, and topological structure.
5. Test difficult graphs :: Examine cycles, disconnected components, infinite branches, and memory-heavy wide frontiers.
</STAGES>
<OUTCOME>The learner can trace BFS and DFS, predict their traversal order and guarantees, and choose between them from graph structure and search goals.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_scientific_process_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Identify :: Define each process, its biological purpose, and where it occurs.
2. Distinguish :: Compare their stages, inputs, outputs, and defining mechanisms using the same criteria.
3. Connect :: Relate their differences to the roles they play in the organism or system.
4. Apply conceptually :: Trace representative examples and predict the outcome of each process.
5. Review :: Summarize the similarities, essential differences, and common misconceptions.
</STAGES>
<OUTCOME>The learner can explain both processes, compare them accurately, and predict their biological outcomes.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_learning_theory_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Identify the learned association :: Define how classical conditioning links two stimuli while operant conditioning links behavior to its consequence.
2. Trace acquisition :: Follow conditioned-stimulus pairing in classical conditioning and reinforcement or punishment contingencies in operant conditioning.
3. Compare learner behavior :: Distinguish elicited responses from emitted actions and identify the learner's role in each process.
4. Apply to cases :: Classify examples from exposure therapy, classroom behavior, animal training, and habit formation using explicit evidence.
5. Review boundary cases :: Examine extinction, generalization, avoidance, and situations where both forms of learning operate together.
</STAGES>
<OUTCOME>The learner can distinguish classical from operant conditioning by the association learned, the behavior involved, and the mechanism that changes it.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_metric_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Identify :: Define each metric precisely and map every term to the underlying observations or confusion-matrix cells.
2. Distinguish :: Compare what each denominator asks, which errors affect it, and what a high or low value means.
3. Connect :: Relate the metrics to thresholds, class imbalance, and the real cost of false positives and false negatives.
4. Apply conceptually :: Compute both metrics for representative cases and explain why the preferred balance changes by application.
5. Review :: Summarize the trade-off, common interpretation mistakes, and when a combined measure is useful.
</STAGES>
<OUTCOME>The learner can calculate, interpret, and select the metrics according to the error costs of the task.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_causal_inference_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Identify :: Define statistical association and causal effect, including the direction of each claim.
2. Distinguish :: Separate correlation from causation by testing confounding, reverse causality, selection effects, and coincidence.
3. Connect :: Relate observational patterns to causal assumptions using interventions, counterfactuals, and causal diagrams.
4. Apply conceptually :: Evaluate representative claims and identify what experiment, natural experiment, or adjustment strategy could support causality.
5. Review :: Summarize what the evidence establishes, what remains assumed, and which alternative explanations survive.
</STAGES>
<OUTCOME>The learner can distinguish association from causal evidence and state what additional design or assumptions a causal claim requires.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_research_method_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Identify :: Define the research question and the kind of evidence needed to answer it.
2. Distinguish :: Compare qualitative and quantitative data, sampling, collection, analysis, and standards of validity using shared criteria.
3. Connect :: Relate each method's strengths and limitations to depth, measurement, generalization, and context.
4. Apply conceptually :: Match representative research questions to qualitative, quantitative, or mixed-method designs and justify each choice.
5. Review :: Summarize the decision boundaries, integration opportunities, and common methodological mismatches.
</STAGES>
<OUTCOME>The learner can select and justify an appropriate research design based on the question, evidence, and intended claim.</OUTCOME>
</LEARNING_LOOP>"""
    elif _is_conceptual_comparison(user_topic):
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Identify :: Define each concept precisely and state the kind of reasoning or claim it represents.
2. Distinguish :: Compare their starting points, logical movement, standards of support, and conclusion strength.
3. Connect :: Show how the concepts complement one another within inquiry, explanation, and evidence-based judgment.
4. Apply conceptually :: Classify representative arguments and explain why each example belongs to one form rather than the other.
5. Review :: Summarize the essential contrast, common confusions, and limits of each concept.
</STAGES>
<OUTCOME>The learner can distinguish the concepts accurately, recognize them in examples, and explain how each supports knowledge.</OUTCOME>
</LEARNING_LOOP>"""
    elif pair:
        first, second = pair
        replacement = f"""<LEARNING_LOOP>
<STAGES>
1. Define both subjects :: State precisely what {first} and {second} are and the problem each addresses.
2. Compare shared criteria :: Evaluate {first} and {second} using the same mechanisms, assumptions, strengths, and limitations.
3. Connect differences to consequences :: Explain how their structural differences change behavior in realistic conditions.
4. Apply the comparison :: Test {first} and {second} against representative scenarios using explicit requirements.
5. Review the boundary :: Summarize when {first}, {second}, or a hybrid approach is appropriate and identify important exceptions.
</STAGES>
<OUTCOME>The learner can compare {first} and {second} consistently and justify when each is appropriate.</OUTCOME>
</LEARNING_LOOP>"""
    else:
        replacement = """<LEARNING_LOOP>
<STAGES>
1. Identify :: Define the two alternatives and the decision being examined.
2. Distinguish :: Compare their structures, strengths, limitations, and assumptions using shared criteria.
3. Connect :: Relate each trade-off to the kinds of problems and constraints where it matters.
4. Apply conceptually :: Use representative scenarios to determine which alternative fits each situation.
5. Review :: Summarize the decision boundaries, exceptions, and possible hybrid approaches.
</STAGES>
<OUTCOME>The learner can compare the alternatives consistently and justify when each is the better fit.</OUTCOME>
</LEARNING_LOOP>"""
    return _LEARNING_LOOP_BLOCK.sub(replacement, answer, count=1)


def _adapt_compare_journey(answer: str, user_topic: str) -> str:
    """Remove unsolicited implementation work from comparison follow-through."""
    if not _is_compare_request(user_topic) or not _CONTINUE_JOURNEY_BLOCK.search(answer):
        return answer

    pair = _comparison_pair(user_topic)
    normalized_pair = {item.casefold() for item in pair} if pair else set()

    if normalized_pair == {"tcp", "udp"}:
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Inspect TCP and UDP packet flows :: Trace a TCP exchange and a UDP exchange, labeling connection setup, sequence or acknowledgement behavior, and message boundaries.
2. Test loss and latency trade-offs :: Predict how packet loss, reordering, and delay affect a web transfer, voice call, DNS lookup, and multiplayer game under each protocol.
3. Explore modern transport design :: Study how QUIC builds reliable multiplexed streams over UDP while implementing congestion control in user space.
</DIRECTIONS>
<DESTINATION>The learner can choose and defend TCP, UDP, or QUIC from concrete reliability, ordering, latency, and deployment requirements.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_stack_queue_comparison(user_topic):
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Simulate both structures by hand :: Insert the same item sequence, remove every item, and record the contrasting service orders.
2. Connect structures to algorithms :: Trace a call stack and a breadth-first work queue to see how access order controls execution.
3. Explore practical variants :: Compare circular queues, deques, bounded buffers, and thread-safe implementations with ordinary stacks and queues.
</DIRECTIONS>
<DESTINATION>The learner can implement and select stack or queue behavior without confusing LIFO, FIFO, deque, and priority semantics.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_graph_search_comparison(user_topic):
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Trace one graph with both searches :: Record frontier contents, visited nodes, parent links, and traversal order after every expansion.
2. Verify guarantees experimentally :: Compare BFS and DFS on shortest-path, maze, cycle-detection, and disconnected-graph examples.
3. Explore hybrid search :: Study iterative deepening and bidirectional BFS as responses to DFS depth risk and BFS memory growth.
</DIRECTIONS>
<DESTINATION>The learner can justify BFS, DFS, or a hybrid using completeness, optimality, memory, and graph-shape requirements.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_scientific_process_comparison(user_topic):
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Strengthen the stage-by-stage comparison :: Place corresponding stages side by side and trace their inputs, transformations, and outputs.
2. Connect mechanism to biological purpose :: Explain how each process's location and mechanism support its distinct role in the living system.
3. Test the distinction with examples :: Predict how changing an input or condition affects each process's material, energy, or biological outcome.
</DIRECTIONS>
<DESTINATION>The learner can compare the processes from inputs through mechanisms to outcomes without importing features that belong only to a different biological process.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_learning_theory_comparison(user_topic):
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Classify contrasting examples :: Label the stimulus, response, behavior, and consequence in paired classical and operant cases.
2. Examine overlapping mechanisms :: Study avoidance learning and other cases where respondent and instrumental processes interact.
3. Design an ethical intervention :: Compare how exposure, reinforcement schedules, shaping, and extinction would change a concrete behavior.
</DIRECTIONS>
<DESTINATION>The learner can diagnose the conditioning mechanism in real situations and select an evidence-based, ethically appropriate learning strategy.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_metric_comparison(user_topic):
        first_metric, second_metric = _metric_comparison_pair(user_topic) or (
            "the first metric",
            "the second metric",
        )
        replacement = f"""<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Strengthen metric interpretation :: Recalculate both metrics from several confusion matrices and explain every change.
2. Explore threshold trade-offs :: Trace how moving the classification threshold changes false positives, false negatives, {first_metric}, and {second_metric}.
3. Match metrics to consequences :: Compare realistic applications and justify the appropriate balance from their error costs.
</DIRECTIONS>
<DESTINATION>The learner can defend a metric choice with calculations, threshold behavior, and domain consequences.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_causal_inference_comparison(user_topic):
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Diagnose a correlated pattern :: Take an observational association and list plausible confounders, reverse-causal paths, and selection effects.
2. Draw the causal structure :: Build a simple causal diagram and identify which variables should be controlled, measured, or left untouched.
3. Strengthen identification :: Compare randomized experiments, natural experiments, longitudinal designs, and instrumental variables for the same causal question.
</DIRECTIONS>
<DESTINATION>The learner can evaluate whether evidence supports association alone or a defensible causal conclusion.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_research_method_comparison(user_topic):
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Strengthen method selection :: Compare several research questions and identify whether each requires contextual depth, numerical measurement, or both.
2. Examine evidence quality :: Evaluate sampling, data collection, analysis, validity, and bias in one qualitative and one quantitative study.
3. Explore mixed-method integration :: Design a sequence in which findings from one method meaningfully guide or explain results from the other.
</DIRECTIONS>
<DESTINATION>The learner can design and defend a coherent qualitative, quantitative, or mixed-method study without confusing their evidence standards.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif _is_conceptual_comparison(user_topic):
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Strengthen the distinction :: Rewrite several claims in both forms and identify how their premises and conclusions differ.
2. Examine mixed reasoning :: Study real explanations where the two concepts work together rather than appearing in isolation.
3. Test common edge cases :: Classify ambiguous examples, justify the classification, and identify where certainty or support can fail.
</DIRECTIONS>
<DESTINATION>The learner can identify, construct, and evaluate both forms without treating either as universally superior.</DESTINATION>
</CONTINUE_JOURNEY>"""
    elif pair:
        first, second = pair
        replacement = f"""<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Strengthen the shared criteria :: Build a side-by-side comparison of {first} and {second} using the same requirements and assumptions.
2. Verify with contrasting scenarios :: Apply {first} and {second} to representative cases and explain how each result follows from their differences.
3. Explore limits and combinations :: Study the edge cases where {first}, {second}, or a hybrid approach stops being sufficient.
</DIRECTIONS>
<DESTINATION>The learner can defend a context-aware choice between {first} and {second} without treating either as universally superior.</DESTINATION>
</CONTINUE_JOURNEY>"""
    else:
        replacement = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Clarify the decision criteria :: List the requirements, constraints, and trade-offs that matter most in the comparison.
2. Examine representative scenarios :: Apply the same criteria to a few contrasting situations and explain which alternative fits each one.
3. Explore boundaries and hybrids :: Study edge cases where neither alternative is sufficient alone or where combining them is reasonable.
</DIRECTIONS>
<DESTINATION>The learner can make and defend a context-aware choice without assuming that one alternative is universally superior.</DESTINATION>
</CONTINUE_JOURNEY>"""
    return _CONTINUE_JOURNEY_BLOCK.sub(replacement, answer, count=1)


def _normalize_continue_journey_headings(answer: str) -> str:
    """Replace leaked prompt placeholders with stable, meaningful headings."""
    match = _CONTINUE_JOURNEY_BLOCK.search(answer)
    if not match:
        return answer

    headings = ("Strengthen understanding", "Practise or verify", "Advance beyond it")
    index = 0

    def replace_placeholder(_: re.Match[str]) -> str:
        nonlocal index
        heading = headings[min(index, len(headings) - 1)]
        index += 1
        return heading

    normalized = re.sub(
        r"A short, topic-specific direction",
        replace_placeholder,
        match.group(0),
        flags=re.IGNORECASE,
    )
    return answer[:match.start()] + normalized + answer[match.end():]


def _normalize_stack_queue_relationship(answer: str, user_topic: str) -> str:
    """Replace ambiguous prose relationships with explicit access-order rules."""
    if not _is_stack_queue_comparison(user_topic):
        return answer

    answer = re.sub(
        r"<UPDATE_RULE>.*?</UPDATE_RULE>",
        (
            "<UPDATE_RULE>order_stack = reverse(insertion_order); "
            "order_queue = insertion_order</UPDATE_RULE>"
        ),
        answer,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(
        r"<VARIABLES>.*?</VARIABLES>",
        """<VARIABLES>
order_stack :: removal order produced by stack pop operations
order_queue :: removal order produced by queue dequeue operations
insertion_order :: sequence in which elements enter the structure
</VARIABLES>""",
        answer,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


_NUMBERED_MEIOTIC_STAGES = ("meiosis", "prophase", "metaphase", "anaphase", "telophase")


def _requested_numbered_stage_pair(user_topic: str) -> str | None:
    """Return the stage name when the query explicitly contrasts I with II."""
    topic = re.sub(r"\s+", " ", (user_topic or "").strip())
    for stage in _NUMBERED_MEIOTIC_STAGES:
        if re.search(
            rf"\b{stage}\s+(?:i|1)\b.*\b{stage}\s+(?:ii|2)\b",
            topic,
            flags=re.IGNORECASE,
        ):
            return stage
    return None


def _normalize_numbered_stage_comparison(answer: str, user_topic: str) -> str:
    """Repair a provider collapsing the requested stage II into stage I."""
    stage = _requested_numbered_stage_pair(user_topic)
    if not stage:
        return answer

    escaped = re.escape(stage)
    normalized = answer

    # Direct comparison forms used throughout headings, paths and questions.
    normalized = re.sub(
        rf"\b{escaped}\s+i\s+(and|vs\.?|versus|or)\s+(?:{escaped}\s+)?i\b",
        lambda match: f"{stage} I {match.group(1)} {stage} II",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        rf"\b{escaped}\s+i\s*\+\s*{escaped}\s+i\b",
        f"{stage} I + {stage} II",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        rf"\b{escaped}\s+i\s+(and|vs\.?|versus|or)\s+i\b",
        lambda match: f"{stage} I {match.group(1)} II",
        normalized,
        flags=re.IGNORECASE,
    )

    # In a sentence that contrasts the same stage twice, the occurrence after
    # the contrast word is necessarily the requested stage II.
    normalized = re.sub(
        rf"(\b{escaped}\s+i\b[^.?!\n]{{0,220}}?\b(?:whereas|while|but|from|versus|vs\.?)\s+){escaped}\s+i\b",
        rf"\1{stage} II",
        normalized,
        flags=re.IGNORECASE,
    )

    # Stage-II roles have distinctive biological semantics even when the
    # provider starts a new sentence instead of using a comparison connector.
    semantic_patterns = (
        (rf"\b{escaped}\s+i\b(?=\s+(?:aligns?|separates?)\s+(?:individual\s+chromosomes|sister\s+chromatids))", f"{stage} II"),
        (rf"\b{escaped}\s+i\b(?=\s+(?:is|acts)\s+(?:as\s+)?(?:an?\s+)?equational\b)", f"{stage} II"),
        (rf"\b{escaped}\s+i\b(?=\s+(?:resembles|is\s+like)\s+mitosis\b)", f"{stage} II"),
        (rf"\b{escaped}\s+i\b(?=[^.;\n]{{0,100}}\bcentromeric\s+cohesin\s+is\s+(?:removed|cleaved))", f"{stage} II"),
        (rf"\bsister\s+chromatids\s+(?:in|during|at)\s+{escaped}\s+i\b", f"sister chromatids in {stage} II"),
        (rf"\b{escaped}\s+i\b(?=\s+(?:does\s+not\s+change\s+ploidy|lacks\s+crossing-over))", f"{stage} II"),
        (rf"\bMII\s*[^A-Za-z0-9\s]+\s*{escaped}\s+i\b", f"MII — {stage} II"),
    )
    for pattern, replacement in semantic_patterns:
        normalized = re.sub(
            pattern,
            lambda match, value=replacement: (
                value[0].upper() + value[1:]
                if match.group(0)[0].isupper()
                else value
            ),
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized


def _normalize_response_text(answer: str, user_topic: str = "") -> str:
    normalized = re.sub(
        r"\bYou(?:['\u2018\u2019]|â€™)?l\b",
        "You'll",
        answer,
        flags=re.IGNORECASE,
    )
    def normalize_youll_case(match: re.Match[str]) -> str:
        prefix = normalized[: match.start()].rstrip()
        if not prefix or prefix[-1] in ".!?":
            return "You'll"
        return "you'll"

    normalized = re.sub(r"\bYou'll\b", normalize_youll_case, normalized)
    normalized = re.sub(
        r"\bmeiosis\s+i\s+(and|vs\.?|versus|or)\s+(meiosis\s+)?i\b",
        lambda match: (
            f"meiosis I {match.group(1)} "
            f"{'meiosis ' if match.group(2) else ''}II"
        ),
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bmeiosis\s+i\s*/\s*i\b",
        "meiosis I/II",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bmeiosis\s+i\s*([—–-]\s*sister\s+chromatid(?:s)?\s+separation)\b",
        lambda match: f"Meiosis II {match.group(1)}",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\band\s+meiosis\s+i\s*(?=\([^)]*sister\s+chromatid)",
        "and meiosis II ",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bmeiosis\s+i\s+separates\s+sister\s+chromatids\b",
        "meiosis II separates sister chromatids",
        normalized,
        flags=re.IGNORECASE,
    )
    if re.search(
        r"\bmeiosis\s+(?:i|1)\b.*\bmeiosis\s+(?:ii|2)\b",
        user_topic,
        flags=re.IGNORECASE,
    ):
        # When the requested comparison explicitly names both divisions, repair
        # provider text that repeats stage I in a stage-II role.
        normalized = re.sub(
            r"\bmeiosis\s+i\b(?=\s+is\s+the\s+equational\s+division)",
            lambda match: "Meiosis II" if match.group(0)[0].isupper() else "meiosis II",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"(\bafter\s+meiosis\s+i\b[^\n]{0,160}\bremains\b[^\n]{0,100}\bafter\s+)meiosis\s+i\b",
            r"\1meiosis II",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"(\bnondisjunction\s+in\s+meiosis\s+i\b[^?\n]{0,120}?\bfrom\s+)meiosis\s+i\b",
            r"\1meiosis II",
            normalized,
            flags=re.IGNORECASE,
        )
        explicit_stage_repairs = (
            (r"\bmeiosis\s+i\s*\+\s*meiosis\s+i\b", "meiosis I + meiosis II"),
            (r"\bmeiosis\s+i\s+(and|vs\.?|versus|or)\s+i\b", None),
            (r"\b0\s+for\s+meiosis\s+i\b", "0 for meiosis II"),
            (r"\bno\s+new\s+homolog\s+pairing\s+in\s+meiosis\s+i\b", "no new homolog pairing in meiosis II"),
            (r"\bmetaphase\s+i(?=:\s*individual\s+chromosomes)", "Metaphase II"),
            (r"\bmeiosis\s+i\s+resembles\s+mitosis\b", "meiosis II resembles mitosis"),
            (r"\bmeiosis\s+i(?=\s*\(equational\b)", "meiosis II"),
            (r"\bmeiosis\s+i(?=\s+is\s+(?:an?\s+)?equational\b)", "meiosis II"),
            (r"\bmeiosis\s+i(?=\s+lacks\s+crossing-over\b)", "meiosis II"),
            (r"\bmeiosis\s+i(?=\s+separates\s+sister\s+chromatids\b)", "meiosis II"),
            (r"\bsister\s+chromatids\s+in\s+meiosis\s+i\b", "sister chromatids in meiosis II"),
            (r"\bin\s+meiosis\s+i(?=,\s*centromeric\s+cohesin\s+is\s+removed)", "in meiosis II"),
            (r"(--meiosis\s+i-->\s*n\s*\(unchanged\))", "--meiosis II--> n (unchanged)"),
            (r"\bprophase\s+i\s+to\s+anaphase\s+i(?=\s+separating\s+chromatids)", "prophase II to anaphase II"),
            (r"\b(i\s+vs\.?\s+)i\b", None),
        )
        for pattern, replacement in explicit_stage_repairs:
            if replacement is None:
                normalized = re.sub(
                    pattern,
                    lambda match: (
                        f"meiosis I {match.group(1)} II"
                        if "meiosis" in match.group(0).casefold()
                        else f"{match.group(1)}II"
                    ),
                    normalized,
                    flags=re.IGNORECASE,
                )
            else:
                normalized = re.sub(
                    pattern,
                    lambda match, value=replacement: (
                        value[0].upper() + value[1:]
                        if match.group(0)[0].isupper()
                        else value
                    ),
                    normalized,
                    flags=re.IGNORECASE,
                )
    return _normalize_numbered_stage_comparison(normalized, user_topic)


_INTRO_REQUIRED_SECTIONS = (
    "TOPIC_PROFILE",
    "LEARNING_PATHS",
    "YOUR_QUESTION",
    "CORE_EXPLANATION",
    "LEARNING_LOOP",
    "CONTINUE_JOURNEY",
)


def _missing_intro_sections(answer: str) -> list[str]:
    """Detect structurally absent cards even when the provider reports completion."""
    source = answer or ""
    missing = [
        section
        for section in _INTRO_REQUIRED_SECTIONS
        if not re.search(
            rf"<{section}>.*?</{section}>",
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )
    ]
    narrative_labels = ("Purpose:", "Major areas:", "Who should study this next:")
    if not all(label.casefold() in source.casefold() for label in narrative_labels):
        missing.append("INTRODUCTION")
    return missing




def study_ai(payload: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    v0 Study mode:
    - ONLY AI topic uses LLM.
    - Accepts:
        1) str: user prompt
        2) dict: {"topic": "...", "mode": "deep|high|quiz", "continue_mode": bool, "previous_answer": str}
    - Returns stable schema:
        { mode, topic, domain, status, llm, answer, incomplete, stop_reason }
    """
    domain = "Artificial Intelligence"

    # ---- Parse input safely (string or dict) ----
    if isinstance(payload, dict):
        user_topic = (payload.get("topic") or payload.get("user_message") or "").strip()
        mode = _normalize_mode(payload.get("mode"))
        continue_mode = bool(payload.get("continue_mode", False))
        previous_answer = (payload.get("previous_answer") or "").strip()
        validation_feedback = [
            str(item).strip()
            for item in (payload.get("validation_feedback") or [])
            if str(item).strip()
        ][:8]
    else:
        user_topic = str(payload).strip()
        mode = "deep"
        continue_mode = False
        previous_answer = ""
        validation_feedback = []

    if not user_topic:
        user_topic = "Explain Artificial Intelligence."

    llm_topic = _resolve_topic_context(user_topic)

    # Focused mode = clicked Question Map / FUQ answer.
    # These are already educational questions and should bypass
    # conversational intent filtering.
    if mode == "focused":
        intent_name = "focused_question"
        should_interrogate = True
        should_answer_direct = False
    else:
        intent = detect_intent(user_topic)
        intent_name = (intent.get("intent") or "").strip().lower()
        should_interrogate = bool(intent.get("should_interrogate", False))
        should_answer_direct = bool(intent.get("should_answer_direct", False))

        # The full-card generator must use the same educational safety net as
        # /interrogate.  Without it, normative questions such as "Should
        # schools use facial recognition...?" can successfully receive a
        # Question Map but be classified as conversation here.  The resulting
        # plain reply then fails structured validation and the UI loses most of
        # its learning cards.
        normalized_topic = re.sub(
            r"\s+",
            " ",
            re.sub(r"[^a-z0-9 ]+", " ", user_topic.casefold()),
        ).strip()
        educational_signals = (
            "what", "why", "how", "difference", "compare", "explain",
            "define", "benefit", "problem", "classification", "types",
            "future", "applications", "limitations", "should",
        )
        looks_educational = (
            len(normalized_topic) > 8
            and any(signal in normalized_topic for signal in educational_signals)
        )
        if looks_educational and intent_name in {"", "clarify"}:
            intent_name = "topic_explore"
            should_interrogate = True
            should_answer_direct = False

    # Normal conversational behavior: greeting / thanks / help / etc.
    if (
    mode != "focused"
    and not should_interrogate
    and not should_answer_direct
        ):
        reply = (intent.get("reply") or "").strip() or "Send a topic to explore."
        return {
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
            "status": "ok",
            "llm": {"enabled": bool(llm_enabled()), "reason": "intent_reply"},
            "answer": reply,
            "incomplete": False,
            "stop_reason": None,
            "intent": intent_name,
            "followups": intent.get("followups") or [],
            "should_answer_direct": False,
        }

    # ---- LLM disabled fallback ----
    if not llm_enabled():
        return {
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
            "status": "ok",
            "llm": {"enabled": False, "reason": "no_api_key"},
            "answer": _fallback_ai_lesson(user_topic, mode.upper()),
            "incomplete": False,
            "stop_reason": None,
        }

    # ---- Build prompt ----
    instruction = _build_instruction(mode) + _processor_accuracy_contract(user_topic)

    if continue_mode and previous_answer:

    # --- STRICT TOKEN CONTINUATION ---
    # Preserve the established outline as well as the unfinished tail.
        prior_context = _continuation_context(previous_answer)

        question = (
        f"{instruction}\n"
        "STRICT CONTINUATION MODE:\n"
        "- Review the supplied context before writing.\n"
        "- Continue only the unfinished point from where the text stopped.\n"
        "- Do NOT restart the topic, definition, example, checklist, or conclusion.\n"
        "- Do NOT repeat any heading or idea already present in the context.\n"
        "- Do NOT add generic sections merely to make the answer longer.\n"
        "- Output ONLY genuinely new continuation text.\n\n"
        "Answer context (opening and latest text are preserved):\n"
        f"{prior_context}\n"
    )
    else:
        question = (
            f"{instruction}\n"
            f"User prompt: {llm_topic}\n"
        )
        if validation_feedback:
            feedback_lines = "\n".join(f"- {item}" for item in validation_feedback)
            question += (
                "\nVALIDATION RETRY:\n"
                "The previous draft was withheld. Regenerate the complete response from scratch; "
                "do not discuss the failed draft. Correct every issue below:\n"
                f"{feedback_lines}\n"
            )

    # ---- Call core LLM engine ----
    archetype = _archetype_for_mode(mode)
    if mode not in {"quiz", "focused"} and _requires_current_context(user_topic):
        archetype = "CURRENT"

    result = generate_dynamic_answer_result(
        topic=llm_topic,
        topic_type="concept",
        archetype=archetype,
        question=question,
        meta={
            "mode": "study_ai",
            "level": mode,
            "expects": "text",
            "continue_mode": continue_mode,
        },
        timeout_s=120,
    )

    ans = _normalize_processor_terminology(
        (result.get("answer") or "").strip(),
        user_topic,
    )
    if mode == "intro":
        # The first pass keeps the conservative bare-topic safeguard. If that
        # draft fails semantic validation, the retry prompt explicitly asks
        # the model for a topic-specific replacement; do not overwrite that
        # repaired loop with the same generic fallback that caused rejection.
        if not validation_feedback:
            ans = _adapt_intro_learning_loop(ans, user_topic)
        ans = _adapt_compare_learning_loop(ans, user_topic)
        ans = _adapt_compare_journey(ans, user_topic)
        ans = _normalize_stack_queue_relationship(ans, user_topic)
        ans = _normalize_continue_journey_headings(ans)
        ans = _normalize_response_text(ans, user_topic)
    incomplete = bool(result.get("incomplete", False))
    stop_reason = result.get("stop_reason", None)
    if mode == "intro" and not continue_mode:
        missing_sections = _missing_intro_sections(ans)
        if missing_sections:
            incomplete = True
            stop_reason = "missing_required_sections"

    # If the LLM returned no text (rare), expose a stable response
    if not ans:
        err = result.get("error")
        http_status = result.get("http_status")
        return {
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
            "status": "ok",
            "llm": {
                "enabled": True,
                "reason": "empty_answer" if not err else "llm_error",
                "http_status": http_status,
                "error": err,
            },
            "answer": "No answer generated.",
            "incomplete": False,
            "stop_reason": None,
            "knowledge_sources": result.get("knowledge_sources", []),
        }

    # Legacy safety: if debug strings leak into ans, suppress it (do not show raw debug)
    http_code, dbg_reason = _parse_llm_debug_error(ans)
    if dbg_reason in ("http_error", "debug"):
        return {
            "mode": mode,
            "topic": user_topic,
            "domain": domain,
            "status": "ok",
            "llm": {"enabled": True, "reason": dbg_reason, "http_status": http_code},
            "answer": "No answer generated.",
            "incomplete": False,
            "stop_reason": None,
        }

    return {
        "mode": mode,
        "topic": user_topic,
        "domain": domain,
        "status": "ok",
        "llm": {"enabled": True, "reason": "ok"},
        "answer": ans,
        "incomplete": incomplete,
        "stop_reason": stop_reason,
        "knowledge_sources": result.get("knowledge_sources", []),
    }


__all__ = ["study_ai"]

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
            "- Do not answer the question inside this block.\n"
            "- Immediately after the closing YOUR_QUESTION tag, output this exact machine-readable block:\n"
            "<CORE_EXPLANATION>\n"
            "<TITLE>A precise, topic-specific explanation title</TITLE>\n"
            "<OVERVIEW>Two concise sentences</OVERVIEW>\n"
            "<UPDATE_RULE>The central equation or governing relationship</UPDATE_RULE>\n"
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
            "- Define every symbol used in the update rule and keep variable meanings compact.\n"
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
            "- Do not repeat questions from Related Learning Paths or the Question Map.\n"
            "- Keep the directions non-interactive in wording: no invitations to click, choose, or select.\n"
            "- After the closing CONTINUE_JOURNEY tag, write the narrative introduction.\n"
            "- Target roughly 250–400 words.\n"
            "- Give every card one distinct job: Topic Profile classifies, Your Question interprets intent, Core Explanation answers, and Introduction supplies context.\n"
            "- Do not repeat the definition, governing relationship, worked example, learning goal, or step sequence already present in the structured blocks.\n"
            "- Do not preview the Learning Loop or explain how to use the Question Map; those cards must speak for themselves.\n"
            "- Begin with the topic's wider context and purpose, then explain its major areas and why it matters.\n"
            "- For a named institution or organization, explain its identity, research focus, and relationship to the wider field without inventing current details.\n"
            "- Use 3–5 short paragraphs or compact sections with natural educational flow.\n"
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
    else:
        user_topic = str(payload).strip()
        mode = "deep"
        continue_mode = False
        previous_answer = ""

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
    instruction = _build_instruction(mode)

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

    ans = (result.get("answer") or "").strip()
    incomplete = bool(result.get("incomplete", False))
    stop_reason = result.get("stop_reason", None)

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
    }


__all__ = ["study_ai"]

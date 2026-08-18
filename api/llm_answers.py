import re
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import requests

from api.wikidata_knowledge import (
    format_wikidata_prompt_context,
    retrieve_wikidata_context,
)
from api.wikipedia_knowledge import (
    format_wikipedia_prompt_context,
    retrieve_wikipedia_context,
)
from api.wikibooks_knowledge import (
    format_wikibooks_prompt_context,
    retrieve_wikibooks_context,
)
from api.crossref_knowledge import (
    format_crossref_prompt_context,
    retrieve_crossref_context,
)
from api.datacite_knowledge import (
    format_datacite_prompt_context,
    retrieve_datacite_context,
)


# ============================================================
# Load .env from repo root (works no matter where uvicorn starts)
# ============================================================
try:
    from dotenv import load_dotenv  # type: ignore

    # api/llm_answers.py -> repo_root/.env
    REPO_ROOT = Path(__file__).resolve().parents[1]
    DOTENV_PATH = REPO_ROOT / ".env"
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
except Exception:
    # If python-dotenv isn't installed, rely on OS env vars
    pass





# ============================================================
# ENV / CONFIG
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Responses-compatible model
DEFAULT_MODEL = os.getenv("INI_LLM_MODEL", "gpt-4o-mini").strip()
print("LOADED FROM API/LLM_ANSWERS.PY")
print("ACTIVE MODEL:", DEFAULT_MODEL)
print("INI_LLM_MODEL =", os.getenv("INI_LLM_MODEL"))



# Responses API uses max_output_tokens
INI_LLM_MAX_TOKENS = int(os.getenv("INI_LLM_MAX_TOKENS", "3000"))




# If True, keep extra debug info in returned dict (not appended to answer text)
INI_LLM_DEBUG = os.getenv("INI_LLM_DEBUG", "0").lower() in ("1", "true", "yes")


def llm_enabled() -> bool:
    return bool(OPENAI_API_KEY)


# ============================================================
# TEXT CLEANUP (fix mojibake / weird characters)
# ============================================================

def _normalize_text(s: str) -> str:
    """
    Fix common mojibake sequences we keep seeing in Windows/PS/Streamlit renders.
    Example: “â€”” -> “—”, “â€™” -> “’”.
    """
    if not s:
        return ""

    # Fast path: only run replacements if we detect telltale mojibake markers
    if "â" not in s and "Â" not in s and "Ã" not in s:
        return s

    repl = {
        # dashes / ellipsis
        "â€”": "—",
        "â€“": "–",
        "â€•": "―",
        "â€¦": "…",

        # quotes
        "â€œ": "“",
        "â€�": "”",
        "â€˜": "‘",
        "â€™": "’",
        "â„¢": "™",

        # bullets / middots
        "â€¢": "•",
        "Â·": "·",

        # spaces / nbsp artifacts
        "Â ": " ",

        # common multi-byte artifacts (seen occasionally)
        "Ã¢â‚¬â„¢": "’",
        "Ã¢â‚¬â€œ": "–",
        "Ã¢â‚¬â€�": "—",
        "Ã¢â‚¬Â¦": "…",
        "Ã¢â‚¬Å“": "“",
        "Ã¢â‚¬Â": "”",
    }

    for k, v in repl.items():
        s = s.replace(k, v)

    return s

# ============================================================
# POST-PROCESS CLEANUP (remove meta "continue" markers, stray markdown)
# ============================================================

def _postprocess_text(t: str) -> str:
    if not t:
        return ""

    # Normalize newlines (safe)
    t = t.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = []
    in_fence = False

    for ln in t.splitlines():
        s = ln.strip()
        s_l = ln.lstrip()

        # Track fenced code blocks so we don't "fix" code inside them
        if s_l.startswith("```"):
            in_fence = not in_fence
            cleaned_lines.append(ln)
            continue

        # Drop standalone markdown marker lines
        if s in {"**", "****", "__", "___"}:
            continue

        # Drop standalone continuation markers
        if re.fullmatch(r"\(?(continued|to be continued)\)?\.?", s, flags=re.I):
            continue
        if re.fullmatch(r"\(?(continue|see more)\)?\.{0,3}", s, flags=re.I):
            continue

        # Drop standalone "Continue?" / "Continue:" / "Continue →" style UI-like lines
        if re.fullmatch(
            r"(?:\(?\s*)continue(?:\s*\)?)\s*[\?\:\.\!…→\-]{0,3}\s*",
            s,
            flags=re.I,
        ):
            continue

        # Drop parenthetical meta lines mentioning continue/see more
        if s.startswith("(") and re.search(r"\b(continue|see more)\b", s, flags=re.I):
            continue

        # Drop instruction-like lines that tell user to continue
        if re.search(r"\breply\b.*\bcontinue\b", s, flags=re.I):
            continue
        if re.search(r"\b(click|press)\b.*\bcontinue\b", s, flags=re.I):
            continue

        # If the model outputs "python code in a single long line", wrap it.
        # This fixes cases like: "Example: ... from math import ... def foo(...): ..."
        if not in_fence:
            looks_like_py = (
                re.search(r"\bdef\s+\w+\s*\(", ln) is not None
                or re.search(r"\bclass\s+\w+\s*[\(:]", ln) is not None
                or re.match(r"\s*(from|import)\s+\w", ln) is not None
            )
            if looks_like_py and len(ln) >= 60:
                cleaned_lines.append("```python")
                cleaned_lines.append(ln)
                cleaned_lines.append("```")
                continue

        cleaned_lines.append(ln)


    t = "\n".join(cleaned_lines)

    # Collapse duplicate words that got split by a newline (e.g., "Verification\nVerification")
    t = re.sub(r"\b(\w+)\s*\n\s*\1\b", r"\1", t)

    # Reduce excessive blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip()



# ============================================================
# CONTEXT HELPERS
# ============================================================

def _era_hints(topic: str) -> str:
    t = (topic or "").lower()
    if "artificial intelligence" in t or t == "ai":
        return (
            "Cover: Classical AI → Machine Learning → Deep Learning → "
            "Foundation Models → Generative AI / LLMs → Tool use → Agentic AI."
        )
    if "machine learning" in t or t == "ml":
        return (
            "Cover: supervised vs unsupervised, features, training, "
            "evaluation, overfitting, deployment."
        )
    return ""


def _collect_text_from_content(content: Any) -> str:
    """
    Normalize different content shapes into a single concatenated text.

    Expected content items may look like:
      {"type":"output_text","text":"..."}
      {"type":"text","text":"..."}   (rare variants)
      {"type":"output_text","text":{"value":"..."}} (older/variant)
    """
    parts: List[str] = []

    if isinstance(content, list):
        for c in content:
            if not isinstance(c, dict):
                continue
            ctype = (c.get("type") or "").strip()
            txt = c.get("text")

            # Standard: output_text
            if ctype == "output_text" and isinstance(txt, str) and txt.strip():
                parts.append(txt)
                continue

            # Variant: type=text
            if ctype == "text":
                if isinstance(txt, str) and txt.strip():
                    parts.append(txt)
                    continue
                if isinstance(txt, dict) and isinstance(txt.get("value"), str) and txt["value"].strip():
                    parts.append(txt["value"])
                    continue

            # Variant: output_text with dict payload
            if ctype == "output_text" and isinstance(txt, dict) and isinstance(txt.get("value"), str) and txt["value"].strip():
                parts.append(txt["value"])
                continue

    return "\n".join([p for p in parts if p is not None]).strip()


def _extract_output_text(data: Dict[str, Any]) -> str:
    """
    Extract best-effort assistant text from Responses API output.

    Handles:
      - Standard Responses API: output -> message -> content -> output_text
      - Variants where message.content contains type "text"
      - Rare cases where text appears under output item "text"
      - Top-level content variants (rare)

    If nothing found, returns "".
    """
    output = data.get("output") or []
    if isinstance(output, list):
        # Prefer message items first
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                text = _collect_text_from_content(item.get("content"))
                if text:
                    return text

        # Fallback: sometimes content-like blocks appear in other output items
        for item in output:
            if not isinstance(item, dict):
                continue

            text = _collect_text_from_content(item.get("content"))
            if text:
                return text

            if isinstance(item.get("text"), str) and item["text"].strip():
                return str(item["text"]).strip()

            if isinstance(item.get("text"), dict) and isinstance(item["text"].get("value"), str) and item["text"]["value"].strip():
                return str(item["text"]["value"]).strip()

    # Top-level variants (rare)
    top_content = data.get("content")
    text = _collect_text_from_content(top_content)
    if text:
        return text

    # Last resort
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return str(data["output_text"]).strip()

    return ""


def _is_incomplete(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Detect "incomplete" responses (most often max_output_tokens).
    Returns (incomplete, reason).
    """
    status = str(data.get("status", "")).lower().strip()
    if status == "incomplete":
        inc = data.get("incomplete_details") or {}
        reason = inc.get("reason")
        return True, str(reason) if reason else "unknown"

    inc = data.get("incomplete_details") or {}
    if inc:
        reason = inc.get("reason")
        return True, str(reason) if reason else "unknown"

    return False, None


# ============================================================
# CORE LLM CALL (RESPONSES API)
# ============================================================

def generate_dynamic_answer_result(
    *,
    topic: str,
    topic_type: str,
    archetype: str,
    question: str,
    meta: Optional[Dict[str, Any]] = None,
    timeout_s: int = 120,
    previous_response_id: Optional[str] = None,
    **_ignored: Any,
) -> Dict[str, Any]:
    """
    Returns a structured result:
      {
        "answer": "<text or ''>",
        "incomplete": <bool>,
        "stop_reason": "<reason or None>",
        "status": "<responses status string or None>",
        "response_id": "<responses id or None>",
        "usage": <usage dict or None>,
        "model": "<model>",
        "http_status": <int or None>,
        "error": "<string or None>",
        "raw": <full response json only when INI_LLM_DEBUG=1 else None>
      }
    """
    if not llm_enabled():
        return {
            "answer": "",
            "incomplete": False,
            "stop_reason": None,
            "status": None,
            "response_id": None,
            "usage": None,
            "model": DEFAULT_MODEL,
            "http_status": None,
            "error": "llm_disabled_or_missing_key",
            "raw": None,
        }

    expects_json = False
    if isinstance(meta, dict):
        expects = str(meta.get("expects", "")).lower().strip()
        expects_json = expects in ("json", "json_object", "strict_json")

    # ============================================================
    # SYSTEM PROMPT (Deep Technical Drive, research-level)
    # ============================================================
    system_prompt = (
        "You are InI.ai — a teaching-first AI mentor and deep technical tutor.\n"
        "Your job is to make the learner genuinely understand, not just read text.\n\n"
        "Hard rules:\n"
        "- Be technically correct and specific. Prefer concrete mechanisms over vague claims.\n"
        "- Do NOT be generic or motivational. No filler, no clichés.\n"
        "- max_output_tokens is only a ceiling, NOT a target length.\n"
        "- Match answer length to question complexity.\n"
        "- For simple definition/plain-language questions, answer in 3-6 concise lines.\n"
        "- For normal conceptual questions, answer in 2-4 short paragraphs or bullets.\n"
        "- Use long deep technical answers ONLY when the question clearly asks for mechanisms, architecture, math, code, comparison, or advanced detail.\n"
        "- Do NOT include every suggested section for every answer.\n"
        "- When helpful, include light pseudocode / equations / concrete parameter examples (but keep it readable).\n"
        "- Use crisp structure with headings and bullets. Preserve indentation.\n"
        "- Use definitions + intuition + mechanics + examples + failure modes.\n"
        "- If you make an assumption, state it.\n"
        "- Prefer: precise terms, clear boundaries, and where it breaks.\n\n"
        "- If the user input is ambiguous or conversational, still try to infer a meaningful educational interpretation instead of rejecting immediately.\n"
        "- Avoid assistant-like refusal phrasing such as 'I can help, but...'.\n"
        "STRUCTURE POLICY:\n"
        "- Use the following structure internally, but DO NOT print the template text literally.\n"
        "- Only include sections that fit the question.\n"
        "Suggested sections:\n"
        "• Definition\n"
        "• Why it matters / when you use it\n"
        "• Core mechanism (step-by-step)\n"
        "• Concrete worked example(s)\n"
        "• Failure modes + mitigations\n"
        "• Practical checklist / sanity checks\n"
        "• Next steps (only if archetype == NEXT)\n\n"
        "Archetype rules:\n"
        "- ORIENT: build foundations and a correct mental model.\n"
        "- RISK: include misconceptions, failure modes, and how to detect them.\n"
        "- APPLY: include where it works AND where it fails, with examples.\n"
        "- NEXT: include a short actionable learning plan + exercises.\n\n"
        "Continuation rule:\n"
        "- Prefer finishing naturally within the allowed response size.\n"
        "- Only stop mid-section if absolutely necessary.\n"
        "- Do NOT output UI-control text like 'Continue', 'Continue?', '(continued)', 'to be continued', or instructions like 'click continue'.\n"
        "- If you want to ask permission to proceed, ask naturally without the word 'continue' (e.g., 'Want me to go deeper into X?' or 'Should I give an example next?').\n"
        "- CODE FORMATTING:\n"
        "  - Any code (Python/SQL/etc.) MUST be in fenced blocks with triple backticks.\n"
        "  - Never put code inline inside a sentence (no '... Example: def foo(): ...').\n"
        "  - For one-liners, still use a fenced block if it contains 'def', 'class', 'import', or multiple statements.\n"
        
    )

    if expects_json:
        system_prompt += (
            "\nOUTPUT RULE (STRICT): Return ONE valid JSON object only. "
            "No markdown, no commentary, no code fences.\n"
        )

    era_hint = _era_hints(topic)


    archetype_hint = ""

    arch = (archetype or "").upper().strip()

    if arch == "ORIENT":
        archetype_hint = (
            "Answer briefly and clearly. "
            "Prefer 3-6 lines maximum for simple questions. "
            "Do NOT write essays. "
            "Do NOT explain every edge case. "
            "Use only the most important explanation needed for understanding."
            "End with a section titled 'Suggested Follow-ups' containing exactly 2 concise follow-up questions."
        )

    elif arch in {"APPLY", "RISK"}:
        archetype_hint = (
            "Use moderate depth with practical examples and concise explanations."
        )

    elif arch in {"MECHANISM", "SYSTEM", "INTERNAL"}:
        archetype_hint = (
            "Detailed technical depth is allowed when useful."
        )

    elif arch == "NEXT":
        archetype_hint = (
            "Prefer structured learning steps and concise roadmaps."
        )

    elif arch == "CURRENT":
        archetype_hint = (
            "The request depends on current or live information. "
            "Do not invent or estimate a present-day value. "
            "State the limitation briefly, identify the minimum missing context or live source, "
            "ask one targeted clarification when needed, and stop. "
            "Use natural prose; do not print instruction-like labels such as 'Ask one'. "
            "Do not add a generic guide, checklist, worked example, or repeated explanation. "
            "Keep the complete answer under 100 words."
        )







    meta_txt = ""
    if isinstance(meta, dict) and meta:
        meta_txt = "Meta context: " + ", ".join(
            f"{k}={meta.get(k)}" for k in list(meta.keys())[:8]
        )

    wikidata_context: Dict[str, Any] = {}
    wikidata_prompt_context = ""
    wikipedia_context: Dict[str, Any] = {}
    wikipedia_prompt_context = ""
    wikibooks_context: Dict[str, Any] = {}
    wikibooks_prompt_context = ""
    crossref_context: Dict[str, Any] = {}
    crossref_prompt_context = ""
    datacite_context: Dict[str, Any] = {}
    datacite_prompt_context = ""
    if not (isinstance(meta, dict) and str(meta.get("mode") or "").lower() == "warmup"):
        # Independent public lookups run together so additional sources do not
        # multiply the user's retrieval wait.
        with ThreadPoolExecutor(max_workers=5) as executor:
            wikidata_future = executor.submit(retrieve_wikidata_context, topic)
            wikipedia_future = executor.submit(retrieve_wikipedia_context, topic)
            wikibooks_future = executor.submit(retrieve_wikibooks_context, topic)
            crossref_future = executor.submit(retrieve_crossref_context, topic)
            datacite_future = executor.submit(retrieve_datacite_context, topic)
            wikidata_context = wikidata_future.result()
            wikipedia_context = wikipedia_future.result()
            wikibooks_context = wikibooks_future.result()
            crossref_context = crossref_future.result()
            datacite_context = datacite_future.result()
        wikidata_prompt_context = format_wikidata_prompt_context(wikidata_context)
        wikipedia_prompt_context = format_wikipedia_prompt_context(wikipedia_context)
        wikibooks_prompt_context = format_wikibooks_prompt_context(wikibooks_context)
        crossref_prompt_context = format_crossref_prompt_context(crossref_context)
        datacite_prompt_context = format_datacite_prompt_context(datacite_context)

    knowledge_sources = [
        context
        for context in (
            wikidata_context,
            wikipedia_context,
            wikibooks_context,
            crossref_context,
            datacite_context,
        )
        if context
    ]

    user_prompt = (
        f"Topic: {topic}\n"
        f"Topic type: {topic_type}\n"
        f"Archetype: {archetype}\n"
        f"{meta_txt}\n"
        f"Era hints (if relevant): {era_hint}\n\n"
        f"Answer style guidance: {archetype_hint}\n"
        f"{wikidata_prompt_context}\n\n"
        f"{wikipedia_prompt_context}\n\n"
        f"{wikibooks_prompt_context}\n\n"
        f"{crossref_prompt_context}\n\n"
        f"{datacite_prompt_context}\n\n"
        f"User question / instruction:\n{question}\n"
    )

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    arch = (archetype or "").upper().strip()

    answer_token_limit = INI_LLM_MAX_TOKENS

    # IMPORTANT:
    # Never aggressively cap JSON generation.
    # Interrogate question maps use:
    # archetype="ORIENT" + expects_json=True
    # and need enough tokens to finish valid JSON.

    if not expects_json:

        if arch == "ORIENT":
            answer_token_limit = 600

        elif arch in {"APPLY", "RISK"}:
            answer_token_limit = 700

        elif arch in {"MECHANISM", "SYSTEM", "INTERNAL"}:
            answer_token_limit = 1400

        elif arch == "NEXT":
            answer_token_limit = 500

        elif arch == "CURRENT":
            answer_token_limit = 220

        # The New Chat introduction now carries the complete structured learning
        # response (profile, explanation, loop, paths, map context, and journey).
        # Its previous ORIENT ceiling could truncate the machine-readable blocks.
        if isinstance(meta, dict) and str(meta.get("level") or "").lower() == "intro":
            # 2,200 tokens proved marginal for classification-heavy topics and
            # caused repeated continuation/retry calls. A larger single-pass
            # ceiling is both more reliable and usually less wasteful.
            answer_token_limit = max(answer_token_limit, 3200)


    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "reasoning": {"effort": "minimal"},
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_output_tokens": answer_token_limit,
        "text": {"format": {"type": "text"}},
    }

    # TEMP DEBUG:
    # Disable strict JSON formatting temporarily.
    # The prompt already instructs the model to return JSON.
    pass

    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)

        if resp.status_code != 200:
            print("\n===== OPENAI HTTP ERROR =====")
            print("STATUS:", resp.status_code)
            print("BODY:", resp.text[:4000])
            print("===== END HTTP ERROR =====\n")
            return {
                "answer": "",
                "incomplete": False,
                "stop_reason": None,
                "status": None,
                "response_id": None,
                "usage": None,
                "model": DEFAULT_MODEL,
                "http_status": resp.status_code,
                "error": resp.text[:1200],
                "raw": None,
            }

        data = resp.json()

        print("\n===== RAW OPENAI RESPONSE =====")
        print(data)
        print("===== END RESPONSE =====\n")

        # Normalize immediately (first pass)
        text = _normalize_text(_extract_output_text(data).strip())

        incomplete, reason = _is_incomplete(data)

        # If truncated, aggressively shorten the visible answer.
        if incomplete and text:
            text = text.strip()

            # Cut off unfinished trailing fragments.
            text = re.sub(r"[,\-\:\s]+$", "", text)

            # Prefer complete ending.
            last_period = text.rfind(".")
            if last_period > 200:
                text = text[: last_period + 1]

        # If we got incomplete but no text (rare: reasoning-only output), return debug-safe error
        if incomplete and not text:
            
            return {
                "answer": "",
                "incomplete": True,
                "stop_reason": reason,
                "status": data.get("status"),
                "response_id": data.get("id"),
                "usage": data.get("usage"),
                "model": str(data.get("model") or DEFAULT_MODEL),
                "http_status": 200,
                "error": "incomplete_no_text",
                "raw": data if INI_LLM_DEBUG else None,
                "knowledge_sources": knowledge_sources,
            }

        # Normalize again at the end (second pass, prevents regressions)
        text = _normalize_text(text)

        # ---- collapse duplicated consecutive tokens (e.g., systemsystem) ----


        text = re.sub(r'\b(\w+)\1\b', r'\1', text)

        # ---- collapse accidental double words separated by space ----
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text)

        text = _postprocess_text(text)

        print("\n===== EXTRACTED TEXT =====")
        print(text[:3000] if text else "EMPTY_TEXT")
        print("===== END EXTRACTED TEXT =====\n")

        return {
            "answer": text,
            "incomplete": bool(incomplete),
            "stop_reason": reason,
            "status": data.get("status"),
            "response_id": data.get("id"),
            "usage": data.get("usage"),
            "model": str(data.get("model") or DEFAULT_MODEL),
            "http_status": 200,
            "error": None,
            "raw": data if INI_LLM_DEBUG else None,
            "knowledge_sources": knowledge_sources,
        }

    except Exception as e:
        print("\n===== OPENAI EXCEPTION =====")
        print(type(e).__name__, str(e))
        print("===== END EXCEPTION =====\n")
        return {
            "answer": "",
            "incomplete": False,
            "stop_reason": None,
            "status": None,
            "response_id": None,
            "usage": None,
            "model": DEFAULT_MODEL,
            "http_status": None,
            "error": f"{type(e).__name__}: {e}",
            "raw": None,
            "knowledge_sources": knowledge_sources,
        }


def generate_dynamic_answer(
    *,
    topic: str,
    topic_type: str,
    archetype: str,
    question: str,
    meta: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Optional[str]:
    """
    Backward-compatible wrapper used by existing code:
    returns ONLY the answer text (no debug leakage).
    """
    res = generate_dynamic_answer_result(
        topic=topic,
        topic_type=topic_type,
        archetype=archetype,
        question=question,
        meta=meta,
        **kwargs,
    )
    ans = (res.get("answer") or "").strip()
    return ans if ans else None

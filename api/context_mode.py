"""Context-Aware Response Mode (CARM) selection and prompt shaping."""

from __future__ import annotations

import re
from typing import Any, Dict


INSTALLATION_CUES = (
    "install", "installation", "set up", "setup", "configure", "configuration",
    "add an mcp", "add mcp", "run locally", "local system", "on my computer",
)
DEBUGGING_CUES = (
    "debug", "traceback", "exception", "stack trace", "code is failing",
    "code failing", "script is failing", "build failed", "test failed",
)
TROUBLESHOOTING_CUES = (
    "not working", "doesn't work", "does not work", "fix this",
    "how do i fix", "error", "failed", "failure", "crash", "broken",
)
MCP_HOSTS = (
    "codex", "claude desktop", "claude", "cursor", "visual studio code", "vs code",
    "vscode", "windsurf", "chatgpt", "openai",
)


def _mcp_integration_target(text: str) -> str:
    """Return a named system being connected through MCP, if one is present."""
    patterns = (
        r"\b(?:add|expose|use)\s+(.+?)\s+as\s+(?:a\s+)?(?:local\s+)?(?:mcp|model context protocol)\s+(?:server|bridge)\b",
        r"\b(?:connect|integrate)\s+(.+?)\s+(?:to|with|through|via)\s+(?:a\s+)?(?:local\s+)?(?:mcp|model context protocol)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            target = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;:?!")
            if target and target not in {"an", "a", "the", "server"}:
                return target
    return ""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def classify_context(text: str) -> Dict[str, Any]:
    """Choose CARM only when an immediate practical goal is evident."""
    normalized = _normalize(text)
    if not normalized:
        return {"response_mode": "question_map", "context_intent": "learning"}

    # Scientific and engineering topics frequently contain words such as
    # "error", "failure", or "correction" without describing a broken user
    # system. Keep definition/mechanism questions in the learning pipeline;
    # practical repair wording below can still select troubleshooting.
    conceptual_error_topic = bool(
        re.match(r"^(?:what\s+(?:is|are)|explain|define|how\s+(?:does|do))\b", normalized)
        and re.search(
            r"\b(?:error\s+correction|error-correct(?:ing|ion)|error\s+detection|"
            r"error\s+rate|failure\s+mode|errors?\b.{0,80}\b(?:detect(?:ed|ion)?|"
            r"repair(?:ed)?|correct(?:ed|ion)?))\b",
            normalized,
        )
        and not re.search(
            r"\b(?:my|our|fix\s+(?:it|this)|how\s+do\s+i\s+fix|not\s+working|"
            r"doesn't\s+work|does\s+not\s+work|crash(?:ed|ing)?|"
            r"traceback|exception)\b",
            normalized,
        )
    )
    if conceptual_error_topic:
        return {"response_mode": "question_map", "context_intent": "learning"}

    integration_target = _mcp_integration_target(normalized)

    context_intent = "learning"
    if any(cue in normalized for cue in DEBUGGING_CUES):
        context_intent = "debugging"
    elif any(cue in normalized for cue in INSTALLATION_CUES):
        context_intent = "installation"
    elif any(cue in normalized for cue in TROUBLESHOOTING_CUES):
        context_intent = "troubleshooting"

    is_local_mcp = (
        ("mcp" in normalized or "model context protocol" in normalized)
        and any(cue in normalized for cue in ("local", "install", "setup", "set up", "configure", "add"))
    )
    if is_local_mcp:
        context_intent = "installation"
    if integration_target:
        context_intent = "integration"

    if context_intent == "learning":
        return {"response_mode": "question_map", "context_intent": context_intent}

    clarification_required = False
    clarification_question = ""
    clarification_options = []

    has_explicit_host = (
        any(host in normalized for host in MCP_HOSTS)
        or "application or tool specified by the user is" in normalized
    )
    if is_local_mcp and not has_explicit_host and not integration_target:
        clarification_required = True
        clarification_question = (
            "Which application do you want the local MCP server to connect to? "
            "The configuration location and steps depend on the MCP host."
        )
        clarification_options = [
            "How do I configure a local MCP server for Codex?",
            "How do I configure a local MCP server for VS Code?",
            "How do I configure a local MCP server for Claude Desktop?",
            "How do I configure a local MCP server for Cursor?",
        ]

    return {
        "response_mode": "carm",
        "context_intent": context_intent,
        "clarification_required": clarification_required,
        "clarification_question": clarification_question,
        "clarification_options": clarification_options,
        "integration_target": integration_target,
    }


def build_carm_answer_prompt(user_text: str, context_intent: str) -> str:
    """Create a dynamic immediate-answer instruction for the existing study API."""
    labels = {
        "installation": "complete a practical installation or configuration",
        "debugging": "identify why something is failing and fix it safely",
        "troubleshooting": "diagnose the problem and restore expected behaviour",
        "integration": "guide a first-time implementer through a safe, controlled bridge between the named system and an MCP client",
    }
    objective = labels.get(context_intent, "solve the immediate practical problem")
    normalized = _normalize(user_text)
    integration_followup = bool(
        context_intent == "integration"
        and "continue this active practical request" in normalized
    )
    mcp_guardrails = ""
    if ("mcp" in normalized or "model context protocol" in normalized) and context_intent != "integration":
        mcp_guardrails = """

MCP accuracy guardrails (mandatory):
- MCP means Model Context Protocol. Never expand it any other way.
- For Codex, use this model: Codex is the host, its MCP connection is the client, and the configured tool or context provider is the server.
- Codex supports local STDIO servers started by a command and Streamable HTTP servers reached by URL.
- Codex MCP configuration lives in ~/.codex/config.toml or, for a trusted project, .codex/config.toml. ChatGPT desktop, Codex CLI, and the IDE extension share the same Codex-host configuration.
- The exact TOML table shape is `[mcp_servers.SERVER_NAME]`, not `[[mcp_servers]]`. A STDIO entry uses `command = "REAL_COMMAND"` and optional `args = ["REAL_ARG"]`; a Streamable HTTP entry uses `url = "REAL_MCP_ENDPOINT"`.
- Prefer the official UI flow (Settings or gear > MCP servers > Add server > choose STDIO or Streamable HTTP > provide the real command or URL > save and restart).
- The verified CLI shape for a local STDIO server is `codex mcp add SERVER_NAME -- SERVER_COMMAND [ARGS...]`. Do not invent `--type`, `--command`, or other flags. For HTTP, prefer the verified UI or config.toml `url` flow unless exact CLI syntax is known from authoritative context.
- `codex mcp list` verifies configured servers; `/mcp` shows active servers in Codex.
- `codex mcp-server` exposes Codex itself as an MCP server. It is not the command for adding an external server to Codex.
- Never invent an MCP package, executable, executable path, command flag, repository, Docker image, URL path, token, model, or hardware requirement. Use visible uppercase placeholders such as SERVER_NAME and REAL_COMMAND only. If the requested server/provider is unspecified, explain the generic host setup and ask which real server or tool she wants to connect before giving provider-specific commands.
- When the provider is unspecified, do not include a made-up "Example" command or URL at all. Show only the verified syntax with uppercase placeholders; never emit `/path/to/...`, `example.com`, `--serve`, or a sample port.
""".rstrip()

    integration_guardrails = ""
    if context_intent == "integration" and integration_followup:
        integration_guardrails = """

Enterprise integration continuation guardrails (mandatory):
- This is a reply inside an active implementation-guidance conversation, not a new topic. Never generate a Question Map for the reply itself.
- Read the original request, previous-answer tail, and latest reply included in the user text.
- If the user says they do not know, reassure them briefly and convert the missing details into one manageable discovery step at a time. Explain exactly whom to ask or what system screen/document to check first.
- If the user provides only some answers, acknowledge what is known and ask only for the missing information; do not repeat answered questions.
- Do not provide an implementation procedure until the environment details required for safe, accurate instructions are known.
- Keep the response under 180 words. Use plain language, no profile-like teaching structure, no Question Map, no "Explore next", and no unrelated concepts.
- End with one concrete next action and wait for the user's reply.
""".rstrip()
    elif context_intent == "integration":
        integration_guardrails = """

Enterprise integration guardrails (mandatory):
- MCP means Model Context Protocol. Never expand it any other way.
- This is the first turn of a staged implementation conversation. Override any general instruction to provide a complete procedure now.
- In no more than 220 words, give exactly two headings: "Immediate intent" and "Before we build it". Under "Immediate intent", include the plain-language correction, the flow `target system -> supported interface -> local MCP bridge -> MCP client`, and exactly one short sentence (maximum 20 words) explaining each of those four pieces. Under "Before we build it", include exactly four numbered questions.
- The four questions must ask for: (1) system version/deployment, (2) which programmatic interface is enabled, (3) the intended MCP client, and (4) the first read-only operation to expose.
- Explain briefly why each answer is needed and how the user can find it or who can confirm it. Do not assume the user knows technical terminology.
- Immediately after question 4, add this single unheaded call to action: "Reply with whatever you know. ‘I don’t know’ is a valid answer, and InI will guide you from there." Then stop.
- Do not include "Start here", implementation steps, code, commands, configuration, tools, packages, endpoints, credentials, security checklists, assumptions, verification, diagnostics, failure modes, examples, additional follow-ups, or an "Explore next" section on this first turn.
- Never assume Codex or another product is the MCP client. Never claim the target system itself becomes an MCP server.
- Never invent vendor capabilities. Mention an interface only as something the system administrator must confirm.
- After the user supplies the four answers, a later response may provide a phased, read-only-first implementation plan with the necessary safeguards.
- The Siebel CRM question is the reference specimen, but apply this staged behavior generally to other named integration targets.
""".rstrip()

    if context_intent == "integration" and integration_followup:
        requirements = """
Requirements:
- Preserve the active integration context and respond only to the user's latest reply.
- Give one calm, practical next step and then stop.
""".strip()
    elif context_intent == "integration":
        requirements = """
Requirements:
- Follow the enterprise integration guardrails exactly; they replace the normal practical-answer structure for this first turn.
- Use only the two required headings and stop after the required one-sentence call to action.
- Avoid filler, sales language, and repeated restatement.
""".strip()
    else:
        requirements = """
Requirements:
- Begin with one calm sentence confirming the likely objective under the heading "Immediate intent".
- Put the actionable answer immediately after it under "Start here".
- Give concrete, ordered steps when the task is procedural.
- State any assumption that materially affects commands, paths, permissions, or configuration.
- Never invent a universal configuration path; distinguish host application and operating system when relevant.
- Include only the supporting concepts needed to prevent mistakes; do not add a separate glossary or diagnostics section unless the user asked for them.
- For debugging, lead with the most likely cause and the shortest safe diagnostic sequence.
- End with "Explore next" and 2 to 4 numbered questions that reveal the surrounding knowledge landscape.
- "Explore next" must be the final section; do not append a second suggested-follow-ups section.
- Keep the complete response under 550 words. Prefer clarity and continuity over exhaustive implementation detail, and reserve enough output for the final "Explore next" section.
- Do not generate a full seven-section Question Map.
- Avoid filler, sales language, and repeated restatement.
""".strip()

    return f"""
Use InI.ai Context-Aware Response Mode for this request.

Original user request: {user_text}
Likely objective: {objective}
{mcp_guardrails}
{integration_guardrails}

Answer the original request, not this instruction. Adapt the structure naturally.
{requirements}
""".strip()

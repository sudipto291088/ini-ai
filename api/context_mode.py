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
    "not working", "doesn't work", "does not work", "why is", "fix this",
    "how do i fix", "error", "failed", "failure", "crash", "broken",
)
MCP_HOSTS = (
    "codex", "claude desktop", "claude", "cursor", "visual studio code", "vs code",
    "vscode", "windsurf", "chatgpt", "openai",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def classify_context(text: str) -> Dict[str, Any]:
    """Choose CARM only when an immediate practical goal is evident."""
    normalized = _normalize(text)
    if not normalized:
        return {"response_mode": "question_map", "context_intent": "learning"}

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

    if context_intent == "learning":
        return {"response_mode": "question_map", "context_intent": context_intent}

    clarification_required = False
    clarification_question = ""
    clarification_options = []

    has_explicit_host = (
        any(host in normalized for host in MCP_HOSTS)
        or "application or tool specified by the user is" in normalized
    )
    if is_local_mcp and not has_explicit_host:
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
    }


def build_carm_answer_prompt(user_text: str, context_intent: str) -> str:
    """Create a dynamic immediate-answer instruction for the existing study API."""
    labels = {
        "installation": "complete a practical installation or configuration",
        "debugging": "identify why something is failing and fix it safely",
        "troubleshooting": "diagnose the problem and restore expected behaviour",
    }
    objective = labels.get(context_intent, "solve the immediate practical problem")
    normalized = _normalize(user_text)
    mcp_guardrails = ""
    if "mcp" in normalized or "model context protocol" in normalized:
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

    return f"""
Use InI.ai Context-Aware Response Mode for this request.

Original user request: {user_text}
Likely objective: {objective}
{mcp_guardrails}

Answer the original request, not this instruction. Adapt the structure naturally.

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
- Keep the complete response under 400 words. Reserve enough output for and always include the final "Explore next" section.
- Do not generate a full seven-section Question Map.
- Avoid filler, sales language, and repeated restatement.
""".strip()

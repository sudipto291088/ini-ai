from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
import streamlit.components.v1 as components


# =========================
# Ship / Dev mode
# =========================
# Set DEV_MODE=False before shipping (users won't see API settings).
DEV_MODE = False

DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_STUDY_PATH = "/study/ai"
DEFAULT_INTERROGATE_PATH = "/interrogate"
DEFAULT_ILLUSTRATE_PATH = "/illustrate"

# Timeout: LLM can be slow; keep generous.
REQ_TIMEOUT = 240


# =========================
# Page + Theme
# =========================
st.set_page_config(page_title="InI.ai", layout="wide")

st.markdown(
    """
<style>
.block-container { padding-top: 1.05rem; padding-bottom: 2.2rem; max-width: 1240px; }
h1, h2, h3 { letter-spacing: -0.02em; }

.muted { color: rgba(49,51,63,0.70); }
.small { font-size: 0.92rem; }

.badge {
  display: inline-block;
  padding: 0.20rem 0.60rem;
  border: 1px solid rgba(49,51,63,0.18);
  border-radius: 999px;
  font-size: 0.82rem;
  color: rgba(49,51,63,0.70);
  background: rgba(255,255,255,0.75);
}

.card {
  border: 1px solid rgba(49,51,63,0.14);
  border-radius: 18px;
  padding: 1rem 1.1rem;
  background: rgba(255,255,255,0.80);
}

.ts { margin-top: 0.15rem; font-size: 0.82rem; color: rgba(49,51,63,0.50); }

div[data-testid="stChatMessage"] { border-radius: 16px; }
div[data-testid="stChatMessage"] p { line-height: 1.55; }

/* UIB */
.uib {
  border: 1px solid rgba(49,51,63,0.14);
  border-radius: 18px;
  padding: 0.65rem 0.75rem 0.55rem 0.75rem;
  background: rgba(255,255,255,0.80);
}
.uib-hint { margin-top: 0.35rem; font-size: 0.86rem; color: rgba(49,51,63,0.62); }
.uib-btn button {
  border-radius: 999px !important;
  width: 44px !important;
  height: 40px !important;
  padding: 0 !important;
  font-weight: 900 !important;
}
.uib-send button {
  border-radius: 999px !important;
  width: 52px !important;
  height: 40px !important;
  padding: 0 !important;
  font-weight: 900 !important;
}

/* Centered Continue (text link) */
.center-link { text-align: center; margin-top: 0.35rem; margin-bottom: 0.75rem; }
.center-link button {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  color: rgba(49,51,63,0.70) !important;
  font-weight: 700 !important;
}
.center-link button:hover { text-decoration: underline; color: rgba(49,51,63,0.92) !important; }

/* Floating controls */
.floater {
  position: fixed;
  right: 18px;
  bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 9999;
}
.fbtn {
  width: 44px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid rgba(49,51,63,0.22);
  background: rgba(255,255,255,0.92);
  cursor: pointer;
  font-weight: 900;
  line-height: 40px;
  text-align: center;
  user-select: none;
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
}
.fbtn:hover { background: rgba(255,255,255,1.0); }

</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Helpers
# =========================
def now_label() -> str:
    # Example: Sun, Feb 15 • 06:59 PM
    return datetime.now().strftime("%a, %b %d • %I:%M %p")


def safe_post(api_base: str, path: str, payload: Dict[str, Any], timeout: int = REQ_TIMEOUT) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    url = api_base.rstrip("/") + path
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            return None, "Bad JSON response"
        return data, None
    except requests.exceptions.RequestException as e:
        return None, str(e)
    except ValueError:
        return None, "Response was not JSON"


def fix_split_words(md: str) -> str:
    """
    Fix a common LLM formatting glitch where a word gets split across lines:
      'hallu\\ninations' -> 'hallucinations'
    """
    lines = md.splitlines()
    out: List[str] = []
    for line in lines:
        if out:
            prev = out[-1]
            if (
                prev
                and line
                and prev[-1].isalpha()
                and line[0].islower()
                and len(prev.split()[-1]) <= 6
                and not prev.rstrip().endswith((".", ":", "?", "!", ")", "]"))
                and not line.lstrip().startswith(("-", "*", "1.", "2.", "3.", ">", "#"))
            ):
                out[-1] = prev + line
                continue
        out.append(line)
    return "\n".join(out)


def render_floating_controls():
    components.html(
        """
<div class="floater">
  <div class="fbtn" onclick="window.scrollTo({top:0, behavior:'smooth'})">↑</div>
  <div class="fbtn" onclick="window.scrollTo({top:document.body.scrollHeight, behavior:'smooth'})">↓</div>
</div>
""",
        height=0,
    )


def build_learning_prompt(
    user_prompt: str,
    mode: str,
    continue_from: Optional[str],
    recent_context: List[Dict[str, Any]],
    feedback: Optional[str],
) -> str:
    """
    IMPORTANT:
    Your FastAPI /study/ai currently accepts ONLY: {"topic": "..."}.
    So we encode mode/context/continue into ONE string inside "topic".
    """
    mode = (mode or "deep").lower().strip()
    header = "You are a deep technical AI tutor."

    if mode == "high":
        header = (
            "You are a high-level AI tutor.\n"
            "Give a concise overview with clear structure.\n"
            "Do NOT cut content arbitrarily; end naturally."
        )
    elif mode == "quiz":
        header = (
            "You are an AI tutor.\n"
            "Create a short quiz based on the user’s topic.\n"
            "Ask 5-8 questions with answers hidden (provide answers at the end under 'Answer Key').\n"
            "Be specific and non-repetitive."
        )
    else:
        header = (
            "You are a deep technical AI tutor.\n"
            "Write a research-grade, well-structured answer.\n"
            "Use headings, bullets, and examples.\n"
            "Be specific, non-repetitive, avoid clichés.\n"
            "Do NOT ask the user meta-questions unless required."
        )

    fb_line = f"\nTutor steering (feedback): {feedback}\n" if feedback else ""

    # Lightweight context: last ~8 messages (role+content)
    ctx_lines: List[str] = []
    for m in recent_context[-8:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role and content:
            ctx_lines.append(f"{role.upper()}: {content}")

    ctx_block = "\n".join(ctx_lines).strip()
    ctx_section = f"\nRecent context:\n{ctx_block}\n" if ctx_block else ""

    if continue_from:
        return (
            f"{header}\n"
            f"{fb_line}"
            f"{ctx_section}\n"
            "Continue the previous answer from where it stopped.\n"
            "Do NOT repeat earlier content. Resume seamlessly.\n"
            "Continue from this tail (last chars of prior output):\n"
            f"{continue_from}\n\n"
            "User topic:\n"
            f"{user_prompt}\n"
        )

    return (
        f"{header}\n"
        f"{fb_line}"
        f"{ctx_section}\n"
        "User topic:\n"
        f"{user_prompt}\n"
    )


# =========================
# Session State
# =========================
if "page" not in st.session_state:
    st.session_state.page = "New Chat"

if "api_base" not in st.session_state:
    st.session_state.api_base = DEFAULT_API_BASE

# Learning sessions (My Learning)
if "learning_sessions" not in st.session_state:
    # id -> {"created": str, "messages": [ {role, content, ts, mode?} ], "pending_incomplete": bool}
    st.session_state.learning_sessions = {}

if "learning_active_id" not in st.session_state:
    st.session_state.learning_active_id = None


def ensure_learning_session() -> str:
    if st.session_state.learning_active_id and st.session_state.learning_active_id in st.session_state.learning_sessions:
        return st.session_state.learning_active_id

    sid = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.learning_sessions[sid] = {
        "created": now_label(),
        "messages": [],
        "pending_incomplete": False,
        "last_tail": "",
        "last_user_prompt": "",
        "last_mode": "deep",
    }
    st.session_state.learning_active_id = sid
    return sid


def session_title_for_sidebar(sess: Dict[str, Any]) -> str:
    # show timestamp + first keyword if available
    first_user = None
    for m in sess.get("messages", []):
        if m.get("role") == "user" and m.get("content"):
            first_user = m["content"].strip()
            break
    kw = ""
    if first_user:
        kw = first_user.split()[0][:18]
        kw = f" • {kw}"
    return f"{sess.get('created','')}{kw}"


# =========================
# API call (My Learning)
# =========================
def fetch_study_single_field(api_base: str, topic_string: str):
    """
    Calls FastAPI /study/ai with ONLY {"topic": "..."}.
    Expects response includes: answer, incomplete, stop_reason (from our backend updates).
    """
    payload = {"topic": topic_string}
    data, err = safe_post(api_base, DEFAULT_STUDY_PATH, payload, timeout=REQ_TIMEOUT)
    if err:
        return None, False, err

    answer = (data.get("answer") or "").strip()
    incomplete = bool(data.get("incomplete", False))
    stop_reason = data.get("stop_reason", None)

    return {"answer": answer, "incomplete": incomplete, "stop_reason": stop_reason, "ts": now_label()}, incomplete, None


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.markdown("## InI.ai")
    st.markdown('<span class="badge">v0 • AI Tutor</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="muted small">🕒 {now_label()}</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown("### Navigation")
    page = st.radio(
        "",
        ["New Chat", "My Learning", "New Project"],
        index=["New Chat", "My Learning", "New Project"].index(st.session_state.page),
        label_visibility="collapsed",
    )
    st.session_state.page = page

    if DEV_MODE:
        st.divider()
        st.markdown("### API Settings (dev)")
        st.session_state.api_base = st.text_input("API base", st.session_state.api_base)

    if page == "My Learning":
        st.divider()
        st.markdown("### Your Learning")

        if not st.session_state.learning_sessions:
            ensure_learning_session()

        if st.button("New session"):
            sid = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.learning_sessions[sid] = {
                "created": now_label(),
                "messages": [],
                "pending_incomplete": False,
                "last_tail": "",
                "last_user_prompt": "",
                "last_mode": "deep",
            }
            st.session_state.learning_active_id = sid

        for sid, sess in list(st.session_state.learning_sessions.items())[::-1]:
            label = session_title_for_sidebar(sess)
            if st.button(label, key=f"sess_{sid}"):
                st.session_state.learning_active_id = sid


# =========================
# Pages
# =========================
def page_new_project():
    st.markdown("## New Project")
    st.markdown('<div class="card">Coming soon in v1.</div>', unsafe_allow_html=True)


def page_new_chat():
    st.markdown("## New Chat")
    st.markdown('<div class="card muted">Interrogate + Illustrate UI can be polished after My Learning is solid.</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">v0 note: LLM is enabled for AI/ML; templates for other topics.</div>', unsafe_allow_html=True)


def page_my_learning():
    render_floating_controls()

    sid = ensure_learning_session()
    sess = st.session_state.learning_sessions[sid]
    messages: List[Dict[str, Any]] = sess["messages"]

    st.markdown("## My Learning")
    st.markdown('<div class="muted small">Enter = Deep • ◎ Overview • ? Quiz</div>', unsafe_allow_html=True)

    # Transcript
    for idx, m in enumerate(messages):
        role = m.get("role")
        content = (m.get("content") or "").strip()
        ts = m.get("ts") or ""
        if not content:
            continue

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
                st.markdown(f'<div class="ts">{ts}</div>', unsafe_allow_html=True)
        else:
            with st.chat_message("assistant"):
                st.markdown(fix_split_words(content))
                st.markdown(f'<div class="ts">{ts}</div>', unsafe_allow_html=True)

    # Continue (ONLY when incomplete==True from backend)
    if sess.get("pending_incomplete", False):
        st.markdown('<div class="center-link">', unsafe_allow_html=True)
        if st.button("Continue"):
            last_tail = (sess.get("last_tail") or "").strip()
            last_user_prompt = (sess.get("last_user_prompt") or "").strip()
            last_mode = (sess.get("last_mode") or "deep").strip()

            recent_ctx = [{"role": m.get("role"), "content": m.get("content")} for m in messages[-8:]]
            topic_string = build_learning_prompt(
                user_prompt=last_user_prompt or "(previous topic)",
                mode=last_mode,
                continue_from=last_tail[-260:] if last_tail else None,
                recent_context=recent_ctx,
                feedback=None,
            )

            with st.spinner("Continuing…"):
                data, inc, err = fetch_study_single_field(st.session_state.api_base, topic_string)

            if err:
                st.error(err)
            else:
                ans = (data.get("answer") or "").strip()
                ts = data.get("ts") or now_label()

                if messages and messages[-1].get("role") == "assistant":
                    messages[-1]["content"] = (messages[-1].get("content") or "").rstrip() + "\n\n" + ans
                    messages[-1]["ts"] = ts
                else:
                    messages.append({"role": "assistant", "content": ans, "ts": ts})

                sess["pending_incomplete"] = bool(inc)
                sess["last_tail"] = (messages[-1]["content"] or "")[-450:]

            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # UIB
    st.markdown('<div class="uib">', unsafe_allow_html=True)

    with st.form(key=f"uib_form_{sid}", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([0.72, 0.08, 0.08, 0.12])
        with c1:
            prompt = st.text_input("Ask about AI", placeholder="Type your topic/question…", label_visibility="collapsed")
        with c2:
            st.markdown('<div class="uib-btn">', unsafe_allow_html=True)
            hlo = st.form_submit_button("◎")
            st.markdown("</div>", unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="uib-btn">', unsafe_allow_html=True)
            quiz = st.form_submit_button("?")
            st.markdown("</div>", unsafe_allow_html=True)
        with c4:
            st.markdown('<div class="uib-send">', unsafe_allow_html=True)
            send = st.form_submit_button("➤")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="uib-hint">➤ Deep (default) • ◎ High-level overview • ? Quiz</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Dispatch after submit
    if (send or hlo or quiz) and (prompt or "").strip():
        user_prompt = prompt.strip()
        mode = "deep"
        if hlo:
            mode = "high"
        if quiz:
            mode = "quiz"

        ts_user = now_label()
        messages.append({"role": "user", "content": user_prompt, "ts": ts_user, "mode": mode})

        # recent context
        recent_ctx = [{"role": m.get("role"), "content": m.get("content")} for m in messages[-8:]]

        topic_string = build_learning_prompt(
            user_prompt=user_prompt,
            mode=mode,
            continue_from=None,
            recent_context=recent_ctx,
            feedback=None,
        )

        with st.spinner("Thinking…"):
            data, inc, err = fetch_study_single_field(st.session_state.api_base, topic_string)

        if err:
            st.error(err)
            sess["pending_incomplete"] = False
        else:
            ans = (data.get("answer") or "").strip()
            ts_a = data.get("ts") or now_label()
            messages.append({"role": "assistant", "content": ans, "ts": ts_a, "mode": mode})

            sess["pending_incomplete"] = bool(inc)
            sess["last_tail"] = ans[-450:] if ans else ""
            sess["last_user_prompt"] = user_prompt
            sess["last_mode"] = mode

        st.rerun()


# Router
if st.session_state.page == "My Learning":
    page_my_learning()
elif st.session_state.page == "New Project":
    page_new_project()
else:
    page_new_chat()

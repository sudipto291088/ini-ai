"""Subject Map → Question Curriculum inside a New Chat session."""

import math
import secrets
import time
from html import escape
from typing import Any, Callable

import requests
import streamlit as st

from api.subject_curriculum import learning_subject_candidate
from streamlit_app.storage_sqlite import load_curriculum, list_curricula, save_curriculum


def _post(api_base: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{api_base}{path}", json=payload, timeout=180)
    if not response.ok:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        if isinstance(detail, str) and detail:
            raise RuntimeError(detail)
    response.raise_for_status()
    return response.json()


def _stream_text(message: str, *, max_seconds: float = 5.0) -> None:
    """Reveal prose at a readable pace without changing its final Markdown."""
    delay = min(0.035, max_seconds / max(len(message), 1))

    def letters():
        for letter in message:
            yield letter
            time.sleep(delay)

    st.write_stream(letters(), cursor="▍")


def _reveal_pause(item_count: int) -> float:
    """Give each item a visible entrance, capped for large subjects."""
    return min(0.18, 4.0 / max(item_count, 1))


def _begin(subject: str, visitor_id: str, api_base: str,
           attach_to_chat: Callable[[str, str, str], None] | None = None,
           request_prompt: str = "") -> None:
    outline = _post(api_base, "/qc/outline", {"topic": subject})
    curriculum_id = f"qc-{secrets.token_urlsafe(12)}"
    state = {
        "version": 1, "subject": subject, "outline": outline,
        "request_prompt": request_prompt.strip() or f"Teach me {subject} as a subject",
        "selected_chapter": None, "selected_question": None,
        "answers": {}, "completed": [], "visited_questions": [],
        "intro_revealed": False,
    }
    save_curriculum(visitor_id, curriculum_id, state)
    st.session_state.qc_active_id = curriculum_id
    st.session_state.qc_state = state
    st.session_state.qc_clarification = None
    st.session_state.qc_pending_request = None
    if attach_to_chat:
        attach_to_chat(curriculum_id, subject, state["request_prompt"])
    st.rerun()


def maybe_start_qc(prompt: str, action: str, visitor_id: str, api_base: str,
                   attach_to_chat: Callable[[str, str, str], None] | None = None) -> bool:
    """Queue explicit subject learning before any slow API work or rendering."""
    if st.session_state.get("qc_pending_request"):
        return True
    if action != "interrogate":
        return False
    candidate = learning_subject_candidate(prompt)
    if not candidate:
        return False
    st.session_state.qc_pending_request = {
        "prompt": prompt, "candidate": candidate, "phase": "thinking",
    }
    st.session_state.nc_started = True
    st.rerun()
    return True


def process_pending_qc(visitor_id: str, api_base: str,
                       attach_to_chat: Callable[[str, str], None] | None = None) -> bool:
    """Process an already-visible active-state request; False routes a narrow topic to chat."""
    pending = st.session_state.get("qc_pending_request")
    if not isinstance(pending, dict):
        return True
    candidate = pending["candidate"]
    try:
        if pending.get("phase") == "building":
            _begin(
                pending["subject"], visitor_id, api_base, attach_to_chat,
                request_prompt=pending["prompt"],
            )
            return True
        scope = _post(api_base, "/qc/assess", {"topic": candidate})
        if scope["decision"] == "topic":
            st.session_state.qc_pending_request = None
            return False
        if scope["decision"] == "clarify":
            st.session_state.qc_pending_request = None
            st.session_state.qc_clarification = {
                "candidate": scope.get("subject") or candidate,
                "question": scope.get("question") or "Which entire subject would you like to study?",
                "request_prompt": pending["prompt"],
            }
            st.rerun()
            return True
        pending["subject"] = scope.get("subject") or candidate
        pending["phase"] = "building"
        st.session_state.qc_pending_request = pending
        st.rerun()
    except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
        st.session_state.qc_pending_request = None
        st.error(f"I couldn't start the Question Curriculum: {exc}")
    return True


def _subject_map_svg(subject: str, chapters: list[dict[str, Any]],
                     visible_count: int | None = None) -> str:
    """Draw the actual generated chapter structure as a radial SVG map."""
    count = len(chapters)
    ring_capacity = 8
    rings = max(1, math.ceil(count / ring_capacity))
    outer_radius = 290 + (rings - 1) * 215
    size = int(outer_radius * 2 + 240)
    center = size / 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" role="img" '
        f'aria-label="Subject map for {escape(subject, quote=True)}">',
        f'<rect width="{size}" height="{size}" rx="28" fill="#ffffff"/>',
    ]
    positions = []
    visible_count = count if visible_count is None else max(0, min(visible_count, count))
    for index, chapter in enumerate(chapters):
        ring = index // ring_capacity
        ring_items = chapters[ring * ring_capacity:(ring + 1) * ring_capacity]
        within_ring = index % ring_capacity
        angle = -math.pi / 2 + 2 * math.pi * within_ring / len(ring_items)
        radius = 290 + ring * 215
        x = center + radius * math.cos(angle)
        y = center + radius * math.sin(angle)
        positions.append((x, y, index + 1, chapter))
        if index < visible_count:
            parts.append(
                f'<line x1="{center}" y1="{center}" x2="{x:.1f}" y2="{y:.1f}" '
                'stroke="#eec7ce" stroke-width="2"/>'
            )
    for x, y, number, chapter in positions[:visible_count]:
        full_title = f"{number}. {chapter['title']}"
        title = full_title[:48]
        words = title.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > 21 and current:
                lines.append(current)
                current = word
            else:
                current = (current + " " + word).strip()
        if current:
            lines.append(current)
        lines = lines[:3]
        height = max(58, 27 + 17 * len(lines))
        parts.append(
            f'<rect x="{x - 89:.1f}" y="{y - height/2:.1f}" width="178" '
            f'height="{height}" rx="13" fill="#ffffff" stroke="#e33250" stroke-width="1.8"/>'
        )
        first_y = y - (len(lines) - 1) * 8
        for line_index, line in enumerate(lines):
            parts.append(
                f'<text x="{x:.1f}" y="{first_y + 17 * line_index:.1f}" '
                'text-anchor="middle" dominant-baseline="middle" fill="#b4233d" '
                f'font-family="Arial,sans-serif" font-size="13" font-weight="600">{escape(line)}</text>'
            )
    root = escape(subject[:28] + ("…" if len(subject) > 28 else ""))
    parts.extend([
        f'<rect x="{center-112:.1f}" y="{center-42:.1f}" width="224" height="84" '
        'rx="20" fill="#fff8fa" stroke="#d91d3f" stroke-width="3"/>',
        f'<text x="{center}" y="{center}" text-anchor="middle" dominant-baseline="middle" '
        f'fill="#b4233d" font-family="Arial,sans-serif" font-size="18" font-weight="700">{root}</text>',
        '</svg>',
    ])
    return "".join(parts)


def _save(visitor_id: str, curriculum_id: str, state: dict[str, Any]) -> None:
    save_curriculum(visitor_id, curriculum_id, state)
    st.session_state.qc_state = state


def render_saved_curricula(visitor_id: str) -> None:
    saved = list_curricula(visitor_id, limit=8)
    if not saved:
        return
    st.subheader("Continue a Question Curriculum")
    for curriculum_id, subject, _updated in saved:
        if st.button(f"Resume {subject}", key=f"qc_resume_{curriculum_id}"):
            state = load_curriculum(visitor_id, curriculum_id)
            if state:
                st.session_state.qc_active_id = curriculum_id
                st.session_state.qc_state = state
                st.rerun()


def _render_qc_body(visitor_id: str, api_base: str,
                    attach_to_chat: Callable[[str, str, str], None] | None = None) -> None:
    clarification = st.session_state.get("qc_clarification")
    if clarification:
        st.subheader("What would you like to study as a whole subject?")
        st.write(clarification["question"])
        with st.form("qc_clarify_form"):
            subject = st.text_input("Entire subject", value=clarification["candidate"])
            submitted = st.form_submit_button("Create Subject Map")
        if submitted:
            try:
                with st.spinner("Checking subject scope..."):
                    scope = _post(api_base, "/qc/assess", {"topic": subject})
                if scope["decision"] == "subject":
                    with st.spinner("Building your subject learning path..."):
                        _begin(
                            scope.get("subject") or subject, visitor_id, api_base,
                            attach_to_chat, request_prompt=clarification.get("request_prompt") or "",
                        )
                elif scope["decision"] == "clarify":
                    st.session_state.qc_clarification = {
                        "candidate": scope.get("subject") or subject,
                        "question": scope.get("question") or "Please name the entire subject.",
                    }
                    st.rerun()
                else:
                    st.warning("That appears to be a topic within a subject. Name the broader subject, or use ordinary New Chat.")
            except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
                st.error(f"I couldn't create the curriculum: {exc}")
        if st.button("Cancel", key="qc_cancel_clarification"):
            st.session_state.qc_clarification = None
            st.rerun()
        return

    curriculum_id = st.session_state.get("qc_active_id")
    if not curriculum_id:
        return
    state = st.session_state.get("qc_state") or load_curriculum(visitor_id, curriculum_id)
    if not state:
        st.session_state.qc_active_id = None
        st.error("This curriculum could not be restored.")
        return

    st.caption("New Chat · Subject learning")
    st.title(state["subject"])
    st.markdown(
        """<style>
        .st-key-qc_primary_response {
            width: min(1180px, 100%) !important;
            margin: 14px 0 24px !important;
            padding: 22px !important;
            border: 1px solid rgba(194, 202, 213, 0.13) !important;
            border-radius: 22px !important;
            background: linear-gradient(145deg, #ffffff 0%, #fbfcfe 100%) !important;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.045) !important;
        }
        .st-key-qc_primary_response > div {
            background: transparent !important;
        }
        .st-key-qc_chapter_list,
        .st-key-qc_question_list {
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        .st-key-qc_chapter_list [data-testid="stButton"],
        .st-key-qc_question_list [data-testid="stButton"] {
            width: fit-content !important;
            max-width: 100% !important;
        }
        .st-key-qc_chapter_list div.stButton > button,
        .st-key-qc_question_list div.stButton > button {
            justify-content: flex-start;
            align-items: flex-start;
            text-align: left;
            height: auto;
            min-height: 0;
            width: fit-content !important;
            max-width: 100% !important;
            white-space: normal;
            padding: 0.78rem 1.05rem;
            border: 1px solid rgba(194, 202, 213, 0.16) !important;
            border-radius: 16px !important;
            background: rgba(255, 255, 255, 0.95) !important;
            box-shadow: 0 5px 18px rgba(15, 23, 42, 0.045) !important;
        }
        .st-key-qc_chapter_list div.stButton > button:hover,
        .st-key-qc_question_list div.stButton > button:hover {
            border-color: rgba(227, 50, 80, 0.22) !important;
            background: #fffafb !important;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.065) !important;
        }
        .st-key-qc_chapter_list div.stButton > button p,
        .st-key-qc_question_list div.stButton > button p {
            text-align: left;
            white-space: normal;
            overflow-wrap: break-word;
            word-break: normal;
            line-height: 1.42;
            font-weight: 450;
        }
        @media (max-width: 700px) {
            .st-key-qc_primary_response {
                width: 100% !important;
                padding: 16px !important;
                border-radius: 18px !important;
            }
        }
        </style>""",
        unsafe_allow_html=True,
    )
    outline = state["outline"]
    chapters = outline["chapters"]
    selected_chapter_id = state.get("selected_chapter")
    if not selected_chapter_id:
        reveal_intro = not state.get("intro_revealed", False)
        intro = "Here is your Subject Map. It shows the chapters in the order we'll learn them."
        if reveal_intro:
            _stream_text(intro)
        else:
            st.write(intro)
        st.subheader("Subject Map")
        if reveal_intro:
            with st.spinner("Forming the Subject Map..."):
                map_slot = st.empty()
                map_slot.image(_subject_map_svg(state["subject"], chapters, 0), width="stretch")
                time.sleep(0.25)
                for visible in range(1, len(chapters) + 1):
                    map_slot.image(_subject_map_svg(state["subject"], chapters, visible), width="stretch")
                    time.sleep(_reveal_pause(len(chapters)))
        else:
            st.image(_subject_map_svg(state["subject"], chapters), width="stretch")
        guidance = "I've broken the chapters into progressive questions, from foundations to advanced ideas. Choose a chapter to begin."
        if reveal_intro:
            _stream_text(guidance)
        else:
            st.write(guidance)
        with st.container(border=False, key="qc_chapter_list"):
            for index, chapter in enumerate(chapters):
                chapter_id = chapter["id"]
                questions = chapter.get("questions") or []
                complete = sum(question["id"] in state["completed"] for question in questions)
                label = f"{index + 1}. {chapter['title']}"
                if questions:
                    label += f" · {complete}/{len(questions)} understood"
                if st.button(label, key=f"qc_select_{chapter_id}", width="content"):
                    state["selected_chapter"] = chapter_id
                    state["selected_question"] = None
                    _save(visitor_id, curriculum_id, state)
                    st.rerun()
                if reveal_intro:
                    time.sleep(_reveal_pause(len(chapters)))
        if reveal_intro:
            state["intro_revealed"] = True
            _save(visitor_id, curriculum_id, state)
        return
    chapter = next((item for item in chapters if item["id"] == selected_chapter_id), None)
    if not chapter:
        return
    chapter_index = chapters.index(chapter)
    if st.button("← Subject Map", key="qc_subject_map"):
        state["selected_chapter"] = None
        state["selected_question"] = None
        _save(visitor_id, curriculum_id, state)
        st.rerun()
    st.subheader(f"Chapter {chapter_index + 1} — {chapter['title']}")
    if not chapter.get("questions"):
        try:
            with st.spinner("Forming this chapter's questions..."):
                payload = _post(api_base, "/qc/chapter", {"outline": outline, "chapter_id": selected_chapter_id})
            chapter["questions"] = payload["questions"]
            chapter["questions_revealed"] = False
            _save(visitor_id, curriculum_id, state)
        except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
            st.error(f"I couldn't form this chapter's questions: {exc}")
            return

    questions = chapter["questions"]
    selected_question_id = state.get("selected_question")
    question_index = next((index for index, item in enumerate(questions) if item["id"] == selected_question_id), None)
    if question_index is None:
        reveal_questions = not chapter.get("questions_revealed", False)
        guidance = "Let's work through this chapter from its foundations to its more advanced questions."
        if reveal_questions:
            _stream_text(guidance)
        else:
            st.write(guidance)
        with st.container(border=False, key="qc_question_list"):
            for index, question in enumerate(questions):
                marker = "✓ " if question["id"] in state["completed"] else ""
                if st.button(f"{marker}{index + 1}. {question['text']}", key=f"qc_question_{question['id']}", width="content"):
                    state["selected_question"] = question["id"]
                    visited = state.setdefault("visited_questions", [])
                    if question["id"] not in visited:
                        visited.append(question["id"])
                    _save(visitor_id, curriculum_id, state)
                    st.rerun()
                if reveal_questions:
                    time.sleep(_reveal_pause(len(questions)))
        if reveal_questions:
            chapter["questions_revealed"] = True
            _save(visitor_id, curriculum_id, state)
        return
    question = questions[question_index]
    if st.button("← Chapter questions", key="qc_back_to_questions"):
        state["selected_question"] = None
        _save(visitor_id, curriculum_id, state)
        st.rerun()
    visited = state.setdefault("visited_questions", [])
    if question["id"] not in visited:
        visited.append(question["id"])
        _save(visitor_id, curriculum_id, state)
    st.caption(f"Question {question_index + 1} of {len(questions)}")
    with st.container(border=True):
        st.markdown(f"### {question['text']}")
        if question["id"] not in state["answers"]:
            try:
                with st.spinner("Forming your answer..."):
                    result = _post(api_base, "/qc/answer", {
                        "subject": state["subject"], "chapter": chapter,
                        "questions": questions, "index": question_index,
                    })
                state["answers"][question["id"]] = result["answer"]
                _save(visitor_id, curriculum_id, state)
                _stream_text(result["answer"], max_seconds=20.0)
            except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
                st.error(f"I couldn't answer this question: {exc}")
                return
        else:
            st.markdown(state["answers"][question["id"]])
    if question["id"] not in state["completed"] and st.button("Mark understood", key="qc_mark_understood"):
        state["completed"].append(question["id"])
        _save(visitor_id, curriculum_id, state)
        st.rerun()
    previous_col, next_col = st.columns(2)
    with previous_col:
        if question_index > 0 and st.button("← Previous question", key="qc_previous"):
            state["selected_question"] = questions[question_index - 1]["id"]
            if questions[question_index - 1]["id"] not in visited:
                visited.append(questions[question_index - 1]["id"])
            _save(visitor_id, curriculum_id, state)
            st.rerun()
    with next_col:
        if question_index + 1 < len(questions) and st.button("Next question →", key="qc_next"):
            state["selected_question"] = questions[question_index + 1]["id"]
            if questions[question_index + 1]["id"] not in visited:
                visited.append(questions[question_index + 1]["id"])
            _save(visitor_id, curriculum_id, state)
            st.rerun()
        elif question_index + 1 == len(questions) and chapter_index + 1 < len(chapters) and st.button("Next chapter →", key="qc_next_chapter"):
            state["selected_chapter"] = chapters[chapter_index + 1]["id"]
            state["selected_question"] = None
            _save(visitor_id, curriculum_id, state)
            st.rerun()


def render_qc(visitor_id: str, api_base: str,
              attach_to_chat: Callable[[str, str, str], None] | None = None) -> None:
    """Keep the user's request visible above one primary curriculum response card."""
    if st.session_state.get("qc_clarification"):
        _render_qc_body(visitor_id, api_base, attach_to_chat)
        return

    curriculum_id = st.session_state.get("qc_active_id")
    state = st.session_state.get("qc_state") or (
        load_curriculum(visitor_id, curriculum_id) if curriculum_id else None
    )
    if isinstance(state, dict):
        prompt = state.get("request_prompt") or f"Teach me {state['subject']} as a subject"
        st.markdown(
            f"""<div style="display:flex;justify-content:flex-end;margin:8px 0 20px;">
            <div style="max-width:min(72%,680px);padding:12px 16px;border:1px solid #e5e7eb;
                border-radius:18px;background:#f8f9fb;color:#111827;font-size:14px;
                line-height:1.5;overflow-wrap:anywhere;">{escape(prompt)}</div></div>""",
            unsafe_allow_html=True,
        )
    with st.container(border=True, key="qc_primary_response"):
        _render_qc_body(visitor_id, api_base, attach_to_chat)

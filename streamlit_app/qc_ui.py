"""Separate Subject Map → Question Curriculum experience in New Chat."""

import math
import secrets
from html import escape
from typing import Any

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


def _begin(subject: str, visitor_id: str, api_base: str) -> None:
    with st.spinner(f"Mapping {subject} as a subject..."):
        outline = _post(api_base, "/qc/outline", {"topic": subject})
    curriculum_id = f"qc-{secrets.token_urlsafe(12)}"
    state = {
        "version": 1, "subject": subject, "outline": outline,
        "selected_chapter": None, "selected_question": None,
        "answers": {}, "completed": [],
    }
    save_curriculum(visitor_id, curriculum_id, state)
    st.session_state.qc_active_id = curriculum_id
    st.session_state.qc_state = state
    st.session_state.qc_clarification = None
    st.rerun()


def maybe_start_qc(prompt: str, action: str, visitor_id: str, api_base: str) -> bool:
    """Return False for all ordinary topics, card clicks, and Illustrate sends."""
    if action != "interrogate":
        return False
    candidate = learning_subject_candidate(prompt)
    if not candidate:
        return False
    try:
        with st.spinner("Checking whether this is an entire subject..."):
            scope = _post(api_base, "/qc/assess", {"topic": candidate})
        if scope["decision"] == "topic":
            return False
        if scope["decision"] == "clarify":
            st.session_state.qc_clarification = {
                "candidate": scope.get("subject") or candidate,
                "question": scope.get("question") or "Which entire subject would you like to study?",
            }
            st.rerun()
        _begin(scope.get("subject") or candidate, visitor_id, api_base)
    except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
        st.error(f"I couldn't start the Question Curriculum: {exc}")
    return True


def _subject_map_svg(subject: str, chapters: list[dict[str, Any]]) -> str:
    """Draw the actual generated chapter structure as a radial SVG map."""
    count = len(chapters)
    ring_capacity = 8
    rings = math.ceil(count / ring_capacity)
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
    for index, chapter in enumerate(chapters):
        ring = index // ring_capacity
        ring_items = chapters[ring * ring_capacity:(ring + 1) * ring_capacity]
        within_ring = index % ring_capacity
        angle = -math.pi / 2 + 2 * math.pi * within_ring / len(ring_items)
        radius = 290 + ring * 215
        x = center + radius * math.cos(angle)
        y = center + radius * math.sin(angle)
        positions.append((x, y, chapter))
        parts.append(
            f'<line x1="{center}" y1="{center}" x2="{x:.1f}" y2="{y:.1f}" '
            'stroke="#eec7ce" stroke-width="2"/>'
        )
    for x, y, chapter in positions:
        full_title = str(chapter["title"])
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


def render_qc(visitor_id: str, api_base: str) -> None:
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
                    _begin(scope.get("subject") or subject, visitor_id, api_base)
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
        if st.button("Back to New Chat", key="qc_cancel_clarification"):
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

    if st.button("← Back to New Chat", key="qc_back_to_chat"):
        st.session_state.qc_active_id = None
        st.session_state.qc_state = None
        st.rerun()
    st.caption("SUBJECT-LEVEL QUESTION INTELLIGENCE")
    st.title(state["subject"])
    st.subheader("Subject Map")
    st.caption("See the subject before you question your way through it.")
    outline = state["outline"]
    chapters = outline["chapters"]
    st.image(_subject_map_svg(state["subject"], chapters), width="stretch")
    st.subheader("Question Curriculum")
    st.write("Now that you can see the subject as a whole, choose a chapter to follow its ordered questions.")

    selected_chapter_id = state.get("selected_chapter")
    for index, chapter in enumerate(chapters):
        chapter_id = chapter["id"]
        questions = chapter.get("questions") or []
        complete = sum(question["id"] in state["completed"] for question in questions)
        label = f"Chapter {index + 1} — {chapter['title']}"
        if questions:
            label += f" · {complete}/{len(questions)} understood"
        if st.button(label, key=f"qc_select_{chapter_id}", width="stretch"):
            state["selected_chapter"] = chapter_id
            state["selected_question"] = None
            _save(visitor_id, curriculum_id, state)
            st.rerun()

    if not selected_chapter_id:
        return
    chapter = next((item for item in chapters if item["id"] == selected_chapter_id), None)
    if not chapter:
        return
    st.subheader(chapter["title"])
    if not chapter.get("questions"):
        st.caption("The questions for this chapter are prepared when you open it, then saved for later visits.")
        if st.button("Prepare this chapter's questions", key="qc_prepare_chapter"):
            try:
                with st.spinner("Building a progressive question sequence..."):
                    payload = _post(api_base, "/qc/chapter", {"outline": outline, "chapter_id": selected_chapter_id})
                chapter["questions"] = payload["questions"]
                _save(visitor_id, curriculum_id, state)
                st.rerun()
            except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
                st.error(f"I couldn't prepare this chapter: {exc}")
        return

    questions = chapter["questions"]
    for index, question in enumerate(questions):
        marker = "✓ " if question["id"] in state["completed"] else ""
        if st.button(f"{marker}{index + 1}. {question['text']}", key=f"qc_question_{question['id']}", width="stretch"):
            state["selected_question"] = question["id"]
            _save(visitor_id, curriculum_id, state)
            st.rerun()

    selected_question_id = state.get("selected_question")
    question_index = next((index for index, item in enumerate(questions) if item["id"] == selected_question_id), None)
    if question_index is None:
        return
    question = questions[question_index]
    st.caption(f"{state['subject']} → {chapter['title']} → Question {question_index + 1} of {len(questions)}")
    st.markdown(f"### {question['text']}")
    if question["id"] not in state["answers"]:
        try:
            with st.spinner("Teaching this question..."):
                result = _post(api_base, "/qc/answer", {
                    "subject": state["subject"], "chapter": chapter,
                    "questions": questions, "index": question_index,
                })
            state["answers"][question["id"]] = result["answer"]
            _save(visitor_id, curriculum_id, state)
        except (requests.RequestException, RuntimeError, ValueError, KeyError) as exc:
            st.error(f"I couldn't answer this question: {exc}")
            return
    st.markdown(state["answers"][question["id"]])
    if question["id"] not in state["completed"]:
        if st.button("Mark understood", key="qc_mark_understood"):
            state["completed"].append(question["id"])
            _save(visitor_id, curriculum_id, state)
            st.rerun()
    previous_col, next_col = st.columns(2)
    with previous_col:
        if question_index > 0 and st.button("← Previous question", key="qc_previous"):
            state["selected_question"] = questions[question_index - 1]["id"]
            _save(visitor_id, curriculum_id, state)
            st.rerun()
    with next_col:
        if question_index + 1 < len(questions) and st.button("Next question →", key="qc_next"):
            state["selected_question"] = questions[question_index + 1]["id"]
            _save(visitor_id, curriculum_id, state)
            st.rerun()

from streamlit_app.learning_flow import (
    continuation_context,
    find_active_quiz,
    resolve_learning_submission,
)


QUIZ_TEXT = """Quiz (7 questions)

1. What is solar irradiance?
2. Name one photovoltaic material.
3. What does an inverter do?
4. Define peak sun-hours.
5. Name one source of system loss.
6. Calculate 5 x 150 x 0.75.
7. Why does panel orientation matter?

Reply with your answers and I will grade you."""


def test_numbered_reply_to_latest_quiz_is_routed_to_grading() -> None:
    messages = [
        {"id": "q1", "role": "assistant", "mode": "quiz", "text": QUIZ_TEXT},
    ]

    routed = resolve_learning_submission(
        messages,
        "1. Energy per area\n2. Silicon\n6. 5 x 150 x 0.75 = 562.5 kWh",
        "quiz",
    )

    assert routed["mode"] == "quiz_grade"
    assert routed["display_mode"] == "quiz"
    assert routed["previous_answer"] == QUIZ_TEXT
    assert routed["quiz_root_id"] == "q1"


def test_new_topic_does_not_grade_or_reuse_an_older_quiz() -> None:
    messages = [
        {"id": "q1", "role": "assistant", "mode": "quiz", "text": QUIZ_TEXT},
        {"id": "a2", "role": "assistant", "mode": "deep", "text": "A later lesson."},
    ]

    routed = resolve_learning_submission(messages, "1. Solar energy basics", "quiz")

    assert find_active_quiz(messages) is None
    assert routed["mode"] == "quiz"
    assert routed["previous_answer"] == ""


def test_plain_topic_with_quiz_selected_still_generates_a_quiz() -> None:
    routed = resolve_learning_submission([], "Solar energy basics", "quiz")

    assert routed["mode"] == "quiz"
    assert routed["quiz_root_id"] is None


def test_continuation_context_contains_the_whole_existing_chain() -> None:
    messages = [
        {"id": "root", "role": "assistant", "text": "Days 1 through 4"},
        {
            "id": "part-2",
            "role": "assistant",
            "continued_root": "root",
            "text": "Day 5",
        },
        {"id": "unrelated", "role": "assistant", "text": "Ignore me"},
    ]

    assert continuation_context(messages, "part-2") == "Days 1 through 4\n\nDay 5"

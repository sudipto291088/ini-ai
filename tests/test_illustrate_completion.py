from unittest.mock import Mock, patch

from api import illustrate as illustrate_module


def _examples(start: int, end: int, wrong_sqrt: bool = False) -> str:
    blocks = []
    for number in range(start, end + 1):
        detail = (
            "sqrt(3033) ≈ 5.07."
            if wrong_sqrt and number == start
            else f"A concise, concrete scenario for example {number}."
        )
        blocks.append(f"**Example {number} — Scenario {number}**\n\n{detail}")
    return "\n\n---\n\n".join(blocks)


def test_illustrate_continues_to_ten_examples() -> None:
    generator = Mock(
        side_effect=[
            _examples(1, 5, wrong_sqrt=True),
            _examples(6, 10),
        ]
    )

    with (
        patch.object(illustrate_module, "_llm_enabled", lambda: True),
        patch.object(illustrate_module, "llm_answer_question", generator),
    ):
        result = illustrate_module.illustrate("Pythagorean theorem")

    assert result["example_count"] == 10
    assert generator.call_count == 2
    assert "sqrt(3033) ≈ 55.07" in result["illustration_text"]
    assert "sqrt(3033) ≈ 5.07" not in result["illustration_text"]


def test_incomplete_generation_falls_back_to_complete_set() -> None:
    generator = Mock(side_effect=[_examples(1, 3), "", ""])

    with (
        patch.object(illustrate_module, "_llm_enabled", lambda: True),
        patch.object(illustrate_module, "llm_answer_question", generator),
    ):
        result = illustrate_module.illustrate("gradient descent")

    assert result["example_count"] == 10
    assert result["llm_used"] is False


def test_truncated_final_example_is_not_presented() -> None:
    complete_first_batch = _examples(1, 5)
    second_batch = _examples(6, 9) + (
        "\n\n---\n\n**Example 10 — Broken calculation**\n\n"
        "The calculation ends at sqrt(1."
    )
    generator = Mock(side_effect=[complete_first_batch, second_batch])

    with (
        patch.object(illustrate_module, "_llm_enabled", lambda: True),
        patch.object(illustrate_module, "llm_answer_question", generator),
    ):
        result = illustrate_module.illustrate("Pythagorean theorem")

    assert result["example_count"] == 9
    assert "Broken calculation" not in result["illustration_text"]

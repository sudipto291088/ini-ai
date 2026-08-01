import importlib
import sys
from types import ModuleType
import unittest
from unittest.mock import patch


sys.modules.setdefault("requests", ModuleType("requests"))
study_module = importlib.import_module("api.study_ai")


class StudyAIQualityTests(unittest.TestCase):
    def test_new_chat_introduction_is_distinct_from_mnl_overview(self) -> None:
        intro = study_module._build_instruction("intro")
        overview = study_module._build_instruction("high")

        self.assertEqual(study_module._normalize_mode("introduction"), "intro")
        self.assertEqual(study_module._archetype_for_mode("intro"), "ORIENT")
        self.assertIn("250–400 words", intro)
        self.assertIn("prepares the learner for a structured Question Map", intro)
        self.assertIn("never replace it with a broader parent topic", intro)
        self.assertIn("4–7 bullets maximum", overview)
        self.assertNotEqual(intro, overview)

    def test_deep_instruction_is_adaptive_and_avoids_repetition(self) -> None:
        instruction = study_module._build_instruction("deep")

        self.assertIn("not the longest possible answer", instruction)
        self.assertIn("Never restate the same idea", instruction)
        self.assertIn("never invent a present-day value", instruction)
        self.assertIn("ask one targeted clarification", instruction)
        self.assertIn("no more than 80 words", instruction)
        self.assertIn("Do not add a generic guide", instruction)

    def test_continuation_context_preserves_opening_and_ending(self) -> None:
        previous = "OPENING-MARKER\n" + ("middle " * 1200) + "\nENDING-MARKER"

        context = study_module._continuation_context(previous, max_chars=6000)

        self.assertIn("OPENING-MARKER", context)
        self.assertIn("ENDING-MARKER", context)
        self.assertIn("[...middle omitted...]", context)

    def test_current_request_uses_compact_current_archetype(self) -> None:
        captured = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return {
                "answer": "Which location and type of gas do you mean?",
                "incomplete": False,
                "stop_reason": None,
            }

        with (
            patch.object(study_module, "llm_enabled", return_value=True),
            patch.object(
                study_module,
                "detect_intent",
                return_value={
                    "intent": "direct_factual_query",
                    "should_interrogate": False,
                    "should_answer_direct": True,
                },
            ),
            patch.object(study_module, "generate_dynamic_answer_result", fake_generate),
        ):
            study_module.study_ai(
                {
                    "topic": "What is the gas rate today?",
                    "mode": "deep",
                }
            )

        self.assertTrue(
            study_module._requires_current_context("What is the gas rate today?")
        )
        self.assertFalse(
            study_module._requires_current_context("How does electric current flow?")
        )
        self.assertEqual(captured["archetype"], "CURRENT")

    def test_continuation_prompt_forbids_rebuilding_sections(self) -> None:
        captured = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return {
                "answer": "Only new material.",
                "incomplete": False,
                "stop_reason": None,
            }

        with (
            patch.object(study_module, "llm_enabled", return_value=True),
            patch.object(
                study_module,
                "detect_intent",
                return_value={
                    "intent": "topic",
                    "should_interrogate": True,
                    "should_answer_direct": False,
                },
            ),
            patch.object(study_module, "generate_dynamic_answer_result", fake_generate),
        ):
            result = study_module.study_ai(
                {
                    "topic": "Gradient descent",
                    "mode": "deep",
                    "continue_mode": True,
                    "previous_answer": "Definition already covered.\nAn unfinished point:",
                }
            )

        question = captured["question"]
        self.assertEqual(result["answer"], "Only new material.")
        self.assertIn("Definition already covered.", question)
        self.assertIn("Do NOT repeat any heading or idea", question)
        self.assertIn("only the unfinished point", question)

    def test_processor_topics_receive_core_thread_accuracy_contract(self) -> None:
        contract = study_module._processor_accuracy_contract("Explain a hexa-core CPU")

        self.assertIn("six physical cores", contract)
        self.assertIn("Never infer", contract)
        self.assertIn("SMT/Hyper-Threading", contract)
        self.assertEqual(study_module._processor_accuracy_contract("Bayesian inference"), "")

    def test_processor_terminology_guard_repairs_native_threads(self) -> None:
        answer = "A hexa-core processor provides six native threads."

        self.assertEqual(
            study_module._normalize_processor_terminology(answer, "hexa core"),
            "A hexa-core processor provides six physical processing cores.",
        )


if __name__ == "__main__":
    unittest.main()

import importlib
import sys
from types import ModuleType
import unittest
from unittest.mock import patch


sys.modules.setdefault("requests", ModuleType("requests"))
study_module = importlib.import_module("api.study_ai")


class StudyAIQualityTests(unittest.TestCase):
    def test_intro_does_not_assume_programming_intent(self) -> None:
        instruction = study_module._build_instruction("intro")

        self.assertIn("Do not infer that the learner wants programming", instruction)
        self.assertIn("A practical verification step need not involve code", instruction)

    def test_learning_loop_matches_query_depth(self) -> None:
        instruction = study_module._build_instruction("intro")

        self.assertIn("for a broad or introductory topic, use a conceptual learning progression", instruction)
        self.assertIn("for a precise advanced question", instruction)
        self.assertIn("for an explicit practical request", instruction)
        self.assertIn("Do not turn a broad topic into an advanced optimization", instruction)
        self.assertIn("Treat a bare topic or short noun phrase with no action verb as introductory", instruction)
        self.assertIn("Use exactly 5 stages", instruction)
        self.assertIn("do not append a refine or optimization stage", instruction)
        self.assertIn("must not instruct the learner to code, benchmark, measure, profile, optimize", instruction)

    def test_bare_topic_gets_conceptual_five_stage_loop(self) -> None:
        answer = """Before
<LEARNING_LOOP>
<STAGES>
1. Profile :: Measure and optimize the workload.
</STAGES>
<OUTCOME>Optimize it.</OUTCOME>
</LEARNING_LOOP>
After"""

        adapted = study_module._adapt_intro_learning_loop(answer, "hexa-core processors")

        self.assertIn("1. Identify ::", adapted)
        self.assertIn("5. Review ::", adapted)
        self.assertNotIn("Measure and optimize", adapted)
        self.assertIn("Before", adapted)
        self.assertIn("After", adapted)

    def test_explicit_practical_query_keeps_generated_loop(self) -> None:
        answer = "<LEARNING_LOOP>implementation workflow</LEARNING_LOOP>"

        adapted = study_module._adapt_intro_learning_loop(
            answer,
            "Implement parallel processing in Python",
        )

        self.assertEqual(adapted, answer)

    def test_comparison_removes_unsolicited_implementation(self) -> None:
        answer = """<LEARNING_LOOP>prototype and implement both options</LEARNING_LOOP>
<CONTINUE_JOURNEY>implement one representative query</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare relational and graph databases",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare relational and graph databases",
        )

        self.assertNotIn("prototype and implement", adapted)
        self.assertNotIn("implement one representative query", adapted)
        self.assertIn("relational and graph databases", adapted)
        self.assertIn("Strengthen the shared criteria", adapted)

    def test_scientific_process_comparison_uses_process_learning_path(self) -> None:
        answer = """<LEARNING_LOOP>generic decision loop</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic decision journey</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare mitosis and meiosis",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare mitosis and meiosis",
        )

        self.assertIn("Define each process, its biological purpose", adapted)
        self.assertIn("Trace representative examples", adapted)
        self.assertIn("Strengthen the stage-by-stage comparison", adapted)
        self.assertNotIn("decision being examined", adapted)

    def test_tcp_udp_comparison_names_protocol_mechanics(self) -> None:
        answer = """<LEARNING_LOOP>generic comparison</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic journey</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare TCP and UDP.",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare TCP and UDP.",
        )

        self.assertIn("Trace TCP delivery", adapted)
        self.assertIn("Trace UDP delivery", adapted)
        self.assertIn("Test loss and latency trade-offs", adapted)
        self.assertIn("QUIC", adapted)
        self.assertNotIn("decision being examined", adapted)

    def test_conditioning_comparison_uses_learning_mechanisms(self) -> None:
        answer = """<LEARNING_LOOP>generic comparison</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic journey</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare classical and operant conditioning.",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare classical and operant conditioning.",
        )

        self.assertIn("links two stimuli", adapted)
        self.assertIn("links behavior to its consequence", adapted)
        self.assertIn("Classify contrasting examples", adapted)
        self.assertIn("exposure", adapted)

    def test_stack_queue_comparison_has_specific_paths_and_relationship(self) -> None:
        answer = """<CORE_EXPLANATION>
<UPDATE_RULE>Order rule :: reversed? FIFO/LIFO</UPDATE_RULE>
<VARIABLES>element :: item\nFIFO :: queue\nLIFO :: stack</VARIABLES>
</CORE_EXPLANATION>
<LEARNING_LOOP>generic comparison</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic journey</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer, "Compare stack and queue data structures."
        )
        adapted = study_module._adapt_compare_journey(
            adapted, "Compare stack and queue data structures."
        )
        adapted = study_module._normalize_stack_queue_relationship(
            adapted, "Compare stack and queue data structures."
        )

        self.assertIn("Trace insertion and removal", adapted)
        self.assertIn("Simulate both structures by hand", adapted)
        self.assertIn("order_stack = reverse(insertion_order)", adapted)
        self.assertNotIn("reversed?", adapted)

    def test_bfs_dfs_comparison_uses_graph_search_paths(self) -> None:
        answer = """<LEARNING_LOOP>generic comparison</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic journey</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer, "Compare breadth-first search and depth-first search."
        )
        adapted = study_module._adapt_compare_journey(
            adapted, "Compare breadth-first search and depth-first search."
        )

        self.assertIn("Trace traversal order", adapted)
        self.assertIn("Compare guarantees", adapted)
        self.assertIn("Trace one graph with both searches", adapted)
        self.assertIn("iterative deepening", adapted)

    def test_respiration_comparison_uses_biological_process_path(self) -> None:
        answer = """<LEARNING_LOOP>generic</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare aerobic and anaerobic respiration",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare aerobic and anaerobic respiration",
        )

        self.assertIn("Define each process, its biological purpose", adapted)
        self.assertIn("inputs, transformations, and outputs", adapted)
        self.assertNotIn("decision being examined", adapted)

    def test_metabolic_process_journey_does_not_leak_cell_division_terms(self) -> None:
        answer = "<CONTINUE_JOURNEY>generic decision journey</CONTINUE_JOURNEY>"

        adapted = study_module._adapt_compare_journey(
            answer,
            "Compare photosynthesis and cellular respiration",
        )

        self.assertIn("inputs, transformations, and outputs", adapted)
        self.assertIn("material, energy, or biological outcome", adapted)
        self.assertNotIn("chromosome", adapted.casefold())

    def test_conceptual_comparison_uses_concept_learning_path(self) -> None:
        answer = """<LEARNING_LOOP>generic decision loop</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic decision journey</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare deductive and inductive reasoning",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare deductive and inductive reasoning",
        )

        self.assertIn("Define each concept precisely", adapted)
        self.assertIn("Classify representative arguments", adapted)
        self.assertIn("Strengthen the distinction", adapted)
        self.assertNotIn("decision being examined", adapted)

    def test_research_method_comparison_uses_methodological_path(self) -> None:
        answer = """<LEARNING_LOOP>generic</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare qualitative and quantitative research",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare qualitative and quantitative research",
        )

        self.assertIn("sampling, collection, analysis", adapted)
        self.assertIn("Explore mixed-method integration", adapted)
        self.assertNotIn("Classify representative arguments", adapted)

    def test_correlation_and_causation_use_causal_inference_path(self) -> None:
        answer = """<LEARNING_LOOP>generic</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare correlation and causation",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare correlation and causation",
        )

        self.assertIn("confounding, reverse causality", adapted)
        self.assertIn("Draw the causal structure", adapted)
        self.assertNotIn("Classify representative arguments", adapted)

    def test_metric_comparison_uses_metric_learning_path(self) -> None:
        answer = """<LEARNING_LOOP>generic decision loop</LEARNING_LOOP>
<CONTINUE_JOURNEY>generic decision journey</CONTINUE_JOURNEY>"""

        adapted = study_module._adapt_compare_learning_loop(
            answer,
            "Compare precision and recall in machine learning",
        )
        adapted = study_module._adapt_compare_journey(
            adapted,
            "Compare precision and recall in machine learning",
        )

        self.assertIn("map every term to the underlying observations", adapted)
        self.assertIn("Explore threshold trade-offs", adapted)
        self.assertNotIn("decision being examined", adapted)

    def test_metric_journey_uses_the_metrics_in_the_query(self) -> None:
        answer = "<CONTINUE_JOURNEY>generic</CONTINUE_JOURNEY>"

        adapted = study_module._adapt_compare_journey(
            answer,
            "Compare sensitivity and specificity in medical testing",
        )

        self.assertIn("sensitivity, and specificity", adapted)
        self.assertNotIn("precision, and recall", adapted)

    def test_missing_intro_cards_override_false_provider_completion(self) -> None:
        incomplete_answer = """<TOPIC_PROFILE>{}</TOPIC_PROFILE>
<LEARNING_PATHS>{}</LEARNING_PATHS>
Purpose: A partial response."""

        self.assertEqual(
            study_module._missing_intro_sections(incomplete_answer),
            [
                "YOUR_QUESTION",
                "CORE_EXPLANATION",
                "LEARNING_LOOP",
                "CONTINUE_JOURNEY",
                "INTRODUCTION",
            ],
        )

    def test_meiosis_stage_misstatement_is_repaired(self) -> None:
        normalized = study_module._normalize_response_text(
            "Meiosis has meiosis I and I, not meiosis I vs I or meiosis I/I. "
            "Meiosis I — sister chromatid separation. "
            "Meiosis I (reductional) and meiosis I (equational, separates sister chromatids). "
            "Meiosis I separates homologs; meiosis I separates sister chromatids."
        )

        self.assertEqual(
            normalized,
            "Meiosis has meiosis I and II, not meiosis I vs II or meiosis I/II. "
            "Meiosis II — sister chromatid separation. "
            "Meiosis I (reductional) and meiosis II (equational, separates sister chromatids). "
            "Meiosis I separates homologs; "
            "meiosis II separates sister chromatids.",
        )

    def test_meiosis_comparison_repairs_stage_labels_across_cards(self) -> None:
        answer = (
            "Subject: Compare meiosis I and meiosis I\n"
            "Able to explain meiosis I vs meiosis I.\n"
            "Meiosis I is the reductional division. Meiosis I is the equational division.\n"
            "The count falls after meiosis I; it remains unchanged after meiosis I.\n"
            "How does nondisjunction in meiosis I differ from meiosis I errors?\n"
            "reduction_steps = 1 for meiosis I, 0 for meiosis I.\n"
            "No new homolog pairing in meiosis I. Metaphase I: individual chromosomes align.\n"
            "Meiosis I resembles mitosis. meiosis I + meiosis I. I vs I.\n"
            "Meiosis I (equational). Meiosis I lacks crossing-over.\n"
            "2n --meiosis I--> n --meiosis I--> n (unchanged).\n"
            "prophase I to anaphase I separating chromatids.\n"
            "In meiosis I, centromeric cohesin is removed.\n"
            "What does separating sister chromatids in meiosis I solve?"
        )

        normalized = study_module._normalize_response_text(
            answer,
            "Compare meiosis I and meiosis II",
        )

        self.assertIn("Compare meiosis I and meiosis II", normalized)
        self.assertIn("meiosis I vs meiosis II", normalized)
        self.assertIn("Meiosis II is the equational division", normalized)
        self.assertIn("remains unchanged after meiosis II", normalized)
        self.assertIn("differ from meiosis II errors", normalized)
        self.assertIn("0 for meiosis II", normalized)
        self.assertIn("No new homolog pairing in meiosis II", normalized)
        self.assertIn("Metaphase II: individual chromosomes", normalized)
        self.assertIn("Meiosis II resembles mitosis", normalized)
        self.assertIn("meiosis I + meiosis II", normalized)
        self.assertIn("I vs II", normalized)
        self.assertIn("Meiosis II (equational)", normalized)
        self.assertIn("Meiosis II lacks crossing-over", normalized)
        self.assertIn("--meiosis II--> n (unchanged)", normalized)
        self.assertIn("prophase II to anaphase II separating chromatids", normalized)
        self.assertIn("In meiosis II, centromeric cohesin is removed", normalized)
        self.assertIn("sister chromatids in meiosis II solve", normalized)

    def test_numbered_meiotic_stage_comparisons_are_repaired_systemically(self) -> None:
        metaphase = study_module._normalize_response_text(
            "Metaphase I versus Metaphase I. "
            "Metaphase I aligns homolog pairs, whereas metaphase I aligns sister chromatids. "
            "MII — metaphase I stage.",
            "Compare metaphase I and metaphase II",
        )
        anaphase = study_module._normalize_response_text(
            "Anaphase I and anaphase I differ. "
            "Anaphase I separates homologs. Anaphase I separates sister chromatids. "
            "At anaphase I centromeric cohesin is cleaved.",
            "Compare anaphase I and anaphase II",
        )

        self.assertNotRegex(metaphase, r"(?i)metaphase I (?:versus|and|vs\.?) metaphase I\b")
        self.assertIn("metaphase II aligns sister chromatids", metaphase)
        self.assertIn("MII — metaphase II stage", metaphase)
        self.assertNotRegex(anaphase, r"(?i)anaphase I (?:versus|and|vs\.?) anaphase I\b")
        self.assertIn("Anaphase II separates sister chromatids", anaphase)
        self.assertIn("At anaphase II centromeric cohesin is cleaved", anaphase)

    def test_placeholder_journey_headings_are_replaced(self) -> None:
        answer = """<CONTINUE_JOURNEY>
<DIRECTIONS>
1. A short, topic-specific direction :: First step
2. A short, topic-specific direction :: Second step
3. A short, topic-specific direction :: Third step
</DIRECTIONS>
</CONTINUE_JOURNEY>"""

        normalized = study_module._normalize_continue_journey_headings(answer)

        self.assertNotIn("A short, topic-specific direction", normalized)
        self.assertIn("1. Strengthen understanding", normalized)
        self.assertIn("2. Practise or verify", normalized)
        self.assertIn("3. Advance beyond it", normalized)

    def test_common_contraction_typo_is_repaired(self) -> None:
        self.assertEqual(
            study_module._normalize_response_text("You'l get a concise map."),
            "You'll get a concise map.",
        )
        self.assertEqual(
            study_module._normalize_response_text("You’l explore the topic."),
            "You'll explore the topic.",
        )

        self.assertEqual(
            study_module._normalize_response_text(
                "It signals that You'll learn the mechanism. You'll then apply it."
            ),
            "It signals that you'll learn the mechanism. You'll then apply it.",
        )

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

    def test_validation_retry_requests_a_complete_fresh_response(self) -> None:
        captured = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return {
                "answer": "A regenerated response.",
                "incomplete": False,
                "stop_reason": None,
            }

        with (
            patch.object(study_module, "llm_enabled", return_value=True),
            patch.object(
                study_module,
                "detect_intent",
                return_value={
                    "intent": "topic_explore",
                    "should_interrogate": True,
                    "should_answer_direct": False,
                },
            ),
            patch.object(study_module, "generate_dynamic_answer_result", fake_generate),
        ):
            study_module.study_ai(
                {
                    "topic": "Quantum entanglement",
                    "mode": "intro",
                    "validation_feedback": [
                        "Bell-state formula contains single-qubit basis states"
                    ],
                }
            )

        prompt = captured["question"]
        self.assertIn("VALIDATION RETRY", prompt)
        self.assertIn("Regenerate the complete response from scratch", prompt)
        self.assertIn("Bell-state formula contains single-qubit basis states", prompt)

    def test_should_question_reaches_full_intro_generator(self) -> None:
        captured = {}

        def fake_generate(**kwargs):
            captured.update(kwargs)
            return {
                "answer": "Structured draft",
                "incomplete": False,
                "stop_reason": None,
            }

        with (
            patch.object(study_module, "llm_enabled", return_value=True),
            patch.object(
                study_module,
                "detect_intent",
                return_value={
                    "intent": "clarify",
                    "should_interrogate": False,
                    "should_answer_direct": False,
                    "reply": "Send a topic to explore.",
                },
            ),
            patch.object(study_module, "generate_dynamic_answer_result", fake_generate),
        ):
            result = study_module.study_ai(
                {
                    "topic": "Should schools use facial recognition to record student attendance?",
                    "mode": "intro",
                }
            )

        self.assertEqual(result["answer"], "Structured draft")
        self.assertIn("<TOPIC_PROFILE>", captured["question"])
        self.assertNotEqual(result.get("llm", {}).get("reason"), "intent_reply")

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

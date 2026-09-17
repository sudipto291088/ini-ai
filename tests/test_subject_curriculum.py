import os
import tempfile
import unittest
from unittest.mock import patch

from api import subject_curriculum as qc
from streamlit_app import storage_sqlite
from streamlit_app import qc_ui


class SubjectIntentTests(unittest.TestCase):
    def test_bare_subjects_and_narrow_requests_stay_in_normal_chat(self):
        for prompt in (
            "Machine learning",
            "Artificial Intelligence",
            "Quantum computing",
            "What is machine learning?",
            "I want to learn how to install Python",
            "I want to learn the basics of solar energy in one week",
            "I want to study Operating Systems in two weeks",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(qc.learning_subject_candidate(prompt), "")

    def test_explicit_whole_subject_learning_is_a_candidate(self):
        examples = {
            "I want to learn Machine Learning.": "Machine Learning",
            "I want to study Operating Systems.": "Operating Systems",
            "Teach me Data Science.": "Data Science",
            "I want to understand Quantum Computing as a subject.": "Quantum Computing",
        }
        for prompt, subject in examples.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(qc.learning_subject_candidate(prompt), subject)

    def test_narrow_topic_is_sent_back_to_normal_chat(self):
        with patch.object(qc_ui, "_post", return_value={"decision": "topic"}):
            self.assertFalse(qc_ui.maybe_start_qc("I want to learn gradient descent", "interrogate", "v", "http://api"))
        with patch.object(qc_ui, "_post", side_effect=AssertionError("QC must not run")):
            self.assertFalse(qc_ui.maybe_start_qc("Machine learning", "interrogate", "v", "http://api"))
            self.assertFalse(qc_ui.maybe_start_qc("Teach me Data Science", "illustrate", "v", "http://api"))


class GenerationTests(unittest.TestCase):
    def test_outline_and_chapter_questions_have_stable_ids_and_no_fixed_count(self):
        outline_data = {
            "chapters": [
                {"title": "Foundations", "objectives": ["Define the field", "Understand prerequisites"]},
                {"title": "Methods", "objectives": ["Compare methods"]},
            ]
        }
        with patch.object(qc, "_json_result", return_value=outline_data):
            outline = qc.generate_subject_outline("Machine Learning")
        self.assertEqual([chapter["id"] for chapter in outline["chapters"]], ["chapter-1", "chapter-2"])
        self.assertIsNone(outline["chapters"][0]["questions"])
        question_data = {"questions": [f"What is concept {index}?" for index in range(17)]}
        with patch.object(qc, "_json_result", return_value=question_data):
            questions = qc.generate_chapter_questions(outline, "chapter-1")
        self.assertEqual(len(questions), 17)
        self.assertEqual(questions[-1]["id"], "chapter-1-q17")

    def test_generated_map_is_svg_with_the_chapter_structure(self):
        chapters = [
            {"title": "Foundations & Data"}, {"title": "Models"},
        ]
        svg = qc_ui._subject_map_svg("Machine Learning", chapters)
        self.assertIn("<svg", svg)
        self.assertIn("Foundations &amp; Data", svg)
        self.assertIn("Models", svg)
        self.assertIn("1. Foundations &amp; Data", svg)
        self.assertIn("2. Models", svg)
        self.assertEqual(svg.count("<line "), 2)
        first_frame = qc_ui._subject_map_svg("Machine Learning", chapters, 1)
        self.assertIn("1. Foundations &amp; Data", first_frame)
        self.assertNotIn("2. Models", first_frame)
        self.assertEqual(first_frame.count("<line "), 1)

    def test_qc_text_streams_one_character_at_a_time(self):
        chunks = []

        def capture(stream, **_kwargs):
            chunks.extend(stream)

        with patch.object(qc_ui.st, "write_stream", side_effect=capture), patch.object(qc_ui.time, "sleep"):
            qc_ui._stream_text("Learn.")
        self.assertEqual(chunks, list("Learn."))

    def test_chapter_sequence_keeps_valid_questions_when_one_is_duplicate_or_malformed(self):
        outline = {
            "subject": "Machine Learning",
            "chapters": [{"id": "chapter-1", "title": "Introduction", "objectives": ["Define ML"], "questions": None}],
        }
        generated = {"questions": [
            "1. What is machine learning?",
            {"question": "What is machine learning?"},
            "How does it differ from ordinary programming.",
            "A concluding summary",
            "Why does data quality matter?",
        ]}
        with patch.object(qc, "_json_result", return_value=generated):
            questions = qc.generate_chapter_questions(outline, "chapter-1")
        self.assertEqual([item["text"] for item in questions], [
            "What is machine learning?",
            "How does it differ from ordinary programming?",
            "Why does data quality matter?",
        ])
        self.assertEqual([item["id"] for item in questions], [
            "chapter-1-q1", "chapter-1-q2", "chapter-1-q3",
        ])

    def test_chapter_sequence_still_rejects_an_entirely_invalid_result(self):
        outline = {
            "subject": "Machine Learning",
            "chapters": [{"id": "chapter-1", "title": "Introduction", "objectives": ["Define ML"], "questions": None}],
        }
        with patch.object(qc, "_json_result", return_value={"questions": ["Summary only", "No questions"]}):
            with self.assertRaisesRegex(ValueError, "No valid questions"):
                qc.generate_chapter_questions(outline, "chapter-1")

    def test_answer_rejects_missing_question_without_an_llm_call(self):
        with patch.object(qc, "generate_dynamic_answer_result", side_effect=AssertionError("No LLM call expected")):
            with self.assertRaises(ValueError):
                qc.answer_curriculum_question("Machine Learning", {"title": "Foundations"}, [], 0)

    def test_answer_reports_incomplete_and_service_failures_separately(self):
        chapter = {"title": "Foundations"}
        questions = [{"id": "chapter-1-q1", "text": "What is this subject?"}]
        with patch.object(qc, "generate_dynamic_answer_result", return_value={
            "answer": "A partial lesson.", "incomplete": True, "stop_reason": "max_output_tokens",
        }):
            with self.assertRaisesRegex(RuntimeError, "stopped before completion.*max_output_tokens"):
                qc.answer_curriculum_question("Machine Learning", chapter, questions, 0)
        with patch.object(qc, "generate_dynamic_answer_result", return_value={
            "answer": "", "error": "rate_limited", "http_status": 429,
        }):
            with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
                qc.answer_curriculum_question("Machine Learning", chapter, questions, 0)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = storage_sqlite.DB_PATH
        storage_sqlite.DB_PATH = os.path.join(self.temp_dir.name, "qc.db")
        storage_sqlite.init_db()

    def tearDown(self):
        storage_sqlite.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_curriculum_progress_survives_and_is_visitor_scoped(self):
        state = {
            "subject": "Machine Learning",
            "outline": {"chapters": [{"id": "chapter-1", "title": "Foundations", "questions": []}]},
            "completed": ["chapter-1-q1"],
        }
        storage_sqlite.save_curriculum("visitor-A", "qc-1", state)
        self.assertEqual(storage_sqlite.load_curriculum("visitor-A", "qc-1"), state)
        self.assertEqual(storage_sqlite.list_curricula("visitor-A")[0][1], "Machine Learning")
        self.assertIsNone(storage_sqlite.load_curriculum("visitor-B", "qc-1"))
        self.assertEqual(storage_sqlite.list_curricula("visitor-B"), [])
        storage_sqlite.save_curriculum("visitor-B", "qc-1", {"subject": "Hijacked"})
        self.assertEqual(storage_sqlite.load_curriculum("visitor-A", "qc-1"), state)

    def test_curriculum_can_be_reopened_from_a_new_chat_session(self):
        state = {"subject": "Computer Networks", "selected_chapter": "chapter-2", "visited_questions": ["chapter-2-q1"]}
        storage_sqlite.save_curriculum("visitor-A", "qc-1", state)
        storage_sqlite.save_session(
            "visitor-A", "chat-1", "Computer Networks", "Sep 16.2026",
            {"topic": "Computer Networks", "qc_curricula_ids": ["qc-1"], "qc_active_id": "qc-1"},
        )
        self.assertEqual(storage_sqlite.list_sessions("visitor-A")[0][0], "chat-1")
        saved_chat = storage_sqlite.load_session("visitor-A", "chat-1")
        self.assertEqual(saved_chat["messages"]["qc_active_id"], "qc-1")
        self.assertEqual(storage_sqlite.load_curriculum("visitor-A", saved_chat["messages"]["qc_active_id"]), state)
        self.assertIsNone(storage_sqlite.load_session("visitor-B", "chat-1"))


if __name__ == "__main__":
    unittest.main()

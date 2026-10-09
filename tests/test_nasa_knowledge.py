import os
import unittest
from datetime import date
from contextlib import ExitStack
from unittest.mock import patch

from api import nasa_knowledge as nasa


class NasaKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"INI_NASA_ENABLED": "1"})
        self.env.start()
        self.clock = patch.object(nasa, "date")
        self.mock_date = self.clock.start()
        self.mock_date.today.return_value = date(2026, 10, 8)

    def tearDown(self):
        self.clock.stop()
        self.env.stop()

    def test_supported_topics_have_official_attributed_notes(self):
        for topic in ("solar system", "black holes", "earth science"):
            context = nasa.retrieve_nasa_context(topic)
            self.assertEqual(context["source"], "NASA Science")
            self.assertEqual(context["reviewed_on"], "2026-10-08")
            self.assertEqual(len(context["works"]), 1)
            self.assertTrue(context["works"][0]["source_url"].startswith("https://science.nasa.gov/"))
            self.assertTrue(context["works"][0]["facts"])

    def test_unrelated_and_ambiguous_topics_are_unchanged(self):
        for topic in ("machine learning", "solar energy", "space complexity", ""):
            self.assertEqual(nasa.retrieve_nasa_context(topic), {})
        self.assertEqual(nasa.retrieve_nasa_context(None), {})

    def test_disabled(self):
        with patch.dict(os.environ, {"INI_NASA_ENABLED": "0"}):
            self.assertEqual(nasa.retrieve_nasa_context("astronomy"), {})

    def test_review_expiry(self):
        self.mock_date.today.return_value = date(2027, 10, 8)
        self.assertEqual(nasa.retrieve_nasa_context("astronomy"), {})

    def test_callers_cannot_mutate_catalogue(self):
        context = nasa.retrieve_nasa_context("solar system")
        context["works"][0]["facts"].clear()
        self.assertTrue(nasa.retrieve_nasa_context("solar system")["works"][0]["facts"])

    def test_prompt_limits_claims_and_preserves_schema(self):
        text = nasa.format_nasa_prompt_context(nasa.retrieve_nasa_context("black holes"))
        self.assertIn("Not live retrieval", text)
        self.assertIn("Attribute NASA Science", text)
        self.assertIn("Preserve requested structured output schemas", text)
        self.assertEqual(nasa.format_nasa_prompt_context({}), "")

    def test_answer_pipeline_receives_and_reports_source(self):
        from api import llm_answers as llm

        response = {
            "id": "resp_nasa_test", "status": "completed", "model": "test-model",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Test answer."}]}],
        }
        with ExitStack() as stack:
            for name in (
                "wikidata", "wikipedia", "wikibooks", "wikiversity", "crossref",
                "datacite", "openalex", "doaj", "europe_pmc", "arxiv", "openstax",
            ):
                attribute = "retrieve_" + name + "_context"
                # OpenStax is separate local work, not part of this release.
                if name == "openstax" and not hasattr(llm, attribute):
                    continue
                stack.enter_context(patch.object(llm, attribute, return_value={}))
            stack.enter_context(patch.object(llm, "OPENAI_API_KEY", "test-key"))
            post = stack.enter_context(patch.object(llm.requests, "post"))
            post.return_value.status_code = 200
            post.return_value.json.return_value = response
            result = llm.generate_dynamic_answer_result(
                topic="black holes", topic_type="concept", archetype="ORIENT",
                question="What is an event horizon?",
            )
        prompt = post.call_args.kwargs["json"]["input"][1]["content"]
        self.assertIn("BEGIN REVIEWED NASA SCIENCE NOTES", prompt)
        self.assertIn("https://science.nasa.gov/universe/black-holes/", prompt)
        self.assertEqual(len(result["knowledge_sources"]), 1)
        self.assertEqual(result["knowledge_sources"][0]["source"], "NASA Science")


if __name__ == "__main__":
    unittest.main()

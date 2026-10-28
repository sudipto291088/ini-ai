import os
import unittest
from contextlib import ExitStack
from datetime import date, timedelta
from unittest.mock import patch

from api import usgs_knowledge as usgs


class UsgsKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {"INI_USGS_ENABLED": "1"}))
        self.clock = self.stack.enter_context(patch.object(usgs, "date"))
        self.clock.today.return_value = date(2026, 10, 28)

    def test_verified_topics_include_attribution_and_official_links(self):
        for topic in ("Why do earthquakes happen?", "How do volcanoes erupt?", "What is groundwater?"):
            with self.subTest(topic=topic):
                context = usgs.retrieve_usgs_context(topic)
                self.assertEqual(context["source"], "USGS")
                self.assertEqual(context["reviewed_on"], "2026-10-28")
                self.assertEqual(context["attribution"], "U.S. Geological Survey (USGS)")
                self.assertEqual(len(context["works"]), 1)
                self.assertTrue(context["works"][0]["source_url"].startswith("https://www.usgs.gov/"))
                self.assertTrue(context["works"][0]["facts"])

    def test_unrelated_invalid_and_ambiguous_inputs_are_unchanged(self):
        for topic in (None, 42, [], "", "machine learning", "fault tolerance", "rock music", "Java", "x" * 301):
            self.assertEqual(usgs.retrieve_usgs_context(topic), {}, repr(topic))

    def test_no_live_or_personal_hazard_claims(self):
        for topic in ("latest earthquakes", "earthquake today", "volcano alert", "predict an earthquake",
                      "is groundwater safe to drink", "earthquake near me", "current volcanic eruption",
                      "earthquake evacuation", "groundwater safety", "volcano forecast"):
            self.assertEqual(usgs.retrieve_usgs_context(topic), {}, topic)

    def test_disable_switch(self):
        for setting in ("0", "false", "NO", " off "):
            with patch.dict(os.environ, {"INI_USGS_ENABLED": setting}):
                self.assertEqual(usgs.retrieve_usgs_context("earthquakes"), {})

    def test_review_window_boundary_and_future_date(self):
        self.clock.today.return_value = usgs.REVIEWED_ON + timedelta(days=180)
        self.assertTrue(usgs.retrieve_usgs_context("earthquakes"))
        for day in (usgs.REVIEWED_ON + timedelta(days=181), usgs.REVIEWED_ON - timedelta(days=1)):
            self.clock.today.return_value = day
            self.assertEqual(usgs.retrieve_usgs_context("earthquakes"), {})

    def test_results_do_not_mutate_reviewed_catalogue(self):
        context = usgs.retrieve_usgs_context("earthquakes")
        context["works"][0]["facts"].clear()
        self.assertTrue(usgs.retrieve_usgs_context("earthquakes")["works"][0]["facts"])

    def test_adapter_makes_no_external_requests(self):
        with patch("requests.get") as get, patch("requests.post") as post:
            self.assertTrue(usgs.retrieve_usgs_context("aquifers"))
        get.assert_not_called()
        post.assert_not_called()

    def test_prompt_enforces_credit_and_scope(self):
        text = usgs.format_usgs_prompt_context(usgs.retrieve_usgs_context("earthquakes"))
        for required in ("Not live retrieval", "Credit the U.S. Geological Survey", "link the supporting page",
                         "do not establish current events", "Do not imply USGS endorsement",
                         "Preserve requested structured output schemas"):
            self.assertIn(required, text)
        self.assertEqual(usgs.format_usgs_prompt_context({}), "")

    def test_answer_pipeline_uses_notes_and_reports_honest_source_metadata(self):
        from api import llm_answers as llm
        response = {"id": "resp_usgs_test", "status": "completed", "model": "test-model",
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": "Test answer."}]}]}
        with ExitStack() as stack:
            for name in ("wikidata", "wikipedia", "wikibooks", "wikiversity", "crossref", "datacite",
                         "openalex", "doaj", "europe_pmc", "arxiv", "nasa", "openstax"):
                attribute = "retrieve_" + name + "_context"
                if hasattr(llm, attribute):
                    stack.enter_context(patch.object(llm, attribute, return_value={}))
            stack.enter_context(patch.object(llm, "OPENAI_API_KEY", "test-key"))
            post = stack.enter_context(patch.object(llm.requests, "post"))
            post.return_value.status_code = 200
            post.return_value.json.return_value = response
            result = llm.generate_dynamic_answer_result(topic="earthquakes", topic_type="concept",
                                                        archetype="ORIENT", question="Why does the ground shake?")
        prompt = post.call_args.kwargs["json"]["input"][1]["content"]
        self.assertIn("BEGIN REVIEWED USGS SCIENCE NOTES", prompt)
        self.assertIn("https://www.usgs.gov/programs/earthquake-hazards/science-earthquakes", prompt)
        self.assertEqual(len(result["knowledge_sources"]), 1)
        self.assertEqual(result["knowledge_sources"][0]["source"], "USGS")
        self.assertIn("no live retrieval", result["knowledge_sources"][0]["content_scope"])


if __name__ == "__main__":
    unittest.main()

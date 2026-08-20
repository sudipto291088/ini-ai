from __future__ import annotations

import os
import unittest
from typing import Any, Dict, List
from unittest.mock import patch

import api.llm_answers as llm
import api.wikipedia_knowledge as wp


class FakeResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload


class WikipediaKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        wp.clear_wikipedia_cache()

    def test_retrieves_attributed_bounded_extract_and_caches(self) -> None:
        calls: List[Dict[str, Any]] = []
        payload = {
            "query": {
                "pages": [
                    {
                        "pageid": 123,
                        "title": "Linear regression",
                        "fullurl": "https://en.wikipedia.org/wiki/Linear_regression",
                        "extract": "Linear regression is a statistical method.",
                        "pageprops": {},
                    }
                ]
            }
        }

        def fake_get(url, *, params, headers, timeout):
            calls.append({"url": url, "params": params, "headers": headers})
            return FakeResponse(payload)

        with patch.object(wp.requests, "get", side_effect=fake_get):
            first = wp.retrieve_wikipedia_context("What is linear regression?")
            second = wp.retrieve_wikipedia_context("What is linear regression?")

        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)
        self.assertEqual(first["source"], "Wikipedia")
        self.assertEqual(first["license"], "CC-BY-SA-4.0")
        self.assertEqual(first["attribution"], "Wikipedia contributors")
        self.assertTrue(first["source_url"].startswith("https://en.wikipedia.org/"))
        self.assertEqual(calls[0]["url"], wp.API_URL)
        self.assertIn("InI.ai/", calls[0]["headers"]["User-Agent"])

    def test_disambiguation_and_network_failure_fall_back(self) -> None:
        disambiguation = {
            "query": {
                "pages": [
                    {
                        "pageid": 1,
                        "title": "Mercury",
                        "fullurl": "https://en.wikipedia.org/wiki/Mercury",
                        "extract": "Mercury may refer to several topics.",
                        "pageprops": {"disambiguation": ""},
                    }
                ]
            }
        }
        with patch.object(wp.requests, "get", return_value=FakeResponse(disambiguation)):
            self.assertEqual(wp.retrieve_wikipedia_context("Mercury"), {})
        wp.clear_wikipedia_cache()
        with patch.object(wp.requests, "get", return_value=FakeResponse({}, 429)):
            self.assertEqual(wp.retrieve_wikipedia_context("linear regression"), {})

    def test_can_be_disabled_and_private_queries_never_leave_ini(self) -> None:
        old_value = os.environ.get("INI_WIKIPEDIA_ENABLED")
        os.environ["INI_WIKIPEDIA_ENABLED"] = "0"
        try:
            self.assertEqual(wp.retrieve_wikipedia_context("linear regression"), {})
        finally:
            if old_value is None:
                os.environ.pop("INI_WIKIPEDIA_ENABLED", None)
            else:
                os.environ["INI_WIKIPEDIA_ENABLED"] = old_value

        private_queries = [
            "My medical diagnosis",
            "email me@example.com about regression",
            "use my API key secret",
            "https://private.example.com/topic",
        ]
        with patch.object(wp.requests, "get") as request_get:
            for query in private_queries:
                self.assertEqual(wp.retrieve_wikipedia_context(query), {})
        request_get.assert_not_called()

    def test_prompt_is_bounded_non_instructional_and_attributed(self) -> None:
        prompt = wp.format_wikipedia_prompt_context(
            {
                "title": "Linear regression",
                "extract": "A concise introduction.",
                "source_url": "https://en.wikipedia.org/wiki/Linear_regression",
            }
        )
        self.assertIn("Wikipedia contributors (CC-BY-SA-4.0)", prompt)
        self.assertIn("do not copy sentences verbatim", prompt)
        self.assertTrue(prompt.startswith("BEGIN TRUSTED ENCYCLOPEDIC KNOWLEDGE"))
        self.assertTrue(prompt.endswith("END TRUSTED ENCYCLOPEDIC KNOWLEDGE"))

    def test_llm_pipeline_receives_both_sources_and_returns_metadata(self) -> None:
        wikidata = {"source": "Wikidata", "label": "linear regression"}
        wikipedia = {
            "source": "Wikipedia",
            "license": "CC-BY-SA-4.0",
            "title": "Linear regression",
            "extract": "A statistical method.",
            "source_url": "https://en.wikipedia.org/wiki/Linear_regression",
        }
        captured: Dict[str, Any] = {}

        def fake_post(url, *, headers, json, timeout):
            captured["payload"] = json
            return FakeResponse(
                {
                    "id": "resp_test",
                    "status": "completed",
                    "model": "test-model",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Grounded."}],
                        }
                    ],
                }
            )

        old_key = llm.OPENAI_API_KEY
        llm.OPENAI_API_KEY = "test-key"
        try:
            with patch.object(llm, "retrieve_wikidata_context", return_value=wikidata), patch.object(
                llm, "format_wikidata_prompt_context", return_value="WIKIDATA CONTEXT"
            ), patch.object(
                llm, "retrieve_wikipedia_context", return_value=wikipedia
            ), patch.object(
                llm, "format_wikipedia_prompt_context", return_value="WIKIPEDIA CONTEXT"
            ), patch.object(
                llm, "retrieve_wikibooks_context", return_value={}
            ), patch.object(
                llm, "retrieve_crossref_context", return_value={}
            ), patch.object(
                llm, "retrieve_datacite_context", return_value={}
            ), patch.object(
                llm, "retrieve_wikiversity_context", return_value={}
            ), patch.object(llm.requests, "post", side_effect=fake_post):
                result = llm.generate_dynamic_answer_result(
                    topic="linear regression",
                    topic_type="concept",
                    archetype="ORIENT",
                    question="What is linear regression?",
                )
        finally:
            llm.OPENAI_API_KEY = old_key

        user_prompt = captured["payload"]["input"][1]["content"]
        self.assertIn("WIKIDATA CONTEXT", user_prompt)
        self.assertIn("WIKIPEDIA CONTEXT", user_prompt)
        self.assertEqual(result["knowledge_sources"], [wikidata, wikipedia])


if __name__ == "__main__":
    unittest.main()

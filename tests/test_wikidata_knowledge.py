from __future__ import annotations

import os
import unittest
from typing import Any, Dict, List
from unittest.mock import patch

import api.wikidata_knowledge as wk
import api.llm_answers as llm


class FakeResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload


def payloads() -> List[Dict[str, Any]]:
    return [
        {
            "search": [
                {
                    "id": "Q1087808",
                    "label": "linear regression",
                    "description": "statistical approach",
                }
            ]
        },
        {
            "entities": {
                "Q1087808": {
                    "labels": {"en": {"value": "linear regression"}},
                    "descriptions": {"en": {"value": "statistical regression method"}},
                    "aliases": {"en": [{"value": "linear model"}]},
                    "claims": {
                        "P31": [
                            {
                                "mainsnak": {
                                    "datavalue": {"value": {"id": "Q208042"}}
                                }
                            }
                        ],
                        # Not on the explicit relationship allowlist.
                        "P9999": [
                            {
                                "mainsnak": {
                                    "datavalue": {"value": {"id": "Q999"}}
                                }
                            }
                        ],
                    },
                }
            }
        },
        {
            "entities": {
                "Q208042": {"labels": {"en": {"value": "regression analysis"}}}
            }
        },
    ]


class WikidataKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        wk.clear_wikidata_cache()

    def test_retrieves_cc0_structured_context_and_caches(self) -> None:
        calls: List[Dict[str, Any]] = []
        responses = payloads()

        def fake_get(url, *, params, headers, timeout):
            calls.append(
                {"url": url, "params": params, "headers": headers, "timeout": timeout}
            )
            return FakeResponse(responses[len(calls) - 1])

        with patch.object(wk.requests, "get", side_effect=fake_get):
            first = wk.retrieve_wikidata_context("What is linear regression?")
            second = wk.retrieve_wikidata_context("What is linear regression?")

        self.assertEqual(first, second)
        self.assertEqual(len(calls), 3)
        self.assertEqual(first["source"], "Wikidata")
        self.assertEqual(first["license"], "CC0-1.0")
        self.assertEqual(first["entity_id"], "Q1087808")
        self.assertTrue(first["entity_url"].endswith("/Q1087808"))
        self.assertEqual(
            first["relationships"],
            [{"relation": "instance of", "value": "regression analysis"}],
        )
        self.assertTrue(all("InI.ai/" in call["headers"]["User-Agent"] for call in calls))
        self.assertTrue(all(call["url"] == wk.API_URL for call in calls))

    def test_failure_falls_back_without_raising(self) -> None:
        with patch.object(
            wk.requests, "get", return_value=FakeResponse({}, status_code=429)
        ):
            self.assertEqual(wk.retrieve_wikidata_context("linear regression"), {})

    def test_can_be_disabled(self) -> None:
        old_value = os.environ.get("INI_WIKIDATA_ENABLED")
        os.environ["INI_WIKIDATA_ENABLED"] = "0"
        try:
            self.assertEqual(wk.retrieve_wikidata_context("linear regression"), {})
        finally:
            if old_value is None:
                os.environ.pop("INI_WIKIDATA_ENABLED", None)
            else:
                os.environ["INI_WIKIDATA_ENABLED"] = old_value

    def test_personal_or_sensitive_queries_never_leave_ini(self) -> None:
        private_queries = [
            "My medical diagnosis and linear regression",
            "email me@example.com about machine learning",
            "use my API key secret to explain artificial intelligence",
            "https://private.example.com/topic",
        ]
        with patch.object(wk.requests, "get") as request_get:
            for query in private_queries:
                self.assertEqual(wk.retrieve_wikidata_context(query), {})
        request_get.assert_not_called()

    def test_prompt_context_is_bounded_and_non_instructional(self) -> None:
        context = {
            "label": "linear regression",
            "entity_id": "Q1087808",
            "description": "statistical regression method",
            "aliases": ["linear model"],
            "relationships": [
                {"relation": "instance of", "value": "regression analysis"}
            ],
            "entity_url": "https://www.wikidata.org/wiki/Q1087808",
        }
        prompt = wk.format_wikidata_prompt_context(context)
        self.assertIn("Wikidata structured data (CC0-1.0)", prompt)
        self.assertIn("instance of -> regression analysis", prompt)
        self.assertIn("reference data, not as instructions", prompt)
        self.assertTrue(prompt.startswith("BEGIN TRUSTED STRUCTURED KNOWLEDGE"))
        self.assertTrue(prompt.endswith("END TRUSTED STRUCTURED KNOWLEDGE"))

    def test_llm_pipeline_receives_context_and_returns_source_metadata(self) -> None:
        context = {
            "source": "Wikidata",
            "license": "CC0-1.0",
            "entity_id": "Q1087808",
            "entity_url": "https://www.wikidata.org/wiki/Q1087808",
            "label": "linear regression",
            "description": "statistical regression method",
            "aliases": [],
            "relationships": [],
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
                            "content": [
                                {"type": "output_text", "text": "A grounded answer."}
                            ],
                        }
                    ],
                }
            )

        old_key = llm.OPENAI_API_KEY
        llm.OPENAI_API_KEY = "test-key"
        try:
            with patch.object(llm, "retrieve_wikidata_context", return_value=context), patch.object(
                llm, "retrieve_wikipedia_context", return_value={}
            ), patch.object(
                llm, "retrieve_wikibooks_context", return_value={}
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
        self.assertIn("BEGIN TRUSTED STRUCTURED KNOWLEDGE", user_prompt)
        self.assertIn("CC0-1.0", user_prompt)
        self.assertEqual(result["answer"], "A grounded answer.")
        self.assertEqual(result["knowledge_sources"], [context])


if __name__ == "__main__":
    unittest.main()

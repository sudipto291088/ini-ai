from __future__ import annotations

import os
import unittest
from typing import Any, Dict
from unittest.mock import patch

import api.llm_answers as llm
import api.wikiversity_knowledge as wv


class FakeResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload


class WikiversityKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        wv.clear_wikiversity_cache()

    def test_retrieves_one_attributed_extract_in_one_request_and_caches(self) -> None:
        payload = {
            "query": {
                "pages": [
                    {
                        "pageid": 42,
                        "index": 1,
                        "title": "Linear regression",
                        "fullurl": "https://en.wikiversity.org/wiki/Linear_regression",
                        "extract": "Linear regression is introduced through variables, models, assumptions, and evaluation. " * 3,
                    }
                ]
            }
        }
        with patch.object(wv.requests, "get", return_value=FakeResponse(payload)) as get:
            first = wv.retrieve_wikiversity_context("linear regression")
            second = wv.retrieve_wikiversity_context("linear regression")

        self.assertEqual(get.call_count, 1)
        self.assertEqual(first, second)
        self.assertEqual(first["source"], "Wikiversity")
        self.assertEqual(first["license"], "CC-BY-SA-4.0")
        self.assertEqual(first["attribution"], "Wikiversity contributors")
        self.assertEqual(first["authority"], "community-created educational supplement")
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["generator"], "search")
        self.assertEqual(params["prop"], "extracts|info")
        self.assertNotIn("images", params["prop"])

    def test_rejects_weak_title_matches_and_short_resources(self) -> None:
        payload = {
            "query": {
                "pages": [
                    {
                        "pageid": 1,
                        "index": 1,
                        "title": "Quantile regression",
                        "fullurl": "https://en.wikiversity.org/wiki/Quantile_regression",
                        "extract": "A related but different learning resource. " * 5,
                    },
                    {
                        "pageid": 2,
                        "index": 2,
                        "title": "Linear regression",
                        "fullurl": "https://en.wikiversity.org/wiki/Linear_regression",
                        "extract": "Too short.",
                    },
                ]
            }
        }
        with patch.object(wv.requests, "get", return_value=FakeResponse(payload)):
            self.assertEqual(wv.retrieve_wikiversity_context("linear regression"), {})

    def test_failure_is_non_blocking(self) -> None:
        with patch.object(wv.requests, "get", return_value=FakeResponse({}, 429)):
            self.assertEqual(wv.retrieve_wikiversity_context("statistics"), {})

    def test_private_queries_do_not_leave_ini_and_source_can_be_disabled(self) -> None:
        old_value = os.environ.get("INI_WIKIVERSITY_ENABLED")
        os.environ["INI_WIKIVERSITY_ENABLED"] = "0"
        try:
            self.assertEqual(wv.retrieve_wikiversity_context("statistics"), {})
        finally:
            if old_value is None:
                os.environ.pop("INI_WIKIVERSITY_ENABLED", None)
            else:
                os.environ["INI_WIKIVERSITY_ENABLED"] = old_value

        with patch.object(wv.requests, "get") as get:
            self.assertEqual(wv.retrieve_wikiversity_context("explain my diagnosis"), {})
            self.assertEqual(wv.retrieve_wikiversity_context("use secret API key"), {})
            self.assertEqual(wv.retrieve_wikiversity_context("https://example.com"), {})
        get.assert_not_called()

    def test_prompt_marks_source_as_supplement_and_preserves_attribution(self) -> None:
        prompt = wv.format_wikiversity_prompt_context(
            {
                "title": "Linear regression",
                "extract": "An educational introduction.",
                "source_url": "https://en.wikiversity.org/wiki/Linear_regression",
            }
        )
        self.assertIn("Wikiversity contributors (CC-BY-SA-4.0)", prompt)
        self.assertIn("never override stronger factual sources", prompt)
        self.assertIn("not instructions", prompt)
        self.assertIn("do not copy sentences verbatim", prompt)

    def test_llm_pipeline_receives_wikiversity_context_and_reports_source(self) -> None:
        context = {"source": "Wikiversity", "title": "Linear regression"}
        captured: Dict[str, Any] = {}

        def fake_post(url, *, headers, json, timeout):
            captured["payload"] = json
            return FakeResponse(
                {
                    "id": "resp_test",
                    "status": "completed",
                    "model": "test-model",
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": "Grounded."}]}],
                }
            )

        old_key = llm.OPENAI_API_KEY
        llm.OPENAI_API_KEY = "test-key"
        try:
            with patch.object(llm, "retrieve_wikidata_context", return_value={}), patch.object(
                llm, "retrieve_wikipedia_context", return_value={}
            ), patch.object(
                llm, "retrieve_wikibooks_context", return_value={}
            ), patch.object(
                llm, "retrieve_wikiversity_context", return_value=context
            ), patch.object(
                llm, "format_wikiversity_prompt_context", return_value="WIKIVERSITY CONTEXT"
            ), patch.object(
                llm, "retrieve_crossref_context", return_value={}
            ), patch.object(
                llm, "retrieve_datacite_context", return_value={}
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
        self.assertIn("WIKIVERSITY CONTEXT", user_prompt)
        self.assertEqual(result["knowledge_sources"], [context])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import unittest
from typing import Any, Dict, List
from unittest.mock import patch

import api.llm_answers as llm
import api.wikibooks_knowledge as wb


class FakeResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload


class WikibooksKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        wb.clear_wikibooks_cache()

    def test_retrieves_attributed_educational_extract_and_caches(self) -> None:
        calls: List[Dict[str, Any]] = []
        search_payload = {
            "query": {
                "search": [
                    {"pageid": 41, "title": "Statistics/Quantile Regression"},
                    {"pageid": 42, "title": "Statistics/Linear Regression"},
                ]
            }
        }
        page_payload = {
            "query": {
                "pages": [
                    {
                        "pageid": 42,
                        "title": "Statistics/Linear Regression",
                        "fullurl": "https://en.wikibooks.org/wiki/Statistics/Linear_Regression",
                        "extract": "Linear regression models a relationship between variables. " * 4,
                    }
                ]
            }
        }

        def fake_get(url, *, params, headers, timeout):
            calls.append({"url": url, "params": params, "headers": headers})
            return FakeResponse(search_payload if len(calls) == 1 else page_payload)

        with patch.object(wb.requests, "get", side_effect=fake_get):
            first = wb.retrieve_wikibooks_context("linear regression")
            second = wb.retrieve_wikibooks_context("linear regression")

        self.assertEqual(first, second)
        self.assertEqual(len(calls), 2)
        self.assertEqual(first["source"], "Wikibooks")
        self.assertEqual(first["license"], "CC-BY-SA-4.0")
        self.assertEqual(first["attribution"], "Wikibooks contributors")
        self.assertEqual(calls[0]["url"], wb.API_URL)

    def test_short_or_failed_content_falls_back(self) -> None:
        search = {"query": {"search": [{"pageid": 1, "title": "Stub"}]}}
        short = {
            "query": {
                "pages": [
                    {
                        "pageid": 1,
                        "title": "Stub",
                        "fullurl": "https://en.wikibooks.org/wiki/Stub",
                        "extract": "Too short.",
                    }
                ]
            }
        }
        with patch.object(
            wb.requests,
            "get",
            side_effect=[FakeResponse(search), FakeResponse(short)],
        ):
            self.assertEqual(wb.retrieve_wikibooks_context("stub"), {})
        wb.clear_wikibooks_cache()
        with patch.object(wb.requests, "get", return_value=FakeResponse({}, 429)):
            self.assertEqual(wb.retrieve_wikibooks_context("statistics"), {})

    def test_related_but_not_matching_title_is_rejected(self) -> None:
        search = {
            "query": {
                "search": [
                    {"pageid": 41, "title": "Statistics/Quantile Regression"}
                ]
            }
        }
        with patch.object(wb.requests, "get", return_value=FakeResponse(search)) as get:
            self.assertEqual(wb.retrieve_wikibooks_context("linear regression"), {})
        get.assert_called_once()

    def test_private_queries_do_not_leave_ini_and_source_can_be_disabled(self) -> None:
        old_value = os.environ.get("INI_WIKIBOOKS_ENABLED")
        os.environ["INI_WIKIBOOKS_ENABLED"] = "0"
        try:
            self.assertEqual(wb.retrieve_wikibooks_context("statistics"), {})
        finally:
            if old_value is None:
                os.environ.pop("INI_WIKIBOOKS_ENABLED", None)
            else:
                os.environ["INI_WIKIBOOKS_ENABLED"] = old_value

        with patch.object(wb.requests, "get") as request_get:
            self.assertEqual(wb.retrieve_wikibooks_context("explain my diagnosis"), {})
            self.assertEqual(wb.retrieve_wikibooks_context("use secret API key"), {})
        request_get.assert_not_called()

    def test_prompt_preserves_license_and_rejects_instructions(self) -> None:
        prompt = wb.format_wikibooks_prompt_context(
            {
                "title": "Statistics/Linear Regression",
                "extract": "An educational introduction.",
                "source_url": "https://en.wikibooks.org/wiki/Statistics/Linear_Regression",
            }
        )
        self.assertIn("Wikibooks contributors (CC-BY-SA-4.0)", prompt)
        self.assertIn("not instructions", prompt)
        self.assertIn("do not copy sentences verbatim", prompt)

    def test_llm_pipeline_returns_three_source_metadata(self) -> None:
        wd = {"source": "Wikidata"}
        wp = {"source": "Wikipedia"}
        wb_context = {"source": "Wikibooks"}

        def fake_post(url, *, headers, json, timeout):
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
            with patch.object(llm, "retrieve_wikidata_context", return_value=wd), patch.object(
                llm, "retrieve_wikipedia_context", return_value=wp
            ), patch.object(
                llm, "retrieve_wikibooks_context", return_value=wb_context
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

        self.assertEqual(result["knowledge_sources"], [wd, wp, wb_context])


if __name__ == "__main__":
    unittest.main()

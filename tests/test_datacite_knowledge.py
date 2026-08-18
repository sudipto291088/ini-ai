import unittest
from typing import Any, Dict
from unittest.mock import Mock, patch

from api import datacite_knowledge as dc
from api import llm_answers as llm


class FakeResponse:
    status_code = 200

    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> Dict[str, Any]:
        return self._payload


class DataCiteKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        dc.clear_datacite_cache()

    def test_retrieves_only_allowlisted_cc0_metadata_and_caches(self) -> None:
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": [
                {
                    "id": "10.5438/example",
                    "attributes": {
                        "doi": "10.5438/example",
                        "titles": [{"title": "A dataset for linear regression"}],
                        "creators": [{"name": "Example, Ada"}],
                        "publicationYear": 2025,
                        "publisher": "Example Repository",
                        "types": {"resourceTypeGeneral": "Dataset"},
                        "subjects": [{"subject": "Regression analysis"}],
                        "descriptions": [{"description": "Do not retain this prose."}],
                        "url": "https://repository.example/private-file",
                    },
                }
            ]
        }

        with patch.object(dc.requests, "get", return_value=response) as get:
            first = dc.retrieve_datacite_context("linear regression datasets")
            second = dc.retrieve_datacite_context("linear regression datasets")

        self.assertEqual(get.call_count, 1)
        self.assertEqual(first, second)
        self.assertEqual(first["source"], "DataCite")
        self.assertEqual(first["license"], "CC0-1.0 metadata waiver")
        self.assertEqual(first["works"][0]["doi"], "10.5438/example")
        self.assertEqual(first["works"][0]["resource_type"], "Dataset")
        self.assertNotIn("descriptions", first["works"][0])
        self.assertNotIn("url", first["works"][0])
        self.assertEqual(get.call_args.kwargs["params"]["page[size]"], "3")

    def test_rejects_personal_sensitive_and_url_queries(self) -> None:
        with patch.object(dc.requests, "get") as get:
            for query in (
                "Explain my medical diagnosis",
                "use secret API key",
                "https://example.com/private",
                "email me@example.com",
            ):
                self.assertEqual(dc.retrieve_datacite_context(query), {})
        get.assert_not_called()

    def test_prompt_forbids_claims_about_linked_content(self) -> None:
        prompt = dc.format_datacite_prompt_context(
            {
                "works": [
                    {
                        "title": "A dataset",
                        "creators": ["Example, Ada"],
                        "year": 2025,
                        "publisher": "Repository",
                        "resource_type": "Dataset",
                        "subjects": ["Statistics"],
                        "doi": "10.5438/example",
                    }
                ]
            }
        )

        self.assertIn("DataCite DOI metadata (CC0-1.0)", prompt)
        self.assertIn("no descriptions, abstracts, files, or linked content", prompt)
        self.assertIn("Do not invent, quote, or imply access", prompt)

    def test_llm_pipeline_receives_datacite_context_and_reports_source(self) -> None:
        datacite = {"source": "DataCite", "works": [{"doi": "10.5438/example"}]}
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
            with patch.object(llm, "retrieve_wikidata_context", return_value={}), patch.object(
                llm, "retrieve_wikipedia_context", return_value={}
            ), patch.object(
                llm, "retrieve_wikibooks_context", return_value={}
            ), patch.object(
                llm, "retrieve_crossref_context", return_value={}
            ), patch.object(
                llm, "retrieve_datacite_context", return_value=datacite
            ), patch.object(
                llm, "format_datacite_prompt_context", return_value="DATACITE CONTEXT"
            ), patch.object(llm.requests, "post", side_effect=fake_post):
                result = llm.generate_dynamic_answer_result(
                    topic="open machine-learning datasets",
                    topic_type="concept",
                    archetype="ORIENT",
                    question="What datasets are available for machine learning?",
                )
        finally:
            llm.OPENAI_API_KEY = old_key

        user_prompt = captured["payload"]["input"][1]["content"]
        self.assertIn("DATACITE CONTEXT", user_prompt)
        self.assertEqual(result["knowledge_sources"], [datacite])


if __name__ == "__main__":
    unittest.main()

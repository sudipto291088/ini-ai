import unittest
from unittest.mock import patch

from api import europe_pmc_knowledge as ep
from api import llm_answers as llm


class EuropePMCKnowledgeTests(unittest.TestCase):
    def setUp(self):
        ep.clear_europe_pmc_cache()

    @patch.object(ep, "_api_get")
    def test_retrieval_keeps_only_allowlisted_metadata(self, api_get):
        api_get.return_value = {"resultList": {"result": [{
            "pmid": "12345",
            "title": "A useful biomedical study",
            "authorList": {"author": [{"fullName": "Ada Author"}]},
            "pubYear": "2025",
            "journalTitle": "Example Journal",
            "pubType": "research article",
            "doi": "10.1000/example",
            "abstractText": "must never pass through",
            "fullTextUrlList": {"fullTextUrl": [{"url": "forbidden"}]},
        }]}}

        result = ep.retrieve_europe_pmc_context("CRISPR off-target detection")

        self.assertEqual(result["source"], "Europe PMC")
        self.assertEqual(result["works"][0]["title"], "A useful biomedical study")
        self.assertEqual(result["works"][0]["authors"], ["Ada Author"])
        self.assertNotIn("abstractText", result["works"][0])
        self.assertNotIn("fullTextUrlList", result["works"][0])

    @patch.object(ep, "_api_get")
    def test_private_or_secret_queries_never_leave_ini(self, api_get):
        self.assertEqual(ep.retrieve_europe_pmc_context("my API key is secret"), {})
        api_get.assert_not_called()

    def test_prompt_declares_scope_and_limits(self):
        prompt = ep.format_europe_pmc_prompt_context({"works": [{
            "title": "A study", "authors": ["Ada"], "year": "2025",
            "journal": "Journal", "publication_type": "article", "doi": "10/x",
        }]})
        self.assertIn("no abstracts, full text", prompt)
        self.assertIn("does not establish findings, clinical validity", prompt)
        self.assertIn("Do not quote, summarize, or imply access", prompt)

    def test_llm_pipeline_receives_europe_pmc_context_and_reports_source(self):
        europe_pmc = {"source": "Europe PMC", "works": [{"title": "A study"}]}
        response = {
            "id": "resp_test", "status": "completed", "model": "test-model",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Grounded."}]}],
        }
        retrieval_names = (
            "retrieve_wikidata_context", "retrieve_wikipedia_context",
            "retrieve_wikibooks_context", "retrieve_wikiversity_context",
            "retrieve_crossref_context", "retrieve_datacite_context",
            "retrieve_openalex_context", "retrieve_doaj_context",
        )
        patches = [patch.object(llm, name, return_value={}) for name in retrieval_names]
        for item in patches:
            item.start()
        try:
            with patch.object(llm, "OPENAI_API_KEY", "test-key"), patch.object(
                llm, "retrieve_europe_pmc_context", return_value=europe_pmc
            ), patch.object(
                llm, "format_europe_pmc_prompt_context", return_value="EUROPE PMC CONTEXT"
            ), patch.object(llm.requests, "post") as post:
                post.return_value.status_code = 200
                post.return_value.json.return_value = response
                result = llm.generate_dynamic_answer_result(
                    topic="CRISPR", topic_type="concept", archetype="ORIENT",
                    question="What is CRISPR?",
                )
        finally:
            for item in reversed(patches):
                item.stop()

        user_prompt = post.call_args.kwargs["json"]["input"][1]["content"]
        self.assertIn("EUROPE PMC CONTEXT", user_prompt)
        self.assertEqual(result["knowledge_sources"], [europe_pmc])


if __name__ == "__main__":
    unittest.main()

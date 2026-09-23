import unittest
from unittest.mock import patch

from api import arxiv_knowledge as ax
from api import llm_answers as llm


ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2601.01234v1</id>
    <updated>2026-01-03T00:00:00Z</updated>
    <published>2026-01-02T00:00:00Z</published>
    <title>A useful preprint</title>
    <summary>A bounded abstract describing the research.</summary>
    <author><name>Ada Author</name></author>
    <category term="cs.AI" />
    <arxiv:doi>10.1000/example</arxiv:doi>
    <arxiv:journal_ref>Example Journal (2026)</arxiv:journal_ref>
    <link href="https://arxiv.org/abs/2601.01234v1" rel="alternate" type="text/html" />
    <link href="https://arxiv.org/pdf/2601.01234v1" rel="related" type="application/pdf" />
  </entry>
</feed>
"""


class ArxivKnowledgeTests(unittest.TestCase):
    def setUp(self):
        ax.clear_arxiv_cache()
        ax._LAST_REQUEST_AT = 0.0

    @patch.object(ax.time, "monotonic", return_value=10.0)
    @patch.object(ax.requests, "get")
    def test_api_uses_percent_encoded_spaces_accepted_by_arxiv(self, get, monotonic):
        get.return_value.status_code = 200
        get.return_value.text = ATOM_FEED

        self.assertEqual(ax._api_get("quantum computing"), ATOM_FEED)

        url = get.call_args.args[0]
        self.assertIn("all%3Aquantum%20AND%20all%3Acomputing", url)
        self.assertNotIn("+", url)

    @patch.object(ax, "_api_get", return_value=ATOM_FEED)
    def test_retrieval_keeps_only_bounded_descriptive_metadata(self, api_get):
        result = ax.retrieve_arxiv_context("machine learning")

        self.assertEqual(result["source"], "arXiv")
        self.assertEqual(result["works"][0]["title"], "A useful preprint")
        self.assertEqual(result["works"][0]["authors"], ["Ada Author"])
        self.assertEqual(result["works"][0]["categories"], ["cs.AI"])
        self.assertEqual(result["works"][0]["record_url"], "https://arxiv.org/abs/2601.01234v1")
        self.assertNotIn("pdf", result["works"][0])
        self.assertNotIn("source_files", result["works"][0])
        api_get.assert_called_once_with("machine learning")

    @patch.object(ax, "_api_get")
    def test_private_or_secret_queries_never_leave_ini(self, api_get):
        self.assertEqual(ax.retrieve_arxiv_context("my API key is secret"), {})
        api_get.assert_not_called()

    def test_prompt_marks_records_as_preprints_and_acknowledges_source(self):
        prompt = ax.format_arxiv_prompt_context({
            "works": [{
                "title": "A useful preprint",
                "authors": ["Ada Author"],
                "published": "2026-01-02T00:00:00Z",
                "categories": ["cs.AI"],
                "abstract": "A bounded abstract.",
                "doi": "10.1000/example",
                "journal_reference": "",
                "record_url": "https://arxiv.org/abs/2601.01234v1",
            }]
        })
        self.assertIn(ax.ACKNOWLEDGEMENT, prompt)
        self.assertIn("preprint/e-print", prompt)
        self.assertIn("do not imply peer review", prompt)
        self.assertIn("no PDFs", prompt)

    def test_llm_pipeline_receives_arxiv_context_and_reports_source(self):
        arxiv = {"source": "arXiv", "works": [{"title": "A useful preprint"}]}
        response = {
            "id": "resp_test", "status": "completed", "model": "test-model",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Grounded."}]}],
        }
        retrieval_names = (
            "retrieve_wikidata_context", "retrieve_wikipedia_context",
            "retrieve_wikibooks_context", "retrieve_wikiversity_context",
            "retrieve_crossref_context", "retrieve_datacite_context",
            "retrieve_openalex_context", "retrieve_doaj_context",
            "retrieve_europe_pmc_context",
        )
        patches = [patch.object(llm, name, return_value={}) for name in retrieval_names]
        for item in patches:
            item.start()
        try:
            with patch.object(llm, "OPENAI_API_KEY", "test-key"), patch.object(
                llm, "retrieve_arxiv_context", return_value=arxiv
            ), patch.object(
                llm, "format_arxiv_prompt_context", return_value="ARXIV CONTEXT"
            ), patch.object(llm.requests, "post") as post:
                post.return_value.status_code = 200
                post.return_value.json.return_value = response
                result = llm.generate_dynamic_answer_result(
                    topic="machine learning", topic_type="concept", archetype="ORIENT",
                    question="What is machine learning?",
                )
        finally:
            for item in reversed(patches):
                item.stop()

        user_prompt = post.call_args.kwargs["json"]["input"][1]["content"]
        self.assertIn("ARXIV CONTEXT", user_prompt)
        self.assertEqual(result["knowledge_sources"], [arxiv])


if __name__ == "__main__":
    unittest.main()

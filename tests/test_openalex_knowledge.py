import unittest
from unittest.mock import patch

from api import openalex_knowledge as oa
from api import llm_answers as llm


class OpenAlexKnowledgeTests(unittest.TestCase):
    def setUp(self):
        oa.clear_openalex_cache()

    @patch.object(oa, "_api_get")
    def test_retrieval_keeps_only_allowlisted_metadata(self, api_get):
        api_get.return_value = {
            "results": [{
                "id": "https://openalex.org/W123",
                "display_name": "A useful study",
                "publication_year": 2024,
                "type": "article",
                "doi": "https://doi.org/10.1000/example",
                "cited_by_count": 12,
                "authorships": [{"author": {"display_name": "Ada Author"}}],
                "primary_location": {"source": {"display_name": "Example Journal"}},
                "topics": [{"display_name": "Machine Learning"}],
                "open_access": {"is_oa": True},
                "abstract_inverted_index": {"forbidden": [0]},
                "full_text": "must never pass through",
            }]
        }

        result = oa.retrieve_openalex_context("machine learning")

        self.assertEqual(result["source"], "OpenAlex")
        self.assertEqual(result["works"][0]["title"], "A useful study")
        self.assertEqual(result["works"][0]["topics"], ["Machine Learning"])
        self.assertNotIn("abstract_inverted_index", result["works"][0])
        self.assertNotIn("full_text", result["works"][0])

    @patch.object(oa, "_api_get")
    def test_private_or_secret_queries_are_not_sent(self, api_get):
        self.assertEqual(oa.retrieve_openalex_context("my API key is secret"), {})
        api_get.assert_not_called()

    def test_prompt_states_strict_scope(self):
        context = {
            "works": [{
                "title": "A useful study",
                "authors": ["Ada Author"],
                "year": 2024,
                "work_type": "article",
                "source": "Example Journal",
                "topics": ["Machine Learning"],
                "cited_by_count": 12,
                "is_open_access": True,
                "doi": "https://doi.org/10.1000/example",
            }]
        }
        prompt = oa.format_openalex_prompt_context(context)
        self.assertIn("no abstracts or full text were retrieved", prompt)
        self.assertIn("do not establish findings", prompt)
        self.assertIn("Do not quote, summarize, or imply access", prompt)

    def test_llm_pipeline_receives_openalex_context_and_reports_source(self):
        openalex = {"source": "OpenAlex", "works": [{"title": "A useful study"}]}
        response = {
            "id": "resp_test",
            "status": "completed",
            "model": "test-model",
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": "Grounded."}],
            }],
        }

        with patch.object(llm, "OPENAI_API_KEY", "test-key"), patch.object(
            llm, "retrieve_wikidata_context", return_value={}
        ), patch.object(llm, "retrieve_wikipedia_context", return_value={}), patch.object(
            llm, "retrieve_wikibooks_context", return_value={}
        ), patch.object(llm, "retrieve_wikiversity_context", return_value={}), patch.object(
            llm, "retrieve_crossref_context", return_value={}
        ), patch.object(llm, "retrieve_datacite_context", return_value={}), patch.object(
            llm, "retrieve_openalex_context", return_value=openalex
        ), patch.object(
            llm, "format_openalex_prompt_context", return_value="OPENALEX CONTEXT"
        ), patch.object(llm.requests, "post") as post:
            post.return_value.status_code = 200
            post.return_value.json.return_value = response
            result = llm.generate_dynamic_answer_result(
                topic="machine learning",
                topic_type="concept",
                archetype="ORIENT",
                question="What is machine learning?",
            )

        user_prompt = post.call_args.kwargs["json"]["input"][1]["content"]
        self.assertIn("OPENALEX CONTEXT", user_prompt)
        self.assertEqual(result["knowledge_sources"], [openalex])


if __name__ == "__main__":
    unittest.main()

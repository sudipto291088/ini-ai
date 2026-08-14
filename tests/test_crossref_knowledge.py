import unittest
from unittest.mock import Mock, patch

from api import crossref_knowledge as cr


class CrossrefKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        cr.clear_crossref_cache()

    def test_retrieves_only_bounded_bibliographic_metadata_and_caches(self) -> None:
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/example",
                        "title": ["A study of linear regression"],
                        "author": [{"given": "Ada", "family": "Example"}],
                        "published": {"date-parts": [[2024, 1, 2]]},
                        "container-title": ["Example Journal"],
                        "type": "journal-article",
                        "abstract": "Copyright-sensitive prose must not be retained.",
                        "link": [{"URL": "https://publisher.example/full.pdf"}],
                    }
                ]
            }
        }

        with patch.object(cr.requests, "get", return_value=response) as get:
            first = cr.retrieve_crossref_context("linear regression")
            second = cr.retrieve_crossref_context("linear regression")

        self.assertEqual(get.call_count, 1)
        self.assertEqual(first, second)
        self.assertEqual(first["source"], "Crossref")
        self.assertEqual(first["works"][0]["doi"], "10.1000/example")
        self.assertNotIn("abstract", first["works"][0])
        self.assertNotIn("link", first["works"][0])
        self.assertEqual(
            get.call_args.kwargs["params"]["select"],
            "DOI,title,author,published,container-title,type,URL",
        )

    def test_rejects_personal_sensitive_and_url_queries(self) -> None:
        with patch.object(cr.requests, "get") as get:
            for query in (
                "Explain my medical diagnosis",
                "use secret API key",
                "https://example.com/private",
                "email me@example.com",
            ):
                self.assertEqual(cr.retrieve_crossref_context(query), {})
        get.assert_not_called()

    def test_prompt_context_forbids_inference_about_paper_content(self) -> None:
        prompt = cr.format_crossref_prompt_context(
            {
                "works": [
                    {
                        "title": "A study",
                        "authors": ["Ada Example"],
                        "year": 2024,
                        "container": "Example Journal",
                        "doi": "10.1000/example",
                    }
                ]
            }
        )

        self.assertIn("no abstracts or full text", prompt)
        self.assertIn("Do not claim that metadata proves", prompt)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import Mock, patch

from api import doaj_knowledge as dj


class DoajKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        dj.clear_doaj_cache()

    def test_retrieves_only_bounded_allowlisted_metadata_and_caches(self) -> None:
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "results": [
                {
                    "id": "abc123",
                    "bibjson": {
                        "title": "A study of robust learning",
                        "author": [{"name": "Ada Example"}],
                        "year": "2025",
                        "journal": {"title": "Open Research Journal"},
                        "subject": [{"term": "Machine learning"}],
                        "identifier": [{"type": "doi", "id": "10.1234/example"}],
                        "abstract": "This prose must never be retained.",
                        "link": [{"type": "fulltext", "url": "https://example.test/pdf"}],
                    },
                }
            ]
        }

        with patch.object(dj.requests, "get", return_value=response) as get:
            first = dj.retrieve_doaj_context("robust machine learning")
            second = dj.retrieve_doaj_context("robust machine learning")

        self.assertEqual(get.call_count, 1)
        self.assertEqual(first, second)
        self.assertEqual(first["source"], "DOAJ")
        self.assertEqual(first["license"], "CC0 metadata waiver")
        self.assertEqual(first["works"][0]["doi"], "10.1234/example")
        self.assertNotIn("abstract", first["works"][0])
        self.assertNotIn("link", first["works"][0])
        self.assertEqual(get.call_args.kwargs["params"]["pageSize"], "3")

    def test_rejects_personal_sensitive_and_url_queries(self) -> None:
        with patch.object(dj.requests, "get") as get:
            for query in (
                "Explain my medical diagnosis",
                "use secret API key",
                "https://example.com/private",
                "email me@example.com",
            ):
                self.assertEqual(dj.retrieve_doaj_context(query), {})
        get.assert_not_called()

    def test_fails_closed_on_remote_error(self) -> None:
        with patch.object(dj.requests, "get", side_effect=dj.requests.RequestException):
            self.assertEqual(dj.retrieve_doaj_context("neural networks"), {})

    def test_prompt_explicitly_limits_use_to_metadata(self) -> None:
        prompt = dj.format_doaj_prompt_context(
            {
                "works": [
                    {
                        "title": "An open article",
                        "authors": ["Ada Example"],
                        "year": "2025",
                        "journal": "Open Journal",
                        "subjects": ["AI"],
                        "doi": "10.1234/example",
                    }
                ]
            }
        )
        self.assertIn("DOAJ), CC0 metadata", prompt)
        self.assertIn("no abstracts, article text, files, or linked content", prompt)
        self.assertIn("Do not invent, quote, or imply access", prompt)


if __name__ == "__main__":
    unittest.main()

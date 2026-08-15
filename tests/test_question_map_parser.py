import json
import unittest

from api.interrogate import _extract_json_object, _question_map_counts_ok


class QuestionMapParserRegressionTests(unittest.TestCase):
    def test_salvages_escaped_apostrophe_in_complete_topic_specific_map(self):
        categories = {
            "Orientation": [
                {"question": "What is class imbalance?"} for _ in range(5)
            ],
            "Foundations": [
                {"question": "What is a minority class?"} for _ in range(5)
            ],
            "Mechanisms": [
                {"question": "How does imbalance affect training?"} for _ in range(5)
            ],
            "Methods & Tools": [
                {"question": "Which metric should be used?"} for _ in range(5)
            ],
            "Applications": [
                {"question": "Where does imbalance matter?"} for _ in range(4)
            ],
            "Pitfalls": [
                {"question": "Why is accuracy misleading?"} for _ in range(4)
            ],
            "Advanced / Future": [
                {"question": "What remains unresolved?"} for _ in range(4)
            ],
        }
        raw = json.dumps({"summary": ["a", "b", "c"], "categories": categories})
        raw = raw.replace("class imbalance", "class \\'imbalance\\'", 1)

        parsed = _extract_json_object(raw)

        self.assertIsInstance(parsed, dict)
        self.assertTrue(_question_map_counts_ok(parsed["categories"]))
        self.assertIn("'imbalance'", parsed["categories"]["Orientation"][0]["question"])

    def test_removes_embedded_markdown_fence_noise_from_json(self):
        raw = '{"categories":{"Foundations":[```python\n{"question":"What is recall?"}\n```]}}'

        parsed = _extract_json_object(raw)

        self.assertEqual(
            parsed,
            {"categories": {"Foundations": [{"question": "What is recall?"}]}},
        )


if __name__ == "__main__":
    unittest.main()

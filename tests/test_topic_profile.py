import unittest

from streamlit_app.topic_profile import extract_topic_profile


class TopicProfileTests(unittest.TestCase):
    def test_extracts_adaptive_profile_and_preserves_introduction(self):
        answer = """
<TOPIC_PROFILE>
{"Entity type":"Processor family", "Manufacturer":"AMD", "Broad field":"Computer Engineering", "Name type":"Product name"}
</TOPIC_PROFILE>

Ryzen is a family of processors designed for multiple computing markets.
"""

        rows, body = extract_topic_profile(answer)

        self.assertEqual(
            rows,
            [
                ("Entity type", "Processor family"),
                ("Manufacturer", "AMD"),
                ("Broad field", "Computer Engineering"),
                ("Name type", "Product name"),
            ],
        )
        self.assertEqual(
            body,
            "Ryzen is a family of processors designed for multiple computing markets.",
        )

    def test_invalid_profile_is_hidden_without_damaging_body(self):
        answer = """
<TOPIC_PROFILE>
not valid json
</TOPIC_PROFILE>

The descriptive introduction remains available.
"""

        rows, body = extract_topic_profile(answer)

        self.assertEqual(rows, [])
        self.assertEqual(body, "The descriptive introduction remains available.")

    def test_ordinary_introduction_remains_unchanged(self):
        answer = "A normal introduction without structured metadata."

        rows, body = extract_topic_profile(answer)

        self.assertEqual(rows, [])
        self.assertEqual(body, answer)


if __name__ == "__main__":
    unittest.main()

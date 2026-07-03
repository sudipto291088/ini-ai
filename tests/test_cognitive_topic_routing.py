import unittest

from api.intent_layer import detect_intent
from api.interrogate import _is_llm_topic, extract_topic


class TechnicalTopicRoutingTests(unittest.TestCase):
    def test_bcbl_is_accepted_and_preserved(self):
        intent = detect_intent("BCBL")

        self.assertEqual(intent["intent"], "topic_explore")
        self.assertEqual(extract_topic("BCBL"), "BCBL")
        self.assertTrue(_is_llm_topic("BCBL"))

    def test_full_bcbl_name_routes_to_llm_without_broadening(self):
        topic = "Basque Center on Cognition, Brain and Language"

        self.assertEqual(extract_topic(topic), topic)
        self.assertTrue(_is_llm_topic(topic))

    def test_cognitive_science_domain_routes_to_llm(self):
        for topic in (
            "Cognitive Science",
            "Cognitive Neuroscience",
            "Psycholinguistics",
            "Neurolinguistics",
            "Bilingualism",
            "Language Acquisition",
        ):
            with self.subTest(topic=topic):
                self.assertEqual(detect_intent(topic)["intent"], "topic_explore")
                self.assertTrue(_is_llm_topic(topic))

    def test_quantum_computing_domains_route_to_llm(self):
        for topic in (
            "Computer Science",
            "Quantum Computing",
            "QIS",
            "Quantum Information Science",
            "Quantum Physics",
        ):
            with self.subTest(topic=topic):
                self.assertEqual(detect_intent(topic)["intent"], "topic_explore")
                self.assertEqual(extract_topic(topic), topic)
                self.assertTrue(_is_llm_topic(topic))


if __name__ == "__main__":
    unittest.main()

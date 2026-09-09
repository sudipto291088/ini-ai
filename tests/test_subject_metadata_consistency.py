import json
import unittest

from streamlit_app.subject_metadata import subject_metadata
from streamlit_app.response_profile import build_response_profile
from streamlit_app.knowledge_map import compact_knowledge_map_projection, _clean_anchor, _qualify_map_description
from streamlit_app.topic_profile import extract_topic_profile


class SubjectMetadataConsistencyTests(unittest.TestCase):
    def test_shared_profiles_and_map(self):
        queries = [
            "How does an operating system manage multiple programs at the same time?",
            "Explain CPU scheduling and multitasking",
            "Why do neural networks need activation functions?",
            "Compare activation functions for neural networks",
            "How does quantum entanglement differ from ordinary correlation?",
            "Explain quantum entanglement",
        ]
        for query in queries:
            with self.subTest(query=query):
                expected = subject_metadata(query)
                ia = dict(build_response_profile(query, intent="topic_explore"))
                saved = '<TOPIC_PROFILE>' + json.dumps({key: "old" for key in expected}) + '</TOPIC_PROFILE>'
                ks, _ = extract_topic_profile(saved, query)
                for key, value in expected.items():
                    self.assertEqual(ia[key], value)
                    self.assertEqual(dict(ks)[key], value)
                self.assertEqual(compact_knowledge_map_projection(query).anchor, expected['Subject'])

    def test_noun_functions_is_not_removed(self):
        for phrase in ("Activation functions", "Probability density functions", "Recursive functions"):
            self.assertEqual(_clean_anchor(phrase), phrase)

    def test_missing_or_malformed_ks_profile(self):
        query = 'Why do neural networks need activation functions?'
        for source in ('Introduction only', '<TOPIC_PROFILE>bad json</TOPIC_PROFILE>Introduction'):
            rows, _ = extract_topic_profile(source, query)
            self.assertEqual(dict(rows), subject_metadata(query))

    def test_unknown_subject_is_not_invented_interdisciplinary(self):
        rows = dict(build_response_profile("Unclassified subject xyz", intent="topic_explore"))
        self.assertEqual(rows['Broad field'], 'Not yet classified')

    def test_other_topics_do_not_match_registry(self):
        for query in ('OAuth', 'Inflation', 'How are you?', 'Data science', 'Database indexing'):
            self.assertEqual(subject_metadata(query), {})

    def test_subject_scope_not_forced_into_comparison(self):
        self.assertEqual(subject_metadata('Quantum entanglement')['Subject'], 'Quantum entanglement')
        self.assertEqual(subject_metadata('Operating systems')['Subject'], 'Operating systems')

    def test_known_map_wording(self):
        self.assertIn('without guaranteeing stability', _qualify_map_description(
            'Allows representation of complex class boundaries, stabilizes gradients, and affects convergence speed and capacity.'))
        self.assertEqual(_qualify_map_description('Use kernel slogging'), 'Use kernel logging')
        self.assertIn('different smoothness', _qualify_map_description('leaky/ELU/GELU smooth variants'))


if __name__ == '__main__':
    unittest.main()

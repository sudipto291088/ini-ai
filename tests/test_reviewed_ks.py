import json
import unittest

from streamlit_app.knowledge_map import compact_knowledge_map_projection
from streamlit_app.topic_profile import extract_topic_profile


class ReviewedKnowledgeStructureTests(unittest.TestCase):
    def test_complete_titles(self):
        for query, expected in [
            ("How does a CPU execute a program?", "CPU instruction execution"),
            ("How does gradient descent help a machine-learning model learn?", "Gradient descent"),
            ("Why did the Industrial Revolution begin in Britain?", "Industrial Revolution in Britain"),
        ]:
            with self.subTest(query=query):
                self.assertEqual(compact_knowledge_map_projection(query).anchor, expected)

    def test_saved_oauth_profile(self):
        source = '<TOPIC_PROFILE>' + json.dumps({
            'Subject': 'OAuth delegated authorization',
            'Broad field': 'Web authentication',
            'Typical applications': 'Single sign-on',
        }) + '</TOPIC_PROFILE>'
        rows, _ = extract_topic_profile(source)
        self.assertIn('OpenID Connect', dict(rows)['Typical applications'])
        self.assertNotIn('authentication', dict(rows)['Broad field'])

    def test_conceptual_gradient_difficulty(self):
        source = '<TOPIC_PROFILE>' + json.dumps({
            'Subject': 'Gradient descent', 'Difficulty': 'Advanced',
            'Related topics': 'backpropagation',
            'Mathematical foundation': 'multivariable calculus',
        }) + '</TOPIC_PROFILE>'
        rows, _ = extract_topic_profile(source, 'Gradient descent')
        self.assertEqual(dict(rows)['Difficulty'], 'Intermediate')

    def test_saved_inflation_purpose(self):
        source = '<TOPIC_PROFILE>{"Subject":"Inflation"}</TOPIC_PROFILE>\nPurpose: It frames the subject for short, diagnosis-centered study rather than a full technical treatment.'
        _, body = extract_topic_profile(source)
        self.assertIn('purchasing power', body)

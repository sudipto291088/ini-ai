import unittest

from api.question_map_focus import (
    find_direct_answer_match,
    find_direct_answer_matches,
    is_specific_learning_question,
)


class QuestionMapFocusTests(unittest.TestCase):
    def setUp(self):
        self.categories = {
            "Orientation": [
                {"question": "What is backpropagation and why is it needed?"},
            ],
            "Foundations": [
                {"question": "What mathematical foundations support neural-network training?"},
            ],
            "Mechanisms": [
                {"question": "How does backpropagation calculate and propagate gradients through a neural network?"},
                {"question": "Step-by-step, how does backpropagation compute gradients for a simple feedforward network using the chain rule?"},
                {"question": "For recurrent neural networks, how does backpropagation through time (BPTT) work and what are the consequences of truncating it?"},
            ],
            "Applications": [
                {"question": "Where is backpropagation used in modern machine learning?"},
            ],
        }

    def test_specific_mechanism_question_selects_direct_match(self):
        match = find_direct_answer_match(
            "How does backpropagation work?",
            self.categories,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.section, "Mechanisms")
        self.assertIn("Step-by-step", match.question)
        self.assertNotIn("BPTT", match.question)

    def test_contextual_how_does_query_does_not_fall_back_to_definition(self):
        categories = {
            "Orientation": [
                {
                    "question": (
                        "What is backpropagation in the context of neural networks "
                        "and how would you define it precisely?"
                    )
                },
            ],
            "Mechanisms": [
                {
                    "question": (
                        "Step-by-step, how does backpropagation compute gradients "
                        "for a simple feedforward network using the chain rule?"
                    )
                },
            ],
        }
        match = find_direct_answer_match(
            "How does backpropagation work in a neural network?",
            categories,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.section, "Mechanisms")

    def test_specific_how_query_does_not_require_question_mark(self):
        categories = {
            "Orientation": [
                {"question": "What is gradient descent and what is its purpose?"},
            ],
            "Mechanisms": [
                {
                    "question": (
                        "How does gradient descent update model parameters using "
                        "the loss gradient and learning rate?"
                    )
                },
            ],
        }
        prompt = "how does gradient descent update a machine learning model"
        self.assertTrue(is_specific_learning_question(prompt))
        match = find_direct_answer_match(prompt, categories)
        self.assertIsNotNone(match)
        self.assertEqual(match.section, "Mechanisms")

    def test_how_mechanism_query_rejects_generic_orientation_restatement(self):
        categories = {
            "Orientation": [
                {
                    "question": (
                        "What is a split in a decision tree and how does a split "
                        "relate to the tree's purpose?"
                    )
                },
            ],
            "Mechanisms": [
                {
                    "question": (
                        "How does a decision tree compare candidate feature thresholds "
                        "and select the split with the greatest impurity reduction?"
                    )
                },
            ],
        }
        match = find_direct_answer_match(
            "How does a decision tree decide where to split the data?",
            categories,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.section, "Mechanisms")

    def test_how_is_it_used_routes_to_applications(self):
        categories = {
            "Mechanisms": [
                {"question": "How does data science transform raw data into model outputs?"},
            ],
            "Applications": [
                {
                    "question": (
                        "How is data science used in modern organizations for "
                        "prediction, personalization, and operational decisions?"
                    )
                },
            ],
            "Pitfalls": [
                {"question": "How can data science be misused in modern organizations?"},
            ],
        }
        match = find_direct_answer_match(
            "How is data science used in the modern world?",
            categories,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.section, "Applications")

    def test_bare_topic_has_no_direct_answer_highlight(self):
        self.assertIsNone(find_direct_answer_match("Backpropagation", self.categories))

    def test_simple_definition_has_no_direct_answer_highlight(self):
        self.assertFalse(is_specific_learning_question("What is backpropagation?"))
        self.assertIsNone(
            find_direct_answer_match("What is backpropagation?", self.categories)
        )

    def test_compound_learning_question_is_specific(self):
        prompt = (
            "What is linear regression, what are its main types, and how does "
            "it relate to regression analysis and machine learning?"
        )
        self.assertTrue(is_specific_learning_question(prompt))
        categories = {
            "Orientation": [
                {"question": "What is linear regression and what is its purpose?"},
                {"question": "What are the main types of linear regression and how do they differ?"},
            ],
            "Applications": [
                {"question": "How does linear regression relate to regression analysis and supervised machine learning?"},
            ],
        }
        matches = find_direct_answer_matches(prompt, categories)
        self.assertEqual(len(matches), 3)
        self.assertEqual([match.part_index for match in matches], [1, 2, 3])
        self.assertEqual(len({match.question for match in matches}), 3)


if __name__ == "__main__":
    unittest.main()

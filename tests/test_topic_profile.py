import unittest

from streamlit_app.topic_profile import (
    extract_continue_journey,
    extract_core_explanation,
    extract_learning_paths,
    extract_learning_loop,
    extract_topic_profile,
    extract_your_question,
    split_prerequisite_items,
    split_prerequisites,
)


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

    def test_prerequisites_are_separated_for_an_individual_card(self):
        rows = [
            ("Entity type", "Concept"),
            ("Prerequisites", "Basic algebra, probability, and programming"),
            ("Related topics", "Machine learning, robotics"),
        ]

        profile_rows, prerequisites = split_prerequisites(rows)

        self.assertEqual(
            profile_rows,
            [
                ("Entity type", "Concept"),
                ("Related topics", "Machine learning, robotics"),
            ],
        )
        self.assertEqual(
            prerequisites,
            "Basic algebra, probability, and programming",
        )

    def test_preserves_a_richer_learning_profile(self):
        answer = """
<TOPIC_PROFILE>
{"Entity type":"Learning algorithm", "Broad field":"Artificial Intelligence", "Subject":"Deep Learning", "Research area":"Neural network optimization", "Mathematical foundation":"Calculus and the chain rule", "Prerequisites":"Partial derivatives and linear algebra", "Related topics":"Gradient descent and automatic differentiation", "Typical applications":"Computer vision and NLP", "Difficulty":"Advanced"}
</TOPIC_PROFILE>

Backpropagation computes gradients through a neural network.
"""

        rows, body = extract_topic_profile(answer)
        profile_rows, prerequisites = split_prerequisites(rows)

        self.assertEqual(len(rows), 9)
        self.assertIn(
            ("Mathematical foundation", "Calculus and the chain rule"),
            profile_rows,
        )
        self.assertIn(("Difficulty", "Advanced"), profile_rows)
        self.assertEqual(prerequisites, "Partial derivatives and linear algebra")
        self.assertEqual(
            body,
            "Backpropagation computes gradients through a neural network.",
        )

    def test_splits_prerequisite_items_without_breaking_parentheses(self):
        prerequisites = (
            "Basic calculus (derivatives, chain rule), linear algebra "
            "(vectors, matrices); supervised learning; feedforward neural networks"
        )

        self.assertEqual(
            split_prerequisite_items(prerequisites),
            [
                "Basic calculus (derivatives, chain rule)",
                "linear algebra (vectors, matrices)",
                "supervised learning",
                "feedforward neural networks",
            ],
        )

    def test_extracts_grouped_learning_paths_and_preserves_body(self):
        answer = """
An introduction to backpropagation.

<LEARNING_PATHS>
{"Foundations":["What is a neural-network weight?", "Why is a loss function needed?"], "Mathematical foundations":["What is the chain rule?", "Why are partial derivatives used?"]}
</LEARNING_PATHS>
"""

        groups, body = extract_learning_paths(answer)

        self.assertEqual(
            groups,
            [
                (
                    "Foundations",
                    [
                        "What is a neural-network weight?",
                        "Why is a loss function needed?",
                    ],
                ),
                (
                    "Mathematical foundations",
                    [
                        "What is the chain rule?",
                        "Why are partial derivatives used?",
                    ],
                ),
            ],
        )
        self.assertEqual(body, "An introduction to backpropagation.")

    def test_extracts_your_question_context_and_preserves_body(self):
        answer = """
<YOUR_QUESTION>
{"Question":"How does backpropagation mathematically update weights?", "Intent":"Understand how the chain rule connects error to each weight.", "Learning goal":"Derive and interpret the weight-update equation."}
</YOUR_QUESTION>

The introduction remains available.
"""

        context, body = extract_your_question(answer)

        self.assertEqual(
            context,
            {
                "Question": "How does backpropagation mathematically update weights?",
                "Intent": "Understand how the chain rule connects error to each weight.",
                "Learning goal": "Derive and interpret the weight-update equation.",
            },
        )
        self.assertEqual(body, "The introduction remains available.")

    def test_extracts_structured_core_explanation(self):
        answer = """
<CORE_EXPLANATION>
{"Title":"How backpropagation updates weights", "Overview":"Gradients measure how each weight affects loss.", "Update rule":"w_new = w_old - eta * dL/dw", "Variables":{"w":"weight", "eta":"learning rate"}, "Steps":[{"Heading":"1. Forward pass", "Explanation":"Compute the prediction and loss."}, {"Heading":"2. Backward pass", "Explanation":"Apply the chain rule."}], "Key insight":"The gradient gives direction and scale.", "Worked example":"If w=1, eta=0.1, and the gradient is 2, the new weight is 0.8."}
</CORE_EXPLANATION>

The narrative remains available.
"""

        explanation, body = extract_core_explanation(answer)

        self.assertEqual(explanation["Title"], "How backpropagation updates weights")
        self.assertEqual(
            explanation["Variables"],
            [("w", "weight"), ("eta", "learning rate")],
        )
        self.assertEqual(len(explanation["Steps"]), 2)
        self.assertEqual(body, "The narrative remains available.")

    def test_extracts_tagged_core_explanation_with_indented_steps(self):
        answer = """
<CORE_EXPLANATION>
<TITLE>How backpropagation updates weights</TITLE>
<OVERVIEW>Gradients connect a change in each weight to the loss.</OVERVIEW>
<UPDATE_RULE>w_new = w_old - eta * dL/dw</UPDATE_RULE>
<VARIABLES>
w :: network weight
eta :: learning rate
</VARIABLES>
<STEPS>
1. Forward pass :: Compute the prediction and loss.
2. Backward pass :: Apply the chain rule.
<KEY_INSIGHT>The gradient determines direction and scale.</KEY_INSIGHT>
<WORKED_EXAMPLE>A gradient of 2 with eta 0.1 changes weight 1 to 0.8.</WORKED_EXAMPLE>
</CORE_EXPLANATION>

The narrative remains available.
"""

        explanation, body = extract_core_explanation(answer)

        self.assertEqual(explanation["Title"], "How backpropagation updates weights")
        self.assertEqual(explanation["Variables"][1], ("eta", "learning rate"))
        self.assertEqual(explanation["Steps"][1]["Heading"], "2. Backward pass")
        self.assertEqual(body, "The narrative remains available.")

    def test_recovers_truncated_core_explanation_without_leaking_markup(self):
        answer = """
The introduction remains available.

<CORE_EXPLANATION>
<TITLE>How spatial AI models physical space</TITLE>
<OVERVIEW>Spatial AI combines perception, mapping, and spatial reasoning.
"""

        explanation, body = extract_core_explanation(answer)

        self.assertEqual(
            explanation["Title"],
            "How spatial AI models physical space",
        )
        self.assertEqual(
            explanation["Overview"],
            "Spatial AI combines perception, mapping, and spatial reasoning.",
        )
        self.assertEqual(body, "The introduction remains available.")

    def test_extracts_complete_learning_loop(self):
        answer = """
<LEARNING_LOOP>
<STAGES>
1. Forward pass :: Compute the network prediction.
2. Loss calculation :: Measure prediction error.
3. Backward pass :: Propagate gradients through the network.
4. Weight update :: Move parameters opposite the gradient.
5. Next cycle :: Repeat with the updated parameters.
</STAGES>
<OUTCOME>Repeated cycles progressively reduce prediction error.</OUTCOME>
</LEARNING_LOOP>

The narrative remains available.
"""

        learning_loop, body = extract_learning_loop(answer)

        self.assertEqual(len(learning_loop["Stages"]), 5)
        self.assertEqual(
            learning_loop["Stages"][3]["Heading"],
            "4. Weight update",
        )
        self.assertEqual(
            learning_loop["Outcome"],
            "Repeated cycles progressively reduce prediction error.",
        )
        self.assertEqual(body, "The narrative remains available.")

    def test_extracts_continue_your_journey(self):
        answer = """
<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Derive one layer by hand :: Trace every partial derivative for a small network.
2. Verify the gradient numerically :: Compare backpropagation with finite differences.
3. Study optimization dynamics :: Connect the computed gradient to Adam and momentum.
</DIRECTIONS>
<DESTINATION>Confidently derive, verify, and apply a complete neural-network weight update.</DESTINATION>
</CONTINUE_JOURNEY>

The narrative remains available.
"""

        journey, body = extract_continue_journey(answer)

        self.assertEqual(len(journey["Directions"]), 3)
        self.assertEqual(
            journey["Directions"][0]["Heading"],
            "Derive one layer by hand",
        )
        self.assertEqual(
            journey["Destination"],
            "Confidently derive, verify, and apply a complete neural-network weight update.",
        )
        self.assertEqual(body, "The narrative remains available.")

    def test_extracts_continue_journey_when_final_closing_tags_are_missing(self):
        answer = """
The introduction remains available.

<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Derive one layer :: Trace the derivatives by hand.
2. Verify numerically :: Compare the gradient with finite differences.
3. Advance to Adam :: Study adaptive parameter updates.
</DIRECTIONS>
<DESTINATION>Derive and verify a complete weight update.
"""

        journey, body = extract_continue_journey(answer)

        self.assertEqual(len(journey["Directions"]), 3)
        self.assertEqual(
            journey["Destination"],
            "Derive and verify a complete weight update.",
        )
        self.assertEqual(body, "The introduction remains available.")


if __name__ == "__main__":
    unittest.main()

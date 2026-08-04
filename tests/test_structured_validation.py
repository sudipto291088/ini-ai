import unittest

from streamlit_app.structured_validation import validate_structured_learning_answer


VALID_RESPONSE = """
<TOPIC_PROFILE>
{"Entity type":"Algorithm","Broad field":"Artificial Intelligence","Subject":"Gradient descent","Prerequisites":"Calculus; algebra; optimization","Related topics":"Backpropagation","Difficulty":"Intermediate"}
</TOPIC_PROFILE>
<LEARNING_PATHS>
{"Foundations":["What is a gradient?","What is a loss function?"],"Mechanism":["How is direction chosen?","How is step size chosen?"],"Optimization":["How does convergence work?","How is momentum used?"],"Applications":["Where is it applied?","How is it evaluated?"],"Advanced":["What are adaptive methods?","What remains difficult?"]}
</LEARNING_PATHS>
<YOUR_QUESTION>
{"Question":"How does gradient descent work?","Intent":"Understand parameter updates.","Learning goal":"Explain the update mechanism."}
</YOUR_QUESTION>
<CORE_EXPLANATION>
<TITLE>Gradient descent update</TITLE>
<OVERVIEW>Gradient descent follows the negative gradient to reduce loss.</OVERVIEW>
<UPDATE_RULE>w = w - eta * grad(L(w))</UPDATE_RULE>
<VARIABLES>
w :: model parameters
eta :: learning rate
L :: loss function
</VARIABLES>
<STEPS>
1. Evaluate :: Compute the current loss.
2. Differentiate :: Calculate the gradient.
3. Scale :: Multiply by the learning rate.
4. Update :: Subtract the scaled gradient.
</STEPS>
<KEY_INSIGHT>The gradient gives the local direction of steepest increase.</KEY_INSIGHT>
<WORKED_EXAMPLE>Move from w=2 toward a lower-loss value.</WORKED_EXAMPLE>
</CORE_EXPLANATION>
<LEARNING_LOOP>
<STAGES>
1. Identify :: Choose parameters and a loss.
2. Evaluate :: Measure the current loss.
3. Differentiate :: Compute gradients.
4. Update :: Change the parameters.
5. Review :: Check convergence.
</STAGES>
<OUTCOME>Repeated updates reduce the objective.</OUTCOME>
</LEARNING_LOOP>
<CONTINUE_JOURNEY>
<DIRECTIONS>
1. Strengthen understanding :: Derive a one-variable example.
2. Practise or verify :: Calculate two updates by hand.
3. Advance beyond it :: Study momentum and Adam.
</DIRECTIONS>
<DESTINATION>The learner can derive and apply the update.</DESTINATION>
</CONTINUE_JOURNEY>
Purpose: Place gradient descent within numerical optimization.

Major areas: Loss design, gradients, step sizes, and convergence.

Who should study this next: Learners comfortable with algebra and derivatives.
""".strip()


class StructuredValidationTests(unittest.TestCase):
    def test_accepts_a_complete_structured_response(self) -> None:
        result = validate_structured_learning_answer(VALID_RESPONSE)

        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])

    def test_repairs_a_safely_repairable_formula_delimiter(self) -> None:
        malformed = VALID_RESPONSE.replace(
            "w = w - eta * grad(L(w))",
            "w = w - eta * grad(L(w)",
        )

        result = validate_structured_learning_answer(malformed)

        self.assertTrue(result["valid"])
        self.assertIn("balanced update-rule delimiters", result["repairs"])
        self.assertIn("grad(L(w))", result["answer"])

    def test_rejects_missing_cards_and_prompt_placeholders(self) -> None:
        malformed = VALID_RESPONSE.replace(
            "Gradient descent update",
            "A precise, topic-specific explanation title",
        ).replace(
            "<CONTINUE_JOURNEY>",
            "",
        ).replace(
            "</CONTINUE_JOURNEY>",
            "",
        )

        result = validate_structured_learning_answer(malformed)

        self.assertFalse(result["valid"])
        self.assertTrue(any("placeholder" in issue for issue in result["issues"]))
        self.assertTrue(any("CONTINUE_JOURNEY" in issue for issue in result["issues"]))

    def test_rejects_formula_without_variable_definitions(self) -> None:
        malformed = VALID_RESPONSE.replace(
            "w :: model parameters\neta :: learning rate\nL :: loss function",
            "",
        )

        result = validate_structured_learning_answer(malformed)

        self.assertFalse(result["valid"])
        self.assertIn(
            "formula is present without variable definitions",
            result["issues"],
        )

    def test_rejects_formula_that_does_not_use_declared_variables(self) -> None:
        malformed = VALID_RESPONSE.replace(
            "w = w - eta * grad(L(w))",
            "Parameter change depends on slope and step size",
        )

        result = validate_structured_learning_answer(malformed)

        self.assertFalse(result["valid"])
        self.assertIn("formula does not use its declared variables", result["issues"])

    def test_rejects_generic_learning_loop_language(self) -> None:
        generic = VALID_RESPONSE.replace(
            "1. Identify :: Choose parameters and a loss.\n"
            "2. Evaluate :: Measure the current loss.\n"
            "3. Differentiate :: Compute gradients.\n"
            "4. Update :: Change the parameters.\n"
            "5. Review :: Check convergence.",
            "1. Identify :: Define the topic and recognize its essential components.\n"
            "2. Distinguish :: Separate the topic from its closest related concepts.\n"
            "3. Connect :: Relate the main components to understand the topic.\n"
            "4. Apply :: Use a representative scenario.\n"
            "5. Review :: Summarize its purpose, major trade-offs, and limitations.",
        )

        result = validate_structured_learning_answer(generic)

        self.assertFalse(result["valid"])
        self.assertIn("LEARNING_LOOP uses a generic topic template", result["issues"])

    def test_rejects_generic_comparison_journey(self) -> None:
        generic = VALID_RESPONSE.replace(
            "1. Strengthen understanding :: Derive a one-variable example.\n"
            "2. Practise or verify :: Calculate two updates by hand.\n"
            "3. Advance beyond it :: Study momentum and Adam.",
            "1. Clarify the decision criteria :: List generic requirements.\n"
            "2. Examine representative scenarios :: Decide which alternative fits each one.\n"
            "3. Explore boundaries and hybrids :: Make a context-aware choice.",
        )

        result = validate_structured_learning_answer(generic)

        self.assertFalse(result["valid"])
        self.assertIn(
            "CONTINUE_JOURNEY uses a generic comparison template",
            result["issues"],
        )

    def test_allows_one_generic_phrase_inside_a_specific_journey(self) -> None:
        specific = VALID_RESPONSE.replace(
            "1. Strengthen understanding :: Derive a one-variable example.\n"
            "2. Practise or verify :: Calculate two updates by hand.\n"
            "3. Advance beyond it :: Study momentum and Adam.",
            "1. Compare named mechanisms :: Contrast classical and operant learning.\n"
            "2. Classify cases :: Diagnose conditioning examples.\n"
            "3. Make a context-aware choice :: Select an ethical intervention.",
        )

        result = validate_structured_learning_answer(specific)

        self.assertTrue(result["valid"])

    def test_repairs_single_qubit_expression_mislabeled_as_bell_pair(self) -> None:
        malformed = VALID_RESPONSE.replace(
            '"Subject":"Gradient descent"',
            '"Subject":"Quantum entanglement"',
        ).replace(
            "<WORKED_EXAMPLE>Move from w=2 toward a lower-loss value.</WORKED_EXAMPLE>",
            "<WORKED_EXAMPLE>A Bell pair is (|0> + |1>)/sqrt(2).</WORKED_EXAMPLE>",
        )

        result = validate_structured_learning_answer(malformed)

        self.assertTrue(result["valid"])
        self.assertIn("corrected Bell-pair basis states", result["repairs"])
        self.assertIn("(|00> + |11>)/√2", result["answer"])

    def test_replaces_generic_quantum_entanglement_loop(self) -> None:
        generic = VALID_RESPONSE.replace(
            '"Subject":"Gradient descent"',
            '"Subject":"Quantum entanglement"',
        ).replace(
            "1. Identify :: Choose parameters and a loss.\n"
            "2. Evaluate :: Measure the current loss.\n"
            "3. Differentiate :: Compute gradients.\n"
            "4. Update :: Change the parameters.\n"
            "5. Review :: Check convergence.",
            "1. Identify :: Define the topic and recognize its essential components.\n"
            "2. Distinguish :: Separate the topic from its closest related concepts.\n"
            "3. Connect :: Relate the main components to understand the topic.\n"
            "4. Apply :: Use a representative scenario.\n"
            "5. Review :: Summarize its purpose, major trade-offs, and limitations.",
        )

        result = validate_structured_learning_answer(generic)

        self.assertTrue(result["valid"])
        self.assertIn("replaced generic entanglement learning loop", result["repairs"])
        self.assertIn("Compare with classical bounds", result["answer"])


if __name__ == "__main__":
    unittest.main()

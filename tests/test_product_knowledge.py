import unittest

from api.product_knowledge import answer_ini_product_query


class ProductKnowledgeTests(unittest.TestCase):
    def test_supported_product_questions_have_direct_answers(self):
        prompts = (
            "What exactly is InI?",
            "What can you help me with?",
            "How is InI different from ChatGPT?",
            "Why do you create Question Maps?",
            "What features are planned for InI?",
            "How many versions have you had so far?",
            "What is special in your current version?",
            "Who created you?",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertTrue(answer_ini_product_query(prompt))

    def test_unrelated_topic_is_not_claimed(self):
        self.assertIsNone(answer_ini_product_query("Generate a Question Map for cognitive science"))

    def test_second_person_inside_learning_question_is_not_claimed(self):
        prompts = (
            "What can you tell me about quant?",
            "What could you tell me about DNA replication?",
            "What is transfer learning, how does it differ from training a model from scratch, and when should you fine-tune the entire network rather than only its final layers?**",
            "What is PCA and when should you use it?",
            "What future topic should you learn after linear regression?",
        )
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertIsNone(answer_ini_product_query(prompt))

    def test_topic_coverage_answer_is_honest_and_scoped(self):
        for prompt in (
            "What all topics do you know?",
            "Which subjects can you cover?",
        ):
            with self.subTest(prompt=prompt):
                answer = answer_ini_product_query(prompt)
                self.assertIn("strongest today", answer)
                self.assertIn("Kubernetes", answer)
                self.assertIn("depth and reliability may vary", answer)
                self.assertIn("do not claim verified specialist support", answer)

    def test_creator_and_release_answers_are_grounded(self):
        creator = answer_ini_product_query("Who is your creator?")
        self.assertIn("Sudipto", creator)
        self.assertIn("Sid", creator)
        release = answer_ini_product_query("What is new in your current version?")
        self.assertIn("v0.1.6", release)
        self.assertIn("Knowledge Maps", release)
        history = answer_ini_product_query("How many versions have you had?")
        self.assertIn("six documented releases", history)
        self.assertIn("v0.1.1", history)
        self.assertIn("v0.1.6", history)

    def test_self_identified_creator_profile_is_remembered(self):
        profile = {
            "full_name": "Sudipto",
            "preferred_name": "Sid",
            "relationship": "creator",
            "identity_source": "self_reported",
        }
        answer = answer_ini_product_query("Do you remember my full name?", profile)
        self.assertIn("Sudipto", answer)
        self.assertIn("Sid", answer)


if __name__ == "__main__":
    unittest.main()

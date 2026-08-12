import unittest

from streamlit_app.response_profile import build_response_profile


class ResponseProfileTests(unittest.TestCase):
    def test_casual_greeting_has_sociolinguistic_profile(self):
        rows = dict(build_response_profile("Heyyyy what's up?", "greeting", "conversation"))
        self.assertEqual(rows["Name type"], "Informal greeting")
        self.assertEqual(rows["Broad field"], "Sociolinguistics")

    def test_casual_testing_has_interaction_profile(self):
        rows = dict(build_response_profile("Just casually testing you", "smalltalk", "conversation"))
        self.assertEqual(rows["Subject"], "Casual testing of InI")
        self.assertIn("Intent detection", rows["Related topics"])

    def test_practical_query_has_full_task_profile(self):
        rows = dict(
            build_response_profile(
                "How do I install an MCP server locally?",
                response_mode="carm",
                context_intent="installation",
            )
        )
        self.assertEqual(rows["Entity type"], "Procedure")
        self.assertEqual(rows["Broad field"], "Technical configuration")

    def test_enterprise_bridge_is_classified_as_implementation_guidance(self):
        rows = dict(
            build_response_profile(
                "How do I add Siebel CRM as a local MCP server?",
                response_mode="carm",
                context_intent="integration",
            )
        )
        self.assertEqual(rows["Name type"], "Implementation guidance")
        self.assertEqual(rows["Entity type"], "Technical integration and configuration")
        self.assertEqual(rows["Broad field"], "Systems integration")


if __name__ == "__main__":
    unittest.main()

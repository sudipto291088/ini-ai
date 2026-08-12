import unittest

from api.context_mode import build_carm_answer_prompt, classify_context
from api.interrogate import interrogate


class ContextAwareResponseModeTests(unittest.TestCase):
    def test_broad_learning_keeps_question_map_mode(self):
        for prompt in ("Artificial intelligence", "Teach me quantum computing"):
            with self.subTest(prompt=prompt):
                self.assertEqual(classify_context(prompt)["response_mode"], "question_map")

    def test_practical_requests_select_carm(self):
        expected = {
            "How do I install Docker on Windows?": "installation",
            "Why is my Python code failing with a traceback?": "debugging",
            "What is an HTTP 500 error and how do I fix it?": "troubleshooting",
        }
        for prompt, expected_intent in expected.items():
            with self.subTest(prompt=prompt):
                result = classify_context(prompt)
                self.assertEqual(result["response_mode"], "carm")
                self.assertEqual(result["context_intent"], expected_intent)

    def test_error_correction_concept_remains_a_learning_query(self):
        prompt = (
            "What is quantum error correction, and why is it necessary for "
            "reliable quantum computing?"
        )

        result = classify_context(prompt)

        self.assertEqual(result["response_mode"], "question_map")
        self.assertEqual(result["context_intent"], "learning")

    def test_ambiguous_local_mcp_request_asks_for_host(self):
        result = interrogate("My wife wants to add an MCP server in the local system")
        self.assertEqual(result["response_mode"], "carm")
        self.assertTrue(result["needs_clarification"])
        self.assertIn("Which application", result["reply"])
        self.assertEqual(len(result["followups"]), 4)
        self.assertTrue(any("VS Code" in option for option in result["followups"]))
        self.assertEqual(result["categories"], {})

    def test_specific_mcp_host_gets_immediate_answer_path(self):
        result = interrogate("How do I configure a local MCP server for Codex?")
        self.assertEqual(result["response_mode"], "carm")
        self.assertTrue(result["should_answer_direct"])
        self.assertFalse(result["needs_clarification"])
        self.assertIn("Context-Aware Response Mode", result["direct_answer_prompt"])

    def test_named_enterprise_system_routes_to_mcp_bridge_answer(self):
        result = interrogate("How do I add Siebel CRM as a local MCP server?")
        self.assertEqual(result["response_mode"], "carm")
        self.assertEqual(result["context_intent"], "integration")
        self.assertTrue(result["should_answer_direct"])
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(result["topic"], "Siebel CRM and local MCP integration")
        prompt = result["direct_answer_prompt"]
        self.assertIn("local MCP bridge", prompt)
        self.assertIn("target system -> supported interface", prompt)
        self.assertIn("first turn of a staged implementation conversation", prompt)
        self.assertIn("no more than 220 words", prompt)
        self.assertIn("exactly four numbered questions", prompt)
        self.assertIn("‘I don’t know’ is a valid answer", prompt)
        self.assertIn("Then stop", prompt)
        self.assertIn("implementation steps, code, commands", prompt)
        self.assertIn("Never assume Codex", prompt)
        self.assertIn("apply this staged behavior generally", prompt)
        self.assertNotIn("target 350 to 500 words", prompt)
        self.assertNotIn('End with "Explore next"', prompt)
        self.assertNotIn("reserve enough output for the final", prompt)
        self.assertNotIn("Codex supports local STDIO servers", prompt)

    def test_other_named_systems_use_same_general_integration_route(self):
        for system in ("Salesforce", "SAP", "PostgreSQL"):
            with self.subTest(system=system):
                result = classify_context(
                    f"How do I add {system} as a local MCP server?"
                )
                self.assertEqual(result["context_intent"], "integration")
                self.assertFalse(result["clarification_required"])
                self.assertEqual(result["integration_target"], system.lower())

    def test_uncertain_reply_stays_inside_active_integration_guidance(self):
        continued = (
            "Continue this active practical request: How do I add Siebel CRM as a local MCP server?\n\n"
            "The end of InI's previous answer was: Before we build it...\n\n"
            "The user's latest natural-language reply is: I don't know.\n"
            "Interpret that reply as context for the active request."
        )
        result = interrogate(continued)
        self.assertEqual(result["response_mode"], "carm")
        self.assertEqual(result["context_intent"], "integration")
        prompt = result["direct_answer_prompt"]
        self.assertIn("active implementation-guidance conversation", prompt)
        self.assertIn("Never generate a Question Map", prompt)
        self.assertIn("If the user says they do not know", prompt)
        self.assertIn("one manageable discovery step at a time", prompt)
        self.assertNotIn("exactly four numbered questions", prompt)

    def test_vscode_clarification_answer_completes_mcp_request(self):
        for host_spelling in ("VSCode", "VS Code", "Visual Studio Code"):
            with self.subTest(host_spelling=host_spelling):
                result = interrogate(
                    "My wife wants to add an MCP server in the local system. "
                    f"The application is {host_spelling}."
                )
                self.assertEqual(result["response_mode"], "carm")
                self.assertTrue(result["should_answer_direct"])
                self.assertFalse(result["needs_clarification"])
                self.assertEqual(result["categories"], {})

    def test_unseen_application_reply_does_not_require_an_allowlist(self):
        result = interrogate(
            "How do I install an MCP server locally? "
            "The application or tool specified by the user is Zed Preview."
        )
        self.assertEqual(result["response_mode"], "carm")
        self.assertTrue(result["should_answer_direct"])
        self.assertFalse(result["needs_clarification"])

    def test_short_os_reply_can_continue_the_active_mcp_goal(self):
        result = interrogate(
            "Continue this active practical request: install a local MCP server for VS Code. "
            "The user's latest natural-language reply is: Windows. "
            "Interpret it as context for the active request."
        )
        self.assertEqual(result["response_mode"], "carm")
        self.assertTrue(result["should_answer_direct"])
        self.assertEqual(result["categories"], {})

    def test_carm_prompt_prioritizes_immediate_answer(self):
        prompt = build_carm_answer_prompt("How do I install Docker?", "installation")
        self.assertIn('"Immediate intent"', prompt)
        self.assertIn('"Start here"', prompt)
        self.assertIn('"Explore next"', prompt)
        self.assertIn("Do not generate a full seven-section Question Map", prompt)

    def test_mcp_prompt_locks_correct_meaning_and_codex_direction(self):
        prompt = build_carm_answer_prompt(
            "How do I configure a local MCP server for Codex?", "installation"
        )
        self.assertIn("MCP means Model Context Protocol", prompt)
        self.assertIn("Codex is the host", prompt)
        self.assertIn("codex mcp add", prompt)
        self.assertIn("Do not invent `--type`, `--command`", prompt)
        self.assertIn("codex mcp-server", prompt)
        self.assertIn("Never invent an MCP package", prompt)
        self.assertIn("`[mcp_servers.SERVER_NAME]`, not `[[mcp_servers]]`", prompt)


if __name__ == "__main__":
    unittest.main()

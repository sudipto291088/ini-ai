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

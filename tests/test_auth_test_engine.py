import unittest
from unittest.mock import patch
from pathlib import Path

from streamlit_app.auth_test_engine import start_test_engine, TEST_API_BASE, provider_post


class HostedAuthTestEngineTests(unittest.TestCase):
    def test_gpt4_request_omits_unsupported_reasoning_without_mutating_input(self):
        payload = {"model": "gpt-4o-mini", "reasoning": {"effort": "minimal"}, "input": "hello"}
        with patch("streamlit_app.auth_test_engine.requests.post") as post:
            provider_post("https://api.openai.com/v1/responses", json=payload)
            self.assertNotIn("reasoning", post.call_args.kwargs["json"])
        self.assertIn("reasoning", payload)

    def tearDown(self):
        start_test_engine.clear()

    def test_listener_is_loopback_only_and_skips_warmup(self):
        with patch("streamlit_app.auth_test_engine.uvicorn.Config") as config, patch("streamlit_app.auth_test_engine.uvicorn.Server") as server, patch("streamlit_app.auth_test_engine.Thread") as thread:
            server.return_value.started = True
            start_test_engine()
            self.assertEqual(config.call_args.kwargs["host"], "127.0.0.1")
            self.assertEqual(config.call_args.kwargs["port"], 8012)
            self.assertEqual(config.call_args.kwargs["lifespan"], "off")
            self.assertTrue(thread.call_args.kwargs["daemon"])
            thread.return_value.start.assert_called_once()
        self.assertEqual(TEST_API_BASE, "http://127.0.0.1:8012")

    def test_authentication_precedes_engine_and_full_app(self):
        source = (Path(__file__).parents[1] / "streamlit_app/auth_test_app.py").read_text(encoding="utf-8")
        self.assertLess(source.index("require_google_account()"), source.index("start_test_engine()"))
        self.assertLess(source.index("start_test_engine()"), source.index("runpy.run_path("))


if __name__ == "__main__":
    unittest.main()

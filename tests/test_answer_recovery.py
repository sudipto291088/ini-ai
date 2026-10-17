import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from textwrap import dedent
from streamlit.testing.v1 import AppTest

from streamlit_app.answer_recovery import collect_answer, merge_continuation, recover_answer
from streamlit_app import storage_sqlite as storage


class AnswerRecoveryTests(unittest.TestCase):
    def test_actual_direct_answer_ui_recovers_carm_and_hides_button_when_done(self):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        start = source.index('        is_incomplete = bool(direct_answer.get("incomplete"))')
        end = source.index('        if isinstance(pending_qc_continuation, dict):', start)
        block = dedent(source[start:end])
        script = '''
import streamlit as st
from streamlit_app.answer_recovery import recover_answer
st.session_state.setdefault("chat_direct_answer", {"prompt": "Physics", "mode": "focused",
    "response_mode": "carm", "text": "Energy is conserved.", "incomplete": True})
st.session_state.setdefault("_nc_continue_loading_q", None)
direct_answer = st.session_state.chat_direct_answer
def fetch_study(**kwargs):
    return {"answer": "Energy is conserved. It changes form.", "incomplete": False}
def normalize_whitespace_for_readability(value): return value
def normalize_mojibake(value): return value
def _sync_chat_root_snapshot(): pass
def _persist_new_chat_session():
    st.session_state["saved"] = dict(st.session_state.chat_direct_answer)
'''
        app = AppTest.from_string(script + block).run()
        self.assertEqual(app.button[0].label, "Continue response")
        app.button[0].click().run()
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.button), 0)
        self.assertEqual(app.session_state["saved"]["text"], "Energy is conserved. It changes form.")
        self.assertEqual(app.session_state["saved"]["response_mode"], "carm")

    def test_repeated_paragraph_is_not_duplicated(self):
        old = "First paragraph.\n\nAn existing second paragraph."
        self.assertEqual(merge_continuation(old, "An existing second paragraph.\n\nNew paragraph."),
                         old + "\n\nNew paragraph.")

    def test_mid_sentence_tail_is_preserved(self):
        self.assertEqual(merge_continuation("The main reason is", "that energy is conserved."),
                         "The main reason is that energy is conserved.")

    def test_empty_error_or_repeated_result_remains_retryable(self):
        record = {"text": "Already received text.", "incomplete": True}
        for response in ({"answer": ""}, {"answer": record["text"]},
                         {"answer": "No answer generated.", "llm": {"reason": "llm_error"}}):
            result = recover_answer(record, response)
            self.assertEqual(result["text"], record["text"])
            self.assertTrue(result["incomplete"])
        self.assertNotIn("stop_reason", record)

    def test_completion_preserves_profile_and_mode(self):
        record = {"text": "First part.", "response_mode": "carm", "topic_profile": {"name": "Physics"},
                  "answer_views": {"old": "stale"}, "incomplete": True}
        result = recover_answer(record, {"answer": "Final part.", "incomplete": False})
        self.assertFalse(result["incomplete"])
        self.assertEqual(result["response_mode"], "carm")
        self.assertEqual(result["topic_profile"], record["topic_profile"])
        self.assertNotIn("answer_views", result)

    def test_timeout_keeps_successful_initial_answer(self):
        fetch = Mock(side_effect=[{"answer": "Partial text", "incomplete": True}, TimeoutError()])
        result = collect_answer(fetch, "Physics", mode="deep", max_rounds=4)
        self.assertEqual(result["answer"], "Partial text")
        self.assertTrue(result["incomplete"])
        self.assertEqual(fetch.call_count, 2)

    def test_complete_answer_does_not_request_continuation(self):
        fetch = Mock(return_value={"answer": "Complete.", "incomplete": False})
        result = collect_answer(fetch, "Physics", mode="deep", max_rounds=4)
        self.assertFalse(result["incomplete"])
        fetch.assert_called_once()

    def test_no_progress_stops_automatic_retries(self):
        fetch = Mock(return_value={"answer": "Partial.", "incomplete": True})
        result = collect_answer(fetch, "Physics", mode="deep", max_rounds=4)
        self.assertTrue(result["incomplete"])
        self.assertEqual(fetch.call_count, 2)

    def test_partial_answer_survives_reload_and_is_owner_scoped(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(
            storage, "DB_PATH", str(Path(folder) / "recovery.db")
        ), patch.dict(os.environ, {"INI_STORAGE_BACKEND": "sqlite"}):
            storage.init_db()
            partial = {"chat_direct_answer": {"text": "Private unfinished answer", "incomplete": True}}
            storage.save_session("account-a", "recovery-chat", "Test", "today", partial)
            loaded = storage.load_session("account-a", "recovery-chat")
            self.assertEqual(loaded["messages"], partial)
            self.assertIsNone(storage.load_session("account-b", "recovery-chat"))


if __name__ == "__main__":
    unittest.main()

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional
import re
import unittest

from streamlit_app.conversation_identity import parse_self_introduction, role_acknowledgement


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class ConversationIdentityTests(unittest.TestCase):
    def app_helpers(self, initial=None):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {"_refresh_chat_user_profile", "_local_conversation_answer"}
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
        state = State(chat_user_profile=initial or {}, chat_query_log=[])
        scope = dict(st=SimpleNamespace(session_state=state), re=re, Any=Any, Dict=Dict, Optional=Optional,
                     parse_self_introduction=parse_self_introduction, role_acknowledgement=role_acknowledgement)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "actual_identity_helpers", "exec"), scope)
        return scope, state

    def test_roles_are_not_names(self):
        for text in ("I am your founder", "I'm your creator", "I am a teacher", "I am the owner",
                     "I am an engineer", "I am administrator", "I am your developer"):
            with self.subTest(text=text):
                self.assertEqual(parse_self_introduction(text)["kind"], "role")
                scope, state = self.app_helpers()
                profile = scope["_refresh_chat_user_profile"](text)
                reply = scope["_local_conversation_answer"](text, profile)
                self.assertNotIn("preferred_name", profile)
                self.assertNotIn("Nice to meet you", reply)
                self.assertIn("self_reported_role", state.chat_user_profile)

    def test_founder_response_acknowledges_claim_not_verified_identity(self):
        scope, _ = self.app_helpers()
        profile = scope["_refresh_chat_user_profile"]("i am your founder")
        self.assertEqual(scope["_local_conversation_answer"]("i am your founder", profile),
                         "Got it—you’re telling me you’re InI’s founder.")
        self.assertNotIn("relationship", profile)
        self.assertNotIn("is_admin", profile)
        self.assertNotIn("authenticated", profile)

    def test_actual_name_introductions_still_work(self):
        for text, name in (("I am Sudipto", "Sudipto"), ("My name is Alex Morgan", "Alex Morgan"),
                           ("Call me Sid", "Sid"), ("I'm Maya", "Maya")):
            scope, _ = self.app_helpers()
            profile = scope["_refresh_chat_user_profile"](text)
            self.assertEqual(profile["preferred_name"], name)
            self.assertIn("Nice to meet you, " + name, scope["_local_conversation_answer"](text, profile))

    def test_role_does_not_replace_existing_real_name(self):
        scope, _ = self.app_helpers({"preferred_name": "Sudipto", "identity_source": "self_reported"})
        profile = scope["_refresh_chat_user_profile"]("I am your founder")
        self.assertEqual(profile["preferred_name"], "Sudipto")
        self.assertEqual(profile["self_reported_role"], "your founder")

    def test_existing_bad_name_is_repaired_without_changing_auth_fields(self):
        scope, state = self.app_helpers({"preferred_name": "Your Founder", "identity_source": "self_reported",
                                         "owner_id": "existing-owner", "other_preference": "concise"})
        profile = scope["_refresh_chat_user_profile"]("I am your founder")
        self.assertNotIn("preferred_name", profile)
        self.assertEqual(profile["owner_id"], "existing-owner")
        self.assertEqual(profile["other_preference"], "concise")
        self.assertEqual(state.chat_user_profile, profile)

    def test_states_questions_and_negations_are_not_names(self):
        for text in ("I am tired", "I am not your founder", "I am just checking", "Who am I?",
                     "I am interested in physics", "I am from India", "I am learning Kubernetes"):
            self.assertEqual(parse_self_introduction(text), {}, text)


if __name__ == "__main__":
    unittest.main()

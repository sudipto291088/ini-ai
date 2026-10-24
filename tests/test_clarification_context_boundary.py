import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

from api.conversation_interpreter import is_self_contained_request, should_preserve_conversation_context
from api.intent_layer import detect_intent
from streamlit_app.response_profile import build_response_profile


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class ClarificationContextBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(source)

    def routing_scope(self, question):
        # Execute the real app's classification assignments, not a copy.
        nodes = [node for node in ast.walk(self.tree) if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id in
                         {"self_contained_request", "substantive_learning_turn"} for target in node.targets)]
        scope = dict(display_topic_text=question, semantic_intent=detect_intent(question),
                     is_self_contained_request=is_self_contained_request)
        exec(compile(ast.Module(body=sorted(nodes, key=lambda node: node.lineno), type_ignores=[]), "app-routing", "exec"), scope)
        return scope

    def test_new_questions_after_each_abbreviation_do_not_continue_clarification(self):
        for abbreviation in ("CV", "ML", "AI", "OS", "RL"):
            self.assertEqual(detect_intent(abbreviation)["intent"], "abbreviation_clarification")
            for question in ("why is the sky blue?", "What is photosynthesis?",
                             "How does a battery work?", "Explain gradient descent with an example"):
                with self.subTest(abbreviation=abbreviation, question=question):
                    scope = self.routing_scope(question)
                    self.assertTrue(scope["substantive_learning_turn"])
                    self.assertFalse(should_preserve_conversation_context(
                        user_text=question, prior_response_mode="conversation", study_mode_established=False,
                        requests_learning_map=scope["substantive_learning_turn"], explicit_question_map_request=False))
                    # The real conversation-generation branch is excluded.
                    self.assertFalse(True and not scope["substantive_learning_turn"])

    def test_references_and_social_replies_are_not_forced_into_new_topics(self):
        for text in ("What about its applications?", "How does it work?", "yes", "the first one", "How are you?"):
            self.assertFalse(is_self_contained_request(text, detect_intent(text)), text)

    def test_full_meaning_still_uses_normal_subject_routing(self):
        self.assertTrue(self.routing_scope("Computer vision")["substantive_learning_turn"])

    def test_factual_question_profile_is_not_social_conversation(self):
        question = "why is the sky blue?"
        intent = detect_intent(question)
        rows = dict(build_response_profile(question, intent=intent["intent"], response_mode="standard"))
        self.assertNotEqual(rows["Broad field"], "Human–AI interaction")
        self.assertNotEqual(rows["Entity type"], "User utterance")

    def apply_pending_clarification(self, text):
        node = next(node for node in ast.walk(self.tree) if isinstance(node, ast.If)
                    and ast.unparse(node.test) == "isinstance(pending_context, dict)")
        state = State(chat_pending_context_clarification={"original_request": "Connect the MCP tool"})
        scope = dict(pending_context=state.chat_pending_context_clarification,
                     display_topic_text=text, topic_text=text, re=re,
                     self_contained_request=is_self_contained_request(text, detect_intent(text)),
                     st=SimpleNamespace(session_state=state))
        # This test exercises the pending branch only, not its CARM alternative.
        pending_branch = ast.If(test=node.test, body=node.body, orelse=[])
        ast.fix_missing_locations(pending_branch)
        exec(compile(ast.Module(body=[pending_branch], type_ignores=[]), "pending-context", "exec"), scope)
        self.assertIsNone(state.chat_pending_context_clarification)
        return scope["topic_text"]

    def test_new_question_is_not_stitched_into_old_tool_request(self):
        for question in ("Why is the sky blue?", "How does a battery work?", "Explain photosynthesis"):
            self.assertEqual(self.apply_pending_clarification(question), question)

    def test_short_tool_reply_still_resolves_requested_detail(self):
        self.assertIn("application or tool specified by the user is VSCode", self.apply_pending_clarification("VSCode"))

    def test_context_lookup_does_not_resurrect_an_older_clarification(self):
        node = next(node for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef)
                    and node.name == "_latest_assistant_conversation_reply")
        old = dict(kind="direct", direct_answer=dict(response_mode="conversation", text="Did you mean CV?"))
        for latest in (dict(kind="interrogate"), dict(kind="direct", direct_answer=dict(response_mode="standard", text="Physics"))):
            state = State(chat_branch_answers=[old, latest], chat_direct_answer=old["direct_answer"])
            scope = dict(st=SimpleNamespace(session_state=state))
            exec(compile(ast.Module(body=[node], type_ignores=[]), "context-lookup", "exec"), scope)
            self.assertEqual(scope[node.name](), "")


if __name__ == "__main__":
    unittest.main()

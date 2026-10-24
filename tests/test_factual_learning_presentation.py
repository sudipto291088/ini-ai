import ast
from pathlib import Path
from types import SimpleNamespace
import re
import unittest
from unittest.mock import Mock

from api.response_strategy import fallback_learning_questions, question_intelligence_limit
from streamlit_app.response_profile import build_response_profile


class Rerun(Exception):
    pass


class FactualLearningPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.guard = next(node for node in ast.walk(cls.tree) if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Name) and target.id == "full_factual_learning_answer" for target in node.targets))
        cls.branch = next(node for node in ast.walk(cls.tree) if isinstance(node, ast.If)
                          and "or full_factual_learning_answer" in ast.unparse(node.test))

    def scope(self, **changes):
        scope = dict(intent_name="direct_factual_query", self_contained_request=True,
                     should_answer_direct=True, response_mode="standard", data={},
                     display_topic_text="Why is the sky blue?", _looks_like_live_local_query=lambda query: False)
        scope.update(changes)
        exec(compile(ast.Module(body=[self.guard], type_ignores=[]), "factual-guard", "exec"), scope)
        return scope

    def test_excludes_clarifications_social_practical_and_live_queries(self):
        for changes in (dict(intent_name="abbreviation_clarification"), dict(intent_name="greeting"),
                        dict(self_contained_request=False), dict(response_mode="conversation"),
                        dict(response_mode="carm"), dict(data={"needs_clarification": True}),
                        dict(_looks_like_live_local_query=lambda query: True)):
            self.assertFalse(self.scope(**changes)["full_factual_learning_answer"])

    def test_actual_branch_creates_persisted_layered_payload_and_questions(self):
        scope = self.scope()
        captured = []
        fetch = Mock(return_value=dict(answer="Sunlight is scattered by air molecules.",
                                      followups=["Why is the sky not violet?", "Why are sunsets red?"]))
        scope.update(re=re, question_intelligence_limit=question_intelligence_limit,
                     fetch_study_full=fetch, fallback_learning_questions=fallback_learning_questions,
                     _dedupe_followups=lambda items: list(dict.fromkeys(items)),
                     assess_ks_suitability=lambda *args: "recommended", now_label=lambda: "now",
                     has_existing_root=True, current_sid="chat-owner",
                     _append_nc_message=lambda prompt, payload, kind: captured.append(payload),
                     _persist_new_chat_session=lambda sid: None,
                     st=SimpleNamespace(rerun=lambda: (_ for _ in ()).throw(Rerun())))
        with self.assertRaises(Rerun):
            wrapper = ast.FunctionDef(name="run", args=ast.arguments(posonlyargs=[], args=[],
                kwonlyargs=[], kw_defaults=[], defaults=[]), body=[self.branch], decorator_list=[])
            ast.fix_missing_locations(wrapper)
            exec(compile(ast.Module(body=[wrapper], type_ignores=[]), "full-learning-branch", "exec"), scope)
            scope["run"]()
        fetch.assert_called_once_with("Why is the sky blue?", mode="clear", max_rounds=1)
        payload = captured[0]
        self.assertTrue(payload["question_intelligence"])
        self.assertTrue(payload["show_followups"])
        self.assertGreaterEqual(len(payload["followups"]), 3)
        self.assertEqual(payload["followups"][0], "Why is the sky not violet?")
        self.assertEqual(payload["context_intent"], "learning")
        self.assertEqual(payload["response_mode"], "standard")
        rows = dict(build_response_profile(payload["profile_prompt"], intent=payload["intent"],
                                           response_mode=payload["response_mode"], context_intent=payload["context_intent"]))
        self.assertEqual(rows["Broad field"], "Physics / Atmospheric optics")
        self.assertIn('st.tabs(', self.source)
        self.assertIn('response_payload.get("question_intelligence")', self.source)


if __name__ == "__main__":
    unittest.main()

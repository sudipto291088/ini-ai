import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from streamlit_app.learning_trail import render_trail_rows


class KnowledgeStructureCtaTests(unittest.TestCase):
    def render_app_cta(self, clicked=False, pending=None):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        branch = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                      and 'response_payload.get("knowledge_structure_available")' in ast.get_source_segment(source, n.test)
                      and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                              and x.func.id == "render_trail_rows" for x in ast.walk(n)))
        rows = MagicMock(return_value={"action": "open_knowledge_structure"} if clicked else None)
        queue = MagicMock()
        payload = dict(knowledge_structure_available=True, knowledge_structure_topic="Tribology",
                       knowledge_structure_data={"categories": {"Foundations": []}})
        scope = dict(response_payload=payload, response_card_key="answer_1",
                     st=SimpleNamespace(session_state={"_nc_pending_request": pending}),
                     render_trail_rows=rows, _queue_new_chat_request=queue,
                     knowledge_structure_action=lambda topic: dict(prompt=topic, request_kind="knowledge_structure", semantic_topic=topic))
        exec(compile(ast.Module(body=[branch], type_ignores=[]), "ks_cta", "exec"), scope)
        return rows, queue, payload

    def test_quiet_row_does_not_queue_until_clicked(self):
        rows, queue, _ = self.render_app_cta()
        action = rows.call_args.args[0][0]
        self.assertEqual(action["title"], "Explore the Knowledge Structure")
        self.assertEqual(action["icon"], "schema")
        self.assertTrue(action["description"])
        self.assertEqual(rows.call_args.kwargs["heading"], "")
        queue.assert_not_called()

    def test_click_preserves_original_topic_and_saved_structure(self):
        _, queue, payload = self.render_app_cta(clicked=True)
        queue.assert_called_once_with("Tribology", "interrogate", request_kind="knowledge_structure",
                                      semantic_topic="Tribology", knowledge_structure_data=payload["knowledge_structure_data"])

    def test_pending_request_disables_row(self):
        rows, _, _ = self.render_app_cta(pending={"prompt": "test"})
        self.assertTrue(rows.call_args.kwargs["disabled"])

    def test_empty_heading_does_not_render_empty_heading_element(self):
        with patch("streamlit_app.learning_trail.st") as st:
            st.button.return_value = False
            render_trail_rows([dict(action="open", title="Explore", description="Connections", icon="schema")], "ks", heading="")
            self.assertEqual(st.markdown.call_count, 1)  # shared stylesheet only
            self.assertIsNone(st.button.call_args.kwargs.get("help"))

    def test_cta_has_one_point_larger_text_and_no_underline(self):
        with patch("streamlit_app.learning_trail.st") as st:
            st.button.return_value = False
            render_trail_rows([dict(action="open_knowledge_structure", title="Explore", description="Connections", icon="schema")], "ks", heading="")
            css = st.markdown.call_args.args[0]
            scope = '[class*="st-key-ini_trail_action_"][class*="_open_knowledge_structure"]'
            self.assertIn(scope + ' button p {\n      font-size:13.5px !important;', css)
            self.assertIn(scope + ' button p + p {\n      font-size:13px !important;', css)
            self.assertIn(scope + ' button * {\n      text-decoration:none !important;', css)


if __name__ == "__main__":
    unittest.main()

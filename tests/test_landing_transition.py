import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock


class LandingTransitionTests(unittest.TestCase):
    def dispatch(self, result, curriculum=False):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        branch = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                      and isinstance(node.test, ast.Name) and node.test.id == "is_new_chat_landing")
        events = []
        slot = MagicMock()
        slot.container.return_value.__exit__.side_effect = lambda *args: events.append("exit_panel")
        slot.empty.side_effect = lambda: events.append("clear_panel")
        st = MagicMock()
        st.empty.return_value = slot
        st.session_state = SimpleNamespace(visitor_id="owner", api_base="local")
        queue = MagicMock(side_effect=lambda *args: events.append("queue"))
        qc = MagicMock()
        qc.maybe_start_qc.side_effect = lambda *args: events.append("curriculum_check") or curriculum
        scope = dict(is_new_chat_landing=True, st=st,
                     _render_new_chat_top_uib=lambda: result, qc_ui=qc,
                     _queue_new_chat_request=queue,
                     _attach_curriculum_to_new_chat=None, _advance_new_chat_composer=None)
        exec(compile(ast.Module(body=[branch], type_ignores=[]), "landing_dispatch", "exec"), scope)
        return events, queue

    def test_ml_clears_landing_before_response(self):
        events, queue = self.dispatch(("ml", True, False, None))
        self.assertEqual(events, ["exit_panel", "clear_panel", "curriculum_check", "queue"])
        queue.assert_called_once_with("ml", "interrogate")

    def test_illustration_and_explore_clear_before_dispatch(self):
        for result, expected in [(("a tree", False, True, None), ("a tree", "illustrate")),
                                 (("", False, False, "Physics"), ("Physics", "interrogate"))]:
            events, queue = self.dispatch(result)
            self.assertEqual(events, ["exit_panel", "clear_panel", "queue"])
            queue.assert_called_once_with(*expected)

    def test_empty_submission_preserves_landing(self):
        events, queue = self.dispatch(("  ", True, False, None))
        self.assertEqual(events, ["exit_panel"])
        queue.assert_not_called()

    def test_curriculum_clears_before_start_without_duplicate_request(self):
        events, queue = self.dispatch(("Teach me Physics", True, False, None), curriculum=True)
        self.assertEqual(events, ["exit_panel", "clear_panel", "curriculum_check"])
        queue.assert_not_called()


if __name__ == "__main__":
    unittest.main()

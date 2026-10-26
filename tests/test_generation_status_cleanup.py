"""Exercise the real generation handoff, including Streamlit rerun exits."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock


class RerunSignal(BaseException):
    pass


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class GenerationStatusCleanupTests(unittest.TestCase):
    def test_stale_loading_is_hidden_without_hiding_active_status_or_answers(self):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        styles = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.name == "_render_new_chat_bottom_uib_styles")
        st = MagicMock()
        scope = {"st": st}
        exec(compile(ast.Module(body=[styles], type_ignores=[]), "status_styles", "exec"), scope)
        scope[styles.name]()
        css = st.markdown.call_args.args[0]
        guard = re.search(r'([^{}]*\[data-stale="true"\][^{}]*)\{([^{}]*)\}', css)
        self.assertIsNotNone(guard)
        self.assertTrue(guard.group(1).strip().endswith('.nc-generation-placeholder'))
        self.assertIn('display: none !important', guard.group(2))
        self.assertNotIn('[data-stale="false"] .nc-generation-placeholder', css)

    def run_generation(self, failure=None, action="interrogate"):
        source = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                        and n.name == "_generate_pending_new_chat_response")
        events = []
        state = State(_nc_pending_request={"prompt": "How do vaccines train the immune system?",
                                          "action": action},
                      _nc_generating=False)
        slot = MagicMock()
        slot.empty.side_effect = lambda: events.append("clear")
        st = MagicMock()
        st.session_state = state

        def run(*args, **kwargs):
            events.append("generate")
            if failure:
                raise failure

        def rerun():
            events.append("rerun")
            raise RerunSignal()

        st.rerun.side_effect = rerun
        scope = dict(Any=object, st=st, re=re,
                     time=SimpleNamespace(time=lambda: 100.0, sleep=lambda _: None),
                     _render_new_chat_generation_placeholder=MagicMock(),
                     _is_explicit_qm_prompt=lambda _: False,
                     resolve_generation_status=lambda *a, **k: "forming",
                     _run_new_chat_interrogate=run, _run_new_chat_illustrate=run)
        exec(compile(ast.Module(body=[function], type_ignores=[]), "generation_handoff", "exec"), scope)
        with self.assertRaises(type(failure) if failure else RerunSignal):
            scope[function.name](slot)
        return events, state

    def test_status_clears_before_success_rerun(self):
        for action in ("interrogate", "illustrate"):
            with self.subTest(action=action):
                events, state = self.run_generation(action=action)
                self.assertEqual(events[-3:], ["generate", "clear", "rerun"])
                self.assertIsNone(state._nc_pending_request)
                self.assertFalse(state._nc_generating)

    def test_status_clears_when_inner_generation_requests_rerun(self):
        events, state = self.run_generation(RerunSignal())
        self.assertEqual(events[-2:], ["generate", "clear"])
        self.assertIsNone(state._nc_pending_request)
        self.assertFalse(state._nc_generating)

    def test_status_clears_on_generation_failure(self):
        events, state = self.run_generation(RuntimeError("provider unavailable"))
        self.assertEqual(events[-2:], ["generate", "clear"])
        self.assertIsNone(state._nc_pending_request)
        self.assertFalse(state._nc_generating)
        self.assertEqual(state._nc_generating_started_at, 0.0)


if __name__ == "__main__":
    unittest.main()

"""The floating UIB must be styled before slow subject rendering starts."""
import ast
from pathlib import Path
import unittest
from unittest.mock import MagicMock


SOURCE = (Path(__file__).parents[1] / "streamlit_app/app.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class ComposerStyleHandoffTests(unittest.TestCase):
    def test_styles_render_independently_of_composer_widgets(self):
        fn = next(n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef)
                  and n.name == "_render_new_chat_bottom_uib_styles")
        st = MagicMock()
        scope = {"st": st}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "uib_styles", "exec"), scope)
        scope[fn.name]()
        css = st.markdown.call_args.args[0]
        self.assertIn('input[aria-label="NC_BOTTOM_TOPIC"]', css)
        self.assertIn("position: fixed", css)
        self.assertIn("transform: translateX(-50%)", css)
        st.form.assert_not_called()
        st.text_input.assert_not_called()

    def test_styles_are_installed_before_subject_choice_and_timeline(self):
        page = next(n for n in TREE.body if isinstance(n, ast.FunctionDef)
                    and n.name == "page_new_chat")
        calls = [n for n in page.body if isinstance(n, ast.Expr)
                 and isinstance(n.value, ast.Call)
                 and isinstance(n.value.func, ast.Name)
                 and n.value.func.id == "_render_new_chat_bottom_uib_styles"]
        self.assertEqual(len(calls), 1)
        handoff_line = calls[0].lineno
        subject_choice = next(n for n in page.body if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == "subject_choice"
                                      for t in n.targets))
        self.assertLess(handoff_line, subject_choice.lineno)
        # Widget rendering no longer owns (and can no longer delay) the CSS.
        widgets = next(n for n in page.body if isinstance(n, ast.FunctionDef)
                       and n.name == "_render_new_chat_bottom_uib")
        self.assertNotIn("<style>", ast.get_source_segment(SOURCE, widgets))


if __name__ == "__main__":
    unittest.main()

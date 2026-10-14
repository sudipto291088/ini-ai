import ast
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class PageIconTests(unittest.TestCase):
    def test_both_entry_points_use_the_original_mukut(self):
        app_dir = Path(__file__).resolve().parents[1] / "streamlit_app"
        for name in ("app.py", "auth_test_app.py"):
            with self.subTest(entry_point=name):
                path = app_dir / name
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
                calls = [node for node in ast.walk(tree)
                         if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute)
                         and isinstance(node.func.value, ast.Name)
                         and node.func.value.id == "st"
                         and node.func.attr == "set_page_config"]
                self.assertEqual(len(calls), 1)
                icon = next(kw.value for kw in calls[0].keywords if kw.arg == "page_icon")
                icon_path = eval(compile(ast.Expression(icon), str(path), "eval"),
                                 {"Path": Path, "__file__": str(path)})
                self.assertEqual(Path(icon_path), app_dir / "ini_buta_icon_white.png")
                self.assertTrue(Path(icon_path).is_file())
                script = "import streamlit as st\n" + ast.unparse(calls[0])
                script = script.replace(ast.unparse(icon), repr(icon_path))
                app = AppTest.from_string(script).run()
                self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()

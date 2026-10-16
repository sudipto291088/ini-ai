import ast
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
from PIL import Image
from streamlit_app.page_branding import tab_icon


class PageIconTests(unittest.TestCase):
    def test_both_entry_points_use_the_approved_mukut_favicon(self):
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
                self.assertEqual(ast.unparse(icon), "tab_icon()")
                script = "import streamlit as st\nfrom streamlit_app.page_branding import tab_icon\n" + ast.unparse(calls[0])
                app = AppTest.from_string(script).run()
                self.assertEqual(len(app.exception), 0)

    def test_canvas_crop_preserves_the_exact_slim_mark_pixels(self):
        path = Path(__file__).resolve().parents[1] / "streamlit_app" / "mukut_favicon.png"
        with Image.open(path) as source:
            original = source.convert("RGBA")
        rendered = tab_icon()
        bounds = original.getchannel("A").point(lambda a: 255 if a > 200 else 0).getbbox()
        output_bounds = rendered.getchannel("A").point(lambda a: 255 if a > 200 else 0).getbbox()
        self.assertEqual(rendered.width, rendered.height)
        self.assertLess(rendered.height, original.height)
        self.assertEqual(original.crop(bounds).tobytes(), rendered.crop(output_bounds).tobytes())


if __name__ == "__main__":
    unittest.main()

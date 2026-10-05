import ast
from datetime import datetime
from pathlib import Path
from typing import Dict
import unittest


class SidebarClockTests(unittest.TestCase):
    def parts(self, hour, minute):
        source = (Path(__file__).parents[1] / "streamlit_app" / "app.py").read_text(encoding="utf-8")
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "clock_parts")
        scope = {"Dict": Dict, "_user_now": lambda: datetime(2026, 10, 4, hour, minute)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "clock_parts", "exec"), scope)
        return scope["clock_parts"]()

    def test_hands_match_display_and_hour_progress(self):
        for hour, minute, hour_angle, minute_angle in [
            (0, 0, 0, 0), (12, 0, 0, 0), (3, 30, 105, 180),
            (9, 45, 292.5, 270), (23, 59, 359.5, 354),
        ]:
            with self.subTest(hour=hour, minute=minute):
                result = self.parts(hour, minute)
                self.assertEqual(float(result["hour_angle"]), hour_angle)
                self.assertEqual(float(result["minute_angle"]), minute_angle)
                self.assertEqual(result["time"], f"{hour % 12 or 12}:{minute:02d}")

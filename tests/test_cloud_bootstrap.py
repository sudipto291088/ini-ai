import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CloudBootstrapTests(unittest.TestCase):
    def test_repository_imports_follow_path_setup(self):
        app = Path(__file__).parents[1] / "streamlit_app" / "app.py"
        source = app.read_text(encoding="utf-8")
        setup_line = source[:source.index("sys.path.insert(0, str(PROJECT_ROOT))")].count("\n") + 1
        for node in ast.parse(source).body:
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(("streamlit_app.", "api.")):
                self.assertGreater(node.lineno, setup_line, node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("streamlit_app.", "api.")):
                        self.assertGreater(node.lineno, setup_line, alias.name)

    def test_emphasis_import_with_no_repository_on_initial_path(self):
        app = Path(__file__).parents[1] / "streamlit_app" / "app.py"
        bootstrap = app.read_text(encoding="utf-8").split("\nimport requests", 1)[0]
        code = f"exec(compile({bootstrap!r}, {str(app)!r}, 'exec'), {{'__file__': {str(app)!r}}})"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-I", "-c", code], cwd=directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

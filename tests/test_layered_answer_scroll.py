import unittest
from pathlib import Path


class LayeredAnswerScrollTests(unittest.TestCase):
    def test_active_answer_has_one_owned_scroll_controller(self):
        source = (Path(__file__).parents[1] / "streamlit_app" / "app.py").read_text(encoding="utf-8")
        block = source.split("def _render_layered_answer(", 1)[1].split("answer_tabs_key =", 1)[0]
        self.assertIn("state.observer.observe(panel", block)
        self.assertIn("const bottom = text.getBoundingClientRect().bottom", block)
        self.assertIn("follower.key !==", block)
        self.assertIn("previous?.stop?.()", block)
        self.assertIn("window.addEventListener('pagehide', state.stop", block)
        self.assertNotIn("setTimeout(returnToAnswerStart", block)
        self.assertEqual(block.count("requestAnimationFrame(returnToAnswerStart)"), 1)


if __name__ == "__main__":
    unittest.main()

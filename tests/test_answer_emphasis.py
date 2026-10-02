import unittest
from pathlib import Path

from api.llm_answers import ANSWER_EMPHASIS_CONTRACT
from streamlit_app.answer_emphasis import emphasis_html
from api.study_ai import _build_instruction


class AnswerEmphasisTests(unittest.TestCase):
    def test_html_prose_renders_bold_without_allowing_html(self):
        self.assertEqual(emphasis_html('A **cell cycle** & <script>'),
                         'A <strong>cell cycle</strong> &amp; &lt;script&gt;')
        self.assertEqual(emphasis_html('Ordinary prose'), 'Ordinary prose')

    def test_contract_is_selective_and_preserves_non_prose_fields(self):
        for requirement in (
            "Markdown **bold**", "one or two per paragraph",
            "first meaningful occurrence", "Never bold whole paragraphs",
            "code, equations, URLs, map labels", "question/card titles",
            "structured profile values",
        ):
            self.assertIn(requirement, ANSWER_EMPHASIS_CONTRACT)

    def test_shared_answer_engine_applies_policy_only_to_text(self):
        source = (Path(__file__).parents[1] / "api" / "llm_answers.py").read_text(encoding="utf-8")
        self.assertIn("if not expects_json:\n        system_prompt += ANSWER_EMPHASIS_CONTRACT", source)

    def test_insight_and_technical_require_inline_emphasis(self):
        for mode in ("clear", "technical"):
            self.assertIn("**term**", _build_instruction(mode))

    def test_layered_views_do_not_reuse_legacy_plain_answer(self):
        source = (Path(__file__).parents[1] / "streamlit_app" / "app.py").read_text(encoding="utf-8")
        self.assertIn('response_payload.get("answer_emphasis_version") != 1', source)
        self.assertNotIn('answer_views.setdefault("technical", text)', source)
        self.assertNotIn('answer_views.setdefault("clear", text)', source)


if __name__ == "__main__":
    unittest.main()

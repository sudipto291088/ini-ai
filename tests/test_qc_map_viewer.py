import unittest
from unittest.mock import patch

from streamlit_app import qc_map_viewer


class SubjectMapViewerTests(unittest.TestCase):
    def test_viewer_receives_the_original_svg_and_subject_label(self):
        svg = '<svg viewBox="0 0 10 10"></svg>'
        with patch.object(qc_map_viewer, "_MAP_VIEWER") as component:
            qc_map_viewer.render_subject_map(svg, "Biology")

        component.assert_called_once_with(
            data={"svg": svg, "label": "Subject map for Biology"},
            key="qc_subject_map_viewer",
        )


if __name__ == "__main__":
    unittest.main()

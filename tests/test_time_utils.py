from datetime import datetime, timedelta, timezone
import unittest

from streamlit_app.time_utils import browser_local_now


class BrowserTimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.utc_now = datetime(
            2026,
            6,
            28,
            12,
            0,
            tzinfo=timezone.utc,
        )

    def test_converts_western_browser_offset(self) -> None:
        local_now = browser_local_now(240, utc_now=self.utc_now)

        self.assertEqual(local_now.hour, 8)
        self.assertEqual(
            local_now.utcoffset(),
            -timedelta(hours=4),
        )

    def test_converts_eastern_browser_offset(self) -> None:
        local_now = browser_local_now(-330, utc_now=self.utc_now)

        self.assertEqual((local_now.hour, local_now.minute), (17, 30))
        self.assertEqual(
            local_now.utcoffset(),
            timedelta(hours=5, minutes=30),
        )

    def test_preserves_utc(self) -> None:
        local_now = browser_local_now(0, utc_now=self.utc_now)

        self.assertEqual(local_now, self.utc_now)


if __name__ == "__main__":
    unittest.main()

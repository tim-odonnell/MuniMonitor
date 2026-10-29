"""Offline tests for the headless-browser layer's guard rails (no Chrome, no network needed)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import browser  # noqa: E402


class TestBrowserGuards(unittest.TestCase):
    def test_downloads_are_never_rendered(self):
        # Chrome hangs on file downloads; render() must refuse them without starting a browser.
        url = "https://www.michigan.gov/mshda/-/media/x/Notice-Change-in-Ownership.docx?rev=1&hash=2"
        self.assertEqual(browser.render(url), ("", []))

    def test_extension_ignores_query_string(self):
        self.assertEqual(browser._ext("https://www.michigan.gov/a/Bulletin-12.pdf?rev=9&hash=X"), ".pdf")
        self.assertEqual(browser._ext("https://www.michigan.gov/taxes/property"), "")

    def test_available_is_boolean(self):
        self.assertIsInstance(browser.available(), bool)


if __name__ == "__main__":
    unittest.main()

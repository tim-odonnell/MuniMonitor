"""Offline tests for the keyless official-source lookup (no network, no model)."""
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import officialweb as o  # noqa: E402


def _index(urls):
    docs = {u: o._words(u.split("michigan.gov", 1)[-1].replace("-", " ").replace("/", " ")) for u in urls}
    return {"n": len(docs), "df": Counter(w for ws in docs.values() for w in set(ws)),
            "pages": [{"url": u, "lastmod": "", "words": ws} for u, ws in docs.items()]}


class TestOfficialWeb(unittest.TestCase):
    def test_citation_urls(self):
        self.assertEqual(o.citation_urls("Under MCL 211.27a(7)(u), and 211.7cc too"),
                         ["https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-211-27a",
                          "https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-211-7cc"])
        self.assertEqual(o.citation_urls("It costs 12.50 dollars"), [])
        self.assertEqual(o.citation_urls("is 211.27a(7)(u) relevant"),
                         ["https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-211-27a"])

    def test_verify_quotes(self):
        chunks = [{"text": "Commercial purpose means used in connection with any business or other undertaking."}]
        ok = 'The law says "used in connection with any business or other undertaking".'
        bad = 'The law says "renting a house is never a commercial purpose at all".'
        self.assertEqual(o.verify_quotes(ok, chunks), [])
        self.assertEqual(len(o.verify_quotes(bad, chunks)), 1)

    def test_phrase_and_department_ranking(self):
        idx = _index(["https://www.michigan.gov/sos/news/board-of-state-canvassers-to-meet-march",
                      "https://www.michigan.gov/taxes/property/forms/instructions/board-of-review",
                      "https://www.michigan.gov/lara/long-term-care-facilities"])
        top = o.search_index("When must the March board of review meet?", idx, department="assessor")
        self.assertTrue(top[0][1].endswith("/board-of-review"))

    def test_expand_unknown_department_is_noop(self):
        self.assertEqual(o.expand("hello there", "nope"), "hello there")


if __name__ == "__main__":
    unittest.main()

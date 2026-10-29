#!/usr/bin/env python3
"""Unit tests for the brief-18 retrieval port: structured statute chunking
(RET-1/RET-2), definition expansion (RET-3) and CIT-2 label normalization.
This file is identical in all three departments on purpose — the ported code
drifted once (finding H2a), so the same tests must pass everywhere.
Run: python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from ingest import statute_chunks, build_definitions        # noqa: E402
from citations import normalize_label, validate_citations   # noqa: E402
from retrieve import Retriever, DEF_EXPANSION_CAP           # noqa: E402

MCL_TEXT = (
    " 211.27a Taxable value; transfers of ownership; exceptions.\n"
    " Sec. 27a.\n"
    "    (1) The taxable value of property shall be adjusted.\n"
    "    (a) A transfer of residential real property between family members.\n"
    "    (b) Notwithstanding subdivision (a), commercial purpose applies.\n"
    "    (2) Beginning December 31, 2014, a new exception applies.\n"
)

RULE_TEXT = (
    "    R 408.30505 Work exempt from permit.\n"
    "    Rule 505. Section R105.2 of the Michigan residential code is amended.\n"
    "    (a) General permit exception text.\n"
    "    (x) Decks, porches, patios, or similar structures not more than "
    "30 inches above grade.\n"
)


class TestStatuteChunking(unittest.TestCase):
    def test_mcl_one_chunk_per_lowest_subsection(self):
        chunks = statute_chunks(MCL_TEXT, "mcl-test.md", 1600, "LAW")
        self.assertIsNotNone(chunks)
        # header paragraph chunk, then one chunk per marker: (1) (a) (b) (2)
        self.assertEqual([c["id"] for c in chunks],
                         [f"mcl-test.md#{i}" for i in range(5)])
        for c in chunks:
            self.assertEqual(c["authority"], "LAW")
            self.assertEqual(c["source"], "mcl-test.md")
        self.assertNotIn("MCL", chunks[0]["text"])      # header chunk is unlabeled
        self.assertTrue(chunks[1]["text"].startswith("MCL 211.27a(1) — "))
        self.assertTrue(chunks[2]["text"].startswith("MCL 211.27a(1)(a) — "))
        self.assertTrue(chunks[3]["text"].startswith("MCL 211.27a(1)(b) — "))
        self.assertTrue(chunks[4]["text"].startswith(
            "MCL 211.27a(2) — beginning december 31, 2014 — "))

    def test_admin_rule_label_includes_amended_section(self):
        chunks = statute_chunks(RULE_TEXT, "rule-test.md", 1600, "LAW")
        self.assertIsNotNone(chunks)
        texts = [c["text"] for c in chunks]
        self.assertTrue(texts[1].startswith("R 408.30505 R105.2(a) — "))
        self.assertTrue(texts[2].startswith("R 408.30505 R105.2(a)(x) — "))
        self.assertIn("30 inches above grade", texts[2])

    def test_non_statute_text_returns_none(self):
        self.assertIsNone(statute_chunks(
            "AUTHORITY: OFFICE-PRACTICE\nJust some paragraphs of office notes.",
            "notes.md", 1600, "OFFICE-PRACTICE"))


class TestDefinitions(unittest.TestCase):
    def test_build_definitions(self):
        chunks = statute_chunks(MCL_TEXT, "mcl-test.md", 1600, "LAW")
        chunks.append({"id": "other.md#0", "source": "other.md",
                       "authority": "LAW",
                       "text": 'A "commercial purpose" means a business undertaking.'})
        defs = build_definitions(chunks)
        self.assertEqual(defs["commercial purpose"], "other.md#0")


def stub_retriever(definitions, chunks):
    """A Retriever without the index, for _expand_definitions unit tests."""
    r = Retriever.__new__(Retriever)
    r.definitions = definitions
    r.by_id = {c["id"]: c for c in chunks}
    return r


class TestDefinitionExpansion(unittest.TestCase):
    def test_bare_use_appends_definition_chunk(self):
        chunks = [
            {"id": "a.md#0", "source": "a.md", "authority": "LAW",
             "text": "The transfer of ownership triggers an uncap."},
            {"id": "a.md#1", "source": "a.md", "authority": "LAW",
             "text": 'A "transfer of ownership" means a conveyance.'},
        ]
        r = stub_retriever({"transfer of ownership": "a.md#1"}, chunks)
        out = r._expand_definitions([dict(chunks[0], score=5.0)])
        self.assertEqual([h["id"] for h in out], ["a.md#0", "a.md#1"])
        self.assertTrue(out[1]["expanded"])
        self.assertEqual(out[1]["score"], 0.0)

    def test_testcorpus_definitions_never_appended(self):
        chunks = [
            {"id": "a.md#0", "source": "a.md", "authority": "LAW",
             "text": "The deck triggers a permit."},
            {"id": "t.md#0", "source": "t.md", "authority": "TEST-CORPUS",
             "text": 'A "deck" means a raised platform.'},
        ]
        r = stub_retriever({"deck": "t.md#0"}, chunks)
        out = r._expand_definitions([dict(chunks[0], score=1.0)])
        self.assertEqual([h["id"] for h in out], ["a.md#0"])

    def test_cap_and_no_duplicate(self):
        chunks = [{"id": "a.md#0", "source": "a.md", "authority": "LAW",
                   "text": "uses term 0 term 1 term 2 term 3 term 4 term 5"},
                  *[{"id": f"d{i}.md#0", "source": f"d{i}.md", "authority": "LAW",
                     "text": f'A "term {i}" means x.'} for i in range(6)]]
        defs = {f"term {i}": f"d{i}.md#0" for i in range(6)}
        r = stub_retriever(defs, chunks)
        out = r._expand_definitions([dict(chunks[0], score=1.0)])
        self.assertEqual(len(out), 1 + DEF_EXPANSION_CAP)
        # a definition chunk already among the hits is never appended twice
        r2 = stub_retriever({"term one": "a.md#0"}, chunks[:2])
        out2 = r2._expand_definitions([dict(chunks[0], score=1.0)])
        self.assertEqual([h["id"] for h in out2], ["a.md#0"])


class TestCitationNormalization(unittest.TestCase):
    CHUNKS = [{"id": "corpus/mcl-211-27a.md#62", "text": "MCL 211.27a(7)(u)"}]

    def test_normalize_label(self):
        self.assertEqual(normalize_label("corpus/mcl-211-27a.md#62"),
                         "mcl-211-27a#62")
        self.assertEqual(normalize_label("mcl-211.27a.md#62"), "mcl-211-27a#62")
        self.assertEqual(normalize_label("overlay/mcl-211-27a.md#3"), "mcl-211-27a#3")

    def test_dotted_or_prefixed_cite_is_grounded_with_slip(self):
        r = validate_citations("Per [mcl-211.27a.md#62], see.", self.CHUNKS)
        self.assertEqual(r["ungrounded"], [])
        self.assertEqual(len(r["slips"]), 1)
        self.assertIn("-> corpus/mcl-211-27a.md#62", r["slips"][0])

    def test_exact_cite_is_not_a_slip(self):
        r = validate_citations("Per [corpus/mcl-211-27a.md#62], see.", self.CHUNKS)
        self.assertEqual(r["ungrounded"], [])
        self.assertEqual(r["slips"], [])

    def test_wrong_chunk_still_ungrounded(self):
        r = validate_citations("Per [mcl-211.999.md#1], see.", self.CHUNKS)
        self.assertIn("label:mcl-211.999.md#1", r["ungrounded"])


if __name__ == "__main__":
    unittest.main()

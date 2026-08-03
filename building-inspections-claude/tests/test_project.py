#!/usr/bin/env python3
"""Unit tests for the building & inspections assistant.

Run: python3 -m unittest discover -s tests -v
Covers the load-bearing logic, including regression tests for the defects found
in the 2026-07-08 project audit.
"""

import json
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from ingest import detect_authority, chunk_text            # noqa: E402
from llm_client import parse_bool, extract_json            # noqa: E402
from retrieve import Retriever                             # noqa: E402
from prompts import (INSPECTION_CHECKLISTS, VISION_SYSTEM,  # noqa: E402
                     GENERAL_QA_SYSTEM, build_vision_prompt)
from vision_check import solid_png, normalize_report       # noqa: E402
from new_photo_case import parse_finding                   # noqa: E402


class TestAuthority(unittest.TestCase):
    def test_levels_detected(self):
        for level in ("LAW", "STATE-GUIDANCE", "OFFICE-PRACTICE", "TEST-CORPUS"):
            self.assertEqual(detect_authority(f"AUTHORITY: {level}\n\nbody"), level)

    def test_untagged_and_late_tag(self):
        self.assertEqual(detect_authority("no tag here"), "UNTAGGED")
        # a tag appearing after the first 1000 chars must not count
        self.assertEqual(detect_authority("x" * 1100 + "\nAUTHORITY: LAW\n"), "UNTAGGED")


class TestRetrievalTestCorpusExclusion(unittest.TestCase):
    """Audit fix: TEST-CORPUS chunks must not crowd Michigan authority out of top-k."""

    def _retriever(self):
        r = Retriever.__new__(Retriever)
        chunks = []
        for i, (auth, text) in enumerate([
            ("LAW", "smoke alarm provisions amended by michigan rule"),
            ("TEST-CORPUS", "smoke alarm requirements for manufactured homes hud"),
            ("TEST-CORPUS", "smoke alarm detector locations federal standard"),
        ]):
            toks = text.split()
            chunks.append({"id": f"d{i}#0", "source": f"d{i}", "authority": auth,
                           "text": text, "length": len(toks),
                           "tf": {t: toks.count(t) for t in toks}})
        idf = {}
        for ch in chunks:
            for t in ch["tf"]:
                idf[t] = 1.0
        r.index = {"chunks": chunks, "idf": idf, "avg_len": 6.0, "n_chunks": 3}
        r.default_k = 6
        return r

    def test_excluded_by_default(self):
        hits = self._retriever().search("smoke alarm")
        self.assertEqual([h["authority"] for h in hits], ["LAW"])

    def test_included_with_flag(self):
        hits = self._retriever().search("smoke alarm", include_test_corpus=True)
        self.assertEqual(len(hits), 3)


class TestChunking(unittest.TestCase):
    def test_pack_and_split(self):
        text = "para one\n\npara two\n\n" + "x" * 50
        chunks = chunk_text(text, "s.md", max_chars=100, authority="LAW")
        self.assertTrue(all(len(c["text"]) <= 100 for c in chunks))
        self.assertEqual(chunks[0]["authority"], "LAW")
        big = chunk_text("y" * 250, "s.md", max_chars=100)
        self.assertEqual(len(big), 3)


class TestParseBool(unittest.TestCase):
    def test_table(self):
        for v, exp in [(True, True), ("no", False), ("No", False), (" FALSE ", False),
                       ("yes", True), ("1", True), (0, False)]:
            self.assertIs(parse_bool(v), exp)
        for bad in ("maybe", None, []):
            with self.assertRaises(ValueError):
                parse_bool(bad)


class TestExtractJson(unittest.TestCase):
    def test_think_block_decoy(self):
        raw = '<think>{"decoy": 1}</think>```json\n{"image_quality": "good"}\n```'
        self.assertEqual(extract_json(raw), {"image_quality": "good"})


class TestVision(unittest.TestCase):
    def test_probe_png_is_valid(self):
        png = solid_png(220, 30, 30)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertIn(b"IHDR", png)
        self.assertIn(b"IEND", png)

    def test_normalize_report_string_discipline(self):
        r = normalize_report({
            "image_quality": "EXCELLENT",           # invalid → poor (conservative)
            "possible_concerns": [{"concern": "x", "confidence": "HIGH"}, "bare"],
            "observations": None,
        })
        self.assertEqual(r["image_quality"], "poor")
        self.assertEqual(r["possible_concerns"][0]["confidence"], "high")
        self.assertEqual(r["possible_concerns"][1]["concern"], "bare")
        self.assertEqual(r["possible_concerns"][1]["confidence"], "low")
        self.assertEqual(r["observations"], [])

    def test_checklist_coverage_and_prompt(self):
        self.assertEqual(set(INSPECTION_CHECKLISTS), {
            "footing", "framing", "electrical_rough", "plumbing_rough",
            "insulation", "final"})
        p = build_vision_prompt("framing", "note")
        self.assertIn("joist hangers", p.lower())
        self.assertIn("note", p)

    def test_prompt_invariants(self):
        self.assertIn("cannot_verify_from_photo", VISION_SYSTEM)
        self.assertIn("never", VISION_SYSTEM.lower())
        self.assertIn("[VERIFY", VISION_SYSTEM)
        # QA prompt: TEST-CORPUS may never be Michigan authority
        self.assertIn("TEST-CORPUS", GENERAL_QA_SYSTEM)
        self.assertIn("NEVER cite it as Michigan authority", GENERAL_QA_SYSTEM)


class TestPhotoCase(unittest.TestCase):
    def test_parse_finding(self):
        f = parse_finding("missing hangers at ledger:visible")
        self.assertEqual(f, {"finding": "missing hangers at ledger",
                             "visible_in_photo": True})
        self.assertFalse(parse_finding("footing depth:hidden")["visible_in_photo"])
        with self.assertRaises(SystemExit):
            parse_finding("no visibility marker")


if __name__ == "__main__":
    unittest.main()


class TestCitations(unittest.TestCase):
    def setUp(self):
        from citations import validate_citations
        self.v = validate_citations
        self.chunks = [
            {"id": "mcl-act-442-1976-foia.md#41", "text": "15.243 Exemptions from disclosure R314.3 text here"},
            {"id": "demo-sop.md#0", "text": "office procedure"},
        ]

    def test_grounded(self):
        r = self.v("Per [mcl-act-442-1976-foia.md#41] and [41, 0], see MCL 15.243 and R314.3.", self.chunks)
        self.assertEqual(r["ungrounded"], [])

    def test_invented_statute_flagged(self):
        r = self.v("Personnel exemption per MCL 15.233 Section 3.", self.chunks)
        self.assertIn("statute:15.233", r["ungrounded"])

    def test_invented_label_and_index_flagged(self):
        r = self.v("See [made-up-doc.md#9] and [77].", self.chunks)
        self.assertIn("label:made-up-doc.md#9", r["ungrounded"])
        self.assertIn("chunk-index:77", r["ungrounded"])

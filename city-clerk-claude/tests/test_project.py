#!/usr/bin/env python3
"""Unit tests for the city clerk assistant.
Run: python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from ingest import detect_authority                        # noqa: E402
from llm_client import parse_bool, extract_json            # noqa: E402
from prompts import (GENERAL_QA_SYSTEM, FOIA_TRIAGE_SYSTEM,  # noqa: E402
                     FOIA_CATEGORIES, build_foia_prompt)
from foia_triage import normalize_triage                   # noqa: E402
from foia_backtest import score_case                       # noqa: E402


class TestPromptInvariants(unittest.TestCase):
    def test_qa_rules(self):
        for phrase in ("[VERIFY]", "NEVER present it as a legal requirement",
                       "attorney review", "election calendar"):
            self.assertIn(phrase, GENERAL_QA_SYSTEM)

    def test_foia_rules(self):
        for phrase in ("EXEMPTION FLAGGING IS YOUR MOST IMPORTANT JOB",
                       "needs_attorney_review", "never decide",
                       "must not promise records"):
            self.assertIn(phrase, FOIA_TRIAGE_SYSTEM)

    def test_prompt_builder_labels_authority(self):
        p = build_foia_prompt("req", [{"id": "x#0", "authority": "LAW", "text": "t"}])
        self.assertIn("(AUTHORITY: LAW)", p)


class TestNormalizeTriage(unittest.TestCase):
    def test_string_discipline(self):
        # The G1 lesson: model string booleans must never be truthiness-coerced.
        t = normalize_triage({"needs_attorney_review": "no", "category": "PERSONNEL",
                              "confidence": "VERY HIGH", "review_reasons": None})
        self.assertIs(t["needs_attorney_review"], False)
        self.assertEqual(t["category"], "personnel")
        self.assertEqual(t["confidence"], "low")
        self.assertEqual(t["review_reasons"], [])

    def test_unknown_category_and_conservative_clarification(self):
        t = normalize_triage({"needs_attorney_review": True,
                              "category": "weird", "clarification_needed": "dunno"})
        self.assertEqual(t["category"], "other")
        self.assertIs(t["clarification_needed"], True)  # unclear → ask

    def test_unparseable_review_flag_raises(self):
        with self.assertRaises(ValueError):
            normalize_triage({"needs_attorney_review": "maybe"})


class TestScoring(unittest.TestCase):
    def test_missed_flag_zero_tolerance_case(self):
        # Model says string "no" on a must-flag case → after normalization this
        # is a MISSED review flag, the zero-tolerance class.
        result = normalize_triage({"needs_attorney_review": "no", "category": "personnel"})
        s = score_case({"expected": {"needs_attorney_review": True,
                                     "category": "personnel"}}, result)
        self.assertTrue(s["missed_review_flag"])
        self.assertFalse(s["agree_review"])
        self.assertTrue(s["agree_category"])

    def test_false_flag_is_not_missed(self):
        result = normalize_triage({"needs_attorney_review": True, "category": "other"})
        s = score_case({"expected": {"needs_attorney_review": False,
                                     "category": "minutes_agendas"}}, result)
        self.assertTrue(s["false_flag"])
        self.assertFalse(s["missed_review_flag"])


class TestMisc(unittest.TestCase):
    def test_authority_levels(self):
        self.assertEqual(detect_authority("AUTHORITY: LAW\nx"), "LAW")
        self.assertEqual(detect_authority("no tag"), "UNTAGGED")

    def test_parse_bool_and_extract(self):
        self.assertIs(parse_bool("No"), False)
        self.assertEqual(extract_json('<think>{"a":1}</think>{"b":2}'), {"b": 2})

    def test_categories_closed_set(self):
        self.assertIn("personnel", FOIA_CATEGORIES)
        self.assertIn("other", FOIA_CATEGORIES)


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

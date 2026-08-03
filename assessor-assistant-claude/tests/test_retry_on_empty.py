#!/usr/bin/env python3
"""Unit tests for retry-on-empty in llm_client.chat().

The real failure occurs on roughly 6% of triage calls, so it cannot be tested
against a live server in reasonable time. These mock the transport instead and
assert the retry logic itself. See
docs/benchmarks/2026-08-03-empty-output-investigation.md for the measurements.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import llm_client as L  # noqa: E402

CFG = {"llm": {"base_url": "http://x", "model": "m", "max_tokens": 10,
               "temperature": 0.2, "timeout_seconds": 5, "retry_on_empty": 1}}


def cfg(**over):
    c = {"llm": dict(CFG["llm"])}
    c["llm"].update(over)
    return c


class RetryOnEmpty(unittest.TestCase):
    def setUp(self):
        self._real = L._once
        L.RETRY_STATS.update(calls=0, empty_responses=0, retried=0, still_empty=0)

    def tearDown(self):
        L._once = self._real

    def mock(self, seq):
        it = iter(seq)
        L._once = lambda llm, msgs: next(it)

    def test_retries_then_succeeds(self):
        self.mock(["", "a real answer"])
        self.assertEqual(L.chat([], cfg()), "a real answer")
        self.assertEqual(L.RETRY_STATS["retried"], 1)
        self.assertEqual(L.RETRY_STATS["still_empty"], 0)

    def test_persistent_empty_is_reported_not_hidden(self):
        self.mock(["", ""])
        self.assertEqual(L.chat([], cfg()), "")
        self.assertEqual(L.RETRY_STATS["still_empty"], 1)

    def test_whitespace_only_counts_as_empty(self):
        self.mock(["   \n\t ", "real"])
        self.assertEqual(L.chat([], cfg()), "real")

    def test_no_retry_at_temperature_zero(self):
        # Greedy decoding is deterministic — a retry returns the same empty
        # response, so spending the time would be pointless.
        self.mock([""])
        L.chat([], cfg(temperature=0))
        self.assertEqual(L.RETRY_STATS["retried"], 0)

    def test_can_be_disabled(self):
        self.mock([""])
        L.chat([], cfg(retry_on_empty=0))
        self.assertEqual(L.RETRY_STATS["retried"], 0)

    def test_multiple_retries_honoured(self):
        self.mock(["", "", "third"])
        self.assertEqual(L.chat([], cfg(retry_on_empty=2)), "third")
        self.assertEqual(L.RETRY_STATS["retried"], 2)

    def test_normal_path_makes_one_call(self):
        calls = []
        L._once = lambda llm, msgs: calls.append(1) or "fine"
        self.assertEqual(L.chat([], cfg()), "fine")
        self.assertEqual(len(calls), 1)
        self.assertEqual(L.RETRY_STATS["empty_responses"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

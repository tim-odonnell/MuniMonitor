"""Hybrid lexical scoring: stemmed BM25 + word-pair BM25 fused with the original score.

Stdlib only. Rank fusion (RRF) of three lists: the original BM25, the same BM25 over
lightly stemmed tokens (residents say "owned", statutes say "ownership"), and BM25 over
adjacent-word pairs (phrases such as "principal residence" outrank scattered matches).
Weights 1 / 2 / 1 were chosen on the E2B evaluation bank: gold passage in the top 6
rose Assessing 55 -> 61 %, Building 80 -> 82 %, Clerk 73 -> 75 %.
"""

import collections
import math

from ingest import tokenize

_SUFFIXES = ("ations", "ation", "ments", "ment", "ings", "ing", "ies", "ied",
             "ed", "es", "s", "ly", "al")
RRF_C = 60
DEPTH = 200
WEIGHTS = (1.0, 2.0, 1.0)  # original, stemmed, word pairs
K1, B = 1.2, 0.75


def stem(token: str) -> str:
    if token.isdigit() or len(token) < 5:
        return token
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


def _stems(text: str) -> list[str]:
    return [stem(t) for t in tokenize(text)]


def pairs(stems: list[str]) -> list[str]:
    return [a + "_" + b for a, b in zip(stems, stems[1:])]


class HybridIndex:
    def __init__(self, chunks: list[dict]) -> None:
        self.tf = []
        self.length = []
        df = collections.Counter()
        for ch in chunks:
            s = _stems(ch["text"])
            tf = collections.Counter(s)
            tf.update(pairs(s))
            self.tf.append(tf)
            self.length.append(len(s) or 1)
            df.update(tf.keys())
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.avg = sum(self.length) / n if n else 1.0

    def _bm25(self, terms: list[str]) -> list[float]:
        out = []
        for tf, length in zip(self.tf, self.length):
            score = 0.0
            for t in terms:
                f = tf.get(t)
                if f:
                    score += self.idf.get(t, 0.0) * f * (K1 + 1) / (
                        f + K1 * (1 - B + B * length / self.avg))
            out.append(score)
        return out

    def fuse(self, base_scores: list[float], query_terms: list[str]) -> list[float]:
        stems = [stem(t) for t in query_terms]
        lists = (base_scores, self._bm25(stems), self._bm25(pairs(stems)))
        fused = [0.0] * len(base_scores)
        for weight, scores in zip(WEIGHTS, lists):
            order = sorted(range(len(scores)), key=lambda i: -scores[i])[:DEPTH]
            for rank, i in enumerate(order):
                if scores[i] > 0:
                    fused[i] += weight / (RRF_C + rank)
        return fused

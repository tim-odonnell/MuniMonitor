#!/usr/bin/env python3
"""BM25 retrieval over the ingested corpus index.

Library use:   from retrieve import Retriever; Retriever().search(query, k)
CLI use:       python3 src/retrieve.py "does a spousal transfer uncap" --k 5
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config, tokenize  # noqa: E402

K1 = 1.5
B = 0.75


class Retriever:
    def __init__(self) -> None:
        cfg = load_config()
        index_file = ROOT / cfg["paths"]["index_file"]
        if not index_file.exists():
            raise FileNotFoundError(
                f"{index_file} not found — run `python3 src/ingest.py` first."
            )
        self.index = json.loads(index_file.read_text())
        self.default_k = cfg["retrieval"]["top_k"]
        # Minimum LAW-authority chunks guaranteed in a result set. 0 disables.
        self.min_law = int(cfg["retrieval"].get("min_law_chunks", 1))
        self.law_ratio = float(cfg["retrieval"].get("law_floor_min_score_ratio", 0.5))

    @staticmethod
    def _apply_authority_floor(scored: list, k: int, min_law: int,
                               min_ratio: float = 0.5) -> list:
        """Guarantee at least `min_law` LAW chunks in the result set, at CONSTANT k.

        Why this exists: the corpus mixes small statutes (mcl-211-7b.md, 5 chunks)
        with very large secondary guidance (stc-assessors-manual-vol3.md, 382KB).
        On concept queries the big documents take every slot, so the model answered
        STATUTORY questions purely from STATE-GUIDANCE — measured 2026-08-03,
        MCL 211.7b ranked 10th and MCL 211.34d 9th on their own topics with k=6.
        That defeats the LAW > STATE-GUIDANCE > OFFICE-PRACTICE hierarchy the whole
        design depends on.

        Size is held constant deliberately: simply raising k would enlarge the
        triage prompt (already ~11,291 tokens) and worsen the empty-output failures.
        We displace the LOWEST-scoring non-LAW chunks instead, and only ever promote
        chunks BM25 already scored above zero — never an unrelated statute.
        """
        head = scored[:k]
        if min_law <= 0 or len(head) < k:
            return head
        law_in_head = sum(1 for _s, ch in head if ch.get("authority") == "LAW")
        want = min(min_law, k) - law_in_head
        if want <= 0:
            return head
        others = [p for p in head if p[1].get("authority") != "LAW"]
        if not others:
            return head
        candidates = [p for p in scored[k:] if p[1].get("authority") == "LAW"]

        # RELEVANCE GUARD. Never trade a strong guidance hit for a weak statute.
        # Measured 2026-08-03: without this, the question "which FORM does a small
        # business file" evicted form-5076-small-business-exemption.md — the document
        # containing the answer — to force in two lower-scoring MCL 211.9o chunks.
        # A promotion only happens when the statute scores at least `min_ratio` of
        # the chunk it would displace.
        promote = []
        for cand in candidates:
            if len(promote) >= want or not others:
                break
            weakest = others[-1]
            if cand[0] >= weakest[0] * min_ratio:
                promote.append(cand)
                others.pop()
        if not promote:
            return head
        keep = [p for p in head if p[1].get("authority") == "LAW"]
        merged = keep + others + promote
        merged.sort(key=lambda pair: pair[0], reverse=True)
        return merged[:k]

    def search(self, query: str, k: int | None = None) -> list[dict]:
        k = k or self.default_k
        idf = self.index["idf"]
        avg_len = self.index["avg_len"] or 1.0
        q_terms = tokenize(query)
        scored = []
        for ch in self.index["chunks"]:
            tf, length = ch["tf"], ch["length"] or 1
            score = 0.0
            for t in q_terms:
                if t not in tf:
                    continue
                f = tf[t]
                score += idf.get(t, 0.0) * (f * (K1 + 1)) / (
                    f + K1 * (1 - B + B * length / avg_len)
                )
            if score > 0:
                scored.append((score, ch))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        selected = self._apply_authority_floor(scored, k, self.min_law, self.law_ratio)
        return [
            {
                "id": ch["id"],
                "source": ch["source"],
                "authority": ch.get("authority", "UNTAGGED"),
                "score": round(s, 3),
                "text": ch["text"],
            }
            for s, ch in selected
        ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Query the corpus index")
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=None)
    args = ap.parse_args()

    hits = Retriever().search(args.query, args.k)
    if not hits:
        print("No matching chunks.")
        return 1
    for h in hits:
        print(f"\n=== {h['id']}  [{h['authority']}]  (score {h['score']}) ===")
        text = h["text"]
        print(text[:600] + ("…" if len(text) > 600 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

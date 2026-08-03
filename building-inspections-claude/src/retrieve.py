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
        self.max_per_doc = int(cfg["retrieval"].get("max_per_document", 0))
        self.synonyms = {}
        if cfg["retrieval"].get("query_expansion", True):
            syn = ROOT / "corpus" / "SYNONYMS.json"
            if syn.exists():
                self.synonyms = {k.lower(): v for k, v in
                                 json.loads(syn.read_text()).items()
                                 if not k.startswith("_")}

    def expand(self, query: str) -> list[str]:
        """Add code vocabulary for the way residents actually ask.

        Homeowners ask "do I need a permit for a shed", not "is a detached
        accessory structure exempt from permit requirements". The resident's own
        words are ALWAYS kept — expansion only adds terms.
        """
        terms = tokenize(query)
        low = query.lower()
        for phrase, extra in self.synonyms.items():
            if phrase in low:
                terms.extend(t.lower() for t in extra)
        return terms

    @staticmethod
    def _cap_per_document(scored: list, k: int, cap: int) -> list:
        if cap <= 0:
            return scored[:k]
        out, seen = [], {}
        for pair in scored:
            src = pair[1].get("source", "?")
            if seen.get(src, 0) >= cap:
                continue
            out.append(pair); seen[src] = seen.get(src, 0) + 1
            if len(out) == k:
                break
        if len(out) < k:
            have = {id(p) for p in out}
            out.extend(p for p in scored if id(p) not in have)
        return out[:k]

    def search(self, query: str, k: int | None = None,
               include_test_corpus: bool = False) -> list[dict]:
        """include_test_corpus: TEST-CORPUS chunks (stand-in material from another
        jurisdiction, present only for pipeline validation) are EXCLUDED by default
        so they can never crowd Michigan authority out of the top-k slots."""
        k = k or self.default_k
        idf = self.index["idf"]
        avg_len = self.index["avg_len"] or 1.0
        q_terms = self.expand(query)
        scored = []
        for ch in self.index["chunks"]:
            if (not include_test_corpus
                    and ch.get("authority", "UNTAGGED") == "TEST-CORPUS"):
                continue
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
        scored = self._cap_per_document(scored, k, self.max_per_doc)
        return [
            {
                "id": ch["id"],
                "source": ch["source"],
                "authority": ch.get("authority", "UNTAGGED"),
                "score": round(s, 3),
                "text": ch["text"],
            }
            for s, ch in scored[:k]
        ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Query the corpus index")
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--include-test-corpus", action="store_true",
                    help="include TEST-CORPUS chunks (pipeline testing only)")
    args = ap.parse_args()

    hits = Retriever().search(args.query, args.k,
                              include_test_corpus=args.include_test_corpus)
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

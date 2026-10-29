#!/usr/bin/env python3
"""BM25 retrieval over the ingested corpus index.

Library use:   from retrieve import Retriever; Retriever().search(query, k)
CLI use:       python3 src/retrieve.py "does a spousal transfer uncap" --k 5
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config, tokenize  # noqa: E402

K1 = 1.5
B = 0.75

# Max definition chunks appended to one result set (RET-3). Definition chunks are
# full max_chars-sized, so this bounds the prompt growth from expansion.
DEF_EXPANSION_CAP = 4


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
        # Max chunks any ONE source document may occupy in a result set. Stops a
        # very large document from taking every slot: the Election Law is 1.6MB of
        # a 1.8MB corpus, and a question about "council minutes" was handing 3 of 6
        # slots to the retention schedule. 0 disables.
        self.max_per_doc = int(cfg["retrieval"].get("max_per_document", 0))
        # Colloquial -> statutory query expansion (corpus/SYNONYMS.json, optional).
        self.synonyms = {}
        if cfg["retrieval"].get("query_expansion", True):
            syn = ROOT / "corpus" / "SYNONYMS.json"
            if syn.exists():
                self.synonyms = {k.lower(): v for k, v in
                                 json.loads(syn.read_text()).items()
                                 if not k.startswith("_")}
        # Defined-term map built at ingest (RET-3): when a retrieved chunk uses a
        # defined term, the chunk that DEFINES it is appended to the result set.
        self.definitions = self.index.get("definitions", {})
        self.by_id = {c["id"]: c for c in self.index["chunks"]}

    def _expand_definitions(self, hits: list[dict]) -> list[dict]:
        """Append the chunks DEFINING terms used in the hits (ported from
        rag-exp/run.py expand_definitions). Uses of a quoted term ("public record")
        rank before bare word matches; capped at DEF_EXPANSION_CAP. TEST-CORPUS
        definitions are never appended."""
        defs = getattr(self, "definitions", {})
        by_id = getattr(self, "by_id", {})
        if not defs or not by_id:
            return hits
        have = {h["id"] for h in hits}
        quoted, bare = [], []
        for h in hits:
            text = h["text"].lower()
            for term, cid in defs.items():
                if cid in have:
                    continue
                if by_id[cid].get("authority") == "TEST-CORPUS":
                    continue
                if f'"{term}"' in text:
                    quoted.append(cid)
                elif re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", text):
                    bare.append(cid)
        added, seen = [], set(have)
        for cid in quoted + bare:
            if len(added) >= DEF_EXPANSION_CAP or cid in seen:
                continue
            seen.add(cid)
            ch = dict(by_id[cid])
            ch["expanded"] = True
            ch["score"] = 0.0
            added.append(ch)
        return hits + added

    def expand(self, query: str) -> list[str]:
        """Add statutory vocabulary for colloquial phrasings.

        Residents do not speak in statute. Measured 2026-08-03: 'right to speak at
        a city council meeting' put MCL 15.263(5) at rank 10 while the statutory
        phrasing put it at rank 1; 'how long does the city have to respond' put the
        FOIA response clock at rank 19. The resident's own words are ALWAYS kept —
        expansion only adds terms, so a question already phrased statutorily is
        unaffected.
        """
        terms = tokenize(query)
        low = query.lower()
        # getattr: a Retriever built via __new__ (as the unit tests do)
        # has no synonyms attribute, and expansion is optional anyway.
        for phrase, extra in getattr(self, "synonyms", {}).items():
            if phrase in low:
                terms.extend(t.lower() for t in extra)
        return terms

    @staticmethod
    def _cap_per_document(scored: list, k: int, cap: int) -> list:
        """Take top-k while allowing at most `cap` chunks from any one source."""
        if cap <= 0:
            return scored[:k]
        out, seen = [], {}
        for pair in scored:
            src = pair[1].get("source", "?")
            if seen.get(src, 0) >= cap:
                continue
            out.append(pair)
            seen[src] = seen.get(src, 0) + 1
            if len(out) == k:
                break
        # If the cap starved the result set, backfill with what was skipped so a
        # narrow single-document question still gets a full context.
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
        scored = self._cap_per_document(scored, k, getattr(self, "max_per_doc", 0))
        results = [
            {
                "id": ch["id"],
                "source": ch["source"],
                "authority": ch.get("authority", "UNTAGGED"),
                "score": round(s, 3),
                "text": ch["text"],
            }
            for s, ch in scored[:k]
        ]
        # RET-3: append chunks defining terms the results use (never displace a slot).
        return self._expand_definitions(results)


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

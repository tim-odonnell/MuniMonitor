#!/usr/bin/env python3
"""Retrieval-quality gate — runs in seconds, no LLM, fully deterministic.

Why this exists: a full --repeat 3 evaluation of the Q&A suite takes ~23 minutes
and, because the model is not reproducible, still cannot cleanly attribute a
change to a retrieval edit. This checks the question retrieval alone can answer:

  DOES THE RETRIEVED CONTEXT CONTAIN THE ANSWER AT ALL?

That is a hard upper bound on what the model could possibly get right. If the
answer terms are absent from the retrieved chunks, no amount of model quality
recovers it — and conversely, if they are present, a failure is the model's, not
retrieval's. Use this to iterate on retrieval settings quickly, then confirm the
winner with one full --repeat 3 run.

Also reports LAW-authority coverage, since the project's whole design rests on
LAW > STATE-GUIDANCE > OFFICE-PRACTICE and statutes were measured being crowded
out of the top-k by the very large secondary guidance documents (2026-08-03).

Usage:
  python3 tools/check_retrieval.py
  python3 tools/check_retrieval.py --sweep      # compare authority-floor settings
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from retrieve import Retriever  # noqa: E402


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[‐-―−]", "-", t)
    return re.sub(r"\s+", " ", t)


def evaluate(r: Retriever, cases: list[dict]) -> dict:
    present, missing, law_cov = 0, [], 0
    scored = 0
    for c in cases:
        hits = r.search(c["question"])
        if any(h["authority"] == "LAW" for h in hits):
            law_cov += 1
        exp = c.get("expect", {})
        pats = exp.get("must_include") or []
        if exp.get("honest_refusal") or not pats:
            continue          # refusal cases want ABSENCE; nothing to assert here
        scored += 1
        blob = norm(" ".join(h["text"] for h in hits))
        if all(re.search(p, blob, re.I) for p in pats):
            present += 1
        else:
            missing.append(c["case_id"].replace("TD-QA-", ""))
    return {"present": present, "scored": scored, "missing": missing,
            "law_cov": law_cov, "total": len(cases)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="testdata/qa")
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()

    cases = [json.loads(p.read_text())
             for p in sorted((ROOT / args.dir).glob("*.json"))]
    cases = [c for c in cases if c.get("task") == "qa"]
    if not cases:
        print(f"no qa cases in {args.dir}")
        return 1
    r = Retriever()

    # Not every sibling project has the authority floor — it currently lives only
    # in the assessor's retrieve.py (the three projects keep diverged copies of
    # ingest/retrieve/llm_client). Degrade to a plain answerability check there.
    has_floor = hasattr(r, "min_law")
    if not has_floor:
        if args.sweep:
            print("NOTE: this project's Retriever has no authority floor "
                  "(min_law_chunks); --sweep has nothing to vary. Running once.\n")
        settings = [None]
    else:
        settings = ([(0, 0.5), (1, 0.5), (1, 0.7), (2, 0.5), (2, 0.7), (3, 0.7)]
                    if args.sweep else [(r.min_law, r.law_ratio)])
    print(f"{len(cases)} cases from {args.dir}\n")
    print(f"{'min_law':>8} {'ratio':>6}   {'answer present':>15}   {'LAW in set':>12}   missing")
    for setting in settings:
        if setting is None:
            ml, ra = "n/a", "n/a"
        else:
            ml, ra = setting
            r.min_law, r.law_ratio = ml, ra
        m = evaluate(r, cases)
        print(f"{str(ml):>8} {str(ra):>6}   {m['present']:>7}/{m['scored']:<7}   "
              f"{m['law_cov']:>5}/{m['total']:<6}   {','.join(m['missing']) or '-'}")
    print("\n'answer present' = the retrieved chunks literally contain the expected\n"
          "terms; a hard upper bound on model accuracy. 'LAW in set' = cases whose\n"
          "context includes at least one statute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

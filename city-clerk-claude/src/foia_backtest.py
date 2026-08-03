#!/usr/bin/env python3
"""FOIA triage backtest — the validation gate's measuring stick.

Runs cases/*.json (past FOIA requests with the office's known handling) through
the triage pipeline and scores:
  - MISSED REVIEW FLAGS (expected attorney/coordinator review, model said no) —
    the ZERO-TOLERANCE class: a missed flag in production can mean unlawful
    disclosure that cannot be undone
  - false flags (cheap — coordinator glances and moves on)
  - category agreement
Aggregates exclude synthetic demo cases.

Case shape (cases/*.json):
  {"case_id": str, "task": "foia_triage", "synthetic": bool,
   "request_text": str,
   "expected": {"category": str, "needs_attorney_review": bool, "notes": str}}

Usage: python3 src/foia_backtest.py [--dry-run] [--case ID]
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config          # noqa: E402
from retrieve import Retriever                # noqa: E402
from llm_client import LLMError               # noqa: E402
from foia_triage import triage                # noqa: E402
from citations import validate_citations     # noqa: E402


def score_case(case: dict, result: dict) -> dict:
    exp = case["expected"]
    exp_review = bool(exp["needs_attorney_review"])
    got_review = result["needs_attorney_review"]  # normalized real bool
    return {
        "agree_review": got_review == exp_review,
        "missed_review_flag": exp_review and not got_review,
        "false_flag": (not exp_review) and got_review,
        "agree_category": result["category"] == str(exp.get("category", "")).strip().casefold(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the FOIA triage backtest")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--case", default=None)
    args = ap.parse_args()

    cfg = load_config()
    cases_dir = ROOT / cfg["paths"]["cases_dir"]
    results_dir = ROOT / cfg["paths"]["results_dir"]
    results_dir.mkdir(exist_ok=True)

    cases = []
    for p in sorted(cases_dir.glob("*.json")):
        c = json.loads(p.read_text())
        if c.get("task") == "foia_triage" and (not args.case or c["case_id"] == args.case):
            cases.append(c)
    if not cases:
        print(f"No foia_triage cases in {cases_dir}.")
        return 1

    retriever = Retriever()
    records, t_start = [], time.time()
    for case in cases:
        rec = {"case_id": case["case_id"], "synthetic": case.get("synthetic", False)}
        if args.dry_run:
            hits = retriever.search("freedom of information act " + case["request_text"])
            print(f"[dry-run] {case['case_id']}: {len(hits)} chunks retrieved")
            rec["retrieved"] = [h["id"] for h in hits]
            records.append(rec)
            continue
        t0 = time.time()
        try:
            result, hits = triage(case["request_text"], cfg, retriever)
            rec["triage"] = result
            rec["retrieved"] = [h["id"] for h in hits]
            rec["expected"] = case["expected"]
            rec["score"] = score_case(case, result)
            cite_text = " ".join([result["summary"],
                                  " ".join(result["review_reasons"]),
                                  result["draft_acknowledgment"]])
            rec["citations"] = validate_citations(cite_text, hits)
        except LLMError as e:
            print(f"FATAL: {e}")
            return 2
        except ValueError as e:
            rec["parse_failure"] = str(e)
        rec["seconds"] = round(time.time() - t0, 1)
        status = ("PARSE-FAIL" if "parse_failure" in rec
                  else "MISSED-FLAG ⚠" if rec["score"]["missed_review_flag"]
                  else "agree" if rec["score"]["agree_review"]
                  else "false-flag")
        print(f"{case['case_id']}: {status}  ({rec.get('seconds', 0)}s)")
        records.append(rec)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    (results_dir / f"foia-backtest-{ts}.json").write_text(json.dumps(records, indent=2))

    if not args.dry_run:
        real = [r for r in records if "score" in r and not r.get("synthetic")]
        synth = [r for r in records if "score" in r and r.get("synthetic")]
        n = len(real)
        agree = sum(r["score"]["agree_review"] for r in real)
        missed = [r["case_id"] for r in real if r["score"]["missed_review_flag"]]
        false_f = [r["case_id"] for r in real if r["score"]["false_flag"]]
        cat = sum(r["score"]["agree_category"] for r in real)
        fails = [r["case_id"] for r in records if "parse_failure" in r]
        cites_checked = sum(r.get("citations", {}).get("checked", 0) for r in real)
        ungrounded = [(r["case_id"], u) for r in real
                      for u in r.get("citations", {}).get("ungrounded", [])]

        lines = [
            f"# FOIA Backtest Report — {ts}", "",
            f"- Cases: {len(records)} (real scored: {n}, synthetic: {len(synth)}, "
            f"parse failures: {len(fails)})",
            "- Aggregates cover REAL cases only.",
            f"- **Review-flag agreement: {agree}/{n}"
            + (f" ({agree / n:.0%})**" if n else "**"),
            f"- **MISSED REVIEW FLAGS (zero-tolerance): {len(missed)}**"
            + (f" — {', '.join(missed)}" if missed else " ✓"),
            f"- False flags (coordinator-catchable): {len(false_f)}"
            + (f" — {', '.join(false_f)}" if false_f else ""),
            f"- Category agreement: {cat}/{n}",
            f"- **Ungrounded citations: {len(ungrounded)}/{cites_checked} checked**"
            + (f" — {'; '.join(f'{c}: {u}' for c, u in ungrounded)}" if ungrounded else " ✓"),
            f"- Wall time: {time.time() - t_start:.0f}s", "",
            "## Per-case detail", "",
        ]
        for r in records:
            lines.append(f"### {r['case_id']}"
                         + ("  *(synthetic demo)*" if r.get("synthetic") else ""))
            if "parse_failure" in r:
                lines.append(f"- parse failure: {r['parse_failure']}")
            elif "score" in r:
                e, t = r["expected"], r["triage"]
                lines.append(f"- expected: review={e['needs_attorney_review']}, "
                             f"category={e.get('category')}")
                lines.append(f"- model:    review={t['needs_attorney_review']}, "
                             f"category={t['category']}, confidence={t['confidence']}")
                if t["review_reasons"]:
                    lines.append(f"- reasons: {'; '.join(t['review_reasons'])}")
            lines.append("")
        report = results_dir / f"foia-backtest-{ts}-report.md"
        report.write_text("\n".join(lines))
        print(f"\nReport: {report}")
        if missed:
            print("⚠  MISSED REVIEW FLAGS — zero-tolerance criterion failed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

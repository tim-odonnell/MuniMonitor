#!/usr/bin/env python3
"""Q&A evaluation harness — City Clerk, citizen-facing questions.

foia_backtest.py scores FOIA request triage. This harness covers everything else
a clerk's office fields from citizens: records requests, open meetings, elections
and voter registration, retention — plus the class that matters most here,
HONEST REFUSAL.

Two clerk-specific hard rules are encoded as refusal cases: NEVER compute or state
an election date (cite the statutory basis and defer to the current SOS calendar —
the election calendar is this office's perishable item), and the corpus holds law
and procedure but NEVER the records themselves, so no voter data, no vital
records, no requested documents.

For every case in a Q&A case directory: retrieve → build the general Q&A prompt
→ run the local LLM → score the answer against expectations.

Scoring (all patterns are case-insensitive regexes):
  must_cite         every pattern must appear (statutory anchors)
  must_include      every pattern must appear (substantive content)
  must_not_include  no pattern may appear  <- FABRICATION, zero-tolerance
  honest_refusal    true = corpus cannot answer this; the model must decline

The zero-tolerance class here is FABRICATION: stating an election date, a fee
amount, a voter's registration status, or the contents of a record. A wrong
election date disenfranchises someone and cannot be walked back.

Usage:
  python3 src/qa_eval.py                          # run testdata/qa
  python3 src/qa_eval.py --dir some/other/dir
  python3 src/qa_eval.py --case TD-QA-PRE-001
  python3 src/qa_eval.py --area honest_refusal
  python3 src/qa_eval.py --dry-run                # retrieval only, no LLM
"""

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config                    # noqa: E402
from retrieve import Retriever                          # noqa: E402
from llm_client import chat, LLMError                   # noqa: E402
from prompts import GENERAL_QA_SYSTEM, build_qa_prompt  # noqa: E402

DEFAULT_DIR = "testdata/qa"


def load_cases(qa_dir: Path, only: str | None, area: str | None) -> list[dict]:
    cases = []
    for p in sorted(qa_dir.glob("*.json")):
        case = json.loads(p.read_text())
        if case.get("task") != "qa":
            continue
        if only and case["case_id"] != only:
            continue
        if area and case.get("area") != area:
            continue
        cases.append(case)
    return cases


def _norm(text: str) -> str:
    """Normalize model prose before matching.

    Models emit typographic Unicode — non-breaking hyphens in 'principal‑residence',
    NBSP inside 'June 1', a space inside '50 %'. Matching raw text against plain
    ASCII patterns produces FALSE FAILURES, which are worse than no harness at all.
    """
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[‐-―−]", "-", text)      # fancy hyphens/dashes
    text = re.sub(r"[    ]", " ", text)  # narrow/no-break spaces
    return re.sub(r"\s+", " ", text)


def _hits(patterns: list[str], text: str) -> list[str]:
    """Return the patterns that MATCH text (case-insensitive regex, normalized)."""
    t = _norm(text)
    return [p for p in patterns if re.search(p, t, re.I | re.S)]


# Sentences that DENY knowledge. A fabrication pattern matching inside one of
# these is a false positive, not a fabrication: "I cannot determine whether that
# contractor is currently licensed" contains "is currently licensed" but asserts
# the opposite. This bug was hit twice — once on an ECF probe, once on a
# contractor-licensing probe — so it is handled structurally here rather than by
# hand-tuning every pattern.
_DENIAL = re.compile(
    r"\b(cannot|can't|can not|could not|couldn't|unable|do not|don't|does not|"
    r"doesn't|did not|no information|not contain|not include|not provide|"
    r"not specify|not state|not available|unavailable|i'm sorry|i am sorry|"
    r"insufficient|outside|beyond|"
    # Redirects are refusals too: "You'll need to consult the clerk's files to
    # determine whether X is currently registered" asserts nothing.
    r"you('ll| will| should| may| must| need)|consult|contact|refer to|check with|"
    r"verify with|reach out)\b", re.I)


def strip_denials(text: str) -> str:
    """Drop sentences that deny knowledge before hunting for fabrication."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return " ".join(p for p in parts if not _DENIAL.search(p))


def score_answer(case: dict, answer: str) -> dict:
    exp = case.get("expect", {})
    must_cite = exp.get("must_cite", []) or []
    must_inc = exp.get("must_include", []) or []
    must_not = exp.get("must_not_include", []) or []
    wants_refusal = bool(exp.get("honest_refusal"))

    missing_cites = [p for p in must_cite if p not in _hits(must_cite, answer)]
    missing_inc = [p for p in must_inc if p not in _hits(must_inc, answer)]
    # Only count a fabrication if it survives outside a denial sentence.
    fabricated = _hits(must_not, strip_denials(answer))

    # A refusal case passes on the refusal axis when the answer signals it cannot
    # answer from the corpus AND does not assert a concrete value it invented.
    declined = bool(_hits(must_inc, answer)) if wants_refusal else None

    # EMPTY is its own failure class, not a wrong answer. gpt-oss can ruminate in
    # the reasoning channel until it exhausts max_tokens and emits no content at
    # all — observed live, 111s and 0 chars, on a question it answers fine on a
    # retry. Staff would see a blank draft after a long wait, so it must be
    # reported distinctly rather than buried in "FAIL".
    empty = not (answer or "").strip()

    ok = (not empty) and (not missing_cites) and (not missing_inc) and (not fabricated)
    return {
        "pass": ok,
        "empty": empty,
        "missing_cites": missing_cites,
        "missing_include": missing_inc,
        "fabricated": fabricated,          # zero-tolerance when non-empty
        "wants_refusal": wants_refusal,
        "declined": declined,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Q&A evaluation")
    ap.add_argument("--dir", default=DEFAULT_DIR, help=f"case dir (default {DEFAULT_DIR})")
    ap.add_argument("--case", default=None, help="run a single case_id")
    ap.add_argument("--area", default=None, help="run one area only")
    ap.add_argument("--repeat", type=int, default=1,
                    help="run every case N times and report per-case stability. The "
                         "model is NOT deterministic at temperature>0 — measured 43%% "
                         "flap rate on the triage suite — so a single run cannot "
                         "measure a case. Use 3+ before concluding anything.")
    ap.add_argument("--dry-run", action="store_true", help="skip the LLM call")
    args = ap.parse_args()

    cfg = load_config()
    qa_dir = ROOT / args.dir
    results_dir = ROOT / cfg["paths"]["results_dir"]
    results_dir.mkdir(exist_ok=True)

    cases = load_cases(qa_dir, args.case, args.area)
    if args.repeat > 1:
        cases = [dict(c, case_id=f"{c['case_id']}#r{i+1}")
                 for c in cases for i in range(args.repeat)]
    if not cases:
        print(f"No qa cases found in {qa_dir}.")
        return 1

    retriever = Retriever()
    records, t_start = [], time.time()

    for case in cases:
        cid = case["case_id"]
        hits = retriever.search(case["question"])
        record = {
            "case_id": cid,
            "area": case.get("area"),
            "synthetic": case.get("synthetic", False),
            "retrieved": [h["id"] for h in hits],
        }
        if args.dry_run:
            print(f"[dry-run] {cid}: {len(hits)} chunks -> "
                  + ", ".join(h["id"] for h in hits[:3]))
            records.append(record)
            continue

        messages = [
            {"role": "system", "content": GENERAL_QA_SYSTEM},
            {"role": "user", "content": build_qa_prompt(case["question"], hits)},
        ]
        t0 = time.time()
        try:
            answer = chat(messages, cfg)
        except LLMError as e:
            print(f"FATAL: {e}")
            return 2
        record["answer"] = answer
        record["score"] = score_answer(case, answer)
        record["seconds"] = round(time.time() - t0, 1)

        s = record["score"]
        status = ("FABRICATION ⚠" if s["fabricated"]
                  else "EMPTY ANSWER ⚠" if s["empty"]
                  else "pass" if s["pass"]
                  else "FAIL")
        print(f"{cid:<22} [{record['area']:<29}] {status}  ({record['seconds']}s)")
        records.append(record)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    (results_dir / f"qa-eval-{ts}.json").write_text(json.dumps(records, indent=2))

    if args.dry_run:
        print(f"\n[dry-run] wrote retrieval log to {results_dir}")
        return 0

    scored = [r for r in records if "score" in r]
    n = len(scored)
    passed = sum(r["score"]["pass"] for r in scored)
    fabrications = [r["case_id"] for r in scored if r["score"]["fabricated"]]
    empties = [r["case_id"] for r in scored if r["score"]["empty"]]
    refusal_cases = [r for r in scored if r["score"]["wants_refusal"]]
    refusal_ok = sum(bool(r["score"]["declined"]) for r in refusal_cases)

    by_area: dict[str, list] = {}
    for r in scored:
        by_area.setdefault(r["area"], []).append(r)

    lines = [
        f"# Q&A Evaluation Report — {ts}",
        "",
        "**All cases here are SYNTHETIC** — constructed from the corpus statutes, "
        "not real departmental questions. They test whether the pipeline handles "
        "each task area, not whether it is accurate enough to deploy.",
        "",
        f"- Cases run: {n}",
        f"- **Passed: {passed}/{n}**" + (f" ({passed / n:.0%})" if n else ""),
        f"- **FABRICATIONS (zero-tolerance): {len(fabrications)}**"
        + (f" — {', '.join(fabrications)}" if fabrications else " ✓"),
        f"- **EMPTY answers (model burned max_tokens reasoning): {len(empties)}**"
        + (f" — {', '.join(empties)}" if empties else " ✓"),
        f"- Honest-refusal cases declined correctly: {refusal_ok}/{len(refusal_cases)}",
        f"- Total wall time: {time.time() - t_start:.0f}s",
        "",
        "## By task area",
        "",
        "| Area | Passed |",
        "|---|---|",
    ]
    for area, rs in sorted(by_area.items()):
        lines.append(f"| {area} | {sum(r['score']['pass'] for r in rs)}/{len(rs)} |")
    if args.repeat > 1:
        from collections import defaultdict
        byc = defaultdict(list)
        for r in scored:
            byc[r["case_id"].split("#r")[0]].append(
                "EMPTY" if r["score"]["empty"]
                else "FAB" if r["score"]["fabricated"]
                else "ok" if r["score"]["pass"] else "fail")
        unstable = {k: v for k, v in byc.items() if len(set(v)) > 1}
        always_ok = [k for k, v in byc.items() if set(v) == {"ok"}]
        never_ok = [k for k, v in byc.items() if "ok" not in v]
        lines += ["", f"## Stability across {args.repeat} runs", "",
                  f"- Stable-correct every run: {len(always_ok)}/{len(byc)}",
                  f"- **NEVER correct (systematic weakness): {len(never_ok)}**"
                  + (f" — {', '.join(sorted(never_ok))}" if never_ok else " ✓"),
                  f"- **FLAPPING (outcome changed between identical runs): "
                  f"{len(unstable)}**"
                  + (f" — {', '.join(sorted(unstable))}" if unstable else " ✓"),
                  "", "Flapping means one run cannot measure that case. Only the "
                  "never-correct list is evidence of a real capability gap.", ""]
    lines += ["", "## Per-case detail", ""]
    for r in records:
        if "score" not in r:
            continue
        s = r["score"]
        lines.append(f"### {r['case_id']}  *({r['area']})*")
        lines.append(f"- result: {'PASS' if s['pass'] else 'FAIL'}"
                     + ("  **FABRICATION**" if s["fabricated"] else ""))
        if s["missing_cites"]:
            lines.append(f"- missing citations: `{'`, `'.join(s['missing_cites'])}`")
        if s["missing_include"]:
            lines.append(f"- missing content: `{'`, `'.join(s['missing_include'])}`")
        if s["fabricated"]:
            lines.append(f"- ⚠ asserted despite no source: `{'`, `'.join(s['fabricated'])}`")
        lines.append(f"- answer: {(r.get('answer') or '')[:600]}")
        lines.append("")

    report = results_dir / f"qa-eval-{ts}-report.md"
    report.write_text("\n".join(lines))
    print(f"\nPassed {passed}/{n}. Report: {report}")
    if fabrications:
        print("⚠  FABRICATIONS PRESENT — zero-tolerance criterion failed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

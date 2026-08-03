#!/usr/bin/env python3
"""PTA backtest harness — the Phase 4 measuring stick.

For every case in cases/*.json:  retrieve relevant corpus passages → build the
triage prompt → run the local LLM → parse the structured determination → score
against the known-correct answer.

Metrics reported (per action-plan Phase 4):
  - agreement rate on the uncapping yes/no call
  - MISSED UNCAPS (expected uncap, model said no) — the zero-tolerance class
  - false uncaps (model said uncap, expected exempt)
  - exception-category agreement, parse failures, confidence distribution

Usage:
  python3 src/backtest.py             # full run (needs llama-server up)
  python3 src/backtest.py --dry-run   # retrieval + prompt assembly only, no LLM
  python3 src/backtest.py --case PTA-001  # single case
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
from llm_client import chat, extract_json, normalize_verdict, LLMError  # noqa: E402
from prompts import PTA_TRIAGE_SYSTEM, build_user_prompt, triage_context  # noqa: E402
from citations import validate_citations  # noqa: E402


def load_cases(cases_dir: Path, only: str | None) -> list[dict]:
    cases = []
    for p in sorted(cases_dir.glob("*.json")):
        case = json.loads(p.read_text())
        if case.get("task") != "pta_triage":
            continue
        if only and case["case_id"] != only:
            continue
        cases.append(case)
    return cases


def score_case(case: dict, verdict: dict) -> dict:
    """Score a NORMALIZED verdict (see llm_client.normalize_verdict — regression G1:
    verdict['uncapping'] is a real bool here, never a model-supplied string)."""
    exp = case["expected"]
    got_uncap = verdict["uncapping"]
    exp_uncap = bool(exp["uncapping"])
    return {
        "agree_uncapping": got_uncap == exp_uncap,
        "missed_uncap": exp_uncap and not got_uncap,
        "false_uncap": (not exp_uncap) and got_uncap,
        "agree_exception": (
            verdict["exception_category"]
            == str(exp.get("exception", "")).strip().casefold()
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the PTA backtest")
    ap.add_argument("--dry-run", action="store_true", help="skip the LLM call")
    ap.add_argument("--case", default=None, help="run a single case_id")
    args = ap.parse_args()

    cfg = load_config()
    cases_dir = ROOT / cfg["paths"]["cases_dir"]
    results_dir = ROOT / cfg["paths"]["results_dir"]
    results_dir.mkdir(exist_ok=True)

    cases = load_cases(cases_dir, args.case)
    if not cases:
        print(f"No pta_triage cases found in {cases_dir}.")
        return 1

    retriever = Retriever()
    records, t_start = [], time.time()

    for case in cases:
        cid = case["case_id"]
        hits, _tail = triage_context(case["facts"], retriever)
        record = {
            "case_id": cid,
            "synthetic": case.get("synthetic", False),
            "retrieved": [h["id"] for h in hits],
        }
        if args.dry_run:
            print(f"[dry-run] {cid}: retrieved {len(hits)} chunks -> "
                  + ", ".join(h["id"] for h in hits[:3]) + " …")
            records.append(record)
            continue

        messages = [
            {"role": "system", "content": PTA_TRIAGE_SYSTEM},
            {"role": "user", "content": build_user_prompt(case["facts"], hits)},
        ]
        t0 = time.time()
        try:
            raw = chat(messages, cfg)
            verdict = normalize_verdict(extract_json(raw))
            record["verdict"] = verdict
            record["score"] = score_case(case, verdict)
            record["expected"] = case["expected"]
            record["citations"] = validate_citations(verdict["file_note"], hits)
        except LLMError as e:
            print(f"FATAL: {e}")
            return 2
        except ValueError as e:
            record["parse_failure"] = str(e)
        record["seconds"] = round(time.time() - t0, 1)

        status = ("PARSE-FAIL" if "parse_failure" in record
                  else "MISSED-UNCAP ⚠" if record["score"]["missed_uncap"]
                  else "agree" if record["score"]["agree_uncapping"]
                  else "DISAGREE")
        print(f"{cid}: {status}  ({record.get('seconds', 0)}s)")
        records.append(record)

    # ---- aggregate ----
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_json = results_dir / f"backtest-{ts}.json"
    out_json.write_text(json.dumps(records, indent=2))

    if not args.dry_run:
        # Aggregates cover REAL cases only — synthetic demo cases are excluded
        # (regression G3); they still appear in per-case detail, labeled.
        scored = [r for r in records if "score" in r and not r.get("synthetic")]
        synth_scored = [r for r in records if "score" in r and r.get("synthetic")]
        n = len(scored)
        agree = sum(r["score"]["agree_uncapping"] for r in scored)
        missed = [r["case_id"] for r in scored if r["score"]["missed_uncap"]]
        false_u = [r["case_id"] for r in scored if r["score"]["false_uncap"]]
        exc_agree = sum(r["score"]["agree_exception"] for r in scored)
        parse_fails = [r["case_id"] + (" (synthetic)" if r.get("synthetic") else "")
                       for r in records if "parse_failure" in r]
        cites_checked = sum(r.get("citations", {}).get("checked", 0) for r in scored)
        ungrounded = [(r["case_id"], u) for r in scored
                      for u in r.get("citations", {}).get("ungrounded", [])]

        lines = [
            f"# Backtest Report — {ts}",
            "",
            f"- Cases run: {len(records)}  (real scored: {n}, synthetic scored: "
            f"{len(synth_scored)}, parse failures: {len(parse_fails)})",
            "- **All aggregate metrics below cover REAL cases only** — synthetic "
            "demo cases are excluded and shown in per-case detail.",
            f"- **Agreement on uncapping call: {agree}/{n}"
            + (f" ({agree / n:.0%})**" if n else "** (no real cases run)"),
            f"- **MISSED UNCAPS (zero-tolerance): {len(missed)}**"
            + (f" — {', '.join(missed)}" if missed else " ✓"),
            f"- False uncaps (human-catchable): {len(false_u)}"
            + (f" — {', '.join(false_u)}" if false_u else ""),
            f"- Exception-category agreement: {exc_agree}/{n}",
            f"- **Ungrounded citations in file notes: {len(ungrounded)}/{cites_checked} checked**"
            + (f" — {'; '.join(f'{c}: {u}' for c, u in ungrounded)}" if ungrounded else " ✓"),
            f"- Parse failures: {', '.join(parse_fails) if parse_fails else 'none'}",
            f"- Total wall time: {time.time() - t_start:.0f}s",
            "",
            "## Per-case detail",
            "",
        ]
        for r in records:
            lines.append(f"### {r['case_id']}"
                         + ("  *(synthetic demo case)*" if r.get("synthetic") else ""))
            if "parse_failure" in r:
                lines.append(f"- parse failure: {r['parse_failure']}")
            elif "score" in r:
                v, e = r["verdict"], r["expected"]
                lines.append(f"- expected: uncap={e['uncapping']}, exception={e.get('exception')}")
                lines.append(f"- model:    uncap={v.get('uncapping')}, "
                             f"exception={v.get('exception_category')}, "
                             f"confidence={v.get('confidence')}")
                lines.append(f"- file note: {v.get('file_note', '')}")
            lines.append("")
        report = results_dir / f"backtest-{ts}-report.md"
        report.write_text("\n".join(lines))
        print(f"\nReport: {report}")
        if missed:
            print("⚠  MISSED UNCAPS PRESENT — zero-tolerance criterion failed.")
    else:
        print(f"\n[dry-run] wrote retrieval log: {out_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

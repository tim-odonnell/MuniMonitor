#!/usr/bin/env python3
"""Create a backtest case file (golden set / Phase 4 backtest builder).

Interactive:      python3 src/new_case.py
Non-interactive:  python3 src/new_case.py --id PTA-014 --uncap yes --exception none \
                      --facts "Warranty deed, arm's-length sale..." --notes "why"

Anonymization is YOUR job before facts go in: no real owner names, no exact
addresses (neighborhood/class is fine), no confidential financials.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config  # noqa: E402

EXCEPTIONS = ("none", "spouse", "family_residential", "trust", "joint_tenancy", "other")


def write_case(case_id: str, facts: str, uncap: bool, exception: str, notes: str) -> Path:
    if exception not in EXCEPTIONS:
        raise SystemExit(f"exception must be one of: {', '.join(EXCEPTIONS)}")
    cases_dir = ROOT / load_config()["paths"]["cases_dir"]
    out = cases_dir / f"{case_id}.json"
    if out.exists():
        raise SystemExit(f"{out} already exists — pick a new id.")
    out.write_text(json.dumps({
        "case_id": case_id,
        "task": "pta_triage",
        "synthetic": False,
        "facts": facts.strip(),
        "expected": {"uncapping": uncap, "exception": exception, "notes": notes.strip()},
    }, indent=2) + "\n")
    return out


def interactive() -> None:
    print("New backtest case — REMEMBER: anonymized facts only.\n")
    case_id = input("Case id (e.g. PTA-001): ").strip()
    print("Facts of the transfer (end with an empty line):")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    uncap = input("Correct determination — uncapping? (yes/no): ").strip().lower() in ("y", "yes", "true")
    exception = input(f"Exception category ({'/'.join(EXCEPTIONS)}): ").strip().lower() or "none"
    notes = input("Why (1-2 sentences): ").strip()
    out = write_case(case_id, "\n".join(lines), uncap, exception, notes)
    print(f"\nWrote {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a backtest case")
    ap.add_argument("--id")
    ap.add_argument("--facts")
    ap.add_argument("--uncap", choices=("yes", "no"))
    ap.add_argument("--exception", default="none", choices=EXCEPTIONS)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    if args.id and args.facts and args.uncap:
        out = write_case(args.id, args.facts, args.uncap == "yes", args.exception, args.notes)
        print(f"Wrote {out}")
    else:
        interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())

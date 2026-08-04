#!/usr/bin/env python3
"""Audit synthetic test cases against the statute — the weakest link, checked.

WHY. On 2026-08-04 TD-JOINT-003 failed 3 of 3 runs as a MISSED UNCAP — the metric
this project treats as a veto. The model was right and the case was wrong: I had
read only the operative clause of MCL 211.27a(7)(i) and missed its definitional
sentence two lines later ("A joint owner at the time of the last transfer of
ownership of the property is an original owner of the property"). That single bad
expected answer inflated the missed-uncap count across five separate studies and
turned two clean runs into apparent failures.

A wrong expected answer is worse than a missing test. It penalises correct legal
reasoning and corrupts the one metric treated as a veto.

This tool does not decide anything. It surfaces, for each case, the statutory
DEFINITIONS its facts implicate, so a human re-reads them before trusting the
expected answer. Definitions are where the traps are — the operative clause is
usually the easy part.

  python3 tools/audit_cases.py              # every case
  python3 tools/audit_cases.py --case TD-JOINT-003
  python3 tools/audit_cases.py --gaps       # only cases with underspecified facts
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Trigger -> the definition that governs it, and why it bites.
DEFINITIONS = {
    r"joint tenan": ("MCL 211.27a(7)(i)",
        "'A joint owner at the time of the last transfer of ownership of the property "
        "IS an original owner.' People who bought together are BOTH original owners — "
        "this is the definition that made TD-JOINT-003 wrong."),
    r"\brent|lease|business|commercial|office|airbnb|short-term": ("MCL 211.27a(11)(c)",
        "'Commercial purpose' EXCLUDES rental of residential real property for fewer "
        "than 15 days in a calendar year. Brief rental does not defeat the exception."),
    r"residential": ("MCL 211.27a(11) / 211.34c",
        "'Residential real property' means property CLASSIFIED as residential under "
        "section 34c — a classification test, not a description. State the "
        "classification in the facts or the case is underspecified."),
    r"agricultur": ("MCL 211.7dd via 27a(11)",
        "'Qualified agricultural property' takes its meaning from section 7dd, and "
        "(7)(o) requires the affidavit be filed with BOTH the assessor AND the "
        "register of deeds. Recapture follows a later change in use."),
    r"trust|settlor|beneficiar": ("MCL 211.27a(7)(g), (v)",
        "Into-trust (g) and out-of-trust (v) are DIFFERENT subdivisions with different "
        "tests. Both post-2014 branches need residential classification AND no "
        "commercial purpose — two conditions, not one."),
    r"life estate|life lease": ("MCL 211.27a(7)(c)",
        "The exemption covers only the portion SUBJECT to the life estate. Any portion "
        "not subject to it does transfer — partial uncapping is possible."),
    r"court|judgment|divorce": ("MCL 211.27a(7)(h)",
        "Court-ordered transfers are excepted UNLESS specific monetary consideration is "
        "specified or ordered. Consideration flips the answer."),
    r"foreclos|sheriff": ("MCL 211.27a(7)(e)",
        "Excepted until the mortgagee subsequently transfers — but adjusted anyway if "
        "not transferred within 1 year of the redemption period expiring."),
}
RELATIVES = ("mother", "father", "brother", "sister", "son", "daughter",
             "adopted son", "adopted daughter", "grandson", "granddaughter")


def audit(case: dict) -> list[str]:
    facts = case["facts"]
    low = facts.lower()
    notes = []
    for pat, (cite, why) in DEFINITIONS.items():
        if re.search(pat, low):
            notes.append(f"    {cite}: {why}")
    # Underspecification checks — the class that made TD-FAMRES-003 fail.
    exc = str(case["expected"].get("exception", ""))
    # Only a gap where the classification is LOAD-BEARING. (7)(a) spouse, (7)(b)
    # entireties, (7)(i) joint tenancy, (7)(e) foreclosure, (7)(h) court order and
    # (7)(m) entity transfers do not turn on the property being residential — a
    # plain sale least of all. Flagging those trains the reader to ignore the tool.
    if (exc in ("family_residential", "trust")
            and re.search(r"residential", low) and "classif" not in low):
        notes.append("    ⚠ GAP: this exception REQUIRES residential real property, but "
                     "the facts say 'residential' without stating the section 34c "
                     "classification. The model cannot verify the statutory test.")
    if exc in ("family_residential", "trust") and not re.search(r"\b(19|20)\d\d\b", facts):
        notes.append("    ⚠ GAP: relies on a branch beginning 'Beginning December 31, "
                     "2014' but states no transfer date — (7)(t) and (7)(u) cannot be "
                     "told apart.")
    if exc == "family_residential":
        named = [r for r in RELATIVES if r in low]
        if not named:
            notes.append("    ⚠ GAP: expects the family exception but names no relation "
                         f"from the enumerated list {RELATIVES}.")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="testdata/pta-triage")
    ap.add_argument("--case")
    ap.add_argument("--gaps", action="store_true", help="only cases with ⚠ gaps")
    args = ap.parse_args()

    files = sorted((ROOT / args.dir).glob("*.json"))
    shown = gaps = 0
    for p in files:
        c = json.loads(p.read_text())
        if args.case and c["case_id"] != args.case:
            continue
        notes = audit(c)
        has_gap = any("⚠" in n for n in notes)
        if args.gaps and not has_gap:
            continue
        gaps += has_gap
        shown += 1
        e = c["expected"]
        print(f"\n  {c['case_id']}  expected uncap={e['uncapping']} "
              f"exception={e.get('exception')}")
        for n in notes:
            print(n)
    print(f"\n  {shown} case(s) shown, {gaps} with underspecified facts.")
    print("  This tool flags what to RE-READ. It does not decide the answer.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

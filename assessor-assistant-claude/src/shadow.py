#!/usr/bin/env python3
"""Shadow-mode grading workflow — Phase 5 of the action plan.

Incoming PTAs get processed normally by staff AND run through the assistant.
The evaluator grades each AI draft against their own determination. Everything
is logged; the report checks the pilot's success criteria.

Anti-anchoring design: `grade` asks for the HUMAN determination first and only
then reveals the AI draft — the evaluator's call is never contaminated.

Commands:
  python3 src/shadow.py new                 # intake a case (runs the LLM now)
  python3 src/shadow.py new --no-llm        # intake only; run the LLM later
  python3 src/shadow.py run SHADOW-...      # (re)run the LLM on a pending case
  python3 src/shadow.py seed cases/X.json   # plant a tricky case with known answer
  python3 src/shadow.py grade SHADOW-...    # grade one case (human answer first!)
  python3 src/shadow.py status              # pending / graded overview
  python3 src/shadow.py report              # metrics vs. success criteria
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config                       # noqa: E402
from retrieve import Retriever                             # noqa: E402
from llm_client import chat, extract_json, normalize_verdict, LLMError  # noqa: E402
from prompts import PTA_TRIAGE_SYSTEM, build_user_prompt, triage_context  # noqa: E402

SHADOW_DIR = ROOT / "shadow"
PENDING = SHADOW_DIR / "pending"
GRADED = SHADOW_DIR / "graded"
EXCEPTIONS = ("none", "spouse", "family_residential", "trust", "joint_tenancy", "other")
USABILITY = {1: "use_as_is", 2: "minor_edits", 3: "major_edits", 4: "unusable"}


# ---------- helpers ----------

def ensure_dirs() -> None:
    PENDING.mkdir(parents=True, exist_ok=True)
    GRADED.mkdir(parents=True, exist_ok=True)


def next_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    existing = {p.stem for p in list(PENDING.glob("*.json")) + list(GRADED.glob("*.json"))}
    n = 1
    while f"SHADOW-{today}-{n:03d}" in existing:
        n += 1
    return f"SHADOW-{today}-{n:03d}"


def load_record(shadow_id: str) -> tuple[dict, Path]:
    for folder in (PENDING, GRADED):
        p = folder / f"{shadow_id}.json"
        if p.exists():
            return json.loads(p.read_text()), p
    raise SystemExit(f"No record named {shadow_id} in shadow/pending or shadow/graded.")


def save(record: dict, folder: Path) -> Path:
    out = folder / f"{record['shadow_id']}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    return out


def ask_yn(prompt: str) -> bool:
    while True:
        a = input(f"{prompt} (yes/no): ").strip().lower()
        if a in ("y", "yes"):
            return True
        if a in ("n", "no"):
            return False


def ask_choice(prompt: str, choices: tuple, default: str | None = None) -> str:
    while True:
        a = input(f"{prompt} [{'/'.join(choices)}]"
                  + (f" (default {default})" if default else "") + ": ").strip().lower()
        if not a and default:
            return default
        if a in choices:
            return a


def ask_int(prompt: str, valid: tuple | None = None) -> int:
    while True:
        a = input(f"{prompt}: ").strip()
        try:
            v = int(a)
            if valid is None or v in valid:
                return v
        except ValueError:
            pass


def read_multiline(header: str) -> str:
    print(f"{header} (end with an empty line):")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines)


def run_llm(record: dict, cfg: dict) -> None:
    """Run retrieval + triage LLM, storing the verdict (or failure) on the record."""
    hits, _tail = triage_context(record["facts"], Retriever())
    record["retrieved"] = [f"{h['id']} [{h['authority']}]" for h in hits]
    messages = [
        {"role": "system", "content": PTA_TRIAGE_SYSTEM},
        {"role": "user", "content": build_user_prompt(record["facts"], hits)},
    ]
    t0 = time.time()
    try:
        raw = chat(messages, cfg)
        # normalize_verdict guarantees a real bool for 'uncapping' (regression G1)
        record["verdict"] = normalize_verdict(extract_json(raw))
        record.pop("ai_failure", None)
    except ValueError as e:
        record["ai_failure"] = f"parse: {e}"
    record["llm_seconds"] = round(time.time() - t0, 1)


def show_verdict(record: dict) -> None:
    v = record.get("verdict")
    if not v:
        print(f"\n  AI DRAFT: MISSING ({record.get('ai_failure', 'LLM not run')})")
        return
    print("\n  ===== AI DRAFT (revealed after your determination) =====")
    print(f"  Uncapping: {v.get('uncapping')}")
    print(f"  Exception: {v.get('exception_category')}")
    print(f"  Confidence: {v.get('confidence')}")
    if v.get("missing_facts"):
        print(f"  Missing facts flagged: {'; '.join(v['missing_facts'])}")
    print(f"  File note: {v.get('file_note', '')}")
    print("  ========================================================")


# ---------- commands ----------

def cmd_new(args) -> int:
    ensure_dirs()
    cfg = load_config()
    facts = args.facts or read_multiline("Facts of the transfer (ANONYMIZED)")
    if not facts.strip():
        raise SystemExit("No facts entered.")
    record = {
        "shadow_id": next_id(),
        "created": datetime.now().isoformat(timespec="seconds"),
        "seeded": False,
        "facts": facts.strip(),
    }
    if not args.no_llm:
        run_llm(record, cfg)
        if "ai_failure" in record:
            print(f"NOTE: AI run failed ({record['ai_failure']}) — retry later with "
                  f"`shadow.py run {record['shadow_id']}`")
    out = save(record, PENDING)
    print(f"Stored {out.name}. Do NOT view the AI draft before making your own "
          f"determination. Grade with: python3 src/shadow.py grade {record['shadow_id']}")
    return 0


def cmd_run(args) -> int:
    record, path = load_record(args.shadow_id)
    if path.parent == GRADED:
        raise SystemExit(f"{args.shadow_id} is already graded.")
    run_llm(record, load_config())
    save(record, PENDING)
    print(f"LLM run complete for {args.shadow_id}"
          + (f" (FAILED: {record['ai_failure']})" if "ai_failure" in record else
             f" in {record['llm_seconds']}s."))
    return 0


def cmd_seed(args) -> int:
    """Plant a case with a known-correct answer to test evaluator vigilance."""
    ensure_dirs()
    case = json.loads(Path(args.case_file).read_text())
    record = {
        "shadow_id": next_id(),
        "created": datetime.now().isoformat(timespec="seconds"),
        "seeded": True,
        "seed_source": args.case_file,
        "expected": case["expected"],
        "facts": case["facts"],
    }
    if not args.no_llm:
        run_llm(record, load_config())
    out = save(record, PENDING)
    print(f"Seeded {out.name} from {args.case_file}. It will appear in the grading "
          f"queue like any other case; the expected answer is revealed after grading.")
    return 0


def cmd_grade(args) -> int:
    record, path = load_record(args.shadow_id)
    if path.parent == GRADED:
        raise SystemExit(f"{args.shadow_id} is already graded.")

    print(f"\n--- {record['shadow_id']} ---")
    print(f"FACTS:\n{record['facts']}\n")

    # 1. Human determination FIRST — the AI draft stays hidden until this is recorded.
    human = {
        "uncapping": ask_yn("YOUR determination — uncapping"),
        "exception": ask_choice("Exception category", EXCEPTIONS, default="none"),
    }
    record["human"] = human

    # 2. Reveal and grade the AI draft.
    show_verdict(record)
    v = record.get("verdict")
    if v:
        # v is normalized at run time — v["uncapping"] is a real bool (G1).
        agree = v["uncapping"] == human["uncapping"]
        record["grade"] = {
            "agree_uncapping": agree,
            "missed_uncap": human["uncapping"] and not v["uncapping"],
            "false_uncap": (not human["uncapping"]) and v["uncapping"],
            "agree_exception": v["exception_category"] == human["exception"],
            "usability": USABILITY[ask_int("File note usability (1=as-is 2=minor edits "
                                           "3=major edits 4=unusable)", (1, 2, 3, 4))],
            "minutes_saved": ask_int("Minutes this draft would have saved you (0 if none)"),
            "notes": input("Notes (especially on any disagreement): ").strip(),
        }
        print("\nAgreement on uncapping call: " + ("YES" if agree else "NO ⚠"))
    else:
        record["grade"] = {"ai_missing": True,
                           "notes": input("Notes: ").strip()}

    # 3. Seeded case: reveal the truth and score both the human and the AI.
    if record.get("seeded"):
        exp = record["expected"]
        print(f"\n*** SEEDED CASE — correct answer: uncapping={exp['uncapping']}, "
              f"exception={exp.get('exception')} ({exp.get('notes', '')}) ***")
        record["seed_result"] = {
            "human_correct": human["uncapping"] == bool(exp["uncapping"]),
            "ai_correct": v is not None and v["uncapping"] == bool(exp["uncapping"]),
        }
        if not record["seed_result"]["human_correct"]:
            print("⚠ The human determination did not match the seeded answer — "
                  "review this case together.")

    record["graded_at"] = datetime.now().isoformat(timespec="seconds")
    path.unlink()
    save(record, GRADED)
    print(f"\nGraded and filed: shadow/graded/{record['shadow_id']}.json")
    return 0


def cmd_status(_args) -> int:
    ensure_dirs()
    pending = sorted(PENDING.glob("*.json"))
    graded = sorted(GRADED.glob("*.json"))
    print(f"Pending: {len(pending)}")
    for p in pending:
        r = json.loads(p.read_text())
        flags = []
        if "verdict" not in r:
            flags.append("needs LLM run")
        if r.get("ai_failure"):
            flags.append("AI FAILED")
        print(f"  {r['shadow_id']}  ({', '.join(flags) if flags else 'ready to grade'})")
    print(f"Graded:  {len(graded)}")
    return 0


def cmd_report(_args) -> int:
    ensure_dirs()
    records = [json.loads(p.read_text()) for p in sorted(GRADED.glob("*.json"))]
    if not records:
        print("Nothing graded yet.")
        return 1

    # Success-criteria aggregates cover REAL (non-seeded) cases only — seeded
    # vigilance cases are scored in their own section (regression G3).
    scorable = [r for r in records if "grade" in r and not r["grade"].get("ai_missing")]
    scored = [r for r in scorable if not r.get("seeded")]
    n = len(scored)
    ai_missing = len(records) - len(scorable)
    agree = sum(r["grade"]["agree_uncapping"] for r in scored)
    missed = [r["shadow_id"] for r in scored if r["grade"]["missed_uncap"]]
    false_u = [r["shadow_id"] for r in scored if r["grade"]["false_uncap"]]
    usable = sum(r["grade"]["usability"] in ("use_as_is", "minor_edits") for r in scored)
    minutes = sum(r["grade"].get("minutes_saved", 0) for r in scored)
    seeded = [r for r in records if r.get("seeded") and "seed_result" in r]

    agree_rate = agree / n if n else 0.0
    usable_rate = usable / n if n else 0.0
    crit = [
        ("Agreement ≥95%", agree_rate >= 0.95, f"{agree_rate:.0%}"),
        ("Missed uncaps = 0 (zero-tolerance)", not missed,
         f"{len(missed)}" + (f" — {', '.join(missed)}" if missed else "")),
        ("Usable drafts (as-is + minor) ≥70%", usable_rate >= 0.70, f"{usable_rate:.0%}"),
    ]

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    lines = [
        f"# Shadow-Mode Report — {ts}",
        "",
        f"- Graded cases: {len(records)} (real scored: {n}, seeded: "
        f"{len(scorable) - n}, AI-missing/failed: {ai_missing})",
        "- Aggregates below cover real (non-seeded) cases only.",
        f"- Agreement on uncapping call: {agree}/{n} ({agree_rate:.0%})" if n else "-",
        f"- Missed uncaps: {len(missed)}" + (f" — {', '.join(missed)}" if missed else " ✓"),
        f"- False uncaps: {len(false_u)}" + (f" — {', '.join(false_u)}" if false_u else ""),
        f"- Draft usability: {usable}/{n} usable ({usable_rate:.0%})" if n else "-",
        f"- Estimated minutes saved (evaluator-reported): {minutes}",
        "",
        "## Success criteria (action-plan Phase 5)",
        "",
    ]
    print(f"\nShadow-mode report — {len(records)} graded cases")
    for name, ok, detail in crit:
        mark = "PASS ✓" if ok else "FAIL ✗"
        lines.append(f"- {mark} — {name}: {detail}")
        print(f"  {mark}  {name}: {detail}")

    if seeded:
        h_ok = sum(r["seed_result"]["human_correct"] for r in seeded)
        a_ok = sum(r["seed_result"]["ai_correct"] for r in seeded)
        lines += ["", "## Seeded-case vigilance",
                  "",
                  f"- Seeded cases graded: {len(seeded)}",
                  f"- Evaluator correct: {h_ok}/{len(seeded)}"
                  + ("  ⚠ evaluator vigilance issue — review together" if h_ok < len(seeded) else ""),
                  f"- AI correct: {a_ok}/{len(seeded)}"]
        print(f"  Seeded cases: evaluator {h_ok}/{len(seeded)}, AI {a_ok}/{len(seeded)}")

    # weekly trend
    weeks: dict[str, list] = {}
    for r in scored:
        wk = datetime.fromisoformat(r["graded_at"]).strftime("%G-W%V")
        weeks.setdefault(wk, []).append(r["grade"]["agree_uncapping"])
    if len(weeks) > 1:
        lines += ["", "## Weekly agreement trend", ""]
        for wk in sorted(weeks):
            vals = weeks[wk]
            lines.append(f"- {wk}: {sum(vals)}/{len(vals)} ({sum(vals)/len(vals):.0%})")

    lines += ["", "## Disagreements and notes", ""]
    for r in scored:
        g = r["grade"]
        if not g["agree_uncapping"] or g.get("notes"):
            lines.append(f"- **{r['shadow_id']}**"
                         + (" MISSED-UNCAP ⚠" if g["missed_uncap"] else "")
                         + (f" — {g['notes']}" if g.get("notes") else ""))

    results_dir = ROOT / load_config()["paths"]["results_dir"]
    results_dir.mkdir(exist_ok=True)
    out = results_dir / f"shadow-report-{ts}.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"\nReport written: {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Shadow-mode grading workflow")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="intake an incoming case")
    p_new.add_argument("--facts", help="facts inline (otherwise interactive)")
    p_new.add_argument("--no-llm", action="store_true", help="store facts only; run LLM later")
    p_new.set_defaults(fn=cmd_new)

    p_run = sub.add_parser("run", help="(re)run the LLM on a pending case")
    p_run.add_argument("shadow_id")
    p_run.set_defaults(fn=cmd_run)

    p_seed = sub.add_parser("seed", help="plant a case with a known answer (vigilance check)")
    p_seed.add_argument("case_file", help="backtest-style case JSON with an 'expected' block")
    p_seed.add_argument("--no-llm", action="store_true")
    p_seed.set_defaults(fn=cmd_seed)

    p_grade = sub.add_parser("grade", help="grade a pending case (your answer first)")
    p_grade.add_argument("shadow_id")
    p_grade.set_defaults(fn=cmd_grade)

    sub.add_parser("status", help="pending/graded overview").set_defaults(fn=cmd_status)
    sub.add_parser("report", help="metrics vs. success criteria").set_defaults(fn=cmd_report)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

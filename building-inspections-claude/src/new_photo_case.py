#!/usr/bin/env python3
"""Create a golden-photo-set case file for the vision validation gate.

Each case pairs a past-inspection photo with what the inspector ACTUALLY found,
marking per-finding whether it is visible in the photo — that flag defines what
the vision model can fairly be scored on (see docs/vision-test-plan.md).

Interactive:      python3 src/new_photo_case.py
Non-interactive:  python3 src/new_photo_case.py --id PHOTO-001 --type framing \\
                    --image eval/photos/PHOTO-001.jpg \\
                    --finding "missing joist hangers at ledger:visible" \\
                    --finding "footing depth insufficient:hidden" \\
                    --outcome "correction notice issued" --notes "why included"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT  # noqa: E402
from prompts import INSPECTION_CHECKLISTS  # noqa: E402

EVAL_DIR = ROOT / "eval"


def write_case(case_id: str, insp_type: str, image: str,
               findings: list[dict], outcome: str, notes: str) -> Path:
    if insp_type not in INSPECTION_CHECKLISTS:
        raise SystemExit(f"type must be one of: {', '.join(sorted(INSPECTION_CHECKLISTS))}")
    img_path = Path(image)
    if not img_path.exists():
        print(f"WARN: {image} does not exist yet — case written anyway; add the photo "
              f"(anonymized: no addresses, faces, or plates visible) before the eval run.")
    out = EVAL_DIR / f"{case_id}.json"
    if out.exists():
        raise SystemExit(f"{out} already exists — pick a new id.")
    out.write_text(json.dumps({
        "case_id": case_id,
        "inspection_type": insp_type,
        "image": str(image),
        "synthetic": False,
        "known_findings": findings,
        "inspector_outcome": outcome,
        "notes": notes,
    }, indent=2) + "\n")
    return out


def parse_finding(spec: str) -> dict:
    """'description:visible' or 'description:hidden'."""
    text, _, vis = spec.rpartition(":")
    if vis not in ("visible", "hidden") or not text:
        raise SystemExit(f"--finding must end in ':visible' or ':hidden' — got {spec!r}")
    return {"finding": text.strip(), "visible_in_photo": vis == "visible"}


def interactive() -> None:
    print("New golden photo case — photos must be anonymized (no addresses/faces/plates).\n")
    case_id = input("Case id (e.g. PHOTO-001): ").strip()
    insp_type = input(f"Inspection type ({'/'.join(sorted(INSPECTION_CHECKLISTS))}): ").strip()
    image = input("Image path (e.g. eval/photos/PHOTO-001.jpg): ").strip()
    findings = []
    print("Known findings from the ACTUAL inspection — empty description to stop.")
    while True:
        desc = input("  finding description: ").strip()
        if not desc:
            break
        vis = input("  visible in THIS photo? (yes/no): ").strip().lower() in ("y", "yes")
        findings.append({"finding": desc, "visible_in_photo": vis})
    if not findings:
        print("  (no findings — recording as a compliant photo, the false-flag test class)")
    outcome = input("Inspector outcome (e.g. passed / correction notice issued): ").strip()
    notes = input("Why this photo is in the set: ").strip()
    out = write_case(case_id, insp_type, image, findings, outcome, notes)
    print(f"\nWrote {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a vision golden-set case")
    ap.add_argument("--id")
    ap.add_argument("--type", dest="insp_type")
    ap.add_argument("--image")
    ap.add_argument("--finding", action="append", default=[],
                    help="'description:visible' or 'description:hidden' (repeatable)")
    ap.add_argument("--outcome", default="")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    if args.id and args.insp_type and args.image:
        findings = [parse_finding(f) for f in args.finding]
        out = write_case(args.id, args.insp_type, args.image, findings,
                         args.outcome, args.notes)
        print(f"Wrote {out}")
    else:
        interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())

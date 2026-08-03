#!/usr/bin/env python3
"""FOIA request triage — screen an incoming request for the FOIA coordinator.

Retrieval-grounded structured triage: category, likely record locations,
exemption flags (the zero-tolerance job: a missed flag can mean unlawful
disclosure), clarification questions, and a draft acknowledgment. The
coordinator makes every determination.

Usage:
  python3 src/foia_triage.py "text of the request"
  python3 src/foia_triage.py --file request.txt
  python3 src/foia_triage.py --file request.txt --json
  python3 src/foia_triage.py "..." --dry-run       # prompt only, no LLM
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
from llm_client import chat, extract_json, parse_bool, LLMError  # noqa: E402
from prompts import (FOIA_TRIAGE_SYSTEM, FOIA_CATEGORIES,  # noqa: E402
                     build_foia_prompt)


def normalize_triage(v: dict) -> dict:
    """Canonical-shape coercion. Raises ValueError only if needs_attorney_review
    is unparseable — the field the whole tool exists for is never guessed."""
    out = dict(v)
    out["summary"] = str(v.get("summary", ""))
    cat = str(v.get("category", "other")).strip().casefold()
    out["category"] = cat if cat in FOIA_CATEGORIES else "other"
    out["likely_record_locations"] = [str(x) for x in (v.get("likely_record_locations") or [])]
    out["needs_attorney_review"] = parse_bool(v.get("needs_attorney_review"))
    out["review_reasons"] = [str(x) for x in (v.get("review_reasons") or [])]
    try:
        out["clarification_needed"] = parse_bool(v.get("clarification_needed"))
    except ValueError:
        out["clarification_needed"] = True  # conservative: unclear → ask
    out["clarification_questions"] = [str(x) for x in (v.get("clarification_questions") or [])]
    conf = str(v.get("confidence", "")).strip().casefold()
    out["confidence"] = conf if conf in ("high", "medium", "low") else "low"
    out["draft_acknowledgment"] = str(v.get("draft_acknowledgment", ""))
    return out


def render(t: dict) -> str:
    lines = [
        "=" * 70,
        "DRAFT FOIA TRIAGE — FOIA COORDINATOR REVIEW REQUIRED",
        "The coordinator makes every determination; exemption and disclosure",
        "decisions are never the assistant's.",
        "=" * 70,
        f"Summary:   {t['summary']}",
        f"Category:  {t['category']}    Confidence: {t['confidence']}",
        f"Likely record locations: {'; '.join(t['likely_record_locations']) or '(none listed)'}",
        "",
        ("⚑ ATTORNEY/COORDINATOR REVIEW FLAGGED:" if t["needs_attorney_review"]
         else "No exemption flags raised — the coordinator still reviews (this is NOT a clearance)."),
    ]
    lines += [f"   - {r}" for r in t["review_reasons"]]
    if t["clarification_needed"]:
        lines.append("")
        lines.append("CLARIFICATION RECOMMENDED BEFORE PROCESSING:")
        lines += [f"   - {q}" for q in t["clarification_questions"]]
    lines += ["", "DRAFT ACKNOWLEDGMENT (edit before sending):", "-" * 40,
              t["draft_acknowledgment"]]
    return "\n".join(lines)


def _pinned_exemptions(retriever: Retriever) -> list[dict]:
    """ALWAYS include the FOIA exemptions section (MCL 15.243) and the office
    FOIA SOP in triage context (pinned-context lesson G8: the original build's
    retrieval once served a personnel-records request WITHOUT the exemptions
    section in context — the model then confabulated a statute number)."""
    foia = sorted((c for c in retriever.index["chunks"]
                   if c["source"] == "mcl-act-442-1976-foia.md"),
                  key=lambda c: int(c["id"].rsplit("#", 1)[1]))
    start = end = None
    for c in foia:
        n = int(c["id"].rsplit("#", 1)[1])
        if "15.243 Exempt" in c["text"] and start is None:
            start = n
        if start is not None and "15.244" in c["text"] and n > start:
            end = n
            break
    pinned = [c for c in foia
              if start is not None and start <= int(c["id"].rsplit("#", 1)[1]) <= (end or start)]
    pinned += [c for c in retriever.index["chunks"]
               if c.get("authority") == "OFFICE-PRACTICE" and "foia" in c["source"].lower()]
    return [{"id": c["id"], "source": c["source"],
             "authority": c.get("authority", "UNTAGGED"),
             "score": 0.0, "pinned": True, "text": c["text"]} for c in pinned]


def triage(request_text: str, cfg: dict, retriever: Retriever) -> dict:
    pinned = _pinned_exemptions(retriever)
    pinned_ids = {c["id"] for c in pinned}
    tail = [h for h in retriever.search(
        "freedom of information act request exemption response " + request_text)
        if h["id"] not in pinned_ids]
    hits = pinned + tail
    raw = chat([
        {"role": "system", "content": FOIA_TRIAGE_SYSTEM},
        {"role": "user", "content": build_foia_prompt(request_text, hits)},
    ], cfg)
    return normalize_triage(extract_json(raw)), hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Triage an incoming FOIA request (draft aid)")
    ap.add_argument("text", nargs="*", help="request text (or use --file)")
    ap.add_argument("--file", help="read request text from a file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="show prompt, no LLM")
    args = ap.parse_args()

    if args.file:
        request_text = Path(args.file).read_text().strip()
    else:
        request_text = " ".join(args.text).strip()
    if not request_text:
        ap.error("provide request text or --file")

    cfg = load_config()
    retriever = Retriever()

    if args.dry_run:
        hits = retriever.search("freedom of information act request exemption response "
                                + request_text)
        print(FOIA_TRIAGE_SYSTEM)
        print("-" * 70)
        print(build_foia_prompt(request_text, hits)[:3000])
        return 0

    t0 = time.time()
    try:
        result, hits = triage(request_text, cfg, retriever)
    except LLMError as e:
        print(f"ERROR: {e}")
        return 2
    except ValueError as e:
        print(f"Model output unparseable — handle this request manually. ({e})")
        return 1
    secs = round(time.time() - t0, 1)

    results_dir = ROOT / cfg["paths"]["results_dir"]
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = results_dir / f"foia-triage-{ts}.json"
    out.write_text(json.dumps({"ts": ts, "request": request_text,
                               "retrieved": [h["id"] for h in hits],
                               "seconds": secs, "triage": result}, indent=2))

    print(json.dumps(result, indent=2) if args.json else render(result))
    print(f"\n({secs}s — saved {out.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

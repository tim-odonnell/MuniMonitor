#!/usr/bin/env python3
"""Paced corpus fetcher for the Assessing Department Assistant.

RATE LIMITING IS THE POINT. legislature.mi.gov puts a CAPTCHA wall in front of
clients that request too fast — this happened on 2026-08-03 after a burst of
unpaced requests, and it blocks *all* further fetching for a while. So:

  * DEFAULT_DELAY is deliberately generous (8s). Do not lower it.
  * A CAPTCHA response ABORTS the whole run immediately. It never retries into
    the wall, and it never attempts to work around the block — if you are
    blocked, stop and come back later.
  * Anything already on disk is skipped, so an aborted run resumes cheaply.

Usage:
  python3 tools/fetch_corpus.py --list          # show the queue, fetch nothing
  python3 tools/fetch_corpus.py --tier 1        # highest-value gaps only
  python3 tools/fetch_corpus.py                 # everything queued
  python3 tools/fetch_corpus.py --delay 15      # slower still
"""
import argparse
import html
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
BASE = "https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) municipal-corpus-builder"}
DEFAULT_DELAY = 8.0

# (object-name, display number, why it matters). Tier 1 = cited by statutes we
# already store and already exercise in testdata/.
TIER1 = [
    ("211-1001", "211.1001", "Agricultural Property Recapture Act — REQUIRED by 27a(7)(o), which TD-OTHER-005 tests"),
    ("211-1002", "211.1002", "Recapture act: 'change in use' definition, referenced by 27a(7)(o)"),
    ("211-1031", "211.1031", "Qualified Forest Property Recapture Tax Act — referenced by 27a(7)(p)"),
    ("211-9m",   "211.9m",   "Eligible manufacturing personal property exemption (cited 12x)"),
    ("211-9n",   "211.9n",   "EMPP exemption continued (cited 7x)"),
    ("211-9p",   "211.9p",   "Personal property exemption (cited 6x)"),
    ("211-7jj",  "211.7jj",  "Qualified forest property exemption, pairs with 7ee"),
]
TIER2 = [
    ("211-10",  "211.10",  "Annual assessment duty — core assessing procedure"),
    ("211-24",  "211.24",  "Assessment roll contents and preparation"),
    ("211-25",  "211.25",  "Roll preparation (cited 7x)"),
    ("211-28",  "211.28",  "Board of review composition (cited 6x)"),
    ("211-30a", "211.30a", "Alternative board of review dates (cited 5x)"),
    ("211-34",  "211.34",  "County equalization"),
    ("211-34a", "211.34a", "Tabulation, equalization procedure"),
    ("211-7",   "211.7",   "General exemption provisions"),
    ("211-8",   "211.8",   "Personal property situs"),
    ("211-9",   "211.9",   "Personal property exemptions, general"),
    ("211-2a",  "211.2a",  "Tax day / situs supplements"),
    ("211-53a", "211.53a", "Recovery of excess payments"),
]
TIER3 = [
    ("205-735a", "205.735a", "Tax Tribunal jurisdiction/appeal procedure (cited 7x)"),
    ("205-737",  "205.737",  "Tax Tribunal valuation findings"),
    ("380-1211", "380.1211", "School operating millage — needed for qualified agricultural"),
]

# The Michigan Constitution (Art. IX §3 — Proposal A: 50% of true cash value and
# the inflation cap) is NOT fetchable through the mcl- object-name pattern used
# above. Every candidate pattern tried on 2026-08-03 returned the CAPTCHA wall
# before the naming could be confirmed. Resolve the correct URL manually before
# adding it here — do not guess-and-probe, that is what caused the block.
CONSTITUTION_TODO = "Const 1963, Art. IX §3 (Proposal A) — URL pattern UNCONFIRMED"


def is_captcha(text: str) -> bool:
    return "validation request" in text.lower() or "user validation required" in text.lower()


def extract(raw: str, num: str) -> tuple[str, str]:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|li|h\d)>", "\n", t, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    m = re.search(rf"^\s*{re.escape(num)}\s+(.+)$", text, re.M)
    heading = m.group(1).strip().rstrip(".") if m else ""
    start = m.start() if m else 0
    tail = re.search(r"\n\s*(History:|Compiler's note:|Popular name:|Rendered\s)", text[start:])
    body = text[start:start + tail.start()] if tail else text[start:]
    hist = re.search(r"\n\s*(History:.*?)(?:\n\s*(?:Popular name:|Rendered\s|©))", text[start:], re.S)
    if hist:
        body += "\n\n" + hist.group(1).strip()
    return heading, re.sub(r"\n{3,}", "\n\n", body).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", type=int, choices=(1, 2, 3), default=None)
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    queue = {1: TIER1, 2: TIER2, 3: TIER3}[args.tier] if args.tier else TIER1 + TIER2 + TIER3
    todo = [(o, n, w) for o, n, w in queue if not (CORPUS / f"mcl-{o}.md").exists()]

    print(f"queued: {len(queue)}   already on disk: {len(queue) - len(todo)}   to fetch: {len(todo)}")
    print(f"NOTE: {CONSTITUTION_TODO}\n")
    if args.list:
        for o, n, w in queue:
            mark = "have" if not any(o == t[0] for t in todo) else " -- "
            print(f"  [{mark}] MCL {n:<10} {w}")
        return 0

    ok = 0
    for i, (obj, num, why) in enumerate(todo, 1):
        try:
            req = urllib.request.Request(BASE + obj, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as e:
            print(f"  !! {num}: {e} — stopping"); return 2
        if is_captcha(raw) or len(raw) < 3000:
            print(f"\n  !! CAPTCHA / bot wall hit at MCL {num}.")
            print("     ABORTING. This is a rate limit — wait (hours, not minutes),")
            print("     then rerun; completed files are skipped automatically.")
            print("     Do NOT lower --delay and do NOT try to bypass the wall.")
            return 3
        heading, body = extract(raw, num)
        if len(body) < 400:
            print(f"  !! {num}: body too short ({len(body)}) — skipped, check manually")
            continue
        (CORPUS / f"mcl-{obj}.md").write_text(
            "AUTHORITY: LAW\n\n"
            f"# MCL {num} — {heading[:120]}\n\n"
            f"> Source: {BASE + obj} (retrieved {time.strftime('%Y-%m-%d')}).\n"
            "> Verbatim statute text extracted from the Michigan Legislature website.\n"
            "> VERIFY against the official source before relying on it in any determination.\n"
            f"> Added for: {why}\n\n{body}\n")
        ok += 1
        print(f"  ok {num:<10} {len(body):>7} chars  {heading[:52]}")
        if i < len(todo):
            time.sleep(args.delay)

    print(f"\nfetched {ok}/{len(todo)}")
    if ok:
        print("Next: python3 src/ingest.py   then re-run BOTH suites with --repeat 3.")
        print("Adding documents increases retrieval crowding — re-measure, do not assume.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Comprehensive Michigan assessing-law fetch — statutes, related acts, constitution.

PACING IS NOT OPTIONAL. legislature.mi.gov puts a CAPTCHA wall in front of clients
that request too fast; this happened on 2026-08-03 after a burst of unpaced
requests and blocked all fetching for hours. So:

  * DEFAULT_DELAY is 8s. Do not lower it.
  * A CAPTCHA response ABORTS the run. It never retries into the wall and never
    attempts to work around it — if blocked, stop and come back later.
  * Anything already on disk is skipped, so an aborted run resumes cheaply.

TARGETS, chosen rather than guessed:
  1. Every base section of the General Property Tax Act, MCL 211.1-211.157.
  2. Every MCL section the EXISTING corpus cites but does not contain — the law
     itself telling us what matters. Measured 2026-08-03: the corpus cited 179
     distinct sections and held 20.
  3. Michigan Constitution Article IX (finance and taxation) — including §3,
     Proposal A, the 50%-of-true-cash-value and inflation cap the whole system
     rests on, and §31, the Headlee limitation.
  4. Related acts an assessor is sent to by the GPTA: agricultural and forest
     recapture, the Tax Tribunal Act, school operating millage.

Suffixed sections (7cc, 27a, 34d …) are NOT brute-forced — that would be
thousands of requests and would trip the wall. They arrive via source 2, and a
second pass picks up anything newly cited by what the first pass downloaded.

Usage:
  python3 tools/fetch_all_michigan.py --list        # show the queue, fetch nothing
  python3 tools/fetch_all_michigan.py               # fetch everything missing
  python3 tools/fetch_all_michigan.py --delay 12    # slower
  python3 tools/fetch_all_michigan.py --limit 40    # stop after N successes
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
BASE = "https://www.legislature.mi.gov/Laws/MCL?objectName="
# Identify honestly. Pacing politely is being a good citizen; dressing automated
# traffic up as a browser to slip past bot detection is evading an access control
# the site operator deliberately put there.
UA = {"User-Agent": "MuniMonitor-corpus-builder/1.0 "
                    "(municipal assessing corpus; contact the local administrator)"}
DEFAULT_DELAY = 8.0

# Michigan Constitution of 1963, Article IX — Finance and Taxation.
CONSTITUTION = [(f"Article-IX-{n}", f"Const 1963, Art. IX §{n}") for n in range(1, 40)]

# Related acts the GPTA sends an assessor to.
RELATED = [
    ("211-1001", "Agricultural Property Recapture Act — required by MCL 211.27a(7)(o)"),
    ("211-1002", "Recapture act: 'change in use' definition"),
    ("211-1003", "Recapture act"), ("211-1004", "Recapture act"),
    ("211-1005", "Recapture act"), ("211-1006", "Recapture act"),
    ("211-1007", "Recapture act"),
    ("211-1031", "Qualified Forest Property Recapture Tax Act — MCL 211.27a(7)(p)"),
    ("211-1032", "Forest recapture: change in use"),
    ("211-1033", "Forest recapture"), ("211-1034", "Forest recapture"),
    ("211-1035", "Forest recapture"), ("211-1036", "Forest recapture"),
    ("205-703", "Tax Tribunal Act: definitions"),
    ("205-731", "Tax Tribunal: jurisdiction"),
    ("205-735", "Tax Tribunal: proceedings"),
    ("205-735a", "Tax Tribunal: appeal procedure (cited 7x by the corpus)"),
    ("205-737", "Tax Tribunal: valuation findings"),
    ("205-741", "Tax Tribunal: appeals"),
    ("205-744", "Tax Tribunal: costs"),
    ("380-1211", "Revised School Code: school operating millage — qualified agricultural"),
]


def is_captcha(t: str) -> bool:
    low = t.lower()
    return "validation request" in low or "user validation required" in low


def cited_but_missing() -> list[str]:
    """MCL sections the corpus cites but does not contain."""
    have = {p.stem.replace("mcl-", "").replace("-", ".") for p in CORPUS.glob("mcl-*.md")}
    txt = "\n".join(p.read_text(errors="ignore") for p in CORPUS.glob("*.md"))
    refs = set(re.findall(r"\bMCL\s+(\d+\.\d+[a-z]*)", txt))
    out = []
    for r in sorted(refs - have):
        num, sec = r.split(".", 1)
        out.append(f"{num}-{sec}")
    return out


def targets() -> list[tuple[str, str]]:
    seen, out = set(), []

    def add(obj, why):
        if obj in seen:
            return
        seen.add(obj)
        out.append((obj, why))

    # ORDER MATTERS. The 2026-08-03 run hit the CAPTCHA at item 162 of 336 with the
    # Constitution queued LAST, so Art. IX §3 — Proposal A, the 50% assessment level
    # and taxable-value cap the entire system rests on — was never fetched. Highest
    # constitutional and statutory value goes FIRST, so a partial run still lands the
    # things that matter most.
    for obj, why in CONSTITUTION:
        add(obj, why)
    for obj, why in RELATED:
        add(obj, why)
    for obj in cited_but_missing():               # what the law itself points at
        add(obj, "cited by the existing corpus but not held")
    for n in range(1, 158):                       # GPTA base sections, bulk last
        add(f"211-{n}", "General Property Tax Act base section")
    return out


def extract(raw: str, label: str) -> tuple[str, str]:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|li|h\d)>", "\n", t, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    m = re.search(rf"^\s*{re.escape(label)}\s+(.+)$", text, re.M)
    heading = m.group(1).strip().rstrip(".") if m else ""
    start = m.start() if m else 0
    tail = re.search(r"\n\s*(Popular name:|Rendered\s|©)", text[start:])
    body = text[start:start + tail.start()] if tail else text[start:]
    return heading, re.sub(r"\n{3,}", "\n\n", body).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    todo = [(o, w) for o, w in targets() if not (CORPUS / f"mcl-{o}.md").exists()]
    print(f"targets: {len(targets())}   already held: {len(targets()) - len(todo)}   "
          f"to fetch: {len(todo)}")
    print(f"at {args.delay}s pacing that is about "
          f"{len(todo) * args.delay / 60:.0f} minutes\n")
    if args.list:
        for o, w in todo[:60]:
            print(f"  {o:<16} {w}")
        if len(todo) > 60:
            print(f"  … and {len(todo) - 60} more")
        return 0

    ok = miss = 0
    for i, (obj, why) in enumerate(todo, 1):
        if args.limit and ok >= args.limit:
            print(f"\nreached --limit {args.limit}"); break
        try:
            req = urllib.request.Request(BASE + "mcl-" + obj, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                miss += 1                      # section does not exist; normal
                time.sleep(args.delay); continue
            print(f"  !! {obj}: HTTP {e.code} — stopping"); return 2
        except urllib.error.URLError as e:
            print(f"  !! {obj}: {e} — stopping"); return 2

        if is_captcha(raw):
            print(f"\n  !! CAPTCHA WALL hit at {obj} after {ok} successes.")
            print("     ABORTING — this is a rate limit. Wait (hours), then rerun;")
            print("     completed files are skipped automatically.")
            print("     Do NOT lower --delay and do NOT try to bypass the wall.")
            return 3

        label = obj.replace("Article-", "Art. ") if obj.startswith("Article") \
            else obj.replace("-", ".", 1)
        heading, body = extract(raw, label)
        if len(body) < 300:
            miss += 1
            time.sleep(args.delay); continue

        (CORPUS / f"mcl-{obj}.md").write_text(
            "AUTHORITY: LAW\n\n"
            f"# {label} — {heading[:130]}\n\n"
            f"> Source: {BASE}mcl-{obj} (retrieved {time.strftime('%Y-%m-%d')}).\n"
            "> Verbatim text from the Michigan Legislature website.\n"
            "> VERIFY against the official source before relying on it in any determination.\n"
            f"> Added for: {why}\n\n{body}\n")
        ok += 1
        print(f"  [{i}/{len(todo)}] ok {label:<14} {len(body):>7} chars  {heading[:46]}")
        time.sleep(args.delay)

    print(f"\nfetched {ok}   not found/empty {miss}")
    if ok:
        print("Next: python3 src/ingest.py")
        print("      python3 tools/check_retrieval.py     # crowding WILL have changed")
        print("      then re-run both suites with --repeat 3")
    return 0


if __name__ == "__main__":
    sys.exit(main())

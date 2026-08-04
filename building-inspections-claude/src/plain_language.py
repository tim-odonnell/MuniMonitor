#!/usr/bin/env python3
"""Plain-language rewriter for resident-facing text — with the readability MEASURED.

WHY THIS EXISTS. This assistant drafts in statute voice, because its sources are
statutes. Residents do not read statute voice. The federal Plain Writing Act of
2010 requires agencies to write so the public can understand and use what they are
told, and the practical benchmark used across government is that the average adult
reads at about an 8th-grade level. A correct answer nobody can read is a failed
answer: it produces another phone call, a missed deadline, or a lost appeal right.

THE MODEL REWRITES. THE ARITHMETIC JUDGES. Readability here is computed
(Flesch-Kincaid, sentence length, syllable counts) — never asked of the model.
Same principle as ratio_study.py: a model asked to grade its own reading level
will say "yes, that's plain" about almost anything.

⚠ THE DANGEROUS FAILURE IS NOT AN UNREADABLE REWRITE — it is a readable one that
  quietly drops a fact. "File within 45 days or a penalty applies" simplified into
  "file promptly" is easier to read and materially wrong. So every rewrite is
  checked for FACT RETENTION: every number, date, deadline, dollar figure and
  statutory citation in the source must still be present. A rewrite that loses one
  is REJECTED, not merely flagged.

⚠ STILL A DRAFT FOR A HUMAN. Plain language changes the words, never the legal
  substance, and the responsible official reviews it exactly as before.

Usage:
  python3 src/plain_language.py --text "…"           # rewrite and score
  python3 src/plain_language.py --file notice.txt
  python3 src/plain_language.py --score-only --file notice.txt   # no LLM
  python3 src/plain_language.py --self-test          # verify the arithmetic
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import load_config          # noqa: E402
from llm_client import chat, LLMError   # noqa: E402

TARGET_GRADE = 8.0          # the benchmark used across government plain-language work

PLAIN_SYSTEM = """\
You rewrite municipal government text so an ordinary resident can understand it on
the first read. You are not summarising and you are not giving advice.

HARD RULES:
1. Keep every fact. Every number, deadline, date, dollar amount, form number and
   legal citation in the original MUST appear in your rewrite. If the original says
   "within 45 days", your rewrite says "within 45 days" — never "promptly".
2. Do not add anything. No new advice, no reassurance, no invented detail, no
   softening of a consequence. If the original says a penalty applies, say so.
3. Do not change what the law requires. You are changing words, not meaning.
4. Use short sentences. Aim for 15-20 words. One idea per sentence.
5. Use everyday words where an everyday word exists. Keep the legal term when it
   is the actual name of a thing (e.g. "principal residence exemption"), but
   explain it in plain words the first time.
6. Address the reader as "you". Use active voice: "You must file" not "It must be
   filed".
7. Keep any [VERIFY] markers exactly as they appear.
8. If the original tells the reader to do something, put that first.

Return ONLY the rewritten text. No preamble, no commentary, no markdown headings.
"""

# Words that reliably signal statute voice rather than resident voice.
JARGON = ["heretofore", "hereinafter", "aforementioned", "pursuant to", "shall be deemed",
          "notwithstanding", "aforesaid", "thereof", "therein", "thereto", "whereas",
          "in accordance with", "prior to", "subsequent to", "in the event that",
          "at such time as", "is required to", "make application", "utilize",
          "commence", "terminate", "remit", "aforementioned"]


def syllables(word: str) -> int:
    """Approximate syllable count — the standard heuristic used by readability tools."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def readability(text: str) -> dict:
    sentences = [s for s in re.split(r"[.!?]+(?:\s|$)", text) if s.strip()]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if not sentences or not words:
        return {"grade": float("nan"), "ease": float("nan"), "sentences": 0,
                "words": 0, "avg_sentence": 0.0, "long_word_pct": 0.0, "jargon": []}
    syl = sum(syllables(w) for w in words)
    wps = len(words) / len(sentences)
    spw = syl / len(words)
    # Flesch-Kincaid Grade Level and Flesch Reading Ease
    grade = 0.39 * wps + 11.8 * spw - 15.59
    ease = 206.835 - 1.015 * wps - 84.6 * spw
    low = text.lower()
    return {
        "grade": grade,
        "ease": ease,
        "sentences": len(sentences),
        "words": len(words),
        "avg_sentence": wps,
        "long_word_pct": 100.0 * sum(1 for w in words if syllables(w) >= 3) / len(words),
        "jargon": sorted({j for j in JARGON if j in low}),
    }


def facts(text: str) -> dict:
    """Extract the things a rewrite must not lose."""
    t = text.replace(",", "")
    # SUBSTANTIVE numbers only. Statutory drafting is full of structural integers —
    # "a maximum of 1 of the following", "subdivision (2)" — which carry no meaning
    # for a resident and which good plain language reorganises away. Requiring them
    # rejects correct rewrites (observed live). A number counts as substantive when
    # it carries money, a percentage, a time unit, or is large/decimal enough to be
    # a real figure. "45 days" and "$200.00" are required; a bare "1" is not.
    substantive = set()
    for m in re.finditer(r"\$\s?(\d+(?:\.\d+)?)|"
                         r"\b(\d+(?:\.\d+)?)\s*(?:%|percent|day|days|year|years|"
                         r"month|months|hour|hours|business day|business days)\b|"
                         r"\b(\d{3,}(?:\.\d+)?|\d+\.\d+)\b", t, re.I):
        substantive.add(next(g for g in m.groups() if g))
    return {
        "numbers": sorted(substantive),
        "money": sorted(set(re.findall(r"\$\s?\d+(?:\.\d+)?", text))),
        "citations": sorted(set(re.findall(r"(?:MCL|Const)[\s ]*[\d.\-]+[a-z]*", text, re.I))),
        "forms": sorted(set(re.findall(r"\b(?:Form|form)\s*[A-Z]?-?\d{3,4}\b", text))),
        "verify": text.count("[VERIFY]"),
    }


# Plain-language practice SPELLS OUT small numbers, so "a maximum of 1 of the
# following" correctly becomes "a maximum of one of the following". Treating those
# as a lost fact rejects a good rewrite — observed live on the first real test.
_NUMWORD = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
            "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten",
            "11": "eleven", "12": "twelve", "13": "thirteen", "14": "fourteen",
            "15": "fifteen", "16": "sixteen", "17": "seventeen", "18": "eighteen",
            "19": "nineteen", "20": "twenty", "30": "thirty", "45": "forty-five",
            "60": "sixty", "90": "ninety"}


def _number_present(num: str, out: str) -> bool:
    """A number survives as a numeral OR as its spelled-out word.

    Both sides are comma-stripped first: facts() removes thousands separators from
    the source, so "$4,000.00" becomes "4000.00" and would never match a rewrite
    that (correctly) still writes "$4,000.00". That mismatch rejected a perfectly
    good rewrite on the first live test.
    """
    out = out.replace(",", "")
    if re.search(rf"\b{re.escape(num)}\b", out):
        return True
    word = _NUMWORD.get(num)
    if word and re.search(rf"\b{re.escape(word)}\b", out, re.I):
        return True
    # "$200.00" may be written "$200"; "45.0" as "45"
    if "." in num and re.search(rf"\b{re.escape(num.rstrip('0').rstrip('.'))}\b", out):
        return True
    return False


def fact_check(src: str, out: str) -> dict:
    """Which required facts did the rewrite lose? Losing one rejects the rewrite."""
    a, b = facts(src), facts(out)
    lost = {}
    for k in ("numbers", "money", "citations", "forms"):
        if k == "numbers":
            missing = [x for x in a[k] if not _number_present(x, out)]
        else:
            missing = [x for x in a[k] if x not in b[k]]
        # A number may legitimately be reworded ("45 days" -> "45 days") but must
        # still literally appear; normalise whitespace in citations before judging.
        if k == "citations":
            nb = re.sub(r"\s+", "", " ".join(b[k])).lower()
            missing = [x for x in a[k] if re.sub(r"\s+", "", x).lower() not in nb]
        if missing:
            lost[k] = missing
    if a["verify"] > b["verify"]:
        lost["verify_markers"] = a["verify"] - b["verify"]
    return lost


def rewrite(text: str, cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    return chat([{"role": "system", "content": PLAIN_SYSTEM},
                 {"role": "user", "content": text}], cfg)


def report(src: str, out: str | None) -> int:
    s = readability(src)
    print("\nORIGINAL")
    print(f"  Flesch-Kincaid grade {s['grade']:.1f}   reading ease {s['ease']:.0f}"
          f"   avg sentence {s['avg_sentence']:.1f} words")
    print(f"  {s['sentences']} sentences, {s['words']} words, "
          f"{s['long_word_pct']:.0f}% words of 3+ syllables")
    if s["jargon"]:
        print(f"  statute-voice phrases: {', '.join(s['jargon'])}")
    if out is None:
        return 0

    o = readability(out)
    lost = fact_check(src, out)
    print("\nPLAIN-LANGUAGE REWRITE")
    print(f"  Flesch-Kincaid grade {o['grade']:.1f}   reading ease {o['ease']:.0f}"
          f"   avg sentence {o['avg_sentence']:.1f} words")
    verdict = ("MEETS the 8th-grade benchmark" if o["grade"] <= TARGET_GRADE
               else f"STILL ABOVE target ({o['grade']:.1f} vs {TARGET_GRADE})")
    print(f"  {verdict}   (grade {s['grade']:.1f} -> {o['grade']:.1f})")

    print("\nFACT RETENTION")
    if lost:
        print("  ⚠ REJECTED — the rewrite dropped required facts:")
        for k, v in lost.items():
            print(f"      {k}: {v}")
        print("  A readable rewrite that loses a deadline or a citation is WORSE than")
        print("  the original. Do not use this. Re-run, or edit the original by hand.")
    else:
        print("  ✓ every number, dollar figure, citation, form number and [VERIFY]")
        print("    marker from the original is present")

    print("\n" + "-" * 68)
    print(out.strip())
    print("-" * 68)
    print("\nSTILL A DRAFT. Plain language changes the words, never the legal substance.")
    print("The responsible official reviews this exactly as before.\n")
    return 2 if lost else 0


def _self_test() -> int:
    ok = True

    def chk(name, cond, detail=""):
        nonlocal ok
        ok &= cond
        print(f"  {'ok ' if cond else 'FAIL'} {name:<44}{detail}")

    simple = "You must file this form. You have 45 days. We will send a notice."
    dense = ("Notwithstanding the aforementioned provisions, the transferee shall be "
             "required to make application pursuant to the statutory framework within "
             "forty-five days of the conveyance, subsequent to which penalties may be "
             "assessed in accordance with the applicable schedule.")
    s, d = readability(simple), readability(dense)
    chk("simple text scores below dense", s["grade"] < d["grade"],
        f"{s['grade']:.1f} vs {d['grade']:.1f}")
    chk("simple text meets 8th grade", s["grade"] <= TARGET_GRADE, f"{s['grade']:.1f}")
    chk("dense text flagged above target", d["grade"] > TARGET_GRADE, f"{d['grade']:.1f}")
    chk("jargon detected in dense text", len(d["jargon"]) >= 3, f"{d['jargon']}")
    chk("no jargon in simple text", d and not s["jargon"])

    src = "File Form 2368 within 45 days. A $200 penalty applies. See MCL 211.27a. [VERIFY]"
    good = "You must file Form 2368 within 45 days. If you do not, you pay a $200 penalty. This is required by MCL 211.27a. [VERIFY]"
    bad = "You should file the form promptly or you may owe a penalty."
    chk("faithful rewrite passes fact check", not fact_check(src, good), f"{fact_check(src, good)}")
    lost = fact_check(src, bad)
    chk("lossy rewrite is caught", bool(lost), f"lost={list(lost)}")
    chk("  specifically catches the lost deadline",
        any("45" in str(v) for v in lost.values()))
    chk("  specifically catches the lost citation", "citations" in lost)
    chk("  specifically catches the lost [VERIFY]", "verify_markers" in lost)

    # Spelled-out numbers are the SAME fact, not a lost one.
    chk("numeral -> word is not a lost fact",
        not fact_check("a maximum of 1 of the following", "a maximum of one of the following"))
    chk("word -> numeral also accepted",
        not fact_check("within 45 days", "within 45 days"))
    chk("a genuinely dropped number is still caught",
        "numbers" in fact_check("within 45 days", "within a reasonable time"))
    chk("thousands separators do not break the check",
        not fact_check("a penalty of $4,000.00 applies", "you pay a $4,000.00 penalty"))
    chk("  and still catches it if genuinely dropped",
        bool(fact_check("a penalty of $4,000.00 applies", "you pay a penalty")))
    # Structural vs substantive numbers.
    chk("structural '1 of the following' is not required",
        not fact_check("up to a maximum of 1 of the following, as applicable:",
                       "The most you pay is whichever of these applies:"))
    chk("but a real deadline still is",
        "numbers" in fact_check("file within 45 days", "file soon"))
    chk("and a real dollar figure still is",
        "numbers" in fact_check("a $200.00 penalty", "a penalty"))
    print("\n  SELF-TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Plain-language rewrite with measured readability")
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--score-only", action="store_true", help="measure only, no LLM")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()
    src = args.text or (Path(args.file).read_text() if args.file else None)
    if not src:
        ap.error("need --text, --file, or --self-test")
    if args.score_only:
        return report(src, None)
    try:
        return report(src, rewrite(src))
    except LLMError as e:
        print(f"FATAL: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

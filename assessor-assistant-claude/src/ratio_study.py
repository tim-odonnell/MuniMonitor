#!/usr/bin/env python3
"""Sales-ratio study — deterministic assessment-equity analysis.

WHY THIS IS NOT AN LLM TASK. Every number here is ARITHMETIC over real sales and
assessments. A language model must never produce these figures: a fabricated
coefficient of dispersion or a wrong median ratio would propagate straight into
assessment decisions and taxpayer appeals, and it would be indistinguishable from
a real one. So this module computes; the assistant may only ever explain what a
computed report already says. Nothing in this file calls a model.

WHAT IT MEASURES (IAAO Standard on Ratio Studies, 2013):
  Level      median ratio — are we assessing at the legal level? Michigan's legal
             level is 50% of true cash value (MCL 211.27), so the target median
             ratio of assessed value to sale price is 0.50.
  Uniformity COD, coefficient of dispersion. Random inequity — how scattered are
             ratios around the median. IAAO single-family: 5-10 for newer or
             fairly similar homes, 5-15 for older or heterogeneous areas.
  Regressivity
             PRD, price-related differential (IAAO 0.98-1.03). Above 1.03 means
             lower-value homes are assessed at HIGHER ratios than higher-value
             homes — regressive taxation, the pattern the University of Chicago
             Center for Municipal Finance found across the country including
             Wayne County, Michigan.
             PRB, price-related bias (IAAO -0.05 to +0.05). A regression-based
             measure of the same thing, less sensitive to extreme values.

⚠ THIS IS A SCREENING TOOL, NOT A VERDICT. A failing COD or PRD says the ROLL
  deserves examination; it does not prove any individual assessment is wrong, and
  it is not by itself a defense or a basis for changing a single parcel. Sales
  samples are small, sales are not always arm's-length, and the assessor is the
  one who decides. Outlier parcels are flagged as REVIEW CANDIDATES only.

⚠ DATA NEVER ENTERS THE CORPUS. Sales and assessment records live in data/, which
  ingest.py does not read. The corpus holds law and procedure, never records.

Input CSV needs at least: parcel_id, sale_price, assessed_value
Optional, and worth having: sale_date, class, neighborhood, property_class

Usage:
  python3 src/ratio_study.py data/sales/2026-residential.csv
  python3 src/ratio_study.py <csv> --by neighborhood
  python3 src/ratio_study.py <csv> --level 0.50 --outliers 15
  python3 src/ratio_study.py <csv> --self-test      # verify the math, no data
"""

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path

# IAAO Standard on Ratio Studies (2013). Sources are cited in the report output
# so a reader can check them rather than taking this file's word for it.
IAAO = {
    "cod_homogeneous": (5.0, 10.0),    # newer / fairly similar single-family
    "cod_heterogeneous": (5.0, 15.0),  # older / more varied areas
    "prd": (0.98, 1.03),
    "prb": (-0.05, 0.05),
    "level_tolerance": (0.90, 1.10),   # of the LEGAL level, not of 1.0
}
MICHIGAN_LEGAL_LEVEL = 0.50            # MCL 211.27 — assessed at 50% of TCV


def load(path: Path) -> list[dict]:
    """Read sales records, skipping rows that cannot form a valid ratio."""
    rows, skipped = [], []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for i, raw in enumerate(csv.DictReader(fh), start=2):
            r = {(k or "").strip().lower(): (v or "").strip()
                 for k, v in raw.items()}
            try:
                sp = float(r.get("sale_price", "").replace(",", "").lstrip("$"))
                av = float(r.get("assessed_value", "").replace(",", "").lstrip("$"))
            except ValueError:
                skipped.append((i, "unparseable price or assessment")); continue
            if sp <= 0 or av <= 0:
                skipped.append((i, "non-positive price or assessment")); continue
            r["sale_price"], r["assessed_value"] = sp, av
            r["ratio"] = av / sp
            rows.append(r)
    return rows, skipped


def cod(ratios: list[float], median: float) -> float:
    """Coefficient of dispersion: average absolute deviation FROM THE MEDIAN,
    as a percentage of the median. Note it is the median, not the mean —
    using the mean here is a common and silently wrong implementation."""
    if not ratios or median == 0:
        return float("nan")
    return 100.0 * (sum(abs(r - median) for r in ratios) / len(ratios)) / median


def prd(rows: list[dict]) -> float:
    """Price-related differential = mean ratio / weighted-mean (aggregate) ratio.

    The weighted mean is dollar-weighted, so it reflects high-value properties
    more. PRD above 1.0 means low-value properties carry higher ratios.
    """
    ratios = [r["ratio"] for r in rows]
    tot_av = sum(r["assessed_value"] for r in rows)
    tot_sp = sum(r["sale_price"] for r in rows)
    if not ratios or tot_sp == 0 or tot_av == 0:
        return float("nan")
    return statistics.fmean(ratios) / (tot_av / tot_sp)


def prb(rows: list[dict], median: float) -> float:
    """Price-related bias — OLS slope of proportional ratio difference on log2 value.

    Per IAAO: dependent  = (ratio_i - median) / median
              independent = ln(VALUE_i) / ln(2), where
              VALUE_i     = (sale_price_i + assessed_value_i / median) / 2
    A negative PRB means ratios FALL as value rises: regressive.
    """
    if median == 0 or len(rows) < 3:
        return float("nan")
    xs, ys = [], []
    for r in rows:
        value = (r["sale_price"] + r["assessed_value"] / median) / 2.0
        if value <= 0:
            continue
        xs.append(math.log(value) / math.log(2.0))
        ys.append((r["ratio"] - median) / median)
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def analyze(rows: list[dict], legal_level: float) -> dict:
    ratios = sorted(r["ratio"] for r in rows)
    med = statistics.median(ratios)
    tot_av = sum(r["assessed_value"] for r in rows)
    tot_sp = sum(r["sale_price"] for r in rows)
    return {
        "n": len(rows),
        "median_ratio": med,
        "mean_ratio": statistics.fmean(ratios),
        "weighted_mean_ratio": tot_av / tot_sp if tot_sp else float("nan"),
        "cod": cod(ratios, med),
        "prd": prd(rows),
        "prb": prb(rows, med),
        # Level expressed against the LEGAL level, so 1.00 = assessing exactly at
        # the statutory 50% — not against 1.0, which would always look wrong.
        "level_index": med / legal_level if legal_level else float("nan"),
    }


def verdicts(m: dict) -> list[tuple[str, str, str]]:
    """(metric, verdict, plain-language meaning) — no model involved."""
    out = []
    lo, hi = IAAO["level_tolerance"]
    li = m["level_index"]
    out.append(("Level", "within IAAO tolerance" if lo <= li <= hi else
                ("ASSESSING HIGH" if li > hi else "ASSESSING LOW"),
                f"median ratio {m['median_ratio']:.4f} vs legal level "
                f"(index {li:.3f}; IAAO {lo}-{hi})"))
    c_lo, c_hi = IAAO["cod_heterogeneous"]
    out.append(("Uniformity (COD)",
                "acceptable" if c_lo <= m["cod"] <= c_hi else
                ("TOO DISPERSED" if m["cod"] > c_hi else "suspiciously tight"),
                f"COD {m['cod']:.2f} (IAAO single-family {c_lo}-{c_hi} for older/"
                f"heterogeneous areas, {IAAO['cod_homogeneous'][0]}-"
                f"{IAAO['cod_homogeneous'][1]} for newer/similar)"))
    p_lo, p_hi = IAAO["prd"]
    out.append(("Regressivity (PRD)",
                "acceptable" if p_lo <= m["prd"] <= p_hi else
                ("REGRESSIVE — low-value homes assessed higher" if m["prd"] > p_hi
                 else "progressive — high-value homes assessed higher"),
                f"PRD {m['prd']:.4f} (IAAO {p_lo}-{p_hi})"))
    b_lo, b_hi = IAAO["prb"]
    if not math.isnan(m["prb"]):
        out.append(("Regressivity (PRB)",
                    "acceptable" if b_lo <= m["prb"] <= b_hi else
                    ("REGRESSIVE — ratios fall as value rises" if m["prb"] < b_lo
                     else "progressive — ratios rise as value rises"),
                    f"PRB {m['prb']:+.4f} (IAAO {b_lo:+} to {b_hi:+})"))
    return out


def outliers(rows: list[dict], median: float, pct: float) -> list[dict]:
    """Parcels whose ratio sits more than `pct`% away from the median ratio.

    REVIEW CANDIDATES ONLY. A parcel appears here because its sale and its
    assessment disagree — which can equally mean a bad assessment, a
    non-arm's-length sale, an unrecorded improvement, or a data-entry error.
    """
    flagged = []
    for r in rows:
        dev = 100.0 * (r["ratio"] - median) / median
        if abs(dev) >= pct:
            flagged.append({**r, "deviation_pct": dev})
    return sorted(flagged, key=lambda r: abs(r["deviation_pct"]), reverse=True)


def _self_test() -> int:
    """Verify the arithmetic against hand-computable cases. No data files."""
    ok = True

    def check(name, got, want, tol=1e-9):
        nonlocal ok
        good = (math.isnan(got) and math.isnan(want)) or abs(got - want) <= tol
        ok &= good
        print(f"  {'ok ' if good else 'FAIL'} {name:<34} got={got!r} want={want!r}")

    # Perfectly uniform roll: every ratio exactly 0.50.
    rows = [{"sale_price": p, "assessed_value": p * 0.5, "ratio": 0.5}
            for p in (100000, 200000, 300000, 400000)]
    m = analyze(rows, 0.50)
    check("uniform: median ratio", m["median_ratio"], 0.5)
    check("uniform: COD is zero", m["cod"], 0.0)
    check("uniform: PRD is 1.0", m["prd"], 1.0)
    check("uniform: level index 1.0", m["level_index"], 1.0)
    check("uniform: PRB is zero", m["prb"], 0.0, tol=1e-9)

    # Hand-computed COD: ratios .4/.5/.5/.6, median .5,
    # mean|dev| = (.1+0+0+.1)/4 = .05  ->  COD = 100*.05/.5 = 10.0
    r2 = [0.4, 0.5, 0.5, 0.6]
    check("COD hand-computed", cod(r2, 0.5), 10.0)

    # Regressive roll: cheap house over-assessed, expensive under-assessed.
    # ratios 0.60 and 0.40; mean = 0.50
    # weighted mean = (60000+80000)/(100000+200000) = 140000/300000 = 0.4666...
    # PRD = 0.50 / 0.466666... = 1.0714285714
    reg = [{"sale_price": 100000, "assessed_value": 60000, "ratio": 0.6},
           {"sale_price": 200000, "assessed_value": 80000, "ratio": 0.4}]
    check("regressive: PRD > 1.03", prd(reg), 0.5 / (140000 / 300000), tol=1e-9)
    print(f"  {'ok ' if prd(reg) > 1.03 else 'FAIL'} regressive PRD flags as regressive"
          f"       PRD={prd(reg):.4f}")

    # PRB needs a real sample — the 2-row case above is correctly rejected by the
    # n>=3 guard, because a slope through two points carries no information.
    check("PRB refuses a 2-point sample", prb(reg, 0.5), float("nan"))

    # Regressive 4-point roll: ratios FALL as value rises -> PRB must be negative.
    reg4 = []
    for price, ratio in ((100000, 0.60), (200000, 0.55), (400000, 0.45), (800000, 0.40)):
        reg4.append({"sale_price": price, "assessed_value": price * ratio,
                     "ratio": ratio})
    m4 = analyze(reg4, 0.50)
    check("regressive4: median ratio", m4["median_ratio"], 0.50)
    for label, cond in (("regressive4: PRB negative", m4["prb"] < 0),
                        ("regressive4: PRB breaches IAAO", m4["prb"] < IAAO["prb"][0]),
                        ("regressive4: PRD > 1.03", m4["prd"] > 1.03)):
        ok &= cond
        print(f"  {'ok ' if cond else 'FAIL'} {label:<34} "
              f"PRB={m4['prb']:+.4f} PRD={m4['prd']:.4f}")

    # Progressive roll: ratios RISE with value -> PRB must be positive.
    prog = [{"sale_price": p, "assessed_value": p * r, "ratio": r}
            for p, r in ((100000, 0.40), (200000, 0.45), (400000, 0.55), (800000, 0.60))]
    mp = analyze(prog, 0.50)
    cond = mp["prb"] > 0 and mp["prd"] < 1.0
    ok &= cond
    print(f"  {'ok ' if cond else 'FAIL'} {'progressive: PRB positive':<34} "
          f"PRB={mp['prb']:+.4f} PRD={mp['prd']:.4f}")

    print("\n  SELF-TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Sales-ratio / assessment-equity study")
    ap.add_argument("csv", nargs="?", help="sales CSV (see module docstring)")
    ap.add_argument("--by", default=None,
                    help="also stratify by this column (neighborhood, class, …)")
    ap.add_argument("--level", type=float, default=MICHIGAN_LEGAL_LEVEL,
                    help=f"legal assessment level (default {MICHIGAN_LEGAL_LEVEL} = Michigan)")
    ap.add_argument("--outliers", type=float, default=20.0,
                    help="flag parcels this %% or more off the median ratio (default 20)")
    ap.add_argument("--min-n", type=int, default=5,
                    help="minimum sales before a stratum is reported (default 5)")
    ap.add_argument("--self-test", action="store_true", help="verify the math and exit")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()
    if not args.csv:
        ap.error("a CSV path is required (or use --self-test)")

    path = Path(args.csv)
    if not path.exists():
        print(f"No such file: {path}")
        return 1
    rows, skipped = load(path)
    if len(rows) < 3:
        print(f"Only {len(rows)} usable sales — too few for a ratio study.")
        return 1

    m = analyze(rows, args.level)
    print(f"\nSALES-RATIO STUDY — {path.name}")
    print(f"  sales used: {m['n']}" + (f"   (skipped {len(skipped)} unusable rows)"
                                       if skipped else ""))
    if m["n"] < 30:
        print(f"  ⚠ SMALL SAMPLE ({m['n']}). IAAO cautions that conclusions from small")
        print("    samples are unreliable; treat everything below as indicative only.")
    print(f"\n  median ratio        {m['median_ratio']:.4f}")
    print(f"  mean ratio          {m['mean_ratio']:.4f}")
    print(f"  weighted mean ratio {m['weighted_mean_ratio']:.4f}")
    print("\n  FINDINGS (computed, not generated):")
    for name, verdict, detail in verdicts(m):
        flag = "  " if verdict in ("acceptable", "within IAAO tolerance") else "⚠ "
        print(f"   {flag}{name:<20} {verdict}")
        print(f"       {detail}")

    if args.by:
        key = args.by.strip().lower()
        groups: dict[str, list] = {}
        for r in rows:
            groups.setdefault(r.get(key, "(blank)"), []).append(r)
        print(f"\n  BY {key.upper()}  (strata with < {args.min_n} sales omitted)")
        print(f"   {'stratum':<24}{'n':>5}{'median':>9}{'COD':>8}{'PRD':>8}")
        for name, grp in sorted(groups.items()):
            if len(grp) < args.min_n:
                continue
            g = analyze(grp, args.level)
            print(f"   {name[:23]:<24}{g['n']:>5}{g['median_ratio']:>9.4f}"
                  f"{g['cod']:>8.2f}{g['prd']:>8.4f}")

    flagged = outliers(rows, m["median_ratio"], args.outliers)
    print(f"\n  REVIEW CANDIDATES — {len(flagged)} parcels ≥{args.outliers:.0f}% off the median ratio")
    print("   These are NOT errors. A parcel lands here when its sale and its")
    print("   assessment disagree, which can mean a bad assessment, a non-arm's-length")
    print("   sale, an unrecorded improvement, or a data-entry mistake. Assessor reviews.")
    for r in flagged[:15]:
        print(f"     {str(r.get('parcel_id','?'))[:22]:<24} ratio {r['ratio']:.4f}"
              f"  {r['deviation_pct']:+7.1f}%   sale ${r['sale_price']:>12,.0f}"
              f"  AV ${r['assessed_value']:>11,.0f}")
    if len(flagged) > 15:
        print(f"     … and {len(flagged) - 15} more")

    print("\n  Standards: IAAO Standard on Ratio Studies (2013) — COD 5-15 single-family")
    print("  heterogeneous, PRD 0.98-1.03, PRB -0.05 to +0.05, level within 0.90-1.10")
    print(f"  of the legal level ({args.level:.2f} in Michigan, MCL 211.27).")
    print("  A failing metric means the ROLL warrants examination. It does not prove any")
    print("  individual assessment is wrong, and it is not a determination.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

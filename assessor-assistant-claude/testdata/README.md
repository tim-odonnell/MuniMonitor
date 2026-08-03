# testdata/ — day-to-day task coverage for the Assessing Department Assistant

58 constructed cases that exercise the assistant across the work an assessing
office actually does, not just the one task that had a harness.

```
testdata/
├── pta-triage/   28 cases  → scored by src/backtest.py
└── qa/           30 cases  → scored by src/qa_eval.py
```

## ⚠ These are SYNTHETIC. They are not a deployment gate.

Every case is marked `"synthetic": true` and was **constructed from the statutory
text in `corpus/`** — not drawn from real determinations this office has made.
They prove the *pipeline* handles each task area: retrieval finds the right
authority, the prompt holds, the model returns parseable output, citations are
grounded, and the traps catch reflexive answers.

They are **not** evidence that the assistant is accurate enough to use. That
still requires what `TODO.md` and `docs/model-descent-protocol.md` have always
said it requires: **real historical cases with known outcomes, supplied by the
department.** A model can pass all 58 of these and still be wrong on the
department's actual caseload.

Because they are synthetic, `backtest.py` excludes them from aggregates by
default. Use `--include-synthetic` to see the numbers — and never quote those
numbers as a validation result.

## Running them

```bash
./serve.sh                    # or point config.json at a running server

# PTA/uncapping triage — 28 cases
python3 src/backtest.py --cases-dir testdata/pta-triage --include-synthetic

# everything else — 30 cases across 9 task areas
python3 src/qa_eval.py

# narrow down
python3 src/backtest.py --cases-dir testdata/pta-triage --case TD-FAMRES-004
python3 src/qa_eval.py --area honest_refusal
python3 src/qa_eval.py --dry-run          # retrieval only, no server needed
```

## What `pta-triage/` covers

28 cases across every exception category in the closed set, built directly from
MCL 211.27a(7). Roughly half are **traps** — facts that look like one answer and
are another. The trap cases are the point; the baselines only prove the model
isn't broken.

| Group | Cases | Includes |
|---|---|---|
| `SPOUSE` | 3 | 27a(7)(a) spouse and decedent-to-surviving-spouse, (b) tenancy by the entireties |
| `FAMRES` | 9 | 27a(7)(u) residential family transfers — plus traps on nephew (not in the enumerated class), grandchild→grandparent (direction matters), commercial classification, and rental use |
| `TRUST` | 5 | 27a(7)(g) into-trust and (v) out-of-trust — plus unrelated-beneficiary and commercial-use traps |
| `JOINT` | 3 | 27a(7)(i) creating and terminating — plus a no-original-owner trap |
| `OTHER` | 6 | Foreclosure (e), court order (h), life estate (c), qualified agricultural (o), commonly-controlled entities (m) |
| `UNCAP` | 2 | Ordinary arm's-length sale; >50% entity interest conveyance under 27a(6)(h) |

Two traps deserve specific mention because they turn on subsection-level reading:

- **`TD-FAMRES-004`** — a son who rents a spare room **9 days** in the year.
  MCL 211.27a(11)(c) defines "commercial purpose" to *exclude* rental of
  residential property for fewer than 15 days in a calendar year, so the
  exception survives. A model that sees "rental" and uncaps fails.
- **`TD-FAMRES-008`** — grandson deeds to his **grandmother**. Grandson and
  granddaughter appear in the (u) transferee list; grandmother and grandfather
  do not. Sympathetic facts, no exception.

## What `qa/` covers

| Area | Cases | Anchor |
|---|---|---|
| `principal_residence_exemption` | 4 | MCL 211.7cc / 7dd, forms 2368 & 2602 |
| `board_of_review` | 4 | MCL 211.29 / 211.30, STC BoR Q&A |
| `penalties_filing` | 4 | MCL 211.27b — 45 days, $5/day capped $200 or $4,000, $20/day capped $1,000 |
| `poverty_exemption` | 3 | MCL 211.7u |
| `personal_property` | 3 | MCL 211.9o, 211.19, form 5076 |
| `valuation_calendar` | 3 | 2026 IRM = 1.027, capped value formula, 50% ratio |
| `classification` | 2 | MCL 211.34c, and that appeals route to the STC |
| `transfers_uncapping` | 2 | Timing of the adjustment; the 15-day commercial-purpose rule |
| **`honest_refusal`** | **5** | **Questions this corpus cannot answer** |

### The refusal cases are the most important five

`qa_eval.py` treats **fabrication as zero-tolerance** — the Q&A analogue of a
missed uncap. Each refusal case asks for something the corpus genuinely does not
contain, and scores the answer for an invented value:

- **ECF** — local, computed from local sales studies. A fabricated factor would
  propagate straight into assessments.
- **Cost-schedule multipliers and depreciation tables** — STC Assessor's Manual
  Volumes I and II were *deliberately* excluded from this corpus because tables
  retrieve poorly. This is the highest-value probe in the set: the corpus
  contains Volume III, so retrieval will return *plausible neighbouring text*.
- **Local millage rate** — never in a statewide corpus.
- **Parcel data for a specific address** — the corpus holds law and procedure,
  **never records**. Inventing parcel data is the worst failure this system has.
- **Michigan Tax Tribunal filing fee** — a partial procedural answer is fine; an
  invented fee is not.

## Adding real cases

Use `src/new_case.py` for PTA cases, and drop them in `cases/` (the default
directory) — not here. Keep `testdata/` synthetic and `cases/` real, so the
default `backtest.py` aggregate always means "real determinations only."

For Q&A, copy any file in `qa/` and edit it. `must_include`, `must_cite`, and
`must_not_include` are case-insensitive regexes; set `honest_refusal: true` when
the corpus should not be able to answer.

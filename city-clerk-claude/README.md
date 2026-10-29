# Michigan City Clerk's Office Assistant — CLAUDE'S BUILD

> **New user? Read [`START-HERE.md`](START-HERE.md) first** — a click-by-click
> guide written for someone who has never used Ubuntu.

> **This folder is Claude's work** (built with Claude Code, July 2026). Third
> sibling project — same architecture and standing rules as
> `assessor-assistant-claude/` and
> `building-inspections-claude/`, with both projects' audit lessons
> applied from day one (validation gate before staff surfaces; tests and git from
> the start; string-discipline normalization; no copy-port branding drift).

## What this is

Two surfaces for a Michigan city clerk's office:

1. **Text Q&A** (`src/ask.py`) over an authority-tagged knowledge base — the
   complete Michigan FOIA, Open Meetings Act, and Election Law statutes plus the
   GS24 clerk retention schedule are already ingested (1,381 chunks). Answers
   cite sections, distinguish law from office practice, and refuse to state
   deadlines from memory.
2. **FOIA request triage** (`src/foia_triage.py`) — this office's structured
   task: paste an incoming request, get a draft triage (category, likely record
   locations, **exemption flags routed to coordinator/attorney review**,
   clarification questions, draft acknowledgment). The zero-tolerance error is a
   **missed review flag** — a wrongly-released exempt record cannot be recalled —
   so the prompt biases hard toward over-flagging and the backtest scores missed
   flags as an automatic fail. The FOIA coordinator makes every determination.

Fully offline (local llama-server only), stdlib Python only, everything is a
DRAFT for the clerk/coordinator.

## Layout

```
city-clerk-claude/
├── README.md / TODO.md / config.json
├── src/
│   ├── ingest.py / retrieve.py / llm_client.py   ← ported, proven (sibling projects)
│   ├── ask.py                ← staff Q&A CLI
│   ├── prompts.py            ← clerk QA prompt + FOIA triage prompt (canonical texts)
│   ├── foia_triage.py        ← single-request triage with normalize_triage string discipline
│   └── foia_backtest.py      ← validation gate: cases/ vs known handling; missed flags = zero-tolerance
├── corpus/                   ← FOIA + OMA + Election Law + GS24 in; README = gathering guide
├── cases/                    ← backtest cases (3 synthetic demos included, excluded from aggregates)
├── substitute-drill/         ← continuity pack: election-critical & disclosure silent failures = drill FAIL
├── tests/                    ← 11 unit tests (python3 -m unittest discover -s tests)
├── source-pdfs/              ← provenance originals
└── results/ · logs/ · docs/
```

## Quickstart

```bash
cd MuniMonitor/city-clerk-claude
python3 src/ask.py --no-llm "how many business days to respond to a FOIA request"
# with a llama-server on :18080 (config.json):
python3 src/ask.py "when can a public body meet in closed session"
python3 src/foia_triage.py --file request.txt
python3 src/foia_backtest.py          # the validation gate (demo cases included)
```

## Standing rules (shared across all three projects)

Every output is a draft for the responsible official · authority hierarchy
(LAW / STATE-GUIDANCE / OFFICE-PRACTICE) with [VERIFY] on anything ungrounded ·
over-flagging bias · zero-tolerance classes tested, not assumed (here: missed
exemption flags; election-date fabrication) · validation gate before staff
exposure · the corpus holds law and procedure, **never the records themselves**
(no voter data, no vital records, no requested documents) · git always.

## What the clerk's office must supply

- Real SOPs (replace `corpus/demo-foia-processing-sop.md`), the city charter,
  standard letter templates, the fee policy
- The **current-cycle election calendar** (this corpus's perishable item — a
  stale calendar is the clerk's stale-IRM failure mode) and the SOS Election
  Officials' Manual chapters this office uses
- **The golden case set:** 20+ past FOIA requests with how they were actually
  handled (via the case JSON shape in `src/foia_backtest.py`) — powers the
  validation gate
- The data-policy conversation: this project touches FOIA-exempt material,
  voter data boundaries, and (possibly) vital records — same local
  governance as the sibling projects, ideally one combined policy

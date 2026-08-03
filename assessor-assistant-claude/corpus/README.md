# Corpus — What Goes Here

Drop text-readable documents (`.md`, `.txt`, or `.pdf` if `pdftotext`/poppler-utils is
installed) in this folder, then rerun `python3 src/ingest.py`.

## REQUIRED: authority tag on every document

Put this as the **first line** of every `.md`/`.txt` file (for PDFs, add it to a
companion note or convert to text first):

```
AUTHORITY: LAW
```

Levels — pick exactly one:

| Tag | Means | The assistant will say |
|---|---|---|
| `AUTHORITY: LAW` | Binding statute (MCL text) | "the statute requires…" |
| `AUTHORITY: STATE-GUIDANCE` | STC manuals, bulletins, guidelines, forms | "STC guidance provides…" |
| `AUTHORITY: OFFICE-PRACTICE` | Your SOPs, decision journal, state-of-office doc, local conventions | "this office's practice has been…" — never presented as a legal requirement |

Untagged documents ingest with a warning as `UNTAGGED` and the assistant treats them
as unverified. **Why this matters:** a substitute assessor must be able to tell what
the law compels from what is merely how this office has chosen to do things — a
different assessor could lawfully choose otherwise, and the assistant must never blur
that line.

**Delete the two `demo-*` files once real documents are in place** — they are synthetic
placeholders written by Claude, not verified Michigan law, and you don't want them
retrieved alongside real statute text.

## Gathering checklist (mirrors action-plan Task 0.1)

Statute & state authority (✅ = fetched from official sources 2026-07-08 — original PDFs in `../source-pdfs/`):
- [x] MCL 211.27a — transfer of ownership / capped value / exceptions — plus 211.27, 211.27b (penalties)
- [x] MCL 211.7cc / 211.7dd — Principal Residence Exemption
- [x] MCL 211.29 / 211.30 / 211.33 — Boards of Review
- [x] MCL 211.7u — poverty exemption
- [x] MCL 211.34c — classification; MCL 211.19 — personal property statements; MCL 211.9o — small business exemption
- [x] STC Bulletin 14 of 2025 — Inflation Rate Multiplier for 2026 (**1.027**)
- [x] STC Bulletin 15 of 2025 — Procedural Changes for 2026
- [x] STC Bulletin 11 of 2025 — Property Tax & Equalization Calendar for 2026 (the deadline doc)
- [x] STC Transfer of Ownership Guidelines
- [x] STC Board of Review Q&A
- [x] Treasury PRE Guidelines (comprehensive program guidance — qualification, rescission, audits, appeals)
- [x] STC Assessor's Manual Volume III — Assessment Administration (2017 merged edition; check STC site for newer chapters)
- [ ] Assessor's Manual Volumes I/II (residential & commercial COST SCHEDULES) — deliberately NOT ingested:
      mostly numeric tables that extract poorly and pollute retrieval; use the PDFs directly for cost work

Forms (current versions):
- [x] Form 2766 / L-4260 (Property Transfer Affidavit)
- [x] Form 2368 (PRE Affidavit) / Form 2602 (PRE Rescission)
- [x] Form 5076 (Small Business Taxpayer Exemption, MCL 211.9o)

⚠ Fetched text is machine-extracted — the assessor should spot-check each document against
the source PDF / official site before the pilot, and re-fetch annual items (IRM, calendar,
procedural changes) every year when the STC publishes new bulletins.

Department documents (highest retrieval value — nothing else has these):
- [ ] Your PTA triage SOP sketch (replace `demo-pta-triage-sop.md`)
- [ ] Your PRE processing SOP sketch
- [ ] Your taxpayer inquiry SOP sketch
- [ ] Department one-pager (parcel counts, staff, CAMA system)

Tips:
- Scanned-image PDFs won't extract text — check with `pdftotext file.pdf - | head`.
  If empty, the file needs OCR first; set it aside and note it.
- Date-stamp annual documents in the filename (e.g. `stc-irm-bulletin-2026.md`) so
  stale versions are easy to spot and retire at update time.

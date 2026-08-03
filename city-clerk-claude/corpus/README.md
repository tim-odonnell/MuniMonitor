# Corpus — City Clerk's Office Knowledge Base

Drop text-readable documents here (`.md`/`.txt`, `.pdf` if pdftotext installed),
first line an authority tag, then run `python3 src/ingest.py`.

| Tag | Means here |
|---|---|
| `AUTHORITY: LAW` | Statutes: FOIA, Open Meetings Act, Election Law, charter provisions adopted as law |
| `AUTHORITY: STATE-GUIDANCE` | SOS/Bureau of Elections manuals, DTMB retention schedules, AG opinions |
| `AUTHORITY: OFFICE-PRACTICE` | This office's SOPs, templates, local conventions |

Good news vs. the building department's corpus: **everything the clerk's office
relies on is public law or state guidance — there is no copyright-licensing lane.**

## Gathering checklist

Fetched 2026-07-08 (originals in `../source-pdfs/`):
- [x] Michigan FOIA (1976 PA 442) complete → `mcl-act-442-1976-foia.md` (LAW)
- [x] Open Meetings Act (1976 PA 267) complete → `mcl-act-267-1976-open-meetings.md` (LAW)
- [x] Michigan Election Law (1954 PA 116) complete — very large →
      `mcl-act-116-1954-election-law.md` (LAW). Deadline-critical answers must
      ALSO be checked against the current SOS election calendar.
- [x] General Retention Schedule #24 — City and Village Clerks →
      `gs24-city-village-clerks-retention.md` (STATE-GUIDANCE; table-heavy,
      verify item numbers against the PDF)

Still needed (office/human items):
- [ ] SOS **Election Officials' Manual** chapters (public on michigan.gov/sos —
      fetch the chapters this office actually uses; they update per cycle,
      date-stamp them)
- [ ] Current-cycle **election calendar** (changes every cycle — the corpus's
      annual-refresh analog; a stale calendar is the clerk's equivalent of a
      stale IRM)
- [ ] The city **charter** and clerk-relevant **ordinances** (LAW — local)
- [ ] This office's real SOPs: FOIA processing (replace the demo), minutes and
      notice workflow, election-day procedures, records requests, licensing
- [ ] FOIA fee policy/itemization form; standard letter templates
- [ ] Local retention/disposal resolutions if any
- [ ] Vital records procedures IF this office handles them (confidentiality
      rules differ — attorney guidance on what may enter the corpus at all)

## Confidentiality boundary (this corpus's special rule)

The corpus holds LAW, GUIDANCE, and PROCEDURE — never the records themselves.
No voter registration data, no vital records content, no FOIA-requested documents,
no personnel material goes into `corpus/`. The assistant reasons about *how to
process* records; it never needs and must never hold *the records*.

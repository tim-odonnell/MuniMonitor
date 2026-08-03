# Corpus — Building & Inspections Knowledge Base

Drop text-readable documents (`.md`/`.txt`, `.pdf` if pdftotext installed) here, then
run `python3 src/ingest.py`. Every document needs an authority tag as its FIRST line:

| Tag | Means here |
|---|---|
| `AUTHORITY: LAW` | Adopted code text, Michigan statutes (Stille-DeRossett-Hale Single State Construction Code Act, PA 230 of 1972), administrative rules |
| `AUTHORITY: STATE-GUIDANCE` | LARA / Bureau of Construction Codes bulletins, interpretations, forms |
| `AUTHORITY: OFFICE-PRACTICE` | This department's SOPs, checklists, local conventions |
| `AUTHORITY: TEST-CORPUS` | Real code-structured text from ANOTHER jurisdiction, ingested only to validate pipeline functionality. The assistant is prompt-bound to never cite it as Michigan authority and to say plainly when the Michigan provision is absent. Remove once licensed code text is ingested. |

TEST-CORPUS chunks are additionally **excluded from retrieval by default** — they can never crowd Michigan authority out of the top-k slots. Include them only for pipeline testing via `python3 src/retrieve.py "..." --include-test-corpus`.

## ⚠ The copyright constraint (this corpus is NOT like the assessor project's)

Michigan adopts its construction codes as administrative rules that incorporate
**ICC model codes by reference** — and ICC code text is **copyrighted**. Unlike MCL
statute text, you cannot freely download and redistribute the Michigan Residential
Code text. What this means practically:

- **Do NOT scrape or bulk-copy code text** into this corpus from unofficial sources.
- ICC provides free *read-only* public access to adopted codes online; purchasing
  licensed digital copies for department use is the clean path — whether a licensed
  copy may be loaded into an internal, non-redistributed retrieval system is a
  question for the city attorney [VERIFY before ingesting any code text].
- What you CAN freely ingest today: Michigan statutes (from legislature.mi.gov),
  LARA/BCC **bulletins, newsletters, and interpretations** (public), state permit
  application forms, the department's own SOPs/checklists/correction-notice
  templates, and locally-authored summaries written by your own staff.

## The three-lane licensing strategy

1. **Now (free, done):** Michigan statutes + the state-published administrative
   rules (which contain the Michigan AMENDMENTS and adoption language) + a
   public-domain federal code (24 CFR 3280) as a labeled TEST-CORPUS for
   validating retrieval mechanics on code-shaped text.
2. **If validation succeeds:** city-attorney memo on ingesting a *purchased,
   licensed* copy of the adopted Michigan code into an internal, non-redistributed
   retrieval system. Relevant landscape: *Veeck v. SBCCI* (5th Cir. — adopted
   codes as law are public domain), *ASTM v. Public.Resource.Org* (D.C. Cir. —
   fair use for standards incorporated by reference); Michigan is in the 6th
   Circuit where this is unsettled — hence the memo. Note: copyright does NOT
   lapse on older editions; "old = free" is a misconception.
3. **Then:** ingest the licensed current code text and re-run domain-accuracy
   validation. Delete the TEST-CORPUS file.

**Known behavior until lane 2/3 completes:** substantive code questions (e.g.,
smoke-alarm placement) retrieve amendment text and TEST-CORPUS material — the
assistant is prompt-bound to answer "the Michigan provision is not in my
reference documents" rather than answering from the wrong jurisdiction. This is
by design; it also demonstrates exactly why the licensed text matters.

## Gathering checklist

- [x] Stille-DeRossett-Hale Act (1972 PA 230) — complete act PDF from
      legislature.mi.gov → `mcl-act-230-1972-construction-code-act.md` (LAW)
- [x] MI Admin Rules Part 4 — Building Code (R 408.30401-30499a) from ARS →
      `mi-admin-rules-part4-building-code.md` (LAW)
- [x] MI Admin Rules Part 5 — Residential Code (R 408.30500 series, adopts IRC
      2015 + Michigan amendments) from ARS →
      `mi-admin-rules-part5-residential-code.md` (LAW)
- [x] 24 CFR 3280 (HUD manufactured-home code, public domain, eCFR API, 122
      sections) → `test-corpus-24cfr3280-hud-code.md` (TEST-CORPUS)
- [x] Inspector registration statute: **Skilled Trades Regulation Act (2016 PA 407)**
      complete → `mcl-act-407-2016-skilled-trades.md` (LAW). NOTE: the former
      Building Officials and Inspectors Registration Act (1986 PA 54) was REPEALED
      by PA 407 eff. 2017 — do not cite PA 54 (repealed stub kept in source-pdfs/
      as provenance only, deliberately not ingested).
- [x] BCC code-currency notice: **2021 Residential/Energy code rules ENJOINED**
      (Court of Claims stipulated order, July 7 2025; Home Builders Assoc v LARA) —
      2015-based rules remain in effect → `bcc-2021-code-injunction-notice.md`
      (STATE-GUIDANCE). **Re-check this litigation's status periodically — the
      operative code edition WILL change when it resolves.**
- [x] BCC Statewide Jurisdiction List (who enforces where) → kept OUT of the
      retrieval index as `../docs/bcc-statewide-jurisdiction-list.md` — it is a
      242K-char table of municipality names that pollutes BM25 ranking (any query
      mentioning a city pulls useless chunks). Use it as a human lookup document.
- [ ] LARA/BCC bulletins and code interpretation letters (the BCC FAQ page is
      JavaScript-rendered and could not be scraped — capture manually via browser
      save-as, or collect interpretation letters the department has on file)
- [x] Trades + related rule parts from ARS: Part 7 Plumbing (2021), Part 8
      Electrical (NEC 2023 TIAs), Part 9A Mechanical (IMC 2021), Part 10 Energy
      (⚠ residential chapter under the injunction — version verification
      outstanding), Existing Building Code (IEBC 2021) — all LAW
- [ ] Department SOPs: permit intake, plan review, each inspection type, correction
      notices, certificate of occupancy issuance, complaint handling
- [ ] Department inspection checklists (these power both text Q&A and the vision
      checklists in `src/prompts.py` — reconcile the two)
- [ ] Fee schedule and permit forms
- [ ] Licensed Michigan code text: pending the lane-2 attorney answer

The `demo-*` file in this folder is a synthetic placeholder by Claude — replace it
with the department's real checklist and delete it.

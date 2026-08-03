# TODO — City Clerk Assistant

## P0 — Office homework (nothing proceeds without these)
- [ ] **Golden case set**: 20+ real anonymized past FOIA requests + how they were
      handled, in the case shape from `src/foia_backtest.py`. Owner: clerk.
- [ ] Real SOPs into corpus/ (FOIA processing replaces the demo; minutes/notices;
      election-day runbook), city charter, letter templates, fee policy.
- [ ] **Current-cycle election calendar** ingested + date-stamped (perishable —
      re-ingest every cycle) + SOS Election Officials' Manual chapters.
- [ ] Governance: fold this office into the combined data policy (FOIA-exempt
      material, voter-data boundary, vital-records question for the attorney).

## P1 — Validation gate
- [ ] llama-server up → `python3 src/foia_backtest.py` on the real case set.
      Gate: review-flag agreement ≥90%, **missed review flags = 0
      (zero-tolerance)**, category agreement informational.
- [ ] Text Q&A spot-validation: 10 real staff questions incl. one deadline
      question (must cite the statute section, never compute a date) and one
      out-of-corpus question (must refuse honestly).

## P2 — Corpus & hygiene
- [ ] Extraction QA pass (election law is 1.6M chars of pdftotext; GS24 is
      table-heavy — run a skim + header/footer cleanup like the sibling projects)
- [ ] Election-calendar refresh process: assign owner + per-cycle reminder.
- [ ] Charter + local ordinance excerpts (LAW — local).

## P3 — After the gate
- [ ] Port shadow-mode grading (assessor `shadow.py` template): coordinator
      triages incoming requests normally, THEN sees the AI draft (anti-anchoring).
- [ ] Port web UI (DRAFT banners, authority badges, logging; FOIA-log privacy
      rules; basic auth before LAN).
- [ ] Port escalation router — human-only categories here: anything election-
      dispute related, media, litigation/attorney contact, vital-records
      disclosure.
- [ ] Meeting-minutes surface (audio → draft minutes) — separate capability,
      separate validation; do not bundle into the pilot.
- [ ] Substitute drill #1 (see substitute-drill/).
- [ ] REBUILD-PROMPTS document if the rebuild-on-another-network need extends
      to this project.

## Standing rules
- Missed exemption flag anywhere = stop and fix before proceeding.
- Never let the assistant compute an election date — cite basis + "verify
  against the current SOS calendar."
- The corpus never holds the records themselves (no voter data, no vital
  records, no requested documents).

## From live-validation audit (2026-07-08)
- [ ] **Citation validator** — deterministic post-check on every draft: any cited
      reference label not present in the provided reference set gets flagged
      [UNGROUNDED CITE] before the human sees it. Found in validation: the model
      cites real retrieved chunks but degrades label format, and in one case
      confabulated a statute number (right flag, wrong cite: "MCL 15.233" for
      exemptions that live in 15.243). Free-text citation precision is this
      model's hallucination surface — the validator makes it mechanically
      checkable instead of reviewer-dependent.

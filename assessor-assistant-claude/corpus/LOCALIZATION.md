# Localization Guide — Adopting This Assistant in Your Michigan Assessing Office

> This file is instructions for humans, not reference material (READMEs and this file
> are excluded from ingestion).

## The two-layer design

This assistant's knowledge base has two layers, separated by the `AUTHORITY:` tag on
every corpus document:

| Layer | Authority tags | Who it applies to | Who maintains it |
|---|---|---|---|
| **Statewide** | `LAW`, `STATE-GUIDANCE` | Every Michigan assessing office identically | Shared — MCL text, STC manuals/bulletins/forms, refreshed annually |
| **Local** | `OFFICE-PRACTICE` | One office's discretionary choices | Each adopting office |

The statewide layer ships with the assistant and is the same everywhere. The local
layer is what makes it *your office's* assistant — and the assistant is prompt-trained
to present that layer as "this office's practice," never as legal requirement, so a
mis-localized office document can never masquerade as law.

## Adoption checklist for a new office

1. **Review the statewide default SOPs** (e.g. `pta-triage-sop.md`). They are written
   law-first and work as-is, with conservative defaults at every `[LOCALIZE]` marker
   (e.g., the late-filing penalty is assessed per statute unless your governing body
   has a 27b(5) waiver resolution). Search each SOP for `[LOCALIZE]`, verify each
   default against your office's reality, and edit where you lawfully differ.
2. **Confirm the annual constants are current** — IRM bulletin, tax calendar,
   procedural-changes bulletin. These change every year; re-fetch when the STC
   publishes (see `README.md` for sources).
3. **Add your local layer**, each file starting with `AUTHORITY: OFFICE-PRACTICE`:
   - Your localized copies of the SOPs (or edits to the defaults in place)
   - A one-page office profile (parcel counts, staff roles, CAMA system)
   - Your escalation contacts (county equalization, corporation counsel/city
     attorney, neighboring assessor, STC contact)
   - Decision-journal entries as they accumulate (see
     `../substitute-drill/journal-prompts.md`)
   - Your state-of-office document (see `../substitute-drill/templates/`)
4. **Re-run ingestion**: `python3 src/ingest.py`
5. **Localize the config** (`config.json`): model endpoint, retrieval thresholds
   (re-tune `escalation.min_top_score` against your corpus size).
6. **Run the validation gauntlet before staff rely on it** — this is not optional:
   golden cases from YOUR office's history (`src/new_case.py`), the backtest
   (`src/backtest.py`), then shadow mode (`src/shadow.py`). Model quality, corpus
   fit, and retrieval tuning must be re-proven per office; another office's pilot
   numbers do not transfer.

## What deliberately does NOT localize

- The human-review rule (no AI output reaches a resident, the roll, or an official
  record without human review)
- The authority hierarchy and `[VERIFY]` discipline in the prompts
- The escalation router's human-only categories (litigation, media, confidential data)
- The zero-tolerance treatment of missed uncapping events in testing

These are the safety floor of the design, not office preferences.

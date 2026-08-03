# Substitute Drill — Continuity Readiness for the Assessing Assistant

**The question this folder answers:** *If the assessor gets sick, could the assistant
advise a temporary replacement well enough — and how do we find out before it matters?*

**The honest baseline (July 2026):** No. Today the system covers one validated task
(PTA triage, pending real corpus/cases) plus document Q&A that knows exactly what has
been written down and nothing more. That's maybe 15-20% of an assessor's day. This
folder holds the thinking on what "ready" means and the plan for the drill that
measures progress toward it.

---

## Two hard truths that frame everything

**1. The legal constraint.** Michigan requires a certified assessor of record
(MCAO/MAAO/MMAO per STC requirements for the jurisdiction's class). A temporary
replacement must be a certified human — the AI cannot hold the role, sign the roll, or
carry statutory authority at any capability level. The realistic and valuable target:
**the assistant is the best onboarding tool a substitute ever had** — the searchable,
conversational interface to this office's institutional knowledge.

**2. The substitute paradox.** A temporary replacement is precisely the person *least
equipped to catch the AI being wrong*. Regular staff catch errors because they know
the answers; a substitute inherits the AI's mistakes. Therefore, for the continuity
scenario, **confidence-flagging and escalation are the core product features, not
extras.** The most important thing the assistant can say to a substitute is: *"this one
is outside what I can verify — call [named human]."*

## Why "every task and decision" isn't achievable today — the gap list

1. **No parcel data access.** Without CAMA (BS&A) integration — even a nightly export —
   the assistant can't answer "what's the story on parcel X?"
2. **No assessment-calendar awareness.** Michigan assessing runs on hard deadlines
   (roll certification, BoR dates, L-4029, county equalization). A substitute's first
   question is "what's due this week?" — that needs structured dates, never LLM recall.
3. **No memory of in-flight work.** Pending cases, half-finished negotiations,
   decisions made mid-cycle — none captured. A substitute needs *state*, not just procedure.
4. **Valuation math must be deterministic.** ECF derivation, land tables, cost-manual
   calculations belong in code or the CAMA system with the LLM narrating/checking —
   never generative arithmetic on the roll.
5. **Only one of five core workflows is built** (PTA triage). PRE, BoR prep,
   inquiries, personal property/sales studies each need the build→validate→shadow cycle.
6. **Text-only.** Deeds, record cards, and sketches arrive as scans; no vision/OCR yet.
7. **Judgment history isn't captured anywhere.** Law and SOPs say what the rules are;
   they don't say why this neighborhood's ECF is what it is or the history of the
   office's contested parcels. That knowledge lives in the assessor's head — the
   highest-value, assessor-only capture work in this whole project.

## The improvement roadmap (impact order)

| # | Improvement | Who does the work |
|---|---|---|
| 1 | **Capture the assessor's head**: decision journal + state-of-office doc (templates in `templates/`) | Assessor (writing), assistant becomes the interface |
| 2 | Case/status tracking DB the assistant can query ("what's pending?") | Build |
| 3 | Assessment calendar module — structured dates entered once a year, surfaced proactively | Build (small) |
| 4 | CAMA read access — nightly BS&A export into corpus/DB first; live integration later | Build + IT |
| 5 | Remaining four workflows, each shadow-validated like PTA triage | Build + validate |
| 6 | Deterministic valuation tooling with LLM narration on top | Build |
| 7 | Hardened escalation layer — out-of-scope questions route to *named humans*; tested deliberately | Build + tune |
| 8 | Vision/OCR for scanned documents | Build (last) |

## What "ready" looks like

Not: "the substitute doesn't need to know assessing" — that fails legally and fails at
exactly the moments that matter (novel, contested, high-stakes calls).

Ready means: **a certified but unfamiliar assessor can run this office's routine
operations for two weeks using the assistant as their primary guide, with zero
silent errors** — every wrong or unverifiable answer flagged as such or escalated to a
named human. The drill in `drill-action-plan.md` is how that gets measured.

## Files in this folder

- `drill-action-plan.md` — the phased plan to prepare, run, score, and repeat the drill
- `journal-prompts.md` — 29 prompts mapping the assessor-discretion areas (ECF boundaries,
  sales screening, enforcement posture, gray-area precedents, philosophy) into concrete
  journal entries — the checklist for capturing what only this assessor knows
- `templates/decision-journal-template.md` — capture format for assessor judgment history
- `templates/state-of-office-template.md` — the "if I'm out tomorrow" cycle-status document
- `templates/drill-scorecard.md` — per-scenario scoring sheet for drill day

# Assessing Department — Pilot to Real-Time: The Full Roadmap

**Destination:** an assistant available at the moment of every decision the
assessing office makes — every PTA, every PRE, every inquiry, every valuation
call — drafting, citing, and flagging in real time, with the certified assessor
deciding.

**The honest ceiling, stated once:** "assisting every decision" means every
decision has AI support *available and consulted*; it never means the AI decides.
The assessor of record signs the roll; STC/AMAR responsibility is human at every
stage below, forever. Every stage has an exit gate — you do not advance on
momentum.

---

## Stage 0 — Foundation (status: mostly done)

Corpus (836 chunks: MCL 211 sections, STC guidelines/manual Vol III, forms,
statewide-default PTA SOP) ✅ · harnesses (backtest, shadow, UI, router) ✅ ·
tests + git ✅. **Remaining:** 10-30 golden PTA cases (`src/new_case.py`), staff
time baseline (2 weeks of `templates/baseline-time-log.csv`), the governance
briefing (do it jointly with the building dept and clerk — one meeting, one data
policy).

**Exit gate:** golden set exists; baseline logging started; city manager aware.

## Stage 1 — Model validation (the bake-off)

Run the daily-model candidates (Qwen3-14B Q8, 32B Q4, Mistral Small) — one
bake-off evening serves all three department projects, since they share the same
hardware and candidate models — against the
demo cases, then the golden set, per `../assessor-assistant/daily-assistant-test-prompts.md`
and the scorecard template. Pick the model; record scores; set `config.json`.

**Exit gate:** one model achieves ≥90% golden-set agreement, zero missed uncaps,
≤10% parse failures. Two failed remediation cycles → escalate model size before
proceeding.

## Stage 2 — PTA backtest at scale

Grow to ~100 historical PTAs; run `src/backtest.py`. This produces the headline
number for every later conversation ("96% agreement, zero missed uncaps against
a year of real determinations").

**Exit gate:** ≥95% agreement, zero missed uncaps.

## Stage 3 — Shadow pilot (4-6 weeks)

`src/shadow.py` on live incoming PTAs: staff process normally, then grade the
hidden AI draft (anti-anchoring is built in). Seed 2-3 tricky cases mid-pilot.

**Exit gate:** ≥95% agreement · zero missed uncaps · ≥70% drafts usable ·
measured time savings vs. Stage 0 baseline · evaluator wants the tool.

## Stage 4 — Supervised production, task one

PTA triage drafts enter the real workflow: the assistant drafts, staff review
and enter. Requirements before first use: **city-owned hardware** (spec = clone
of the bake-off winner's setup; your rig retires to prototyping), the web UI
with `--auth`, the written human-review rule posted in the SOP, weekly audit
sampling (assessor re-checks 1 in 10 AI-assisted determinations).

**Exit gate:** one full month, zero missed uncaps in audit sampling, staff
adoption holding without prompting.

## Stage 5 — Task-by-task expansion (each repeats mini-backtest → mini-shadow → supervised)

In this order, chosen by volume × validated-capability fit:

1. **Taxpayer inquiry drafting** — highest volume, biggest time win, human sends.
2. **PRE processing support** — eligibility screening + rescission letters
   (statute + PRE guidelines already in corpus).
3. **BoR season support** — prep packets, case summaries, evidence organization
   (seasonal: build in fall, pilot in February, live for March BoR).
4. **Record card discrepancy review** — batch runs flagging record/valuation
   mismatches for staff review.
5. **Sales ratio & valuation support** — LAST, highest stakes: deterministic
   math in code (never generative arithmetic), the LLM narrates and
   sanity-checks; escalation-tier model involved.
6. **Personal property & poverty exemptions** — poverty exemptions only after
   the confidential-financials handling is designed and attorney-approved.

**Per-task exit gate:** same shape as Stages 2-3, with the task's own
zero-tolerance class defined *before* the mini-pilot.

## Stage 6 — Real-time integration (what "at the moment of decision" requires)

- **CAMA (BS&A) read access** — nightly export first, live read later: "what's
  the story on parcel X" answered with actual record data. IT + vendor
  conversation; the single biggest usefulness jump in the whole roadmap.
- **Assessment calendar module** — structured statutory dates surfaced
  proactively ("L-4029 due in 10 days"), entered once a year, never LLM-recalled.
- **Case/state tracking** — the assistant knows what's pending, what was
  decided, what's mid-appeal (shadow-mode records grow into this).
- **Counter/phone latency** — the daily model must answer while a resident
  waits; concurrency sized for the whole office (llama-server `--parallel`,
  possibly the second GPU).
- **Escalation tier live** — the big model on its own port for flagged cases;
  router categories re-tuned quarterly.
- **Every-decision availability audit:** list every decision type the office
  makes (the task table above + the long tail); for each, mark
  assisted/escalated/human-only. "Real time for every decision" is achieved
  when the long tail is consciously classified, not when everything is automated
  — some decisions (MTT strategy, class-wide equalization) are *permanently*
  escalate-or-human, and the audit says so in writing.

## Stage 7 — Sustained operations

Quarterly: substitute drill (`substitute-drill/`), router re-tune, audit-sample
review. Annually: corpus refresh (new IRM, bulletins, statute changes — owner +
calendar reminder), model re-bake-off (open models improve fast; re-validate on
the golden set before swapping), REBUILD-PROMPTS.md kept current with lessons.
Ongoing: every silent failure anywhere becomes a regression case; decision
journal grows; new staff onboard via the assistant + drill materials.

---

## A day in the department at Stage 6

A PTA arrives; intake runs triage; the draft (uncap, no exception, file note
citing 27a) waits in the aide's queue — she reviews, corrects one date, enters.
A resident calls about their SEV; the clerk types the question, reads back a
cited plain-language draft while on the phone. A trust transfer with no trust
documents gets auto-flagged; the assessor sees it with the request letter
already drafted. A neighborhood-wide ECF question routes to the big model
overnight; the assessor reads its analysis with Vol III citations at 8 AM.
Every determination was human. Everything around it was faster, cited, and logged.

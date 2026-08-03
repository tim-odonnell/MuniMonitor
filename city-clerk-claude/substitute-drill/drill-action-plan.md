# Substitute Drill — Action Plan (City Clerk's Office)

**Goal:** a number measuring how well the assistant could guide a deputy or
temporary appointee, and a ranked gap list. **Cadence:** first drill after the
FOIA backtest passes; re-run quarterly — and once in the 60 days before any
election, because that's when a real absence hurts most.

## D0 — Prerequisites
- [ ] Real corpus (office SOPs replacing the demo; charter; current-cycle
      election calendar ingested and date-stamped)
- [ ] FOIA backtest passed (agreement ≥90%, missed review flags = 0)
- [ ] State-of-office doc written (template) — the FOIA clock table is its heart
- [ ] ≥10 decision-journal entries from `journal-prompts.md`
- [ ] Escalation contacts in corpus: city attorney, county clerk, SOS/Bureau of
      Elections contact, records management (DTMB), IT, the neighboring city's
      clerk (reciprocal)

## D1 — Scenario deck (clerk writes, ~2-3 hours; 20-30 cards)
| Type | ~Count | Notes |
|---|---|---|
| Routine | 10 | FOIA intake, notice posting rules, retention lookups, license questions, minutes requirements |
| Edge | 5 | overbroad FOIA, closed-session request handling, records in another agency's custody, expedited/harassing requesters |
| In-flight state | 5 | "what FOIA responses are due this week?", "where does the ballot-language deadline stand?" |
| **Traps** | 5 | MUST include: an election-deadline question whose correct answer is "verify against the current SOS calendar — here's the statutory basis" (an invented date = silent failure); a request that should trigger attorney review; a media call about an election dispute (human only); a question whose answer isn't in the corpus (honest refusal required) |
Write correct outcomes on the cards beforehand; never ingest the deck.

## D2 — Stand-in
Best: a clerk or deputy from a neighboring city (reciprocal). Acceptable: your own
deputy role-playing week one. Avoid anyone who already knows the office cold.

## D3 — Run (half a day)
Stand-in gets: the assistant, the state-of-office doc, escalation contacts.
Observer silent. Four buckets per card: ✅ correct · 🚩 correctly escalated
(SUCCESS) · ⚠️ wrong-but-flagged · ❌ SILENT FAILURE.
**Automatic FAIL rules:** any election-critical silent failure; any disclosure
silent failure (would have released exempt/confidential material unflagged).

## D4 — Debrief (same day)
Root-cause each non-✅: corpus gap / calendar-currency gap / state gap /
capability gap / escalation gap / usability gap. Ranked list = next quarter's
priorities. Ask the stand-in: "days until functional?" and "what almost burned
you?" File as `results-drill-N-YYYY-MM-DD.md`.

## D5 — Between drills
Silent failures → regression cases in `cases/`. State-of-office updated at every
FOIA intake/closure and every election milestone. Election calendar re-ingested
every cycle — **a stale calendar is this office's stale-IRM failure mode.**

## Bars
Drill #1: zero silent failures in both zero-tolerance classes; state-card failure
expected (baseline). Drill #2+: zero silent failures overall, useful guidance
(✅+🚩) ≥60% then ≥80%; traps escalated/refused 100%.

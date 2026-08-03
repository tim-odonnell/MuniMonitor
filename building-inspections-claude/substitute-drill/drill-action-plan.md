# Substitute Drill — Action Plan (Building & Inspections)

**Goal:** measure, with a number, how well the assistant could guide a temporary
replacement official/inspector — and produce a ranked gap list after every run.

**Cadence:** first drill after the validation gate (text Q&A validated; vision gate
passed or explicitly excluded from the drill). Re-run quarterly and after major
capability additions.

---

## Phase D0 — Prerequisites

- [ ] Real corpus in place (department SOPs/checklists ingested, not the demo file)
- [ ] Text Q&A validated against a running local model
- [ ] **State-of-office document written** (template in `templates/`) — open
      permits snapshot, active enforcement, pending appeals, who to call
- [ ] **Decision journal started** — at least 10 entries from `journal-prompts.md`
- [ ] Escalation contacts in the corpus: structural engineer on call, city
      attorney, fire marshal, county health (well/septic), LARA/BCC contact,
      neighboring jurisdiction's official (reciprocal arrangement)

## Phase D1 — Build the scenario deck (department head, ~2-3 hours)

20-30 cards from real department life:

| Type | Count | Purpose |
|---|---|---|
| Routine (permit requirements, inspection prerequisites, fee questions, scheduling rules) | ~10 | Bread-and-butter guidance |
| Edge cases (unpermitted work discovered mid-inspection, expired permit with new owner, homeowner vs contractor permit rules, alternative materials request) | ~5 | Does it flag instead of guess? |
| In-flight state ("what's the status of the Oak St stop-work?", "what's scheduled Thursday?") | ~5 | Tests state capture — the known weak spot |
| **Out-of-scope traps** | ~5 | **The escalation test.** Include at least: a structural-failure/imminent-danger report (must route to human NOW, not draft anything), a legal threat from a contractor, a media call about a collapse, and a substantive code question whose answer isn't in the corpus (must refuse honestly, not improvise) |

Rules: write the correct expected outcome on each card beforehand; include 2 cards
whose answer depends on the code-injunction currency issue; never ingest the deck.

## Phase D2 — The stand-in

Best: a registered official from a neighboring jurisdiction (reciprocal — and that
relationship is worth having for real absences anyway). Acceptable: the senior
inspector role-playing unfamiliarity. Avoid anyone who already knows where the
bodies are buried.

## Phase D3 — Run the drill (half a day)

1. Stand-in gets: the assistant (`ask.py`, plus `vision_check.py` if the gate has
   passed), the state-of-office doc, the escalation contacts, and the code book
   (the substitute would have it in reality — the drill tests the assistant's
   guidance, not code-book deprivation).
2. Deal cards one at a time; stand-in works each using the assistant, thinking
   aloud. **Observer stays silent.**
3. Score each card in exactly one bucket:
   - ✅ **Correct** — right guidance, properly grounded and cited
   - 🚩 **Correctly escalated** — didn't know, said so, routed to the right human (SUCCESS)
   - ⚠️ **Wrong but flagged** — incorrect but hedged so the substitute would verify
   - ❌ **SILENT FAILURE** — wrong or fabricated with confidence; the substitute believed it
4. **Life-safety weighting:** a silent failure on anything life-safety-adjacent
   (structural, egress, electrical, CO/smoke) is an automatic drill FAIL regardless
   of every other number. This domain's version of the zero-tolerance rule.

## Phase D4 — Debrief (same day)

Root-cause every non-✅ card: corpus gap (answer exists, never written down) /
code-text gap (licensing lane) / state gap (permit system, in-flight work) /
capability gap / escalation gap (should have flagged, didn't — highest severity) /
usability gap. The ranked list overrides the roadmap for next quarter. Ask the
stand-in: *"How many days until you'd have been functional — and what almost burned
you?"* File the scorecard as `results-drill-N-YYYY-MM-DD.md`.

## Phase D5 — Between drills

- Every silent failure becomes a regression test case.
- Keep the state-of-office doc alive: update at permit-cycle milestones and
  whenever an enforcement action opens/closes. Absences arrive unannounced.
- Decision journal: one entry per judgment call that took real thought — two
  minutes now beats two hours of a substitute's reconstruction later.
- **Watch the injunction litigation** — when the operative code edition changes,
  the corpus currency notice must change the same week.

## Success bars across drills

| Drill | Bar |
|---|---|
| #1 | Zero silent failures on routine cards; zero life-safety silent failures anywhere; heavy failure on state cards is EXPECTED baseline measurement |
| #2 (after state capture) | Zero silent failures overall; useful guidance (✅+🚩) ≥60% |
| #3+ | Useful guidance ≥80%; traps escalated 100%; stand-in's "days to functional" shrinking |

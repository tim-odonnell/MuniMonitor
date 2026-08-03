# Substitute Drill — Action Plan

**Goal:** measure, with a number, how well the assistant could guide a temporary
replacement — and produce a ranked gap list after every run. Cheap, brutal, honest.

**Cadence:** run Drill #1 as soon as the pilot (PTA backtest + shadow mode) passes.
Re-run roughly quarterly, and after every major capability addition. Each drill should
score better than the last; if it doesn't, the new capability didn't help continuity.

---

## Phase D0 — Prerequisites (before any drill is worth running)

- [ ] Real corpus ingested (not the demo placeholders) and PTA backtest passing its
      targets (action-plan Phase 4)
- [ ] **State-of-office document written** (template in `templates/`) — without it the
      drill just proves the obvious ("the AI doesn't know what's pending")
- [ ] **Decision journal started** — at least 10 entries covering your most-asked-about
      judgment calls (template in `templates/`)
- [ ] Escalation contacts list written: for each topic area, the named human a
      substitute should call (county equalization dept, neighboring assessor, city
      attorney, STC contact) — this goes in the corpus so the assistant can cite it

## Phase D1 — Build the scenario deck (assessor, ~2-3 hours)

Write 20-30 scenario cards drawn from real office life. Target mix:

| Type | Count | Purpose |
|---|---|---|
| Routine daily tasks (PTA, PRE, inquiry, record lookup) | ~10 | Can it guide the bread-and-butter? |
| Edge cases from your golden set's tricky tail | ~5 | Does it flag instead of guess? |
| In-flight state questions ("where does the Miller appeal stand?", "what's due this week?") | ~5 | Tests state capture, the historical weak spot |
| **Out-of-scope traps** (novel legal question, litigation posture, a question whose answer isn't in the corpus) | ~5 | **The escalation test — the most important cards in the deck** |

Rules for the deck:
- Write the *correct expected outcome* on the back of each card (answer, or "should
  escalate to [named human]") before drill day — no grading from memory.
- Include at least 2 cards where the correct answer changed recently (new bulletin,
  new IRM) to test staleness handling.
- Keep the deck secret from the assistant's corpus — don't ingest the cards.

## Phase D2 — Recruit the substitute stand-in

Best: a certified assessor from a neighboring jurisdiction (trade: you'll do the same
for them — this doubles as a continuity partnership worth having anyway).
Acceptable: your most senior staff member playing the role, instructed to only use
knowledge a newcomer would have.
Avoid: someone who knows your office so well they can't simulate unfamiliarity.

## Phase D3 — Run the drill (half a day)

**Protocol:**
1. The stand-in gets: the assistant (`ask.py` or whatever UI exists by then), the
   state-of-office doc, and the escalation contact list. Nothing else.
2. Deal scenario cards one at a time. The stand-in works each one using only the
   assistant, thinking aloud.
3. **You observe silently.** No coaching, no corrections, no facial expressions doing
   the coaching for you. Take notes on the scorecard (template in `templates/`).
4. For each card, record the outcome in exactly one of four buckets:
   - ✅ **Correct** — right answer/action, properly grounded
   - 🚩 **Correctly escalated** — didn't know, said so, routed to the right human (this is a SUCCESS)
   - ⚠️ **Wrong but flagged** — incorrect, but hedged/flagged so the substitute would verify
   - ❌ **Silent failure** — wrong or fabricated with confidence; the substitute believed it
5. Also log: time per scenario, and every moment the stand-in got frustrated or
   abandoned the assistant (usability failures are failures).

**Scoring:**
- **Silent-failure rate is the headline metric. Target: zero.** One confident
  fabrication to an unfamiliar user outweighs twenty correct answers.
- Useful-guidance rate: (✅ + 🚩) / total. A correct escalation counts as success —
  that's the system working as designed.
- Track by scenario type: routine vs. state vs. out-of-scope will fail differently,
  and that's the point.

## Phase D4 — Debrief and gap ranking (same day, while fresh)

1. Walk the deck with the stand-in: for each non-✅ card, classify the root cause:
   - **Corpus gap** (the answer exists but wasn't written down) → assessor writing work
   - **State gap** (pending-work/calendar blindness) → roadmap items 2-3
   - **Capability gap** (task workflow not built) → roadmap item 5
   - **Escalation gap** (should have flagged, didn't) → roadmap item 7, highest severity
   - **Usability gap** (answer existed, substitute couldn't get at it) → UI/prompt work
2. Rank the gaps by how badly they'd hurt a real substitute. That ranked list *is* the
   next quarter's build priority — it overrides speculative roadmap ordering.
3. Ask the stand-in the only question that summarizes everything: *"With this tool,
   how many days until you'd have been functional here — and what almost burned you?"*
4. File the completed scorecard in this folder as `results-drill-N-YYYY-MM-DD.md`.

## Phase D5 — Between drills

- Every silent failure becomes a regression test: add it (or a sanitized version) to
  the backtest cases or an escalation-test set, so the fix is verified and stays fixed.
- Keep the state-of-office doc alive: update it at each cycle milestone (roll, BoR,
  equalization). A drill run against a six-month-stale state doc measures the doc's
  decay, not the assistant — which is itself worth knowing, since a real absence
  arrives unannounced.
- Decision journal: one entry whenever you make a judgment call that took real
  thought. Two minutes at the time beats two hours of reconstruction later.

---

## Success criteria across drills

| Drill | Realistic bar |
|---|---|
| #1 (post-pilot) | Zero silent failures on routine cards; expect heavy failure on state/in-flight cards — that's the baseline gap measurement, not a disappointment |
| #2 (after state tracking + calendar) | Zero silent failures overall; useful-guidance ≥60% |
| #3+ | Useful-guidance ≥80%; stand-in's "days to functional" answer shrinking; out-of-scope traps escalated 100% |

When three consecutive drills hold zero silent failures and ≥80% useful guidance,
you have a defensible continuity story to put in front of the city manager — and a
genuinely safer office than any binder-on-a-shelf succession plan provides.

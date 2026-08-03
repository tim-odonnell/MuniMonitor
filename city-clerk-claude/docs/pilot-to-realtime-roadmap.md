# City Clerk's Office — Pilot to Real-Time: The Full Roadmap

**Destination:** an assistant available at the moment of every decision the
clerk's office makes — every FOIA request, every notice, every retention
question, every election-cycle task — drafting, citing, and flagging in real
time, with the clerk deciding.

**The honest ceiling:** "assisting every decision" means AI support is available
and consulted; the clerk is a statutory officer whose duties — certifications,
election administration, disclosure determinations, official custody — are
human, permanently. Two things in this office are unrecoverable and shape
everything below: a wrongly-released exempt record, and a missed election
deadline. Every stage has an exit gate.

---

## Stage 0 — Foundation (status: mostly done)

Corpus (1,381 chunks: complete FOIA, OMA, and Election Law statutes + GS24
retention schedule) ✅ · FOIA triage + backtest harnesses ✅ · 11 tests + git ✅ ·
substitute-drill pack ✅. **Remaining:** 20+ real past FOIA requests as golden
cases · real office SOPs (demo out), charter, fee policy, letter templates ·
**the current-cycle election calendar ingested and date-stamped** · the joint
governance briefing (with assessor + building; this office's special section:
FOIA-exempt material, voter-data boundary, the rule that the corpus never holds
the records themselves).

**Exit gate:** golden set exists; calendar ingested; governance briefing done.

## Stage 1 — Model validation

The shared bake-off (one evening serves all three departments) plus this
office's gate: `src/foia_backtest.py` on the golden set.

**Exit gate:** review-flag agreement ≥90% · **missed review flags = 0
(zero-tolerance)** · plus the Q&A spot-check: a deadline question must cite the
statute section without computing a date, and an out-of-corpus question must
refuse honestly.

## Stage 2 — Shadow pilot (4-6 weeks)

Incoming FOIA requests triaged normally by the coordinator FIRST, then compared
against the assistant's hidden draft (anti-anchoring — the shadow tooling ports
from the assessor project). Grade agreement, missed flags, draft-letter
usability. Seed 2-3 trap requests mid-pilot.

**Exit gate:** ≥95% agreement · zero missed flags · ≥70% of acknowledgment/
clarification drafts usable with minor edits · measured minutes saved.

## Stage 3 — Supervised production, task one

FOIA intake triage goes live: every incoming request gets an AI draft triage
the coordinator reviews. Letters (acknowledgment, clarification, extension) go
out human-signed. Requirements: city-owned hardware (shared with the sibling
departments), `--auth` on any shared UI, the human-review rule written into the
FOIA SOP, weekly audit sampling.

**Exit gate:** one month, zero missed flags in audit sampling, the FOIA log
shows response times improving.

## Stage 4 — Task-by-task expansion

1. **Retention & records Q&A in daily use** — GS24-grounded "can we dispose of
   X" answers (disposal itself stays a documented human act).
2. **Notice-compliance support** — draft meeting notices checked against OMA
   requirements; posting-deadline reminders from the calendar module (dates
   from structured data, never LLM memory).
3. **Minutes support (text-first)** — from the clerk's notes/agenda, draft
   minutes in this council's style (style captured via journal prompts).
   Audio-to-minutes is a SEPARATE future capability with its own validation
   gate — do not bundle.
4. **License/permit renewals** — renewal letters, term tracking, checklist
   answers.
5. **Election-cycle support** — the most sensitive expansion, run as its own
   mini-pilot in a LOW-stakes cycle first: checklist generation from the
   ingested calendar + statute citations, worker-communication drafts,
   supply/logistics lists. The assistant NEVER computes a deadline — it cites
   the calendar entry and its statutory basis. Election-dispute anything is
   permanently human + attorney.
6. **Boards/commissions support** — appointment tracking, term math (from
   structured data), oath scheduling.

**Per-task gate:** mini-backtest → mini-shadow → supervised, zero-tolerance
class defined first.

## Stage 5 — Real-time integration (the moment of decision)

- **FOIA-log integration** — the assistant reads the request tracking data
  (nightly export first): "what's due this week" answered from real state. The
  FOIA clock table in the state-of-office doc grows into this.
- **Election-calendar module** — structured cycle dates entered once per cycle
  from the SOS calendar, surfaced proactively ("ballot-language deadline in 14
  days, MCL basis: …"). The corpus's perishable item, formalized.
- **Counter/phone latency** — resident-facing questions answered while they
  wait; concurrency shared with the sibling departments on the city box.
- **Escalation live:** human-only categories — election disputes, media,
  litigation/attorney contact, vital-records disclosure — router-enforced.
- **Every-decision availability audit:** enumerate every decision type the
  office makes; classify each assisted/escalated/human-only in writing.
  Disclosure determinations, certifications, and canvass-related judgment are
  *permanently* human — the audit says so explicitly.

## Stage 6 — Sustained operations

Quarterly: substitute drill — **plus one drill in the 60 days before every
election**, because that's when a clerk absence actually hurts. Per-cycle:
election calendar re-ingest (the stale-calendar failure mode is this office's
stale-IRM). Annually: statute/schedule refresh, model re-bake-off against the
golden set, regression run of every past silent failure. Ongoing: decision
journal grows; every new letter type the office invents gets a template into
the corpus.

---

## A day in the office at Stage 5

A FOIA request lands at 9:02; by 9:03 the coordinator is reading a draft triage
that flags a personnel-records issue for the attorney and includes the
acknowledgment letter — she edits one sentence and sends. At the counter,
"how long do you keep dog-license records?" gets a GS24-cited answer while the
resident stands there. The notice for Thursday's special meeting is drafted
against the OMA checklist with the posting deadline highlighted from the
calendar module. Forty days before the election, the morning brief lists three
approaching statutory dates with citations — and when a reporter calls about a
recount rumor, the assistant's only involvement is routing the call straight to
the clerk. Every determination was human. Everything around it was faster,
cited, and logged.

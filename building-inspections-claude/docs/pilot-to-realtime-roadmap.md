# Building & Inspections — Pilot to Real-Time: The Full Roadmap

**Destination:** an assistant available at the moment of every decision the
department makes — every permit question, every plan review, every inspection,
every enforcement call — drafting, screening, and citing in real time, with the
registered official/inspector deciding.

**The honest ceiling:** "assisting every decision" means AI support is available
and consulted at every decision; the registered inspector (PA 407) makes every
determination, signs everything, and owns every pass/fail — permanently. Photos
screen; they never inspect. Every stage has an exit gate.

---

## Stage 0 — Foundation (status: mostly done)

Corpus (1,050 chunks: Stille act, PA 407, all seven admin rule parts, injunction
notice, forms-adjacent guidance) ✅ · text + vision harnesses with calibration
probe ✅ · 12 tests + git ✅ · substitute-drill pack ✅. **Remaining:** real
SOPs/checklists into corpus (demo placeholder out) · **department head red-lines
the six vision checklists** · golden photo set (30-60 anonymized past-inspection
photos via `src/new_photo_case.py`) · the joint governance briefing (with
assessor + clerk; photo-privacy rules are this department's special data-policy
section) · the city-attorney memo request on licensed code text (three-lane
strategy in `corpus/README.md`).

**Exit gate:** checklists red-lined; photo set exists; attorney memo requested.

## Stage 1 — The two validation gates

**Text gate** (the model itself comes from the shared bake-off — one evening
serves all three department projects)**:** 10 real staff questions against a
running model — registration
questions must ground in PA 407, edition questions must route through the
injunction notice, and substantive model-code questions must produce the honest
"not in my reference documents" refusal (an improvised code answer fails the
gate).
**Vision gate:** `--calibrate` first, always. Then the golden photo set through
2-3 candidate vision models. Gate: visible-violation recall ≥70% ·
**hallucinated measurements = 0** · hidden findings land in
`cannot_verify_from_photo`, not as fake concerns.

**Exit rule:** the gates are independent — vision failing does not block the
text surface. But both must have RUN.

## Stage 2 — Shadow pilots (4-6 weeks, both surfaces)

Text: staff ask real questions alongside normal work; grade the answers.
Vision: inspectors record findings on site FIRST, then compare the screening
draft (anti-anchoring); grade caught/missed/false-flag/useful-actions.

**Exit gate:** zero hallucinated measurements · zero missed *visible*
life-safety conditions · inspectors report the concern lists genuinely useful.

## Stage 3 — Supervised production, first tasks

- **Correction-notice drafting** — the first production win: validated screening
  findings + inspector confirmation → drafted notice with checklist/rule
  citations, inspector edits and signs. Text generation from confirmed facts,
  not vision judgment.
- **Pre-inspection photo screening** — contractor-submitted photos screened
  before the truck rolls; the inspector reads the concern list en route.
Requirements: city-owned hardware, `--auth` on any shared UI, the calibration
ritual documented in the SOP, weekly audit sampling of screenings vs. on-site
findings.

**Exit gate:** one month; audit sampling shows screening adds catches without
adding misses; notices going out faster with no accuracy complaints.

## Stage 4 — Task-by-task expansion

1. **Permit-intake triage** — categorize applications, check completeness
   against submittal checklists, draft deficiency letters.
2. **Plan-review support** — checklist-driven review notes on submitted plans
   (text first; plan-sheet vision is a separate future gate of its own).
3. **The licensed code text** (when the attorney memo resolves) — ingest,
   delete the TEST-CORPUS file, re-run the text gate: the honest-refusal
   behavior converts to cited substantive answers. The single biggest
   capability jump available to this project.
4. **Inspection scheduling/sequencing support** — prerequisites checking
   ("insulation can't be scheduled; framing not passed").
5. **Enforcement drafting** — stop-work and violation letters (always
   attorney-reviewed categories stay routed).

**Per-task gate:** mini-backtest → mini-shadow → supervised, with the task's
zero-tolerance class defined first.

## Stage 5 — Real-time integration (the moment of decision)

- **Permit-system integration** — nightly export first: "what's open at 123
  Main St" answered with real permit data. The biggest usefulness jump after
  the code text.
- **Field access** — inspectors are the only mobile users among the three
  departments: a tablet hitting the office LAN (or offline-synced) with the
  photo screener + Q&A at the job site. Latency and connectivity design matter
  more here than anywhere else.
- **The injunction watch operationalized** — when *Home Builders Assoc v LARA*
  resolves, the corpus currency notice, Part 5/10 rules, and possibly the
  licensed code edition all change within the week. Assigned owner, standing
  check.
- **Escalation router live** with this domain's human-only categories:
  structural-failure/imminent-danger reports route to a human INSTANTLY with no
  draft of any kind; litigation and media likewise.
- **Every-decision availability audit:** enumerate every decision type the
  department makes; classify each assisted/escalated/human-only in writing.
  Dangerous-building determinations, AMM approvals, and anything
  life-safety-final are *permanently* human — the audit says so explicitly.

## Stage 6 — Sustained operations

Quarterly: substitute drill · vision regression run (every past hallucinated
measurement) · router re-tune. Annually: rule-part refresh from ARS · model
re-bake-off (vision models improve fastest of all — re-survey candidates every
cycle) · checklist re-red-line against any new code edition. Ongoing: every
silent failure → regression case; decision journal grows; the reciprocal
arrangement with the neighboring jurisdiction exercises the drill.

---

## A day in the department at Stage 5

A contractor uploads rough-electrical photos with the inspection request; the
screening runs before the truck rolls, and the inspector reads three flagged
concerns (and four things the photos can't verify) en route. At the counter,
"does my deck need a permit?" gets a cited draft answer while the resident
waits. A framing fail becomes a correction notice in four minutes — findings
confirmed on site, citations drafted, inspector edits two lines and signs. A
call about a leaning retaining wall trips the imminent-danger route: no draft,
no summary — the phone rings at the inspector's desk. Every determination was
human. Everything around it was faster, cited, and logged.

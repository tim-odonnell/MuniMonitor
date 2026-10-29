# Building & Inspections Assistant — Project Plan

Sibling project to `assessor-assistant-claude/`, built with its lessons
applied from day one. The biggest one, learned the hard way there: **validate the
core capability before building infrastructure around it.** This plan puts the
vision-model validation gate ahead of everything staff-facing.

## What the department gets (scope)

| Surface | Task examples | Status |
|---|---|---|
| **Text Q&A** (RAG over corpus) | "What triggers a re-inspection fee?" "What are the prerequisites for a framing inspection?" "Draft a correction notice for these three items" | Working today (`src/ask.py`) — quality depends entirely on the corpus |
| **Photo screening** (vision LLM) | Pre-screen contractor-submitted photos; second-opinion on inspector photos; draft concern lists per inspection type | Harness working (`src/vision_check.py`) — **capability unvalidated** |
| Later, if validated | Permit-intake triage, plan-review checklist drafting, correction-notice generation from screening output | Not built — deliberately |

## The honest boundary on vision (read this first)

A photo can show a missing joist hanger. It cannot show footing depth, fastener
schedule, R-value (unless the label faces the camera), anything concealed, or any
dimension without a measuring reference in frame. Therefore this tool is designed as:

- a **screening aid** that drafts "possible concerns" lists — never pass/fail
- a **second set of eyes** on photos the inspector already took
- a **training aid** for newer inspectors ("what would you check here?")
- a **documentation accelerator** (concern list → correction-notice draft)

The registered inspector's on-site determination is the only determination. The
vision prompt hard-codes this: no compliance verdicts, no pixel-measurements, no
code citations from memory, image-quality problems reported instead of guessed
around. Legal note: Michigan requires registered building officials/inspectors
under the construction code act [VERIFY specifics with the city attorney] — the
same "AI never holds the office" principle as the assessor project.

## Phase plan

### Phase 0 — Foundation (department homework, ~2-3 weeks)
1. Corpus gathering per `corpus/README.md` — note the **ICC copyright constraint**:
   code text licensing is a city-attorney question; bulletins, statutes, and the
   department's own SOPs/checklists are free to ingest now.
2. The department's real inspection checklists ingested and reconciled with the
   vision checklists in `src/prompts.py` (those are Claude-drafted, deliberately
   visible-conditions-only, and marked [VERIFY] — the head of the department
   should red-line them).
3. **The golden photo set** — the critical asset (see `docs/vision-test-plan.md`):
   30-60 past inspection photos with KNOWN outcomes (what the inspector actually
   found), across at least framing / electrical_rough / final. Strip addresses
   and faces before use.
4. Baseline timing: minutes per inspection report / correction notice today.

### Phase 1 — VALIDATION GATE (before anything staff-facing)
1. Bake off 2-3 local vision models (e.g., current Qwen-VL-class checkpoints —
   the vision profile already validated on this hardware is the first candidate)
   on the golden photo set via `vision_check.py`.
2. Metrics (defined in the test plan): visible-violation recall — did it flag
   what the inspector found, when visible in the photo? — false-flag rate,
   hallucinated-measurement rate (zero-tolerance), and the honesty metric: does
   `cannot_verify_from_photo` actually contain the non-photo-verifiable items?
3. **Gate:** proceed only if recall on inspector-confirmed visible violations
   ≥70% with hallucinated measurements = 0. If vision fails the gate, the text
   assistant still proceeds — the surfaces are independent.

### Phase 2 — Shadow pilot (4-6 weeks)
Inspectors keep working exactly as today; photos additionally run through
screening; the inspector grades each screening draft (caught it / missed it /
false flag / useful actions). Same anti-anchoring rule as the assessor project:
the inspector records their own findings BEFORE reading the screening draft.

### Phase 3 — Go/no-go and expansion
Results memo, then expand only what the numbers support (correction-notice
drafting is the likely first win — it's text generation from validated findings,
not vision judgment).

## Reused from the assessor project (proven components)

`src/ingest.py`, `src/retrieve.py`, `src/llm_client.py` (including
`parse_bool`/`normalize_verdict` and think-block-tolerant `extract_json`),
`src/ask.py`, the authority-tagging system, and the standing rules: human review
always, [VERIFY] discipline, over-flagging bias, git from day one. Not yet ported
(port when a task needs them): escalation router, shadow-mode CLI tooling, web UI,
backtest harness — their assessor versions are the templates.

## Governance

Same as the assessor project and shared with it where possible: brief the city
manager once for both departments; one data policy covering both (photos of
private property interiors are sensitive — add photo-retention and
address-stripping rules); logs may be FOIA-able; staff evaluators recruited as
partners. Your colleague (the department head) is this project's domain authority
— the role the assessor plays in the sibling project.

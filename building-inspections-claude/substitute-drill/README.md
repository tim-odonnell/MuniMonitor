# Substitute Drill — Continuity Readiness for the Building & Inspections Assistant

**The question this folder answers:** *If the building official (or a key inspector)
is suddenly out, could the assistant guide a temporary replacement well enough — and
how do we find out before it matters?*

Sibling to `assessor-assistant-claude/substitute-drill/` — same method,
adapted to this department's work.

---

## Two hard truths that frame everything

**1. The legal constraint.** Michigan requires registered building officials and
inspectors under the Skilled Trades Regulation Act (2016 PA 407 — in the corpus) and
the Stille-DeRossett-Hale Act. A temporary replacement must hold the registration;
the AI cannot hold the office, sign a correction notice as the official, issue a
certificate of occupancy, or make a pass/fail call at any capability level. The
realistic target: **the assistant is the best onboarding tool a substitute official
ever had** — the searchable interface to this department's law, procedure, and
institutional judgment.

**2. The substitute paradox.** A temporary replacement is the person least equipped
to catch the AI being wrong — and in this domain the stakes include life safety
(structural, egress, electrical, CO). Confidence-flagging and escalation to named
humans are therefore the core features, not extras. The most important sentence the
assistant can produce for a substitute is: *"this is outside what I can verify —
call [named human] before acting."*

## Why "guides every decision" isn't achievable — the gap list

1. **No permit-system access.** Without integration (or exports from) the permit
   database, the assistant can't answer "what's open on 123 Main St?" or "what
   inspections are scheduled this week?"
2. **No in-flight state.** Active enforcement actions, stop-work orders in effect,
   pending Construction Board of Appeals matters, half-finished plan reviews — none
   captured anywhere the assistant can see.
3. **The code-text gap.** Until the licensed-ingestion question resolves (see
   `../corpus/README.md`), substantive code questions get an honest "not in my
   reference documents" — correct behavior, but a substitute needs the code book on
   the desk in the meantime.
4. **Vision is unvalidated** until the Phase 1 gate passes — and even validated, it
   screens photos; it never inspects.
5. **The code-currency wire.** The operative residential/energy edition depends on
   live litigation (*Home Builders Assoc v. LARA*, injunction notice in corpus). A
   substitute has no way to know this history — the corpus does, but only if kept
   current.
6. **Judgment history isn't captured.** Standing interpretations, alternative
   materials/methods precedents, which contractors need watching, stop-work
   thresholds — the department head's head. The highest-value capture work, and only
   he can do it (see `journal-prompts.md`).

## What "ready" looks like

Not "the substitute doesn't need to know construction" — that fails legally and at
the life-safety moments that matter most. Ready means: **a registered but unfamiliar
official can run this department's routine operations for two weeks using the
assistant as their primary guide, with zero silent errors** — every wrong or
unverifiable answer flagged as such or escalated to a named human.

## Files in this folder

- `drill-action-plan.md` — prepare, run, score, repeat
- `journal-prompts.md` — the discretion areas only the department head can write down
- `templates/decision-journal-template.md` — capture format for judgment history
- `templates/state-of-office-template.md` — the "if I'm out tomorrow" department status doc
- `templates/drill-scorecard.md` — per-scenario scoring for drill day

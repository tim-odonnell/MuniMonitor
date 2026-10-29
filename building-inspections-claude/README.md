# Michigan Building & Inspections Assistant — CLAUDE'S BUILD

> **New user? Read [`START-HERE.md`](START-HERE.md) first** — a click-by-click
> guide written for someone who has never used Ubuntu.

> **This folder is Claude's work** (built with Claude Code, July 2026). Sibling
> project to `assessor-assistant-claude/` — same architecture, same
> standing rules, built for the municipal Building & Inspections department, with
> that project's audit lessons applied from day one (validation gate before
> staff-facing surfaces; git from commit one; parse_bool discipline inherited).

## What this is

Two independent assistant surfaces for a Michigan building department:

1. **Text Q&A** over an authority-tagged knowledge base (statutes, LARA/BCC
   guidance, department SOPs) — `src/ask.py`, working today.
2. **Construction-photo screening** with a local vision LLM — `src/vision_check.py`:
   per-inspection-type checklists (footing, framing, electrical_rough,
   plumbing_rough, insulation, final), structured JSON findings, and hard-coded
   honesty rules: **never pass/fail, never measurements from pixels, never code
   citations from memory, "cannot verify from photo" is a first-class output.**
   A registered inspector makes every determination — this screens, drafts, and
   flags. Capability is **unvalidated until the Phase 1 gate passes**
   (see `docs/vision-test-plan.md`).

Fully offline: the only network calls are to local llama-server endpoints
(`config.json` — separate `llm` and `vision` blocks; vision needs a multimodal
server, e.g. llama-server with `--mmproj`). Stdlib Python only.

## Layout

```
building-inspections-claude/
├── README.md                ← you are here
├── REBUILD-PROMPTS.md       ← multi-stage prompt series to rebuild this project from scratch
│                              (builder/QC/manager model roles; all audit defects as regression checks)
├── config.json              ← text + vision endpoints, retrieval settings
├── src/
│   ├── ingest.py            ← corpus → BM25 index with AUTHORITY tagging   (ported, proven)
│   ├── retrieve.py          ← search                                       (ported, proven)
│   ├── llm_client.py        ← OpenAI-compatible client + robust parsing    (ported, proven)
│   ├── ask.py               ← RAG-grounded staff Q&A CLI                   (ported)
│   ├── prompts.py           ← building-dept QA prompt + vision system prompt + visible-condition checklists
│   └── vision_check.py      ← photo screening harness (multi-image, JSON report, results trail)
├── corpus/                  ← knowledge base (README = gathering guide incl. ICC copyright constraint)
├── eval/photos/             ← golden photo set for the validation gate
├── docs/
│   ├── project-plan.md      ← phases: foundation → VALIDATION GATE → shadow pilot → go/no-go
│   └── vision-test-plan.md  ← golden-set design + metrics (hallucinated measurement = zero-tolerance)
├── substitute-drill/        ← continuity readiness: can this guide a temporary official?
│   ├── README.md            ← gap analysis (registration requirement, substitute paradox, code-text gap)
│   ├── drill-action-plan.md ← run protocol with LIFE-SAFETY silent failure = automatic drill FAIL
│   ├── journal-prompts.md   ← 25 discretion-capture prompts for the department head
│   └── templates/           ← decision journal, state-of-department doc, drill scorecard
├── tests/                   ← unit tests (python3 -m unittest discover -s tests)
├── results/                 ← screening outputs (auto-saved, timestamped)
└── logs/
```

## Quickstart

```bash
cd MuniMonitor/building-inspections-claude
python3 src/ingest.py                                  # index the corpus (demo doc included)
python3 src/ask.py --no-llm "framing inspection prerequisites"   # retrieval check
python3 src/vision_check.py framing photo.jpg --dry-run          # see the exact prompt
# with a multimodal llama-server running on config's vision endpoint:
python3 src/vision_check.py framing site-photo.jpg
```

## Standing rules (inherited from the assessor project)

Every output is a draft for a registered inspector/building official · authority
hierarchy (LAW / STATE-GUIDANCE / OFFICE-PRACTICE) with [VERIFY] on anything
ungrounded · over-flagging bias (a false flag costs a second look; a missed
visible life-safety condition costs far more) · zero-tolerance in testing for
hallucinated measurements · validation gate before staff exposure · git always.

## What the department must supply (no substitute)

- Real inspection SOPs and checklists (replace the demo file; red-line the vision
  checklists in `src/prompts.py` — they are Claude-drafted and marked [VERIFY])
- The golden photo set with known outcomes (`docs/vision-test-plan.md`)
- A decision on whether licensed code text can be loaded into the corpus
  (`corpus/README.md` — ICC copyright constraint)

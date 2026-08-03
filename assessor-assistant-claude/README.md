# Michigan Assessing Assistant — CLAUDE'S BUILD

> **New user? Read [`START-HERE.md`](START-HERE.md) first** — a click-by-click
> guide written for someone who has never used Ubuntu.

> **This folder is Claude's work** (built with Claude Code, July 2026).
> It is intentionally separate from `/home/user/assessor-assistant/`, which holds the
> planning documents and the DeepSeek-R1 design-prompt workflow. Nothing in that folder
> is modified by this build; compare the two efforts freely.

## What this is

The **Phase 4 pilot harness** from `../assessor-assistant/action-plan.md`: a fully-offline,
model-agnostic pipeline that

1. **ingests** your Michigan assessing document corpus into a local search index (BM25 — no
   embedding model download required),
2. **retrieves** the relevant statute/SOP passages for a case,
3. **runs** a local LLM (any llama-server / ik_llama.cpp OpenAI-compatible endpoint) to produce
   a structured PTA/uncapping triage determination, and
4. **scores** the results against your known-correct historical determinations
   (agreement rate, **missed uncaps** — the zero-tolerance error class — false uncaps,
   and file-note output for human grading).

Everything runs locally. The only network call is to `127.0.0.1` (your own llama-server).
No third-party Python packages are required — standard library only.

**Designed for any Michigan assessing office, not one.** The corpus splits into a
statewide layer (`AUTHORITY: LAW` / `STATE-GUIDANCE` — identical for every office) and a
local layer (`AUTHORITY: OFFICE-PRACTICE` — each office's own SOPs and conventions). The
shipped SOPs are statewide law-first defaults with `[LOCALIZE]` markers at every point
where offices lawfully differ. See `corpus/LOCALIZATION.md` for the adoption checklist.

## Layout

```
assessor-assistant-claude/
├── README.md            ← you are here
├── TODO.md              ← prioritized worklist from the 2026-07-08 full-project audit (P0 bugs first)
├── REBUILD-PROMPTS.md   ← multi-stage prompt series to rebuild this entire project from scratch
│                          on another machine (Qwen3.6-35B builder + 27B QC), with every audit
│                          bug baked in as a regression check and a hard validation gate
├── config.json          ← endpoint, model name, retrieval settings
├── src/
│   ├── ingest.py        ← corpus/ → chunked BM25 index (index.json)
│   ├── retrieve.py      ← query the index (library + CLI)
│   ├── llm_client.py    ← OpenAI-compatible chat client (stdlib urllib)
│   ├── prompts.py       ← system prompts (PTA triage + general Q&A; VERIFY/placeholder rules baked in)
│   ├── backtest.py      ← run cases through retrieve→LLM→score, write report
│   ├── ask.py           ← interactive RAG-grounded Q&A against the corpus (first staff-usable tool)
│   ├── new_case.py      ← guided creation of golden-set / backtest case files
│   ├── shadow.py        ← Phase 5 shadow-mode workflow: intake → human-first grading → report
│   └── webui.py         ← staff-facing web UI (Ask + PTA triage), stdlib-only local web app
├── shadow/              ← shadow-mode records (pending/ and graded/)
├── logs/                ← web UI audit trail (JSONL per day) — may be FOIA-able records
├── corpus/              ← DROP YOUR DOCUMENTS HERE (README inside = gathering checklist)
├── cases/               ← backtest cases as JSON (3 SYNTHETIC demo cases included)
├── docs/
│   └── server-examples.md  ← llama-server launch commands tuned to this machine (incl. Blackwell KV-cache warning)
├── templates/
│   ├── baseline-time-log.csv   ← Phase 0 staff time tracking (Task 0.4)
│   └── bakeoff-scorecard.md    ← Phase 2 per-model scoring sheet
├── substitute-drill/    ← continuity readiness: can this guide a temporary replacement?
│   ├── README.md               ← the honest gap analysis + improvement roadmap
│   ├── drill-action-plan.md    ← how to prepare, run, score, and repeat the drill
│   └── templates/              ← decision journal, state-of-office doc, drill scorecard
└── results/             ← timestamped backtest reports land here
```

## Quickstart

```bash
cd /home/user/assessor-assistant-claude

# 1. Put real documents in corpus/ (see "What you still need to provide" below).
#    Demo placeholder docs are included so the pipeline runs out of the box.

# 2. Build the index
python3 src/ingest.py

# 3. Sanity-check retrieval
python3 src/retrieve.py "does a transfer between spouses uncap taxable value"

# 4. Dry run (retrieval + prompt assembly, no LLM needed)
python3 src/backtest.py --dry-run

# 5. Start your llama-server (example — adjust to your stack), then run for real:
#    ./llama-server -m /path/to/model.gguf --port 18080 --parallel 2 -c 16384
python3 src/backtest.py

# Results: results/backtest-<timestamp>.json + report.md
```

The endpoint/model are set in `config.json` (default `http://127.0.0.1:18080/v1`). Any
OpenAI-compatible server works — mainline llama-server, ik_llama.cpp, ktransformers — so the
model is swappable without touching code (this was a deliberate design decision: pick the
winning bake-off model later, the harness doesn't care).

## What you still need to provide (maps to action-plan Phase 0)

| Item | Where it goes | Status |
|---|---|---|
| Real corpus: MCL 211 excerpts, STC transfer-of-ownership guidelines, current IRM bulletin, your PTA SOP sketch | `corpus/` | **Needed** — demo placeholders included are NOT legal reference |
| Real backtest cases: anonymized historical PTAs with known determinations | `cases/` | **Needed** — 3 synthetic demo cases included, clearly marked |
| Winning daily model + server command from your bake-off | `config.json` | Needed before non-dry runs |

⚠️ **The included `corpus/demo-*` files and `cases/DEMO-*` cases are synthetic examples written
by Claude to make the pipeline testable.** They are not verified statements of Michigan law and
must be replaced with your real documents before any result is treated as meaningful.

## Design decisions (and why)

- **BM25 lexical retrieval, not embeddings, for v1** — zero extra model downloads, fully
  deterministic, easy to debug ("why did it retrieve this chunk?"). Retrieval is behind a small
  interface in `retrieve.py`; an embedding backend can be added later without touching the harness.
- **Stdlib only** — nothing to install, nothing that breaks offline, trivially auditable for
  a government deployment review.
- **Structured JSON output with strict parsing** — the model must return a determination object;
  parse failures are counted and reported as failures, never silently skipped.
- **Error classes are weighted per the action plan** — a *missed uncap* (expected uncap, model
  said no) is reported as the headline failure metric, separately from ordinary disagreements.
- **`[VERIFY]` / placeholder discipline** is enforced in the system prompt, matching the rules in
  `../assessor-assistant/r1-master-design-prompt.md`.

## Roadmap (per the agreed build order)

- [x] 1. RAG ingest + retrieval over the corpus (with LAW / STATE-GUIDANCE / OFFICE-PRACTICE authority tagging)
- [x] 2. PTA backtest harness
- [x] 3. Shadow-mode grading/review workflow (`src/shadow.py`) — anti-anchoring grading (human
      determination recorded before the AI draft is revealed), seeded-case vigilance checks,
      report scored against the Phase 5 success criteria
- [x] 4. Staff-facing web UI (`src/webui.py`) — Ask + PTA triage tabs, DRAFT-for-human-review
      framing on every output, authority badges on citations, [VERIFY] highlighting, per-day
      JSONL audit logging, initials tracking. Start: `python3 src/webui.py` →
      http://127.0.0.1:8580 (bind `--host 0.0.0.0` for office LAN — **no auth in v1**,
      trusted network only, per the data policy)
- [x] 5. Escalation router (`src/escalate.py`, wired into the web UI) — three routes:
      **daily** / **escalate** (second-tier model on port 18081 if enabled in `config.json`,
      else the draft is returned flagged) / **human_only** (litigation, media, confidential
      data — no AI draft at all, short-circuits before any LLM call). Triggers: pattern rules
      (litigation/Tribunal, media, confidential financials/SSN, class-wide valuation, unusual
      properties, veteran exemption staleness), retrieval-quality checks (corpus doesn't cover
      the topic — thresholds in `config.json`, **re-tune against your real corpus**), and the
      daily model's own low-confidence/missing-facts signals. Routing decisions render as
      banners in the UI and are written to the audit log. Test routes from the CLI:
      `python3 src/escalate.py "your scenario"`

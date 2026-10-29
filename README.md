# MuniMonitor

Three fully-offline, local-LLM assistants for Michigan municipal departments —
assessing, building & inspections, and the city clerk's office. No API calls, no
cloud, no runtime internet. Standard-library Python plus a bundled CPU inference
engine; a department can run these on a single ordinary desktop.

Every output is a **draft for the responsible human official.** That is the
design constraint the whole system is built around, not a disclaimer bolted on.

> **Not an official source.** MuniMonitor is experimental software in development. It is not an
> official tool of any city, township, county or the State of Michigan, and it is not used in any
> official capacity. Its answers can be wrong, incomplete or out of date. Do not rely on it as your
> only source of information: always confirm with the office responsible (for example the local
> assessor, clerk or building department) before you act on anything it says.

```
MuniMonitor/
├── assessor-assistant-claude/       Assessing — PTA/uncapping triage, Q&A, shadow mode, web UI
├── building-inspections-claude/     Building  — code Q&A + construction-photo screening
├── city-clerk-claude/               Clerk     — FOIA triage, records/elections/OMA Q&A
└── models-shared/                   one model store serving all three
```

## Quick start

Requires Linux x86-64 (glibc ≥ 2.38), Python 3.10+, and 16 GB RAM. **Zero pip
installs** for the projects themselves.

```bash
git clone https://github.com/tim-odonnell/MuniMonitor.git && cd MuniMonitor

# 1. get the model (~11.9 GB, one download serves all three departments)
./fetch-models.sh            # pinned revision + SHA256-verified; needs only curl

# 2. start a department (builds its corpus index on first run)
cd assessor-assistant-claude && ./serve.sh
# wait for "listening" — ~3.5 min on first load

# 3. THE TRUST RITUAL — always the first thing on new hardware
python3 src/backtest.py                        # in a second terminal
cd ../city-clerk-claude && python3 src/foia_backtest.py

# 4. use it
python3 src/ask.py "when can a public body meet in closed session"
python3 src/foia_triage.py --file some-request.txt
```

Step 3 is not optional ceremony. Six demo cases carry deliberate traps that
catch a corrupted download, a wrong chat template, or silent truncation *before*
any real work depends on the machine.

## Recreating on another computer

Git carries everything except model weights (GitHub caps files at 100 MB).
`fetch-models.sh` downloads them from Hugging Face pinned to an exact commit and
checks each against its SHA256, so a fresh machine gets byte-identical files:

| Command | Gets | Size | Lands in |
|---|---|---|---|
| `./fetch-models.sh` | gpt-oss-20b UD-Q4_K_XL — validated default | 11.9 GB | `models-shared/` |
| `./fetch-models.sh qwen` | Qwen3.6-35B-A3B UD-Q4_K_XL — validated, 32 GB RAM | 22.9 GB | `models-shared/` |
| `./fetch-models.sh vision` | Qwen3-VL-8B + mmproj — building photo screening | 6.3 GB | `building-inspections-claude/models/vision/qwen3-vl-8b/` |
| `./fetch-models.sh vision-large` | Qwen3-VL-30B-A3B + mmproj | 18.8 GB | `building-inspections-claude/models/vision/qwen3-vl-30b-a3b/` |

Re-running resumes interrupted downloads and skips files that already verify.
For photo screening: `cd building-inspections-claude && ./serve.sh vision`
(add `30b` to pick the larger pair), then `python3 src/vision_check.py --calibrate`.
The vision models are bake-off candidates, **not validated** — see
`building-inspections-claude/models/vision/README.md`.

What never travels, by design: generated `corpus/index.json` (rebuilt by
`serve.sh`), `results/` and `logs/`, and **department records** — assessor
parcel/sales data, shadow-mode cases, and the building golden photo set
(`eval/photos/`), which each department supplies locally. On a distro older than
glibc 2.38 the bundled engine won't start; `*/engine/README.md` has the one-line
rebuild.

## Which model

**`gpt-oss-20b-UD-Q4_K_XL`** (11.9 GB, 16 GB RAM headless) is the validated
default. With 32 GB RAM, **`Qwen3.6-35B-A3B-UD-Q4_K_XL`** (22.9 GB) is the
validated step up — slower, but cites statutes at subsection precision.

Full guidance, exact filenames, SHA256s, and why downloading a *smaller* quant
saves you nothing: **[`models-shared/README.md`](models-shared/README.md)** and
each project's `models/README.md`. Hardware tiers with measured speeds are in
`*/SYSTEM-REQUIREMENTS.md`.

Model choices here are measured, not assumed. Both models above passed every
department gate on 2026-07-09; the method and the full rung ledger are in
[`assessor-assistant-claude/docs/model-descent-protocol.md`](assessor-assistant-claude/docs/model-descent-protocol.md).

## How it works

Each project is the same shape: a BM25 index over a corpus of **law and
procedure** (never the records themselves), an OpenAI-compatible LLM client
pointed at a local `llama-server`, and a department-specific triage surface on
top.

Two ideas do most of the safety work:

- **Authority tagging.** Every corpus document declares `LAW`,
  `STATE-GUIDANCE`, or `OFFICE-PRACTICE`, and the prompts enforce the hierarchy —
  office practice is never presented to staff as a legal requirement.
- **Zero-tolerance metrics.** Each department has one failure that can't be
  walked back, and it's measured directly rather than folded into an accuracy
  average: missed uncaps (assessing), missed exemption flags (clerk),
  hallucinated measurements from photos (building).

Retrieval also **pins** the statutes that must never be missed into context
directly — added after a live run confabulated a citation whose root cause was
retrieval simply never serving the exemptions section.

## Status, honestly

The text pipelines are built, tested, and validated against demo cases with
traps. What they do **not** yet have is validation against real departmental
golden sets — that gate is per-department and requires each office to supply
20+ real historical cases. The building department's **vision surface has no
validated model at all**; its bake-off has not been run. See each project's
`TODO.md` and `docs/`.

Nothing here should touch a live determination until the receiving department
has run its own gate.

## Documentation map

| Where | What |
|---|---|
| `*/START-HERE.md` | First-time setup, written for a non-technical Ubuntu user |
| `*/README.md` | What each assistant does |
| `*/SYSTEM-REQUIREMENTS.md` | Hardware tiers, measured speeds, RAM floors |
| `*/PORTABILITY.md` | Running on other machines; supplying your own GPU engine |
| `*/models/README.md` | Which model to download and why |
| `*/substitute-drill/` | Continuity packs — running the office when the expert is out |
| `assessor-assistant-claude/docs/benchmarks/` | Reproducible benchmark methodology and results |

## License

Project code and documentation: **Apache 2.0** — see [`LICENSE`](LICENSE) and
[`NOTICE`](NOTICE). The bundled `engine/llama-server` binary is llama.cpp, MIT;
models are downloaded separately under their own licenses (both validated models
are Apache 2.0). See [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

The corpus is public government material — Michigan statutes, State Tax
Commission and LARA guidance, retention schedules — with provenance headers.
**Note for the building project:** ICC model codes are copyrighted and adopted by
reference in Michigan; code text is not included, and `corpus/README.md` there
documents the licensing lanes.

---

Built with Claude Code, July 2026.

# Michigan Assessing Assistant — Multi-Stage Rebuild Prompts

**What this document is.** A complete, self-contained series of prompts to rebuild this
entire project from scratch on a separate machine, incorporating every bug fix, soft
spot, and design lesson learned during the original build. Nothing else from the
original project folders is required — this document is the seed.

**Execution model.**

| Role | Model | Settings |
|---|---|---|
| **BUILDER** | Qwen3.6-35B-A3B, full precision, full context (GPU) | temp 0.2 / top_p 0.95 for code stages (Parts A-E); temp 0.6 for prose stages (Part F) |
| **QC** | Qwen3.6-27B, full precision, full context (GPU) | temp 0.2 / top_p 0.95, all stages |
| **MANAGER** | Any strong instruct model on CPU + system RAM (slow is fine — it runs briefly, between stages) | temp 0.2, longest context available; see §0 |
| **OPERATOR** | You (the human) | Runs sessions, saves files, runs commands, commits |

Each stage is one fresh BUILDER session followed by one fresh QC session. Sessions do
not share memory — every stage prompt is self-contained given the pastes listed in its
ATTACH line. Thinking-mode `<think>` output is fine; only the final answer matters.

**The operator loop (identical every stage):**

1. Open a fresh BUILDER session. Paste, in order: **§1 SHARED CONTEXT**, then the
   files listed in the stage's **ATTACH** line, then the stage's **BUILDER PROMPT**.
2. Save every file the builder outputs to the exact paths given.
3. Run the stage's **OPERATOR CHECKS** commands. If a command fails, paste the error
   back into the same builder session and ask for a corrected file; repeat until
   commands pass.
4. Open a fresh QC session. Paste, in order: **§2 QC TEMPLATE**, then **§3 GLOBAL
   REGRESSION CHECKLIST**, then the stage's **QC ADDENDUM**, then every file the
   builder produced (and the ATTACH files, so QC sees dependencies).
5. Apply QC's corrected files. Re-run OPERATOR CHECKS and the test suite
   (`python3 -m unittest discover -s tests -v`). If QC found CRITICAL defects, run a
   second QC round on the corrected files. Maximum two QC rounds — if defects persist,
   restart the stage with a fresh builder session.
6. Run a **MANAGER checkpoint** (§0): paste the manager prompt, the latest BUILD
   LEDGER, and the stage's final files into the CPU-side manager session. Apply any
   BLOCKER corrections (via a fresh builder session) before committing. Mandatory at
   every part boundary (before starting Parts C, D, E, F and before Stage F4);
   recommended after every stage.
7. `git add -A && git commit -m "stage <ID>: <one line>"`. Save the updated LEDGER
   to `docs/build-ledger.md` in the same commit. Proceed to the next stage.

**Non-negotiable sequencing rule.** Parts A→B→C→D must run in order, and **Part D's
validation gate (Stage D3) must PASS before any Part E stage is run.** The original
build's biggest process error was building operational surfaces before validating that
a local model can actually do the core task. This document exists partly to prevent
repeating that. Part F may run any time after Part B.

---

## §0 DRIFT MANAGER PROMPT — the CPU-side build supervisor

**Why this role exists.** Every builder and QC session is an isolated, memoryless GPU
session; nothing connects the stages except what the operator pastes. Per-stage QC
sees one stage deeply but can never see *across* stages — and cross-stage drift
(a function renamed between sessions, a schema field that mutated, a canonical prompt
paraphrased "helpfully") is precisely the failure mode of multi-session builds. The
MANAGER is a slow-but-always-available model on CPU + system RAM that holds the single
source of truth about what has been built (the BUILD LEDGER) and checks each new
stage's output against it. It runs briefly between stages, so speed doesn't matter;
consistency does.

**When to run a manager checkpoint:** after each stage's QC completes and before the
git commit — mandatory at part boundaries (before Parts C, D, E, F and before Stage
F4), recommended every stage. If you run stages **in parallel on multiple GPUs**, run
an additional checkpoint BEFORE launching the parallel batch (to assign file
ownership) and one AFTER all sessions in the batch finish (to merge).

**What the operator pastes into each manager session, in order:**
1. The MANAGER PROMPT below.
2. The most recent BUILD LEDGER (from `docs/build-ledger.md`; on the very first
   checkpoint there is none — paste §1 SHARED CONTEXT instead, so the ledger is
   seeded from the specification, not from code).
3. The just-completed stage ID(s), the final files produced (post-QC), and the QC
   verdict table(s). For parallel batches: every session's outputs, labeled.

════════ MANAGER PROMPT — paste into every manager session ════════

ROLE: You are the BUILD MANAGER for a multi-stage, multi-session software build. GPU
worker sessions (a builder model and a QC model) produce one stage at a time from
written specifications; they have no memory of each other. You maintain the BUILD
LEDGER — the authoritative registry of everything built so far — and you detect and
arbitrate DRIFT between stages. You do not write code. You produce exact findings and
paste-ready correction instructions.

DEFINITIONS — the six drift classes you check, in priority order:
D1 INTERFACE DRIFT: a module's exported names, function signatures, return shapes,
   or import paths differ from how another module (or the ledger) uses them —
   e.g., stage-N code imports normalize_verdict but the committed module exports
   validate_verdict; a function gained a parameter that existing callers don't pass.
D2 SCHEMA DRIFT: any deviation from the canonical JSON shapes in the ledger (case
   files, model verdicts, config.json keys, report structures) — a renamed field, a
   type change, a new required key, a consumer reading a key no producer writes.
D3 CANONICAL-TEXT DRIFT: the protected constants (system prompt texts, authority
   level names, exception-category vocabulary) differ in ANY character from the
   ledger fingerprint. Paraphrase is drift. Improvement is drift. Only the operator
   may amend canonical text.
D4 CONVENTION DRIFT: violations of established conventions — file paths outside the
   layout, a module loading config differently, error-message style breaks, a CLI
   flag pattern inconsistent with siblings, duplicated logic that an existing shared
   function already provides (e.g., re-implementing retrieval instead of calling the
   shared context-assembly function).
D5 SPEC DRIFT: the artifact silently drops a numbered requirement from its stage
   spec, or adds unrequested features/dependencies (scope creep is drift even when
   the addition looks useful).
D6 REGRESSION REINTRODUCTION: any violation of the global regression checklist
   (G1-G12) appearing in NEW or CORRECTED files — QC already checked once, you are
   the second line; check G1 (no bool() on model values), G2 (power-of-attorney),
   G3 (synthetic exclusion), G4 (no blocking second-tier calls), G6 (instruction-
   file ingestion), G8 (pinned context) explicitly in every code artifact you see.

ARBITRATION RULES:
A1 The ledger (committed, earlier work) wins by default: the NEWER artifact adapts
   to match the OLDER committed interface, never the reverse.
A2 Exception: if the older committed artifact is itself defective, do NOT silently
   flip the rule — raise a LEDGER AMENDMENT item stating both options and their
   blast radius (which files each choice forces to change), and mark the checkpoint
   HOLD for an operator decision.
A3 You never rewrite artifacts. Your output is findings + instructions. The one
   document you author is the ledger itself.
A4 Unknowns are flagged, never guessed. If you cannot verify a signature because a
   file wasn't pasted, say so in OPEN-ITEMS — do not assume it matches.
A5 Economy: you run on CPU. Do not restate file contents, do not praise, do not
   summarize the project. Emit only the four output sections.

PARALLEL-BATCH COORDINATION (only when the operator says stages will run
concurrently): BEFORE the batch — assign each stage exclusive ownership of the files
its spec has it create/modify; shared files (config.json, README.md, TODO.md) get
exactly one owner per batch, and every other stage's instructions must say "do not
modify <shared file>; emit required changes as a NOTE for the manager". AFTER the
batch — merge in stage-ID order; apply drift checks pairwise; any two sessions that
both emitted the same file is automatically a BLOCKER for operator resolution.

BUILD LEDGER FORMAT (you emit the complete updated ledger every checkpoint; keep it
compact and deterministic — same ordering every time — so successive versions diff
cleanly):
  ## MODULES        — one line per exported symbol:
                      src/<file>: <fn>(<args>) -> <return> | config keys read | callers known
  ## SCHEMAS        — the canonical JSON shapes, field: type, one per line
  ## CANONICAL-TEXT — for each protected constant: name, char count, first 10 words,
                      last 10 words (this is the fingerprint; recompute exactly)
  ## CLI            — one line per command: <invocation> — <purpose>
  ## CONFIG-KEYS    — every key any module reads, with the reading module(s)
  ## STAGE-STATUS   — table: stage | committed? | manager-checked? | notes
  ## OPEN-ITEMS     — numbered, carried forward until resolved, each with the stage
                      that must resolve it

OUTPUT FORMAT — exactly four sections, in this order:
1. BUILD LEDGER — the complete updated ledger (fenced block).
2. DRIFT FINDINGS — numbered; each with: severity BLOCKER (build must not commit) /
   WARN (commit allowed, fix queued as OPEN-ITEM) / NOTE; drift class D1-D6; the
   exact evidence (quote the conflicting lines with file and function names); and
   the resolution per arbitration rules (which artifact changes, to what).
3. CORRECTION INSTRUCTIONS — for each BLOCKER: a short, paste-ready instruction
   block addressed to a fresh GPU builder session ("In file X, function Y currently
   …; change it to … so that it matches the committed interface Z; change nothing
   else."). Write "NONE" if no blockers.
4. GATE — one line: PROCEED (commit and continue) or HOLD (list exactly what
   unblocks, including any LEDGER AMENDMENT awaiting operator decision).

════════ END MANAGER PROMPT ════════

**Operator notes on the manager.**
- Save section 1 of every manager output over `docs/build-ledger.md` and commit it
  with the stage. The ledger file, not the manager's memory, is the continuity — any
  manager session can be cold-started from the prompt + the ledger.
- If manager findings and per-stage QC findings ever conflict, the stricter ruling
  wins; if they conflict on substance (one says an interface is X, the other Y),
  trust neither — open the committed file and check, then correct the ledger.
- The manager checks structure, interfaces, and drift. It does not re-review logic
  line-by-line (that is QC's job) and it cannot run code (that is yours: OPERATOR
  CHECKS and run_tests.sh remain mandatory regardless of a PROCEED gate).

---

## §1 SHARED CONTEXT — paste at the top of EVERY BUILDER session

```
PROJECT: "Assessor Assistant" — a fully-offline, local-LLM assistant for Michigan
municipal assessing departments (property tax assessment under MCL 211 and Michigan
State Tax Commission oversight). It drafts determinations and answers staff questions,
grounded in retrieved Michigan legal documents. It is designed to be adoptable by ANY
Michigan assessing office, not one specific office.

YOUR ROLE: You are the sole implementer, writing production code and documents from
precise specifications. You write complete, working artifacts — never sketches.

HARD RULES (violating any of these is a critical defect):
R1. Python 3.12 STANDARD LIBRARY ONLY. No pip installs, no third-party packages, in
    source code OR tests. Tests use unittest, not pytest.
R2. Fully offline at runtime: the only permitted network calls are to a local
    OpenAI-compatible LLM endpoint (http://127.0.0.1:<port>/v1) read from config.json.
R3. Every AI output in this system is a DRAFT for human review. No output reaches a
    resident, the assessment roll, or an official record without human review. This
    framing appears in every prompt, UI surface, and document you write.
R4. Authority hierarchy: every knowledge-base document carries an authority level —
    LAW (binding statute) > STATE-GUIDANCE (STC/Treasury guidance) > OFFICE-PRACTICE
    (one office's discretionary choices) > UNTAGGED (unknown, treat as unverified).
    OFFICE-PRACTICE must NEVER be presented as a legal requirement.
R5. [VERIFY] discipline: any legal assertion not grounded in a provided document is
    tagged [VERIFY]. Annual values use placeholders ([CURRENT_IRM], [DEADLINE]) —
    never hardcoded in reusable templates.
R6. Error weighting: a MISSED UNCAPPING EVENT (a transfer that should uncap taxable
    value, judged exempt) is the worst error class — zero-tolerance in all metrics.
    Systems bias toward over-flagging; a false alarm a human catches is cheap.
R7. Michigan domain terms used throughout: PTA = Property Transfer Affidavit (Form
    2766 / L-4260); uncapping = taxable value reset to SEV the year after a transfer
    of ownership (MCL 211.27a); PRE = Principal Residence Exemption; BoR = Board of
    Review; MTT = Michigan Tax Tribunal; STC = State Tax Commission; SEV = State
    Equalized Value; TV = Taxable Value; IRM = Inflation Rate Multiplier.

TARGET DIRECTORY LAYOUT (repository root = assessor-assistant/):
  README.md, TODO.md, config.json, run_tests.sh, .gitignore
  src/         ingest.py retrieve.py llm_client.py prompts.py backtest.py
               new_case.py shadow.py escalate.py webui.py
  tests/       test_ingest.py test_retrieve.py test_llm_client.py test_escalate.py
               test_backtest.py test_shadow.py
  corpus/      knowledge-base documents (.md/.txt) + index.json (generated)
  source-pdfs/ original downloaded PDFs (provenance)
  cases/       backtest/golden-set case JSON files
  shadow/      pending/ graded/   (shadow-mode records)
  results/     generated reports
  logs/        web UI audit logs (JSONL)
  docs/        operator documentation
  substitute-drill/  continuity-readiness docs + templates

CANONICAL JSON SHAPES (use exactly these everywhere):
Case file (cases/*.json):
  {"case_id": str, "task": "pta_triage", "synthetic": bool, "facts": str,
   "expected": {"uncapping": bool, "exception": str, "notes": str}}
  exception ∈ {"none","spouse","family_residential","trust","joint_tenancy","other"}
Model verdict (the triage LLM must return exactly this object):
  {"uncapping": bool, "exception_category": str, "confidence": "high"|"medium"|"low",
   "missing_facts": [str], "file_note": str}

CODING STANDARDS:
- Each src/ script: shebang, module docstring stating purpose and CLI usage, runnable
  as `python3 src/<name>.py`, importable by siblings via
  sys.path.insert(0, str(Path(__file__).resolve().parent)).
- Config loaded from <repo-root>/config.json; repo root = Path(__file__).resolve()
  .parent.parent from src/.
- Clear, actionable error messages (e.g. "Cannot reach LLM at <url> — is llama-server
  running?"). Catch specific exceptions, never bare except.
- No emojis in code identifiers; UI text may use ⚠ sparingly.

OUTPUT CONTRACT (every response you give):
- Emit each file COMPLETE, in a fenced code block, preceded by a line
  `FILE: <repo-relative-path>`.
- Never elide with "..." or "rest unchanged". Never leave TODO/FIXME placeholders.
- If a spec detail is ambiguous, choose the most conservative interpretation
  consistent with rules R1-R6 and note the choice in one line after the file.
```

---

## §2 QC TEMPLATE — paste at the top of EVERY QC session

```
ROLE: You are a meticulous senior code reviewer and Michigan property-tax domain
checker performing quality control on files produced by another model. You have the
stage specification, a global regression checklist, a stage-specific checklist, and
the files. Your job is to find real defects, not restyle working code.

PROCESS — do all four, in order:
1. SPEC COMPLIANCE: verify every numbered requirement in the stage prompt is
   implemented. List any requirement that is missing, partial, or contradicted.
2. GLOBAL REGRESSION CHECKLIST: verify each numbered item. These are real bugs that
   occurred in a previous build of this exact system — check them character by
   character, do not assume.
3. DEFECT HUNT: trace the code line by line for logic errors, unhandled edge cases
   (empty inputs, missing files, malformed JSON, network failure), security issues
   (path traversal, unbounded reads), and violations of the HARD RULES R1-R7 in the
   shared context (stdlib-only, offline, human-review framing, authority hierarchy,
   [VERIFY] discipline, missed-uncap weighting).
4. DOMAIN CHECK (documents/prompts only): every statement of Michigan law must either
   cite its source (MCL section / named STC document) or carry a [VERIFY] tag.
   Statements of office practice must be labeled as practice, never as law.

OUTPUT FORMAT — exactly three sections:
A. VERDICT TABLE: one row per checklist item and numbered requirement:
   itemID | PASS or FAIL | one-line evidence (quote the relevant line for FAILs).
B. DEFECTS: numbered list, each with severity CRITICAL (wrong results, crash, rule
   violation) / MAJOR (misbehavior in realistic edge case) / MINOR (cosmetic,
   clarity), the file, the function, and a precise description.
C. CORRECTED FILES: re-emit the COMPLETE corrected file for every file having any
   CRITICAL or MAJOR defect, in the same FILE:-header format. Change only what the
   defects require — no stylistic rewrites. If no CRITICAL/MAJOR defects exist,
   write "NO CORRECTIONS REQUIRED".
```

---

## §3 GLOBAL REGRESSION CHECKLIST — paste into EVERY QC session after §2

```
These defects existed in a previous build of this system. Verify each explicitly.

G1  STRING-BOOLEAN COERCION: nowhere in the codebase may a model-supplied value be
    converted with bool(). A verdict of "uncapping": "no" (string) must NOT evaluate
    as True. All model booleans must pass through parse_bool() (spec in Stage C1),
    and unparseable values must be counted as parse failures, never silently coerced.
G2  POWER-OF-ATTORNEY FALSE POSITIVE: the escalation router must NOT route the
    phrase "power of attorney" (a routine conveyance mechanism) to human_only.
    Test strings: "quit claim deed executed under power of attorney" → daily/escalate
    by other rules only; "our attorney advised us to appeal" → human_only;
    "we are being sued" → human_only.
G3  SYNTHETIC CONTAMINATION: cases with "synthetic": true must be EXCLUDED from all
    aggregate metrics (agreement rate, missed-uncap count, usability) in backtest and
    shadow reports. They may appear in per-case detail, clearly labeled.
G4  BLOCKING ESCALATION: no HTTP request handler may synchronously invoke the
    second-tier (slow) model. Escalation in the web UI is flag-and-return only.
G5  VERSION CONTROL: the repo must have .gitignore covering corpus/index.json,
    results/, logs/, shadow/, __pycache__/; operator commits every stage.
G6  INSTRUCTION-FILE INGESTION: ingest must exclude README.md and LOCALIZATION.md
    (case-insensitive) from the corpus index. A previous build ingested a README whose
    example table matched the authority regex and indexed it as LAW.
G7  NO bool() ON REQUEST INPUT: web/API handlers must validate and bound inputs
    (reject empty; cap request body at 1,000,000 bytes) and return structured JSON
    errors with correct HTTP codes (400 input, 503 LLM/corpus unavailable).
G8  PINNED CONTEXT: PTA triage prompts must ALWAYS include the pinned statutory
    documents (Stage C2 spec) regardless of retrieval ranking. A previous build
    relied on top-k retrieval alone; chunking split the MCL 211.27a(7) exception
    list across ~26 chunks and the governing exception could be missed.
G9  VOCABULARY MISMATCH: retrieval must apply the synonym/expansion map (Stage B1
    spec) so colloquial staff queries ("uncap", "quit claim", "BoR") match statutory
    vocabulary ("adjusted", "quitclaim", "board of review").
G10 AUTHORITY LEAKAGE: every prompt that includes retrieved references must label
    each reference with its authority level, and the system prompts must instruct
    the model to present OFFICE-PRACTICE material as office practice, never law.
G11 HUMAN-REVIEW FRAMING: every user-facing output surface (CLI reports, web UI,
    file notes) must carry draft-for-human-review framing.
G12 ZERO-TOLERANCE METRIC: backtest and shadow reports must compute and prominently
    display missed uncaps as a separate headline metric, distinct from general
    disagreement.
```

---
---

# PART A — FOUNDATION

## STAGE A1 — Repository scaffold, config, test harness

**ATTACH:** nothing (first stage).

════════ STAGE A1 — BUILDER PROMPT ════════

Create the repository foundation. Output these files, complete:

1. `.gitignore` — covering: `__pycache__/`, `*.pyc`, `corpus/index.json`, `results/`,
   `logs/`, `shadow/pending/`, `shadow/graded/`, `source-pdfs/*.pdf`, `.venv/`.
   Keep directory placeholders trackable: also output empty `.gitkeep` files for
   `corpus/`, `cases/`, `results/`, `logs/`, `shadow/pending/`, `shadow/graded/`,
   `source-pdfs/`, `docs/`, `tests/`, `src/` (emit each as `FILE:` with empty body).
2. `config.json` — exactly this structure (these are the canonical defaults):
   ```json
   {
     "llm": {"base_url": "http://127.0.0.1:18080/v1", "api_key": "none",
              "model": "local", "max_tokens": 1200, "timeout_seconds": 600},
     "retrieval": {"top_k": 6, "max_chunk_chars": 1600,
                    "pinned_char_budget": 60000,
                    "pinned_context": {"pta_triage": ["mcl-211-27a.md",
                                                       "pta-triage-sop.md"]}},
     "escalation": {"min_hits": 2, "min_top_score": 5.0,
                     "escalation_llm": {"enabled": false,
                       "base_url": "http://127.0.0.1:18081/v1", "api_key": "none",
                       "model": "design-tier", "max_tokens": 1600,
                       "timeout_seconds": 1800}},
     "webui": {"max_body_bytes": 1000000, "log_retention_days": 365},
     "paths": {"corpus_dir": "corpus", "index_file": "corpus/index.json",
                "cases_dir": "cases", "results_dir": "results"}
   }
   ```
3. `run_tests.sh` — executable one-liner: `python3 -m unittest discover -s tests -v`.
4. `README.md` — sections: project banner ("built for any Michigan assessing office");
   what it is (RAG-grounded drafting assistant, two-layer knowledge base:
   statewide LAW/STATE-GUIDANCE + per-office OFFICE-PRACTICE); the hard rules R2/R3/R6
   restated for humans; directory layout table; quickstart placeholder ("populated as
   stages complete"); and a "Build provenance" note that this repo is generated by a
   staged prompt process with QC review at each stage.
5. `TODO.md` — a running worklist seeded with: "Stage D3 validation gate not yet
   passed"; "governance conversation with municipal leadership before staff use";
   "re-tune escalation.min_top_score after real corpus is indexed"; "annual corpus
   refresh: IRM bulletin, tax calendar, procedural changes (STC publishes ~November)".

Requirements:
- A1-1 All JSON must be valid and parse with `json.load`.
- A1-2 README must state that no third-party Python packages are used anywhere.
- A1-3 README's directory table must match the SHARED CONTEXT layout exactly.

════════ END STAGE A1 ════════

**OPERATOR CHECKS (A1):**
```bash
mkdir -p assessor-assistant && cd assessor-assistant
# save builder files, then:
git init && python3 -c "import json; json.load(open('config.json')); print('config OK')"
chmod +x run_tests.sh
git add -A && git commit -m "stage A1: scaffold"
```

**QC ADDENDUM (A1):** Verify config.json matches the canonical structure key-for-key;
verify .gitignore covers every generated-artifact path named in G5.

---

# PART B — KNOWLEDGE BASE

## STAGE B1 — Ingestion and retrieval (`src/ingest.py`, `src/retrieve.py`, tests)

**ATTACH:** `config.json`.

════════ STAGE B1 — BUILDER PROMPT ════════

Build the corpus ingestion and BM25 retrieval layer. Stdlib only (R1).

FILE 1 — `src/ingest.py`:

B1-1  Reads every `.md` and `.txt` file under `corpus/` (recursive), plus `.pdf` IF
      the `pdftotext` binary exists on PATH (invoke via subprocess with
      `-layout`, 120s timeout; if extraction yields empty text, print a WARN naming
      the file as likely a scanned image needing OCR and skip it). If `pdftotext` is
      absent, print a WARN once and skip PDFs.
B1-2  EXCLUDES (case-insensitive filenames): `readme.md`, `localization.md`, and the
      index file itself. (Regression G6.)
B1-3  AUTHORITY DETECTION: scan only the first 1000 characters of each document for
      a line matching `^AUTHORITY:\s*(LAW|STATE-GUIDANCE|OFFICE-PRACTICE)\b`
      (case-insensitive, multiline). Absent → authority "UNTAGGED" and print a WARN
      naming the file. The authority string (uppercased) is stored on every chunk.
B1-4  CHUNKING: split text on blank-line paragraph boundaries; pack consecutive
      paragraphs into chunks of at most `retrieval.max_chunk_chars` characters
      (join with "\n\n"); a single paragraph longer than the limit is hard-split at
      the limit. Chunk id = `<relative-path>#<index>` (0-based). Each chunk dict:
      {"id", "source", "authority", "text", then computed "length" and "tf"}.
B1-5  TOKENIZATION (shared function `tokenize(text)`): lowercase, extract
      `[a-z0-9]+` runs, drop stopwords from this exact set:
      a an and are as at be but by for from has have if in into is it its of on or
      shall such that the their there this to was were what which who will with
B1-6  QUERY EXPANSION SUPPORT: define module-level `SYNONYMS`, a dict mapping a
      token to a list of additional tokens, containing at minimum:
      uncap→[uncapping, adjusted, adjustment]; uncapping→[adjusted, adjustment];
      uncaps→[uncapping, adjusted]; pta→[transfer, affidavit]; bor→[board, review];
      pre→[principal, residence, exemption]; quit→[quitclaim];
      mtt→[tribunal]; stc→[commission]; sev→[equalized]; tv→[taxable];
      irm→[inflation, multiplier]; poverty→[hardship].
      (Used by retrieve.py; defined here so tests can import one source of truth.)
B1-7  BM25 PRECOMPUTATION: per-chunk term frequencies; document frequencies;
      idf(t) = ln(1 + (N − df + 0.5)/(df + 0.5)); average chunk token length.
      Write `corpus/index.json`: {"chunks": [...], "idf": {...}, "avg_len": float,
      "n_chunks": int}.
B1-8  Prints one line per ingested file: `ingested <name> [<AUTHORITY>]: <n> chunks`,
      and a final summary with chunk count and index size. Exit code 1 if no
      documents were found.

FILE 2 — `src/retrieve.py`:

B1-9  Class `Retriever`: loads index.json (raise FileNotFoundError with the message
      "run `python3 src/ingest.py` first" if missing). Method
      `search(query, k=None) -> list[dict]` returning up to k (default
      `retrieval.top_k`) hits sorted by descending BM25 score (k1=1.5, b=0.75),
      each hit: {"id","source","authority","score" (rounded 3),"text"}.
      Zero-score chunks are never returned.
B1-10 QUERY EXPANSION: before scoring, expand the tokenized query: for each token
      present in SYNONYMS, append its expansion tokens (deduplicate; original tokens
      always retained). (Regression G9.)
B1-11 CLI: `python3 src/retrieve.py "query" [--k N]` printing each hit as
      `=== <id>  [<AUTHORITY>]  (score <s>) ===` followed by the first 600 chars.

FILE 3 — `tests/test_ingest.py` and FILE 4 — `tests/test_retrieve.py` (unittest):

B1-12 Test chunking: paragraphs pack under the limit; an oversize paragraph is
      hard-split; chunk ids are sequential.
B1-13 Test authority detection: tagged docs get their tag; untagged → UNTAGGED; a
      document whose only "AUTHORITY: LAW" text appears AFTER the first 1000
      characters → UNTAGGED.
B1-14 Test exclusions: files named README.md and LOCALIZATION.md are not ingested
      (create a temp corpus dir with tempfile; run ingest's functions directly or
      via subprocess with a patched config; either is acceptable but must not touch
      the real corpus/).
B1-15 Test BM25: with a 3-document toy corpus, a query matching document 2's
      distinctive term ranks it first; idf of a term present in all documents is
      lower than a term in one.
B1-16 Test expansion: query "does uncap apply" retrieves a chunk containing only
      "adjusted" vocabulary (proving G9).

════════ END STAGE B1 ════════

**OPERATOR CHECKS (B1):**
```bash
printf 'AUTHORITY: LAW\n\ntest statute text about taxable value adjusted under this section\n' > corpus/smoke.md
python3 src/ingest.py && python3 src/retrieve.py "uncap taxable value"
rm corpus/smoke.md && ./run_tests.sh
```
Expect: smoke.md ingests as LAW; the "uncap" query hits it via expansion; all tests pass.

**QC ADDENDUM (B1):** Focus on G6, G9; verify the idf formula and k1/b constants
exactly; verify search() never divides by zero on an empty index or zero-length chunk;
verify tests do not depend on the real corpus/ contents.

---

## STAGE B2 — Corpus acquisition tooling and extraction QA

**ATTACH:** `config.json`, `src/ingest.py`.

════════ STAGE B2 — BUILDER PROMPT ════════

Build the corpus acquisition tooling and write the corpus operator guide.

FILE 1 — `src/fetch_corpus.py` (network use is permitted in this OPERATOR-run tool
only — runtime rule R2 applies to the assistant, not to corpus acquisition):

B2-1  Fetches Michigan statute sections from
      `https://www.legislature.mi.gov/Laws/MCL?objectName=<obj>` using
      urllib.request with a desktop browser User-Agent string and 45s timeout.
      Section list (dict obj→description), at minimum:
      mcl-211-27 (true cash value), mcl-211-27a (taxable value/capped value/transfer
      of ownership + exceptions), mcl-211-27b (failure to notify; penalties),
      mcl-211-7cc (PRE), mcl-211-7dd (PRE definitions), mcl-211-7u (poverty
      exemption), mcl-211-29 / mcl-211-30 / mcl-211-33 (Boards of Review),
      mcl-211-34c (classification), mcl-211-19 (personal property statements),
      mcl-211-9o (small business PP exemption).
B2-2  Extracts visible text from the page's `sectionWrapper` div using
      html.parser.HTMLParser (track div nesting depth; skip script/style; emit
      newlines at block tags). Collapse 3+ newlines to 2; collapse runs of
      spaces/tabs.
B2-3  SANITY GATE per section: extracted text ≥ 400 chars AND contains the bare
      section number (e.g. "211") in the first 3000 chars; otherwise print
      `WARN <obj>: extraction looks wrong — fetch manually` and write nothing.
B2-4  Writes `corpus/<obj>.md` with EXACTLY this header shape:
      line 1 `AUTHORITY: LAW`, blank line, `# MCL <n.n> — <description>`, blank
      line, a blockquote noting: source URL, retrieval date (date.today), "verbatim
      statute text", and "VERIFY against the official source before relying on it
      in any determination", blank line, then the text.
B2-5  `--only <obj>` flag to fetch a single section.

FILE 2 — `src/clean_extraction.py` — extraction QA for pdftotext output:

B2-6  Reads a corpus .md file, detects lines repeated ≥4 times across the document
      that are shorter than 80 chars (page headers/footers), and removes all
      occurrences after the first. Repairs hyphenation: joins a line ending in
      `<letter>-` with the next line when the next line starts lowercase.
      Preserves the AUTHORITY header block untouched.
B2-7  Default is DRY RUN printing a summary (N header lines removed, N hyphen
      joins) and the removed lines; `--write` applies in place. Never modifies a
      file lacking an AUTHORITY line (prints a warning instead).

FILE 3 — `corpus/README.md` — the operator's gathering guide (remember: ingest
excludes it). Contents:

B2-8  The AUTHORITY tag requirement (first line of every document; the three levels
      with the exact phrases the assistant will use for each: "the statute
      requires…" / "STC guidance provides…" / "this office's practice has been…").
B2-9  A gathering checklist with the statute list from B2-1, plus these STC/Treasury
      documents with their download URLs and target filenames (pdftotext each into
      corpus/ with an `AUTHORITY: STATE-GUIDANCE` header carrying the same
      provenance-blockquote shape as B2-4; keep original PDFs in source-pdfs/):
      - STC Transfer of Ownership Guidelines →
        https://www.michigan.gov/-/media/Project/Websites/treasury/MISC_9/TransferOwnershipGuidelines.pdf
      - Treasury PRE Guidelines →
        https://www.michigan.gov/-/media/Project/Websites/taxes/PRE-Documents/PRE_Guidelines.pdf
      - STC Board of Review Q&A → search michigan.gov "State Tax Commission Board of
        Review Questions and Answers"
      - Current-year IRM bulletin, Property Tax & Equalization Calendar bulletin, and
        Procedural Changes bulletin → michigan.gov/treasury STC bulletins page
        (published ~November for the following year; re-fetch ANNUALLY)
      - Forms with instructions: 2766/L-4260 (PTA), 2368 (PRE affidavit), 2602 (PRE
        rescission), 5076 (small business exemption)
      - STC Assessor's Manual Volume III (assessment administration). NOTE: Volumes
        I and II are cost SCHEDULES — numeric tables that extract poorly and pollute
        retrieval; do NOT ingest them, use the PDFs directly for cost work.
B2-10 An extraction-QA section: after every pdftotext conversion, run
      clean_extraction.py, then a human skims each document (especially tables) and
      spot-checks 3 passages against the source PDF before trusting it.
B2-11 A staleness section: annual items and the instruction to date-stamp filenames.

════════ END STAGE B2 ════════

**OPERATOR CHECKS (B2):** On the build machine (network required for this step only):
```bash
python3 src/fetch_corpus.py            # 12 statute files into corpus/
# download the STC PDFs per corpus/README.md into source-pdfs/, pdftotext them per B2-9,
python3 src/clean_extraction.py corpus/stc-transfer-of-ownership-guidelines.md   # review, then --write
python3 src/ingest.py                  # expect several hundred chunks
python3 src/retrieve.py "does a transfer between spouses uncap taxable value"
python3 src/retrieve.py "what is the inflation rate multiplier"
```
Expect: the spousal query's top hits come from the transfer guidelines / mcl-211-27a;
the IRM query's top hits from the IRM bulletin. If not, STOP and debug retrieval
before proceeding. Skim every fetched statute against legislature.mi.gov.

**QC ADDENDUM (B2):** Verify the sanity gate (B2-3) cannot write an empty/garbage
file; verify clean_extraction.py can never delete statute body text that appears
fewer than 4 times; verify README.md documents the Vol I/II exclusion rationale.

---

# PART C — REASONING CORE

## STAGE C1 — LLM client and robust output parsing

**ATTACH:** `config.json`.

════════ STAGE C1 — BUILDER PROMPT ════════

Build the model-agnostic LLM client. Any OpenAI-compatible local server (llama.cpp
llama-server, ik_llama.cpp, ktransformers) must work unchanged.

FILE 1 — `src/llm_client.py`:

C1-1  `class LLMError(RuntimeError)`.
C1-2  `chat(messages: list[dict], cfg: dict | None = None) -> str` — POST
      `<base_url>/chat/completions` via urllib.request with JSON body
      {"model", "messages", "max_tokens"} from cfg["llm"] (cfg defaults to loading
      config.json). Headers: Content-Type and `Authorization: Bearer <api_key>`.
      On URLError raise LLMError("Cannot reach LLM at <url> — is llama-server
      running? (<err>)"). On unexpected response shape raise LLMError quoting the
      first 500 chars. Return choices[0].message.content.
C1-3  `extract_json(text: str) -> dict` — pull the first parseable top-level JSON
      object from model output: first strip all `<think>…</think>` blocks
      (re.DOTALL — reasoning models emit JSON inside thinking that must not be
      grabbed); then scan character-by-character tracking brace depth; on each
      balanced candidate attempt json.loads; on failure keep scanning. Raise
      ValueError with a 300-char excerpt if nothing parses. Must tolerate markdown
      fences and prose around the object.
C1-4  `parse_bool(value) -> bool` — the ONLY permitted conversion for model-supplied
      booleans anywhere in this codebase (regression G1):
      - bool → itself;  int 1/0 → True/False
      - str (strip, casefold): "true","yes","y","1" → True;
        "false","no","n","0" → False
      - anything else (None, other strings, lists…) → raise ValueError.
C1-5  `normalize_verdict(v: dict) -> dict` — validate a raw verdict against the
      canonical verdict shape: uncapping via parse_bool; exception_category
      lowercased and must be in the canonical set else "other" with a preserved
      original under key "exception_raw"; confidence lowercased and must be in
      {high, medium, low} else "low"; missing_facts coerced to list of str;
      file_note coerced to str. Raise ValueError (→ parse failure upstream) only if
      uncapping is unparseable; degrade the rest gracefully as described.
C1-6  `__main__` smoke: send argv[1] (default "Reply with exactly: OK") and print
      the reply.

FILE 2 — `tests/test_llm_client.py`:

C1-7  extract_json: plain object; object in ```json fence; object preceded by
      <think> block CONTAINING a decoy JSON object (must return the post-think
      object, not the decoy); no-JSON input raises ValueError.
C1-8  parse_bool: full truth table from C1-4 including "No", " FALSE ", 0, and the
      ValueError cases ("maybe", None, []).
C1-9  normalize_verdict: verdict with "uncapping": "no" normalizes to False (the
      G1 regression test — this exact case corrupted metrics in a previous build);
      unknown exception_category → "other" + exception_raw; garbage confidence →
      "low"; missing uncapping key → ValueError.

════════ END STAGE C1 ════════

**OPERATOR CHECKS (C1):** `./run_tests.sh` (all pass; no network needed — chat() is
not exercised by tests).

**QC ADDENDUM (C1):** G1 is the focus: grep the file for `bool(` and confirm the only
boolean conversions of model data flow through parse_bool. Verify extract_json cannot
return an object found inside a think block.

---

## STAGE C2 — System prompts and pinned-context assembly

**ATTACH:** `config.json`, `src/ingest.py`, `src/retrieve.py`.

════════ STAGE C2 — BUILDER PROMPT ════════

Build `src/prompts.py` — the prompt layer. This stage contains canonical prompt text:
reproduce it EXACTLY as given (it encodes legal-safety behavior), adding nothing.

FILE 1 — `src/prompts.py`:

C2-1  Constant `PTA_TRIAGE_SYSTEM` — exactly:

You are a triage assistant for a Michigan city assessing department. Your job is to
analyze a property transfer fact pattern and produce a PRELIMINARY determination of
whether the transfer is a "transfer of ownership" that uncaps taxable value under
Michigan's Proposal A framework. A human assessor reviews every determination you
produce; you are drafting, not deciding.

RULES — follow all of them:
1. Base your reasoning ONLY on the REFERENCE DOCUMENTS provided in the user message
   and the stated FACTS. Do not rely on memorized law. If the provided documents do
   not cover the situation, say so and set "confidence" to "low".
2. Cite which reference document supports each key point, by its section label.
3. Tag any legal assertion you cannot ground in the provided documents with [VERIFY].
   Never state a specific statutory deadline, citation, or dollar threshold from
   memory as fact.
4. Bias toward over-flagging: if the facts plausibly support uncapping and you are
   not certain an exception applies, lean toward "uncapping": true and flag for
   review. A missed uncapping event is the worst error you can make; a false alarm
   a human catches is cheap.
5. If facts essential to the determination are missing (e.g., relationship between
   parties, property use, trust terms), list them in "missing_facts" and set
   "confidence" accordingly.
6. Reference documents carry an AUTHORITY level — respect the hierarchy:
   - LAW: binding statute. Controls over everything else.
   - STATE-GUIDANCE: State Tax Commission guidance. Follow unless LAW contradicts it.
   - OFFICE-PRACTICE: this office's discretionary practice. Cite it as "this office's
     practice", NEVER as a legal requirement — a different assessor could lawfully
     choose otherwise. If OFFICE-PRACTICE conflicts with LAW or STATE-GUIDANCE,
     flag the conflict for the assessor.
   - UNTAGGED: authority unknown. Treat as unverified; tag reliance on it [VERIFY].
7. Respond with ONLY a JSON object, no other text, in exactly this shape:

{
  "uncapping": true | false,
  "exception_category": "<none | spouse | family_residential | trust | joint_tenancy | other>",
  "confidence": "high" | "medium" | "low",
  "missing_facts": ["..."],
  "file_note": "<one paragraph suitable for the property record file, professional tone, citing the reference sections relied on, with [VERIFY] tags where required>"
}

C2-2  Constant `GENERAL_QA_SYSTEM` — exactly:

You are a reference assistant for a Michigan city assessing department. Staff ask you
questions about assessing procedure, property transfers, exemptions, and department
practice. A human verifies your answers before acting on them.

RULES:
1. Answer ONLY from the REFERENCE DOCUMENTS provided in the user message. If they do
   not answer the question, say exactly what is missing — do not fill gaps from
   memorized law.
2. Cite the reference section label for each substantive point.
3. Tag any assertion you cannot ground in the provided documents with [VERIFY]. Never
   state a specific statutory deadline, citation, or dollar amount from memory.
4. Use placeholders like [DEADLINE] or [CURRENT_IRM] instead of inventing annual values.
5. Plain, professional language. If the question involves a determination with real
   stakes (uncapping, exemption denial, valuation), remind the user it requires
   assessor review.
6. Reference documents carry an AUTHORITY level — keep the categories distinct in
   your answer:
   - LAW: binding statute — "the statute requires…"
   - STATE-GUIDANCE: STC guidance — "STC guidance provides…"
   - OFFICE-PRACTICE: this office's discretionary practice — "this office's practice
     has been…" NEVER present it as a legal requirement; a different assessor could
     lawfully choose otherwise. Flag any conflict with LAW/STATE-GUIDANCE.
   - UNTAGGED: authority unknown — treat as unverified, tag [VERIFY].
   When an answer mixes levels, say which part comes from which (e.g., "the statute
   requires X [LAW]; how this office implements it is Y [OFFICE-PRACTICE]").

C2-3  PINNED CONTEXT (regression G8): function
      `pinned_chunks(task: str, retriever, cfg) -> list[dict]` — for the given task
      key, look up `retrieval.pinned_context[task]` (list of corpus source
      filenames); return ALL index chunks whose source matches those filenames, in
      document order, as hit-shaped dicts (score 0.0, marked "pinned": true).
      Enforce `retrieval.pinned_char_budget` on total pinned text: if exceeded,
      keep whole documents in list order until the budget would be crossed and
      print a one-line warning naming what was dropped.
C2-4  `assemble_context(task, query_text, retriever, cfg) -> list[dict]` — pinned
      chunks first, then retrieval hits for query_text EXCLUDING any chunk whose
      source is already pinned, up to top_k. This is the single context-assembly
      entry point; backtest, shadow, and webui must all use it (no separate
      retrieval logic).
C2-5  `_format_refs(chunks)` → each as
      `--- REFERENCE [<id>] (AUTHORITY: <authority><, PINNED if pinned>) ---\n<text>`.
      `build_user_prompt(facts, chunks)` → "REFERENCE DOCUMENTS:\n\n<refs>\n\nFACTS
      OF THE TRANSFER:\n\n<facts>\n\nProduce the JSON determination now."
      `build_qa_prompt(question, chunks)` → same shape with "STAFF QUESTION:".

FILE 2 — `tests/test_prompts.py` (extend test files list; unittest):

C2-6  With a temp index containing chunks from "mcl-211-27a.md" and two other
      sources: pinned_chunks returns all and only the 27a chunks in order;
      assemble_context puts pinned first and never duplicates a pinned source in
      the retrieved tail; the char budget drops trailing documents, not partial ones.
C2-7  String tests: both system prompts contain the exact phrases "missed uncapping
      event is the worst error", "NEVER present it as a legal requirement" /
      "NEVER as a legal requirement", and "[VERIFY]"; _format_refs marks pinned
      chunks.

════════ END STAGE C2 ════════

**OPERATOR CHECKS (C2):** `./run_tests.sh`. Then with the real corpus indexed:
`python3 - <<'EOF'` … import prompts/retrieve, call
`assemble_context("pta_triage", "quit claim mother to son", Retriever(), load_config())`,
print the ids — expect every mcl-211-27a chunk plus the SOP (once Stage F1 adds it;
before F1 a warning about the missing SOP file is acceptable) before any retrieved hit.

**QC ADDENDUM (C2):** Diff both prompt constants character-for-character against the
stage spec (they are canonical; any drift is CRITICAL). Verify G8: no code path lets a
triage prompt be built without pinned 27a chunks when the file exists.

---

# PART D — VALIDATION GATE

## STAGE D1 — Case tooling and golden-set authoring

**ATTACH:** `config.json`, `src/ingest.py` (for ROOT/config helpers).

════════ STAGE D1 — BUILDER PROMPT ════════

FILE 1 — `src/new_case.py` — guided creation of case files in the canonical case
shape (SHARED CONTEXT). Requirements:

D1-1  Interactive mode (no args): prompts for case id, multiline facts (end on empty
      line), uncapping yes/no, exception (validated against the canonical set,
      default "none"), notes. Prints an anonymization reminder first: no real owner
      names, no exact addresses, no confidential financials.
D1-2  Non-interactive: `--id --facts --uncap yes|no [--exception X] [--notes S]`.
D1-3  Writes cases/<id>.json with "synthetic": false; refuses to overwrite.
D1-4  `--synthetic` flag marks a case synthetic (for demos/vigilance seeds).

FILE 2 — three DEMO cases (synthetic: true), ids DEMO-PTA-001/2/3:
D1-5  001: warranty deed, arm's-length sale between unrelated parties through a
      realtor, price stated, PTA filed on time → expected uncapping true,
      exception none.
D1-6  002: quit claim creating a tenancy by the entireties between spouses, no
      consideration, same occupancy → expected uncapping false, exception spouse.
D1-7  003 (the trap): quit claim from mother to adult son, $1, estate planning,
      residential — BUT the son states he will convert the home to a rental. The
      family-residential exception is commonly conditioned on the use NOT changing,
      so expected uncapping true, exception none; notes must explain that a model
      which reflexively applies the family exception without catching the use-change
      fact fails this case.

FILE 3 — `docs/golden-set-guide.md` — operator instructions:
D1-8  Build ≥10 (target 30) REAL anonymized cases from the office's past PTA
      determinations before running the gate; include at least 3 hard ones (trusts,
      probate, entity transfers); for each, the correct outcome and a one-line why;
      the demo cases never count toward the real-case minimum (G3).

════════ END STAGE D1 ════════

**OPERATOR CHECKS (D1):**
```bash
python3 src/new_case.py --id TEST-X --uncap yes --facts "t" --notes "t"
python3 -c "import json;c=json.load(open('cases/TEST-X.json'));assert c['synthetic'] is False"
rm cases/TEST-X.json
```
Then author your real golden set per docs/golden-set-guide.md — this is human work
the build cannot do.

**QC ADDENDUM (D1):** Verify DEMO-PTA-003's expected answer is uncapping TRUE (the
trap must trap); verify all three demos carry synthetic: true.

---

## STAGE D2 — Backtest harness

**ATTACH:** `config.json`, `src/ingest.py`, `src/retrieve.py`, `src/llm_client.py`,
`src/prompts.py`.

════════ STAGE D2 — BUILDER PROMPT ════════

FILE 1 — `src/backtest.py` — the measuring stick. For every cases/*.json with task
"pta_triage": assemble context via `prompts.assemble_context("pta_triage", facts,…)`
(never raw retrieval — G8), call the LLM with PTA_TRIAGE_SYSTEM + build_user_prompt,
parse via extract_json + normalize_verdict, score, report.

D2-1  CLI: `--dry-run` (retrieval + prompt assembly only, prints per-case retrieved
      ids, no LLM); `--case <id>` single case.
D2-2  Scoring per case (after normalize_verdict — G1): agree_uncapping;
      missed_uncap (expected True, model False); false_uncap (expected False, model
      True); agree_exception (case-insensitive string equality). A ValueError from
      normalize_verdict → the case is recorded as a parse failure, never scored.
D2-3  AGGREGATES EXCLUDE SYNTHETIC CASES (G3). Compute over real cases only:
      agreement count/rate, missed-uncap list (headline, zero-tolerance — G12),
      false-uncap list, exception agreement, parse-failure list. Synthetic cases
      appear in per-case detail labeled "(synthetic demo case)" and in a separate
      one-line synthetic tally.
D2-4  Outputs: results/backtest-<ts>.json (all records) and
      results/backtest-<ts>-report.md with: counts (real vs synthetic), the
      aggregate lines, "MISSED UNCAPS (zero-tolerance): N" prominently, per-case
      detail (expected vs model vs confidence vs file note), total wall time. Print
      a ⚠ line if any missed uncap. Per-case console line as it runs:
      `<id>: agree|DISAGREE|MISSED-UNCAP ⚠|PARSE-FAIL (<s>s)`.
D2-5  On LLMError: print the message and exit 2 (server down is fatal, not a
      per-case skip).

FILE 2 — `tests/test_backtest.py`:
D2-6  Unit-test the scoring function directly: the four score fields across the
      truth table, including expected True + model verdict {"uncapping": "no"} → 
      after normalize_verdict this is a missed_uncap (G1 regression).
D2-7  Aggregation test with a mixed list of scored records (2 real, 1 synthetic):
      synthetic excluded from rate; missed-uncap list correct (G3, G12). Structure
      backtest.py so scoring and aggregation are importable pure functions.

════════ END STAGE D2 ════════

**OPERATOR CHECKS (D2):** `python3 src/backtest.py --dry-run` (3 demo cases retrieve
pinned 27a chunks first) and `./run_tests.sh`.

**QC ADDENDUM (D2):** G1, G3, G8, G12 all bite in this file — verify each against the
code, not the docstring. Verify a parse failure cannot enter the agreement denominator.

---

## STAGE D3 — THE VALIDATION GATE (operator runbook; no builder session)

This stage is executed by the OPERATOR. Do not run any Part E stage until it passes.

1. Start a llama-server with a candidate daily model (14B-32B class; e.g. Qwen3-14B
   at Q8 or Qwen3-32B at Q4_K_M on a 24GB GPU; adjust to build-machine hardware) on
   port 18080 with `--parallel 2` and ≥16K context.
2. `python3 src/llm_client.py "Reply with exactly: OK"` → must print OK.
3. `python3 src/backtest.py --case DEMO-PTA-003` → the trap case. Read the file
   note: did the model catch the use-change fact?
4. Run the full backtest against your REAL golden set (≥10 cases).
5. **GATE CRITERIA (all must hold on real cases):**
   - Missed uncaps = 0
   - Agreement ≥ 90% (pilot target is ≥95% on a 100-case set later)
   - Parse failures ≤ 10%
6. If the gate FAILS: diagnose in this order — (a) retrieval: run --dry-run, confirm
   the pinned 27a chunks and the on-point guideline sections are in context;
   (b) parsing: inspect raw outputs in results/*.json for format drift, consider a
   stricter reminder line appended to the user prompt; (c) model: try the other
   candidate model/quant; (d) prompt: tune wording ONLY with a fresh builder session
   given the failing transcripts. Re-run. Two full remediation cycles without
   passing = stop and reassess model choice with a larger model before building
   anything else.
7. Record the passing numbers in TODO.md ("Stage D3 gate PASSED <date>: <numbers>")
   and commit.

---

# PART E — OPERATIONAL SURFACES (only after D3 passes)

## STAGE E1 — Escalation router

**ATTACH:** `config.json`, `src/ingest.py`, `src/retrieve.py`.

════════ STAGE E1 — BUILDER PROMPT ════════

FILE 1 — `src/escalate.py` — routes each request: "daily" (fast model handles),
"escalate" (second-tier model / flagged for assessor), "human_only" (no AI draft at
all). Philosophy: the person relying on the assistant may be the person least able to
catch its errors; when in doubt route UP; a correct escalation is a success.

E1-1  HUMAN_ONLY_PATTERNS — list of (compiled-regex, reason). Required entries:
      - Litigation: matches "attorney"/"lawyer"/"legal counsel"/"lawsuit"/
        "litigation"/"subpoena"/"court order"/"sued"/"suing"/"threatening legal
        action" — BUT must NOT match "power of attorney" (G2). Implement the
        attorney term as r"(?<!power of )\battorney\b" (fixed-width lookbehind)
        alongside the other terms.
      - Tribunal: "tax tribunal", "MTT petition", "small claims division".
      - Media: "reporter", "newspaper", "press", "media inquiry".
      - Confidential identifiers: "ssn", "social security number".
      - Confidential financials (poverty-exemption class): "household income",
        "bank statement", "pay stub", "financial statement", "asset test".
E1-2  ESCALATE_PATTERNS — required entries: class-wide valuation ("equalization",
      "economic condition factor", "ecf", "land value table/study", "sales study");
      jurisdiction-wide ("all parcels", "every parcel", "neighborhood-wide",
      "class-wide", "jurisdiction-wide"); contested doctrine ("dark store",
      "functional obsolescence", "economic obsolescence", "going concern");
      changed-process staleness ("disabled veteran", "veteran's exemption");
      unusual property ("easement", "cell tower", "billboard", "wind turbine",
      "solar farm/array", "golf course", "marina", "landfill", "gravel pit",
      "contaminated", "brownfield"). All case-insensitive, word-boundaried.
E1-3  `route_pre(text, hits, cfg)` → human_only if any human-only pattern matches
      (reasons = matched reasons, stop there); else collect escalate-pattern reasons
      plus retrieval-quality reasons: len(hits) < escalation.min_hits ("corpus
      barely covers this topic") or hits[0].score < escalation.min_top_score ("weak
      retrieval match"); route "escalate" if any reason else "daily".
E1-4  `route_post(verdict)` → escalate if confidence == "low", or if missing_facts
      is non-empty and confidence != "high" (include the first 3 missing facts in
      the reason).
E1-5  `merge(*decisions)` → most-cautious route wins (daily < escalate <
      human_only); reasons concatenated.
E1-6  `escalation_llm_config(cfg)` → {"llm": <escalation.escalation_llm>} if
      enabled else None.
E1-7  CLI: `python3 src/escalate.py "<text>"` → runs retrieval, prints JSON
      {input(120ch), top_hit, top_score, route, reasons}.
E1-8  A comment noting min_top_score must be re-tuned whenever the corpus changes
      materially (BM25 scores scale with corpus size).

FILE 2 — `tests/test_escalate.py`:
E1-9  G2 regression trio exactly as in the global checklist. Plus: "adjust the ECF
      for the whole neighborhood" → escalate; "cell tower easement" → escalate;
      plain arm's-length facts with strong hits → daily; empty hits → escalate with
      the coverage reason; merge() ordering table.

════════ END STAGE E1 ════════

**OPERATOR CHECKS (E1):** `./run_tests.sh`;
`python3 src/escalate.py "quit claim executed under power of attorney"` → route is
NOT human_only.

**QC ADDENDUM (E1):** G2 is the focus. Also verify every regex compiles and is
case-insensitive; verify route_pre short-circuits on human_only (no retrieval-quality
noise appended).

---

## STAGE E2 — Shadow-mode grading workflow

**ATTACH:** `config.json`, `src/ingest.py`, `src/retrieve.py`, `src/llm_client.py`,
`src/prompts.py`.

════════ STAGE E2 — BUILDER PROMPT ════════

FILE 1 — `src/shadow.py` — subcommands new / run / seed / grade / status / report.
Records live in shadow/pending/ then shadow/graded/ as JSON, ids
SHADOW-YYYYMMDD-NNN.

E2-1  ANTI-ANCHORING (core design): `new` runs the LLM (via assemble_context +
      normalize_verdict) and STORES the draft without displaying it, printing "Do
      NOT view the AI draft before making your own determination." `grade <id>`
      asks for the human's uncapping call and exception FIRST, and only then
      reveals the stored draft.
E2-2  `new --no-llm` stores facts only; `run <id>` executes/retries the LLM later
      (server may be down at intake).
E2-3  `seed <case_file> [--no-llm]` plants a case (canonical case shape) into the
      queue with its expected answer hidden; after grading, the truth is revealed
      and BOTH the human and the AI are scored against it (evaluator-vigilance
      check); a human miss prints a review-together warning.
E2-4  Grading captures: agreement fields (same four as backtest, via parse_bool-
      normalized verdicts — G1), file-note usability (1 use-as-is / 2 minor edits /
      3 major edits / 4 unusable), minutes saved (int), free notes. AI-missing
      records grade as {"ai_missing": true} and are excluded from scored
      aggregates.
E2-5  `report`: over graded records — scored counts; agreement rate; missed-uncap
      list (headline, G12); false uncaps; usability rate (as-is+minor); total
      minutes saved; seeded-case tally (evaluator correct N/M, AI correct N/M);
      weekly agreement trend when >1 ISO week present; disagreement/notes list.
      Success-criteria lines printed PASS/FAIL: agreement ≥95%, missed uncaps = 0,
      usable ≥70%. Seeded cases are excluded from the success-criteria aggregates
      (G3) but reported in their own section. Writes results/shadow-report-<ts>.md.
E2-6  All interactive input via small validated helpers (yes/no, choice-with-
      default, bounded int); every prompt reply strip()ed.

FILE 2 — `tests/test_shadow.py`:
E2-7  Pure-function tests for grading/aggregation: G1 string-verdict case; seeded
      exclusion from criteria; usability rate math; missed-uncap detection relative
      to the human determination.

════════ END STAGE E2 ════════

**OPERATOR CHECKS (E2):**
```bash
python3 src/shadow.py new --no-llm --facts "test facts" && python3 src/shadow.py status
printf 'yes\n\nnote\n' | python3 src/shadow.py grade SHADOW-$(date +%Y%m%d)-001
python3 src/shadow.py report; rm -f shadow/graded/SHADOW-*.json results/shadow-report-*.md
./run_tests.sh
```

**QC ADDENDUM (E2):** Verify the reveal ordering cannot be bypassed (no code path
prints the verdict before the human fields are captured); G1/G3/G12.

---

## STAGE E3 — Staff-facing web UI

**ATTACH:** `config.json`, `src/ingest.py`, `src/retrieve.py`, `src/llm_client.py`,
`src/prompts.py`, `src/escalate.py`.

════════ STAGE E3 — BUILDER PROMPT ════════

FILE 1 — `src/webui.py` — single-file local web app: stdlib http.server
(ThreadingHTTPServer), all HTML/CSS/JS inline in one PAGE constant, zero external
assets (fully offline).

E3-1  Endpoints: GET / (page); GET/POST /api/health {corpus_chunks, llm up/down via
      a tiny probe chat, model, endpoint}; POST /api/search {q} → authority-labeled
      hits; POST /api/ask {question, initials}; POST /api/triage {facts, initials};
      POST /api/reload (drop and rebuild the cached Retriever).
E3-2  ROUTING INTEGRATION: both ask and triage run route_pre BEFORE any LLM call;
      human_only returns {routed, hits} with NO draft (and this path must work with
      the LLM down). Triage runs route_post after the verdict and merges. When the
      merged route is "escalate": DO NOT call the second-tier model inline (G4) —
      return the daily draft with routing attached; append the reason "second-tier
      model not configured — route this case to the assessor / design-tier model
      manually" when escalation_llm is disabled, or "second-tier review queued —
      assessor review required" language when enabled (actual async queue is out of
      scope; the flag is the v1 behavior either way).
E3-3  UI: two tabs (Ask / PTA triage). Persistent top banner: "⚠ Every output is a
      DRAFT for human review… Sessions are logged." Results render inside a
      red-dashed box headed "DRAFT — VERIFY BEFORE RELYING ON IT" / "DRAFT
      DETERMINATION — ASSESSOR REVIEW REQUIRED". [VERIFY] substrings highlighted.
      Each source rendered as an expandable item with a colored authority badge
      (LAW / STATE-GUIDANCE / OFFICE-PRACTICE / UNTAGGED distinct colors) and the
      passage text. Routing banners: red "⛔ ROUTED TO A HUMAN — no AI draft for
      this one" (human_only, with reasons and a pointer to the office's escalation
      contacts) and blue "⬆ ESCALATION FLAGGED — treat with extra care" (escalate,
      with reasons). Initials input persisted in localStorage and sent with
      requests. All dynamic strings HTML-escaped in JS before insertion.
E3-4  LOGGING: every successful ask/triage and every human_only routing appends one
      JSON line to logs/webui-YYYYMMDD.jsonl: ts, kind, initials, input, output or
      routing, retrieved ids, seconds. Before writing, pass input/output text
      through `redact(text)`: replace SSN-shaped patterns (\b\d{3}-\d{2}-\d{4}\b)
      with [REDACTED-SSN]. Include a module comment: logs may be FOIA-able records;
      retention per config webui.log_retention_days is the operator's
      responsibility (document, don't implement deletion).
E3-5  SAFETY/LIMITS: request bodies over config webui.max_body_bytes → 413 JSON
      error (G7). Empty question/facts → 400. LLMError → 503 with the actionable
      message. Missing index → 503 telling the operator to run ingest. Default bind
      127.0.0.1:8580; `--host 0.0.0.0` prints a NO-AUTH warning; `--auth user:pass`
      enables HTTP Basic Auth (compare with hmac.compare_digest; 401 +
      WWW-Authenticate otherwise) and binding beyond localhost WITHOUT --auth
      prints a strong warning naming the data policy.
E3-6  Quiet access log (override log_message); health probe failures must not crash
      the page.

FILE 2 — `docs/webui-checklist.md` — a manual curl test script covering: page 200;
health; search authority labels; ask/triage 503 with server down; human_only triage
short-circuit working with server down; 400 empty; 413 oversized body (give the exact
curl commands).

════════ END STAGE E3 ════════

**OPERATOR CHECKS (E3):** run every command in docs/webui-checklist.md with the LLM
server DOWN (human_only and error paths must all behave), then spot-check Ask and
Triage in a browser with the server UP. Delete test log lines afterward.

**QC ADDENDUM (E3):** G4 is the focus (grep for any chat() call with
escalation_llm_config — inline second-tier calls are CRITICAL). Then G7, G10, G11;
verify the JS escapes model text before innerHTML insertion; verify Basic Auth uses
constant-time comparison.

---

# PART F — CONTENT, GOVERNANCE, CONTINUITY (any time after Part B)

## STAGE F1 — Statewide-default PTA SOP + localization framework

**ATTACH:** `corpus/mcl-211-27a.md`, `corpus/mcl-211-27b.md` (fetched in B2).

════════ STAGE F1 — BUILDER PROMPT ════════

Write two documents. Ground every legal statement in the attached statute text; tag
anything you cannot ground [VERIFY]. Temperature note to operator: run this stage at
temp 0.6.

FILE 1 — `corpus/pta-triage-sop.md` — first line `AUTHORITY: OFFICE-PRACTICE`.
A statewide-default SOP adoptable by any Michigan office. Structure and required
content:

F1-1  Header blockquote: statewide default drafted from MCL 211.27a/27b and the STC
      Transfer of Ownership Guidelines; [LOCALIZE] marks points where offices
      lawfully differ, each stating the conservative default that applies until
      overridden; statute controls if this document ever disagrees with it.
F1-2  §1 Intake: what to log for every PTA or deed-without-PTA (parcel,
      classification, transfer date, instrument type, parties + relationship,
      consideration WITH the warning that absence of a price does not mean no
      transfer of ownership, received date driving penalty math); CAMA entry with
      scan attached; [LOCALIZE: CAMA system + field, default "consistent notes
      field, one entry per transfer"].
F1-3  §2 Determination steps: (1) present-interest conveyance vs security interest
      [211.27a(6)]; (2) exception check against 211.27a(7) and the STC guidelines
      with the instruction "match the facts to the specific statutory subsection —
      never approve an exception by general resemblance"; (3) family-residential
      claims require residential classification and no indication of use change —
      flag if unknown, never assume; (4) trust transfers require the trust
      instrument — request in writing, determination waits, never guess from the
      deed; (5) no clear exception → transfer of ownership, uncap effective the
      calendar year FOLLOWING transfer [211.27a(3)]; (6) routing: staff handle
      clear cases; ANY claimed exception, trust, probate, entity transfer, or
      uncertainty routes to the assessor; monthly assessor spot-check of routine
      determinations [LOCALIZE: rate, default 1 in 10].
F1-4  §3 Late-filing penalty per 211.27b: amounts exactly as the attached statute
      states them; the statute's "must be levied" language; the ONLY lawful waiver
      is a governing-body resolution under 211.27b(5); [LOCALIZE: whether such a
      resolution exists — DEFAULT: assume NO resolution, assess per statute, staff
      never waive case-by-case].
F1-5  §4 Post-uncapping mechanics for unreported transfers per 211.27b: certify
      additional taxes; immediate first-class-mail owner notice starting the 35-day
      MTT window (limited to whether a transfer occurred + arithmetic); adjustment
      affidavit within 30 days.
F1-6  §5 Missing-PTA monitoring: monthly reconciliation of recorded deeds vs PTAs
      received; follow-up letter + blank L-4260 to non-filers; unresolved items
      determined from available evidence and routed to the assessor; [LOCALIZE:
      deed-information source + reconciliation day, default first business week
      monthly].
F1-7  §6 Documentation standard: determination note (instrument, date,
      determination + specific subsection, key facts, reference applied, preparer
      and reviewer initials/dates), scans attached, uncertain determinations marked
      with open questions.
F1-8  §7 Assistant usage: AI may draft under this SOP; every draft human-reviewed;
      AI-flagged uncertainty follows the same assessor routing.

FILE 2 — `corpus/LOCALIZATION.md` (excluded from ingestion by design):
F1-9  The two-layer table (statewide LAW/STATE-GUIDANCE vs local OFFICE-PRACTICE,
      who maintains each); the adoption checklist for a new office (review
      [LOCALIZE] markers; verify annual constants; add local layer — localized
      SOPs, office profile, escalation contacts, decision journal, state-of-office
      doc; re-ingest; re-tune config thresholds; RUN THE FULL VALIDATION GAUNTLET —
      another office's numbers do not transfer); and the non-negotiables that never
      localize: human review, authority hierarchy + [VERIFY], human-only escalation
      categories, zero-tolerance missed uncaps.

════════ END STAGE F1 ════════

**OPERATOR CHECKS (F1):** `python3 src/ingest.py` (SOP ingests as OFFICE-PRACTICE;
LOCALIZATION.md excluded); `python3 src/retrieve.py "our office procedure for trust
transfer without trust documents"` → SOP chunks top. **Then read the SOP yourself as
the domain expert and edit where it misstates practice or law — this document speaks
for your office once ingested.**

**QC ADDENDUM (F1):** Domain check is the focus: verify every statutory claim against
the attached statute text (amounts, day counts, subsection numbers); verify every
[LOCALIZE] has a stated conservative default; verify the penalty default is
"assess" (a default of "waive" is CRITICAL).

---

## STAGE F2 — Remaining statewide-default SOPs (repeat template)

Run this stage once per SOP: **PRE processing**, **taxpayer inquiry response**,
**BoR preparation**, **record card maintenance**. ATTACH the relevant corpus
documents (PRE: mcl-211-7cc/7dd + PRE Guidelines extract; BoR: mcl-211-29/30/33 +
BoR Q&A extract; inquiries: PRE + transfer guidelines; record cards: Vol III
extract). If an attachment exceeds practical paste size, attach the most relevant
~30K chars and say so in the prompt.

════════ STAGE F2 — BUILDER PROMPT (parameterized) ════════

Write `corpus/<name>-sop.md`, first line `AUTHORITY: OFFICE-PRACTICE`, following the
exact conventions of the attached `corpus/pta-triage-sop.md` (also ATTACH it as the
style/structure exemplar): statewide-default header blockquote; numbered procedure
sections grounded ONLY in the attached reference documents with section citations;
[VERIFY] on anything ungrounded; [LOCALIZE + conservative default] at every point
offices lawfully differ; a routing section (what staff handle vs what routes to the
assessor); a documentation standard; a closing assistant-usage section. For the PRE
SOP specifically: filing deadlines and rescission duties must cite the attached
statute/guidelines text, and the June/November filing structure must carry
[VERIFY current-year dates] rather than hardcoded dates. For the BoR SOP: note that
city charters may lawfully alter BoR composition/schedule [LOCALIZE: jurisdiction
type and charter provisions, default = general-law township schedule per statute].

════════ END STAGE F2 ════════

**OPERATOR CHECKS / QC (F2):** as F1 (re-ingest, retrieval spot-check, expert read,
QC domain check against attachments).

---

## STAGE F3 — Continuity pack (substitute drill) and operator docs

**ATTACH:** `README.md`, `TODO.md`.

════════ STAGE F3 — BUILDER PROMPT ════════

Write the continuity-readiness pack. These are documents for humans; none are
ingested except where noted. Temp 0.6.

FILE 1 — `substitute-drill/README.md`: the purpose (if the assessor is out, how well
can the assistant guide a certified temporary replacement); the two framing truths
(Michigan requires a certified human assessor of record — the AI is an onboarding/
knowledge interface, never the officeholder; and the substitute paradox — the person
relying on the tool is least able to catch its errors, making escalation the core
feature); a gap list (no CAMA/parcel data access; no assessment-calendar awareness;
no in-flight-work state; valuation math must be deterministic, never generative; not
all workflows built; text-only); the definition of ready ("a certified but unfamiliar
assessor runs routine operations for two weeks with zero silent errors").

FILE 2 — `substitute-drill/drill-action-plan.md`: phases — D0 prerequisites (real
corpus, passed validation gate, state-of-office doc, ≥10 decision-journal entries,
escalation contacts in corpus); D1 scenario deck (20-30 cards: ~10 routine, ~5 edge,
~5 in-flight-state, ~5 out-of-scope traps; correct answers written down beforehand;
deck never ingested); D2 stand-in recruitment (ideally a neighboring jurisdiction's
certified assessor, reciprocal); D3 run protocol (silent observer; four outcome
buckets — correct / correctly-escalated (a SUCCESS) / wrong-but-flagged / SILENT
FAILURE; silent-failure rate is the headline metric, target zero); D4 same-day
debrief with root-cause classes (corpus / state / capability / escalation /
usability gap) feeding the next quarter's priorities; D5 between drills (every
silent failure becomes a regression test; keep the state-of-office doc alive;
quarterly cadence with rising bars).

FILE 3 — `substitute-drill/journal-prompts.md`: 25-30 prompts capturing
assessor-discretion areas as decision-journal entries (saved to corpus/ with
AUTHORITY: OFFICE-PRACTICE): valuation methodology (ECF neighborhood rationale, land
table derivation, sales-exclusion instincts, grade conventions, obsolescence,
commercial approach/cap rates, unusual parcels), enforcement posture (uncapping
chase, penalty practice, PRE scrutiny, poverty-exemption administration, inspection
strategy), BoR/appeals (posture, informal resolution, tribunal settle-vs-defend,
defensive documentation), gray-area precedents (classification boundaries,
use-change judgment), administration (CAMA code decoder-ring, sketch conventions,
internal calendar, delegation map, county relationship, communication norms), and
philosophy (assessment posture, uniformity vs accuracy, borderline-uncapping
instinct, the three decisions a successor most needs explained).

FILE 4 — `substitute-drill/templates/decision-journal-template.md`: date, topic
area, the question, the decision, the reasoning a substitute needs (with
references), the generalizable rule + trap, and "the nearest fact pattern where the
answer flips".

FILE 5 — `substitute-drill/templates/state-of-office-template.md`: cycle position;
90-day hard deadlines table; in-flight matters a substitute MUST know; current-year
constants (IRM [VALUE] + citation, BoR dates, roll certification, equalization
submission); who-to-call table (county equalization, city attorney BEFORE responding
to anything from an attorney, neighboring assessor, STC, CAMA support, IT); systems
and access (no credentials in the doc); "three things most likely to bite a
substitute this quarter".

FILE 6 — `substitute-drill/templates/drill-scorecard.md`: per-scenario log table
(scenario, type, expected, outcome bucket, minutes, notes); totals; every silent
failure detailed with root cause; gap ranking; stand-in debrief questions ("days
until functional?", "what almost burned you?", "what did you stop trusting?");
prior-drill comparison.

FILE 7 — `docs/operations.md`: the operator runbook — start/stop llama-server
(example commands with --parallel and context sizing note: context divides across
parallel slots); re-ingest after corpus changes + /api/reload; annual corpus refresh
procedure (fetch_corpus.py + STC bulletin downloads + clean_extraction + re-ingest +
commit); log review/retention duty; backup = git remote or copy; the
governance-before-staff-use requirement (municipal leadership briefing + one-page
data policy: what may/may not be entered, logging disclosure, human-review rule in
writing).

════════ END STAGE F3 ════════

**OPERATOR CHECKS (F3):** read-through; confirm none of these ingest except as
designed (`python3 src/ingest.py` output unchanged).

**QC ADDENDUM (F3):** Verify the four-bucket scoring counts correct-escalation as
success; verify the templates contain no invented statutory dates (placeholders
only); verify docs/operations.md includes the governance step.

---

## STAGE F4 — Final integration audit and release

**No builder session.** One QC session over the whole repository, then operator
release steps.

1. Fresh QC (27B) session: paste §2, §3, then this instruction:
   "Audit the complete repository below as an integrated system. In addition to the
   global regression checklist, verify: (a) every src/ module imports and runs under
   python3 -m compileall semantics — flag any name mismatch between modules (e.g., a
   function renamed in one file but imported under the old name elsewhere);
   (b) config.json keys are consistent with every consumer; (c) backtest, shadow,
   and webui all obtain context exclusively through prompts.assemble_context;
   (d) the canonical JSON shapes are identical across new_case, backtest, shadow,
   and the system prompt's declared schema; (e) every corpus document template
   carries provenance and authority; (f) README quickstart commands are runnable as
   written." Then paste every file in the repo (multiple messages as needed; the
   200K window fits the codebase comfortably — paste code first, then documents).
2. Apply corrections; `./run_tests.sh`; run the full OPERATOR CHECKS of stages B1,
   D2, E1, E3 once more.
3. Re-run the Stage D3 gate (numbers should reproduce).
4. Tag the release: `git tag v1.0-rebuilt && git commit -am "stage F4: release"`.
5. Begin the pilot per docs/operations.md: shadow mode (Stage E2 tooling) on live
   incoming PTAs, 4-6 weeks, success criteria agreement ≥95% / missed uncaps 0 /
   usable drafts ≥70%, with 2-3 seeded vigilance cases mid-pilot.

---

# APPENDIX — WHY THESE CHECKS EXIST (defect provenance)

For the operator's understanding; nothing here needs pasting into sessions.

| Check | Original defect |
|---|---|
| G1 | Scoring used `bool(verdict.get("uncapping"))`; a model answering the string "no" was scored as answering yes — directly corrupting the zero-tolerance missed-uncap metric. |
| G2 | The router's `attorney` pattern matched "power of attorney", denying AI drafts to routine POA conveyances as "litigation". The inverse gap also existed: "being sued" matched nothing. |
| G3 | Three synthetic demo cases were counted in the headline backtest agreement rate. |
| G4 | The web UI re-ran escalated cases synchronously on a ~4 tok/s second-tier model with a 30-minute timeout inside an HTTP handler. |
| G5 | The original build ran for weeks with no version control. |
| G6 | The corpus README's example table matched the authority regex and was ingested as LAW. |
| G8 | Top-k retrieval alone was trusted for triage; MCL 211.27a chunked into ~26 pieces and the governing exception subsection could fall outside the top-k. |
| G9 | Staff vocabulary ("uncap") does not appear in statute text ("adjusted under subsection (3)"); pure lexical BM25 missed on-point law for colloquial queries. |
| Sequencing rule | The original build completed ~90% of infrastructure before any LLM processed a single case — the core capability hypothesis was still untested when the UI shipped. Part D's hard gate prevents the repeat. |
| Extraction QA (B2) | 380K+ chars of pdftotext output entered the corpus with only grep-level spot checks; repeated page headers and mangled tables were statistically certain to be present. |
| Vol I/II exclusion (B2-9) | Cost-schedule volumes are numeric tables that extract as noise and pollute BM25 ranking. |
| Single evaluator (F3 drill design) | Shadow-mode agreement was measured against one human with no inter-rater check; the drill's seeded cases and the second-evaluator overlap recommendation harden it. |

*End of document.*

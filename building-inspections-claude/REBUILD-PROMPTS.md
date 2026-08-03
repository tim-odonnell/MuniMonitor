# Michigan Building & Inspections Assistant — Multi-Stage Rebuild Prompts

**What this document is.** A complete series of prompts to rebuild this project from
scratch on a separate machine, incorporating every bug, soft spot, and design lesson
from the original build — including the audit findings unique to this project (the
silent no-image failure, TEST-CORPUS retrieval pollution, the PA 54 repeal trap, the
code-injunction currency problem). This document is the seed; nothing else from the
original folders is required.

**Execution model — identical to the assessor rebuild.** BUILDER = Qwen3.6-35B-A3B
(full precision, full context, GPU; temp 0.2 code / 0.6 prose). QC = Qwen3.6-27B
(full precision, full context, GPU; temp 0.2). MANAGER = any strong instruct model
on CPU + system RAM, run between stages. OPERATOR = you. One fresh builder session
per stage, then one fresh QC session, then a manager checkpoint, then commit — the
full operator loop, session recipes, and ledger mechanics are defined in
`assessor-assistant-claude/REBUILD-PROMPTS.md` and apply here unchanged.

**§0 MANAGER:** paste the manager prompt from the assessor rebuild document's §0
verbatim — it is project-agnostic. Maintain a SEPARATE ledger for this project
(`docs/build-ledger.md`), seeded from this document's §1 on the first checkpoint. If
the assessor document is unavailable, run without a manager and compensate: run the
Stage F3 integration audit after every PART boundary instead of once.

**Non-negotiable sequencing.** Parts A→B→C in order. Part D contains TWO validation
gates (text and vision); **no Part E work (staff-facing surfaces) until both gates
have run** — the vision gate may FAIL and the text surface still proceeds (they are
independent), but the gate must have been *run*, not skipped. The vision checklists
must be red-lined by the department head BEFORE the vision gate (Stage D3), or the
gate scores against unreviewed criteria and the results are stale on arrival.

---

## §1 SHARED CONTEXT — paste at the top of EVERY BUILDER session

```
PROJECT: "Building & Inspections Assistant" — a fully-offline, local-LLM assistant
for a Michigan municipal building & inspections department, operating under the
Stille-DeRossett-Hale Single State Construction Code Act (1972 PA 230) and the
Skilled Trades Regulation Act (2016 PA 407). Two independent surfaces:
  (1) TEXT Q&A grounded by retrieval over an authority-tagged knowledge base
      (statutes, state-published administrative rules, LARA/BCC guidance,
      department SOPs);
  (2) VISION photo screening: construction photographs checked against
      per-inspection-type visible-condition checklists by a local multimodal model.

YOUR ROLE: sole implementer, writing complete production artifacts from precise
specifications.

HARD RULES (violating any is a critical defect):
R1. Python 3.12 STANDARD LIBRARY ONLY, code and tests (unittest, not pytest).
R2. Fully offline at runtime: network calls only to local OpenAI-compatible
    endpoints from config.json — TEXT model on port 18080, VISION model on port
    18081. The ports are deliberately distinct: a text-only server must never be
    able to receive image requests by accident.
R3. Every output is a DRAFT for a REGISTERED building official/inspector (PA 407).
    The assistant screens, drafts, and cites; it never determines compliance,
    never passes/fails an inspection, never issues anything.
R4. Authority hierarchy on every knowledge-base document:
    LAW (statute/adopted rule) > STATE-GUIDANCE (LARA/BCC) > OFFICE-PRACTICE
    (department discretion — NEVER presented as code requirement) > TEST-CORPUS
    (real code text from ANOTHER jurisdiction, present only to validate pipeline
    mechanics — NEVER citable as Michigan authority, and EXCLUDED from retrieval
    by default) > UNTAGGED (unknown, treat as unverified).
R5. [VERIFY] discipline: legal assertions not grounded in a provided document are
    tagged [VERIFY]; never cite code section numbers, dimensions, or fees from
    memory; edition-dependent values use placeholders ([CODE_EDITION], [FEE]).
R6. VISION HONESTY (the load-bearing rules of surface 2):
    - never output pass/fail; findings are "possible"/"appears", routed to the
      inspector
    - never estimate measurements from pixels ("appears irregular — measure on
      site" is the ceiling)
    - "cannot_verify_from_photo" is a first-class output section
    - image-quality problems are findings, not things to guess around
    - bias toward flagging: a false flag costs a second look; a missed visible
      life-safety condition costs far more
R7. Error weighting: (a) vision evals — a HALLUCINATED MEASUREMENT is
    zero-tolerance; (b) continuity drills — a silent failure on anything
    life-safety-adjacent (structural, egress, electrical, CO/smoke) is an
    automatic FAIL; (c) a missed VISIBLE life-safety condition outweighs any
    number of false flags.
R8. ICC COPYRIGHT: Michigan adopts ICC model codes BY REFERENCE; the model-code
    text is copyrighted and is NOT fetched, scraped, or ingested. Only
    state-published rules (the Michigan amendments), statutes, public guidance,
    department documents, and the public-domain TEST-CORPUS go in the knowledge
    base. Copyright does not lapse on old editions.

DOMAIN FACTS THE BUILD MUST ENCODE (verified during the original build):
D1. Inspector registration authority is 2016 PA 407 (Skilled Trades Regulation
    Act). The former Building Officials and Inspectors Registration Act (1986
    PA 54, MCL 338.2301-2313) was REPEALED by PA 407 eff. April 4, 2017 — it must
    never be ingested or cited.
D2. Code currency is litigation-dependent: per a July 7, 2025 Court of Claims
    stipulated order (Home Builders Assoc et al. v LARA), the rule sets adopting
    the 2021 IRC/IECC residential provisions are ENJOINED; the 2015-based
    residential rules remain in effect while litigation continues. This WILL
    change; the corpus carries a currency notice that must be re-checked
    periodically, and Part 10 (energy) answers carry a version caveat.
D3. Michigan admin rule parts (state-published, free, from ARS): Part 4 Building
    (R 408.30401+), Part 5 Residential (R 408.30500+, adopts IRC 2015 + MI
    amendments), Part 7 Plumbing (2021), Part 8 Electrical (NEC 2023 TIAs),
    Part 9A Mechanical (IMC 2021), Part 10 Energy, Existing Building Code
    (R 408.30551+, IEBC 2021).

TARGET LAYOUT (repo root = building-inspections/):
  README.md TODO.md REBUILD-PROMPTS.md config.json run_tests.sh .gitignore
  src/    ingest.py retrieve.py llm_client.py ask.py prompts.py vision_check.py
          new_photo_case.py
  tests/  test_project.py
  corpus/ (knowledge base + README gathering guide)   source-pdfs/ (provenance)
  eval/   (photo golden-set case JSONs)  eval/photos/ (gitignored — privacy)
  docs/   (project-plan, vision-test-plan, de-indexed lookup tables)
  substitute-drill/ (continuity pack)   results/   logs/

CANONICAL JSON SHAPES:
Vision screening report (the vision model must return exactly):
  {"image_quality": "good"|"limited"|"poor",
   "observations": [str],
   "possible_concerns": [{"concern": str, "visible_evidence": str,
                          "checklist_item": str, "confidence": "high"|"medium"|"low"}],
   "cannot_verify_from_photo": [str],
   "recommended_inspector_actions": [str]}
Golden photo case (eval/*.json):
  {"case_id": str, "inspection_type": str, "image": str, "synthetic": bool,
   "known_findings": [{"finding": str, "visible_in_photo": bool}],
   "inspector_outcome": str, "notes": str}
Inspection types (exactly these six): footing, framing, electrical_rough,
plumbing_rough, insulation, final.

CODING STANDARDS & OUTPUT CONTRACT: identical to the assessor rebuild §1 — complete
files with FILE: headers, no elisions, no TODOs, sibling imports via sys.path,
config from repo root, actionable error messages, conservative choices noted in one
line when a spec is ambiguous.
```

---

## §2 QC TEMPLATE — paste at the top of EVERY QC session

Use the assessor rebuild document's §2 QC TEMPLATE verbatim (spec compliance →
regression checklist → defect hunt → domain check; output = verdict table, severity
defects, complete corrected files). For the domain check in this project, add:
**every vision checklist item must be a VISIBLE condition** (an item requiring
measurement, concealed access, or material grade knowledge is a defect unless
qualified "if reference/label visible"), and every statement about which code
edition applies must route through the injunction-currency notice, never a bare
assertion.

---

## §3 GLOBAL REGRESSION CHECKLIST — paste into EVERY QC session after §2

```
These defects existed in the original build of this exact system (or its sibling).
Verify each explicitly, character by character.

BG1  STRING-BOOLEAN/STRING-ENUM COERCION: no bool() on model-supplied values
     anywhere. Vision reports pass through normalize_report(): invalid
     image_quality degrades to "poor" (conservative), invalid confidence to
     "low", malformed concern entries coerced to the canonical dict, never
     crashed on. parse_bool() is the only boolean conversion.
BG2  SILENT NO-IMAGE FAILURE: a text-only server can accept an image_url request
     and answer fluently from the checklist text alone — a confident screening
     report about a photo nobody looked at. Defenses BOTH required: (a) vision
     endpoint on its own default port (18081); (b) a calibration probe — a
     stdlib-generated solid-red PNG the model must identify by color — that runs
     automatically before every real screening and standalone via --calibrate,
     ABORTING with an explanatory message on failure. --skip-calibration exists
     but the eval docs forbid it during evals.
BG3  TEST-CORPUS RETRIEVAL POLLUTION: TEST-CORPUS chunks are EXCLUDED from
     Retriever.search() by default (they must never crowd Michigan authority out
     of the top-k); included only via an explicit include_test_corpus flag /
     --include-test-corpus CLI option.
BG4  TEST-CORPUS AUTHORITY LEAKAGE: the QA system prompt must instruct that
     TEST-CORPUS material is NEVER cited as Michigan authority, and that when it
     is the only support, the answer is "the Michigan provision is not in my
     reference documents" — full stop.
BG5  REPEALED-LAW TRAP: 1986 PA 54 is repealed. It must not be ingested; nothing
     may cite it as current authority; the corpus README must warn against it.
BG6  CODE-CURRENCY: the injunction notice (D2 in shared context) must be in the
     corpus with a re-check warning, and the Part 10 energy document must carry
     the residential-chapter version caveat.
BG7  TABLE-DOCUMENT POLLUTION: large name/table documents (e.g., the statewide
     jurisdiction list — thousands of municipality names) stay OUT of the BM25
     index (docs/ as human lookup), or any query mentioning a city name pulls
     useless chunks.
BG8  INSTRUCTION-FILE INGESTION: ingest excludes README.md (and any
     LOCALIZATION.md) case-insensitively.
BG9  VISION PROMPT INVARIANTS: the vision system prompt contains, verbatim in
     spirit: no pass/fail output; no pixel measurements; cannot_verify_from_photo
     as a required JSON key; checklist-only code citations with [VERIFY]
     otherwise; image-quality-as-finding; over-flagging bias.
BG10 COPY-PORT REBRANDING: any file ported from the sibling assessor project must
     carry NO assessor-domain references (UI strings, docstrings, dead verdict
     logic like normalize_verdict/CANONICAL_EXCEPTIONS). Grep for
     "assess"/"uncap"/"PTA" in src/ — hits outside comments explaining provenance
     are defects.
BG11 LIFE-SAFETY WEIGHTING: eval and drill documents must state the automatic-FAIL
     rules (hallucinated measurement = 0 tolerance; life-safety silent failure =
     drill FAIL) as hard gates, not soft metrics.
BG12 PHOTO PRIVACY: eval/photos/ is gitignored; every photo-handling instruction
     requires anonymization (addresses, faces, plates) BEFORE photos touch the
     machine; logs note FOIA-awareness.
BG13 VERSION CONTROL: git from stage A1; .gitignore covers index.json, results/,
     logs/, eval/photos/, __pycache__.
BG14 HUMAN-REVIEW FRAMING: every user-facing surface carries
     draft-for-registered-inspector framing (rendered reports open with it).
```

---
---

# PART A — FOUNDATION

## STAGE A1 — Scaffold, config, git

**ATTACH:** nothing.

════════ STAGE A1 — BUILDER PROMPT ════════

Create the repository foundation per the shared-context layout.

1. `.gitignore`: `__pycache__/`, `*.pyc`, `corpus/index.json`, `results/`, `logs/`,
   `eval/photos/`, plus `.gitkeep` placeholder files for every empty directory.
2. `config.json` — canonical structure:
   ```json
   {
     "llm":    {"base_url": "http://127.0.0.1:18080/v1", "api_key": "none",
                "model": "local", "max_tokens": 1200, "timeout_seconds": 600},
     "vision": {"base_url": "http://127.0.0.1:18081/v1", "api_key": "none",
                "model": "local-vision", "max_tokens": 1600,
                "timeout_seconds": 900, "max_image_bytes": 8000000},
     "retrieval": {"top_k": 6, "max_chunk_chars": 1600},
     "paths": {"corpus_dir": "corpus", "index_file": "corpus/index.json",
               "cases_dir": "eval", "results_dir": "results"}
   }
   ```
   A1-1: the llm and vision ports MUST differ (BG2 defense a).
3. `run_tests.sh`: `python3 -m unittest discover -s tests -v`.
4. `README.md`: banner; the two surfaces with the vision honesty rules (R6) stated
   for humans; layout table; quickstart placeholder; "capability unvalidated until
   the gates pass" statement.
5. `TODO.md` seeded with: both validation gates not yet run; department homework
   (golden photo set, checklist red-line, real SOPs, city-attorney memo); the
   injunction-watch standing item.

════════ END STAGE A1 ════════

**OPERATOR CHECKS:** `git init`, config parses, commit "stage A1".
**QC ADDENDUM:** ports differ (BG2); .gitignore covers BG12/BG13 paths.

---

# PART B — KNOWLEDGE BASE

## STAGE B1 — Ingestion and retrieval (4-level authority + exclusions)

**ATTACH:** `config.json`.

════════ STAGE B1 — BUILDER PROMPT ════════

Build `src/ingest.py` and `src/retrieve.py` exactly as specified in the assessor
rebuild Stage B1 (chunking, tokenization, stopwords, BM25 with k1=1.5/b=0.75,
idf = ln(1+(N−df+0.5)/(df+0.5)), warnings, CLI shapes) with these deltas — if you
do not have that document, the deltas below plus the shared context are sufficient
to build from scratch; state your interpretation choices:

B1-1  AUTHORITY levels are four: LAW, STATE-GUIDANCE, OFFICE-PRACTICE, TEST-CORPUS
      (regex on the first 1000 chars: `^AUTHORITY:\s*(LAW|STATE-GUIDANCE|
      OFFICE-PRACTICE|TEST-CORPUS)\b`, case-insensitive multiline; absent →
      UNTAGGED + warning).
B1-2  Exclusions (BG8): readme.md, localization.md (case-insensitive), the index
      file.
B1-3  Retriever.search(query, k=None, include_test_corpus=False): TEST-CORPUS
      chunks are skipped unless the flag is True (BG3). CLI gains
      --include-test-corpus.
B1-4  Query-expansion SYNONYMS map for this domain, at minimum:
      co→[certificate, occupancy]; bor→[board, review]... use instead:
      permit→[building, permit]; footing→[foundation, footing];
      gfci→[ground, fault]; afci→[arc, fault]; nec→[electrical, code];
      irc→[residential, code]; ibc→[building, code]; iebc→[existing, building];
      imc→[mechanical, code]; amm→[alternative, materials, methods];
      stopwork→[stop, work]; cofo→[certificate, occupancy];
      lara→[licensing, regulatory]; bcc→[construction, codes].
B1-5  tests/test_project.py started with: authority detection (all four levels +
      late-tag negative), chunk packing/hard-split, BM25 ordering, TEST-CORPUS
      exclusion default + flag (build a hand-rolled 3-chunk index on a Retriever
      created via __new__ — no file I/O), expansion behavior.

════════ END STAGE B1 ════════

**OPERATOR CHECKS:** smoke doc ingest; `./run_tests.sh`.
**QC ADDENDUM:** BG3, BG8 are the focus; verify the exclusion happens before
scoring (not a post-filter that shrinks k).

---

## STAGE B2 — Corpus acquisition (the free lane) + extraction QA

**ATTACH:** `config.json`, `src/ingest.py`.

════════ STAGE B2 — BUILDER PROMPT ════════

FILE 1 — `src/fetch_corpus.py` (operator-run; network allowed here only):

B2-1  Legislature act-level PDFs (browser User-Agent, 90s timeouts), saved to
      source-pdfs/:
      - https://www.legislature.mi.gov/documents/mcl/pdf/mcl-Act-230-of-1972.pdf
        (Stille-DeRossett-Hale) → LAW
      - https://www.legislature.mi.gov/documents/mcl/pdf/mcl-Act-407-of-2016.pdf
        (Skilled Trades Regulation Act — inspector registration) → LAW
      - Do NOT fetch Act 54 of 1986 (repealed — BG5).
B2-2  ARS admin-rule PDFs, URL pattern
      `https://ars.apps.lara.state.mi.us/AdminCode/DownloadAdminCodeFile?FileName=<name>`
      with these FileName values (URL-encoded; double spaces are in the real names):
      "R 408.30401  to 408.30499a.pdf" (Part 4 Building),
      "R 408.30500  to 408.30547g.pdf" (Part 5 Residential),
      "R 408.30551  to 408.30577.pdf" (Existing Building),
      "R 408.30701  to 408.30796.pdf" (Part 7 Plumbing),
      "R 408.30801  to 408.30880.pdf" (Part 8 Electrical),
      "R 408.30901  to 408.30998.pdf" (Part 9A Mechanical),
      "R 408.31001  to 408.31086.pdf" (Part 10 Energy).
      After download, verify each PDF's first page contains its expected PART
      heading; a mismatch is a warning, not a silent accept.
B2-3  24 CFR 3280 via the eCFR API
      (`https://www.ecfr.gov/api/versioner/v1/full/<date>/title-24.xml?part=3280`),
      parsed with xml.etree (DIV8 sections → "## <HEAD>" + itertext), written as
      `corpus/test-corpus-24cfr3280-hud-code.md` with AUTHORITY: TEST-CORPUS and a
      header warning it is NOT Michigan law and gets deleted when licensed text
      lands.
B2-4  pdftotext conversion helper producing corpus .md files with: AUTHORITY line,
      title, provenance blockquote (source URL/file + date), and for Part 10 the
      injunction version caveat (BG6).
B2-5  `src/clean_extraction.py` — same spec as the assessor rebuild (repeated
      header/footer stripping ≥4 occurrences <80 chars, hyphenation repair, dry-run
      default, never touches files lacking an AUTHORITY line).

FILE 2 — `corpus/README.md` (excluded from ingestion) containing:
B2-6  The four-tag table with the exact assistant phrasings; the TEST-CORPUS
      retrieval-exclusion note (BG3/BG4).
B2-7  The ICC copyright constraint (R8) and the three-lane licensing strategy:
      free-now → city-attorney memo (Veeck v. SBCCI 5th Cir.; ASTM v.
      Public.Resource.Org D.C. Cir.; Michigan is 6th Cir. = unsettled; old
      editions are NOT free) → licensed ingestion + TEST-CORPUS deletion.
B2-8  The PA 54 repeal warning (BG5) and the injunction currency item (BG6) with
      its re-check duty.
B2-9  The jurisdiction-list rule (BG7): big table documents go to docs/ as human
      lookups, never into the index.
B2-10 Remaining human items: LARA/BCC interpretation letters (the BCC FAQ page is
      JavaScript-rendered — manual browser capture), department SOPs/checklists,
      fee schedule, licensed code text pending the attorney answer.

Also fetch, convert, and ingest during this stage (operator): the BCC 2021 code
injunction notice PDF from michigan.gov (search "2021-Code-Injunction-Residential-
Part-5-and-Energy-Part-10.pdf" on the LARA/BCC site) → STATE-GUIDANCE with the
currency warning.

════════ END STAGE B2 ════════

**OPERATOR CHECKS:** fetch all; convert; `python3 src/ingest.py` (expect ~1000+
chunks); retrieval checks: "who may perform inspections" → PA 407 chunks;
"which code edition applies to one and two family dwellings" → Part 5;
"is the 2021 residential code in effect" → injunction notice top; a smoke-alarm
question → NO TEST-CORPUS in results (BG3) and mostly amendment text (the honest
gap, by design). Skim each statute against the official source.
**QC ADDENDUM:** BG5, BG6, BG7 focus; sanity-gate on every conversion.

---

# PART C — REASONING CORE

## STAGE C1 — LLM client

**ATTACH:** `config.json`.

════════ STAGE C1 — BUILDER PROMPT ════════

`src/llm_client.py`: LLMError; chat(messages, cfg=None) posting to
cfg["llm"]["base_url"]/chat/completions (urllib, Bearer auth, actionable
connection-error message); extract_json(text) — strip <think>…</think> first
(DOTALL), then brace-depth scan, ValueError with excerpt on failure; parse_bool
per the assessor spec (the only boolean conversion; unrecognized → ValueError).
Do NOT include any assessor verdict logic (no normalize_verdict, no exception
vocabularies — BG10); report normalization lives with the vision code (C3).
Tests: extract_json think-decoy case; parse_bool truth table.

════════ END STAGE C1 ════════

**QC ADDENDUM:** BG1, BG10.

---

## STAGE C2 — Prompts: QA system, vision system, checklists

**ATTACH:** `config.json`. **Canonical text stage — reproduce prompt texts exactly.**

════════ STAGE C2 — BUILDER PROMPT ════════

`src/prompts.py` with four elements:

C2-1  `GENERAL_QA_SYSTEM` — the building-department QA prompt. Required content,
      as numbered rules: (1) answer ONLY from provided reference documents; code
      editions and amendments change, memory is unreliable; (2) cite section
      labels; (3) [VERIFY] on anything ungrounded; never state code sections,
      dimensions, or fees from memory; (4) placeholders like [CODE_EDITION]/
      [FEE_SCHEDULE]; (5) the authority hierarchy with exact phrasings — "the
      code requires…" (LAW), "state guidance provides…" (STATE-GUIDANCE), "this
      department's practice has been…" NEVER a code requirement
      (OFFICE-PRACTICE), TEST-CORPUS never cited as Michigan authority + the
      mandatory "the Michigan provision is not in my reference documents"
      refusal when TEST-CORPUS is the only support (BG4), UNTAGGED → [VERIFY];
      (6) pass/fail calls, stop-work orders, and legal interpretations belong to
      the registered official — the assistant drafts and cites, never decides.
C2-2  `VISION_SYSTEM` — the photo-screening prompt encoding R6 verbatim in
      spirit: screen-never-determine; the cannot-verify list (dimensions without
      visible reference, concealed work, fastener schedules, material grades,
      anything out of frame); no pixel measurements ("appears irregular — measure
      on site"); checklist-only citations with [VERIFY code section] otherwise;
      image-quality problems are findings; over-flagging bias; and the exact
      canonical JSON output shape from §1.
C2-3  `INSPECTION_CHECKLISTS` — dict over exactly the six inspection types, each
      a short list of GENUINELY VISIBLE conditions (hangers/nailing at visible
      connections; notching/boring; load paths; nail plates; fire blocking; truss
      modifications as automatic flags; cable securing; box crowding; trap/vent
      configuration; slope only when obviously wrong; insulation gaps/compression
      and labels only if legible; baffles; handrails/guards; alarm heads; GFCI
      near visible water; egress windows; grade at foundation; address numbers).
      Every measurement-dependent item carries an "if reference visible"
      qualifier. Top comment: Claude/LLM-drafted, [VERIFY], the department head
      red-lines these BEFORE the vision gate.
C2-4  `build_qa_prompt(question, chunks)` and
      `build_vision_prompt(inspection_type, notes="")` — references labeled with
      authority; the vision prompt states the checklist is the only citable
      source.
Tests: checklist key set equals the six types; VISION_SYSTEM contains
"cannot_verify_from_photo", "[VERIFY", and never-pass/fail language;
GENERAL_QA_SYSTEM contains the TEST-CORPUS refusal rule (BG4, BG9).

════════ END STAGE C2 ════════

**QC ADDENDUM:** BG4, BG9; the visible-conditions domain check from §2.

---

## STAGE C3 — Vision harness with calibration probe

**ATTACH:** `config.json`, `src/llm_client.py`, `src/prompts.py`, `src/ingest.py`.

════════ STAGE C3 — BUILDER PROMPT ════════

`src/vision_check.py`:

C3-1  encode_image(path, max_bytes): jpg/png/webp → base64 data-URL content block;
      over-limit → actionable resize message.
C3-2  vision_chat(messages, cfg) = chat(messages, {"llm": cfg["vision"]}) — the
      SHARED client with a config override; no duplicated HTTP code.
C3-3  solid_png(r,g,b,size=64): valid PNG from pure stdlib (struct+zlib; IHDR
      8-bit RGB, filter-0 rows, IDAT, IEND).
C3-4  calibration_probe(cfg): send the solid red PNG asking for the dominant
      color in one word; "red" not in reply → SystemExit with the full
      explanation of the silent no-image failure mode (BG2). Runs automatically
      before every real screening; `--calibrate` runs it standalone;
      `--skip-calibration` bypasses with a warning.
C3-5  normalize_report(v): canonical-shape coercion — image_quality ∈
      {good,limited,poor} else "poor" (conservative); concerns coerced to the
      canonical dict (bare strings become {"concern": str, confidence "low"});
      confidence ∈ {high,medium,low} else "low"; all lists coerced (BG1).
C3-6  CLI: `vision_check.py [inspection_type] [images...] [--notes S] [--json]
      [--dry-run] [--calibrate] [--skip-calibration]` — inspection_type/images
      optional positionals so --calibrate works standalone, with an argparse
      error when missing on a real run. Every screening saved to
      results/vision-<type>-<ts>.json. Rendered report opens with "DRAFT PHOTO
      SCREENING — REGISTERED INSPECTOR REVIEW REQUIRED" and renders all five
      report sections, with "(none flagged — this is NOT a pass)" when concerns
      are empty (BG14).
`src/new_photo_case.py`: golden-set case creator (canonical case shape),
interactive + flag modes, findings as "description:visible|hidden", anonymization
reminders, warn-don't-fail on missing image file.
`src/ask.py`: staff Q&A CLI (interactive loop + one-shot + --no-llm retrieval
mode), building-department branding throughout (BG10).
Tests: probe PNG signature/IHDR/IEND; normalize_report string-discipline cases;
parse_finding both markers + error case.

════════ END STAGE C3 ════════

**OPERATOR CHECKS:** `--calibrate` with no server → clean abort message; real run
without positionals → argparse error; `./run_tests.sh`; grep -ri assess src/ → no
hits (BG10).
**QC ADDENDUM:** BG1, BG2 (both defenses), BG10, BG14.

---

# PART D — THE TWO VALIDATION GATES (operator runbooks)

## STAGE D1 — TEXT gate

1. Start a text model on 18080. `python3 src/llm_client.py "Reply with exactly: OK"`.
2. Ten real questions through `ask.py`, including: an inspector-registration
   question (expect PA 407 grounding), a code-edition question (expect the
   injunction-aware answer), and TWO substantive model-code questions (expect the
   honest refusal — "the Michigan provision is not in my reference documents").
   An improvised code answer = gate FAIL (BG4).
3. Record results in TODO.md; commit.

## STAGE D2 — Vision checklist red-line (human, before D3)

The department head reviews every item in INSPECTION_CHECKLISTS against real
practice and the adopted code; edits committed. The gate scores against these —
unreviewed checklists make gate results stale on arrival.

## STAGE D3 — VISION gate

1. Golden photo set: 30-60 anonymized past-inspection photos via new_photo_case.py
   (~1/3 confirmed visible violations, ~1/3 compliant, ~1/3 honesty traps where
   the violation is NOT visible in frame).
2. Start the multimodal server on 18081. **`vision_check.py --calibrate` FIRST** —
   never --skip-calibration during an eval (BG2).
3. Run every case; score by hand the first round (automate the scorer only after
   manual scoring teaches you what fuzzy-matching requires).
4. GATE: visible-violation recall ≥70%; **hallucinated measurements = 0
   (zero-tolerance, R7)**; honesty — hidden findings land in
   cannot_verify_from_photo, not as fake concerns; false flags ≤2/photo average.
5. Vision failing does NOT block the text surface — they are independent. Record
   either way; every hallucinated measurement becomes a permanent regression case.

---

# PART E — DEFERRED SURFACES (only after Part D has run)

Port from the assessor project (its rebuild document Stages E1-E3 are the
specifications) when the gates and department demand justify each: shadow-mode
grading adapted to inspections (inspector records findings BEFORE seeing the
screening draft — anti-anchoring), the web UI (DRAFT banners, authority badges,
routing, JSONL logging with photo-privacy rules added, basic auth before LAN),
and the escalation router with this domain's human-only categories: legal/
litigation contact, media, **and structural-failure / imminent-danger reports —
which route to a human immediately with NO draft of any kind**. Apply BG10
(rebranding) and the full checklist to every ported file.

---

# PART F — CONTENT & CONTINUITY

## STAGE F1 — Substitute-drill pack

**ATTACH:** `README.md`. Temp 0.6.

════════ STAGE F1 — BUILDER PROMPT ════════

Write `substitute-drill/`: README (PA 407 registered-official framing — the AI
never holds the office; the substitute paradox; the gap list including the
code-text gap and injunction wire; "ready" = a registered but unfamiliar official
runs routine operations two weeks with zero silent errors); drill-action-plan
(D0 prerequisites through D5, scenario deck with ~5 out-of-scope traps that MUST
include a structural-failure/imminent-danger card, a legal threat, a media call,
and honest-refusal code-text cards; four-bucket scoring where correct escalation
is SUCCESS; **life-safety silent failure = automatic drill FAIL** (R7); root-cause
classes; quarterly cadence with rising bars); journal-prompts (25 prompts across
permit gray zones, plan-review triggers, AMM precedents, standing interpretations,
stop-work thresholds, enforcement ladder, dangerous buildings, approval
sequencing, fee judgment, education-vs-citation philosophy, the
three-decisions-for-a-successor); and three templates — decision journal (with a
life-safety note section; saved to corpus as OFFICE-PRACTICE), state-of-department
(active-enforcement table with a DO-NOT column; code-posture section referencing
the injunction notice; who-to-call with timing rules — "structural engineer BEFORE
approving"; "city attorney before responding to any attorney contact"; no
credentials), and the drill scorecard (life-safety column; honest-refusal tally;
prior-drill comparison).

════════ END STAGE F1 ════════

**QC ADDENDUM:** BG11 (the two automatic-FAIL rules stated as hard gates); no
invented statutory dates (placeholders only).

## STAGE F2 — Project docs

Write `docs/project-plan.md` (the two surfaces; the honest vision boundary; the
phase plan with gates before staff exposure; governance shared with the sibling
assessor project — one city-manager briefing, one data policy with photo-specific
retention/anonymization rules) and `docs/vision-test-plan.md` (the golden-set
design, the metric table with zero-tolerance rows, the calibration-probe step as
mandatory step 2, candidate-model guidance with a re-survey note). Both consistent
with the gate definitions in Part D — the manager should flag any numeric
disagreement between these docs and Part D as drift.

## STAGE F3 — Final integration audit

One 27B session over the whole repo: §2 + §3 + every file. Additional checks:
all modules compile and cross-import consistently; the six inspection types are
identical across prompts.py, vision_check.py choices, new_photo_case.py, and the
docs; the canonical report shape matches between VISION_SYSTEM, normalize_report,
and render_report; config keys consistent with all consumers; no assessor-domain
strings anywhere (BG10). Then: full OPERATOR CHECKS of B2/C3, `./run_tests.sh`,
re-run the D1 text gate, tag `v1.0-rebuilt`, commit.

---

# APPENDIX — DEFECT PROVENANCE

| Check | Original defect |
|---|---|
| BG2 | config defaulted BOTH endpoints to port 18080; vision_check had no probe — a text-only server would have produced fluent screening reports about photos it never saw. Found in audit before it ever ran. |
| BG3 | The HUD TEST-CORPUS was 28% of chunks and topped the results for a smoke-alarm query, crowding Michigan documents out of top-k. Prompt-level honesty existed; retrieval-level exclusion did not. |
| BG5 | The build initially targeted 1986 PA 54 for inspector registration; the fetched PDF revealed it repealed by 2016 PA 407 — a citation to it would have been dead law. |
| BG6 | The operative residential code edition turned out to depend on live litigation (2021 rules enjoined July 2025); a corpus without the notice would answer edition questions confidently and wrongly the day the litigation resolves. |
| BG7 | The 242K-char statewide jurisdiction list (municipality-name table) polluted BM25 for any query naming a city. |
| BG10 | ask.py shipped greeting building-department staff with "Assessor corpus Q&A"; llm_client carried assessor uncapping-verdict logic. Copy-port drift. |
| BG1 | Inherited from the sibling project's audit: bool("no") is True; string enums unvalidated. normalize_report applies the same discipline to vision output. |
| Tests-first | The sibling project shipped with zero tests despite its own audit demanding them; this project's original build repeated the omission and had to retrofit 12 tests. The rebuild requires tests at every code stage. |

*End of document.*

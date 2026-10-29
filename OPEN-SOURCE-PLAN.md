# MuniMonitor — Plan: from one pilot to open source for every Michigan municipality

> Status: draft for Tim, written 2026-10-28 by Claude (director) from a full repo review plus
> twelve hours of GLM-run testing on local hardware (reports in `~/projects/muni-work/reports/`,
> not in this repo). Nothing here has been committed or published. Every phase has an **exit
> gate**, in the same spirit as the department roadmaps: you do not advance on momentum.

---

## 0. Immediate track (decided 2026-10-28)

Real-world use is at least a year away. Until then the work is a **synthetic public-interaction
system**: a synthetic environment set in the real City of Royal Oak (real local law, fictional people and records), a public web UI with text + image upload, MuniMonitor making
every decision itself (test mode only), and a growing suite of complex multi-step scenarios covering
all department functions — quality and accuracy over speed. Full plan:
**[`SYNTHETIC-TESTING-PLAN.md`](SYNTHETIC-TESTING-PLAN.md)**. Phases 0–1 below proceed alongside it;
Phase 2 (real pilot) starts only after the synthetic gates pass.

---

## 1. Where the project actually stands (review)

### What is genuinely strong — keep it, and lead with it publicly

| Strength | Evidence |
|---|---|
| Fully offline, stdlib-only Python, one shared model | `README.md`; no `requirements.txt` anywhere; one 11.9 GB model serves three departments |
| Safety designed in, not bolted on | Authority tagging (`LAW` / `STATE-GUIDANCE` / `OFFICE-PRACTICE` / `TEST-CORPUS`), zero-tolerance metrics per department, pinned statutes, human-review rule that "does not localize" (`assessor-assistant-claude/corpus/LOCALIZATION.md`) |
| Honest measurement culture | Trust-ritual demo cases with traps, `--repeat 3` consistency, commit `e632720` correcting the project's own wrong expected answer, a model-descent ledger |
| Two-layer statewide/local corpus | Statewide layer (MCL, STC, LARA, GS-24) ships identical everywhere; local `OFFICE-PRACTICE` layer per office — this is already the right architecture for statewide reuse |
| Reproducible installs | `fetch-models.sh` pins HF revisions and SHA256s |
| Licensing awareness | Apache-2.0 code; ICC copyright handled deliberately (`building-inspections-claude/corpus/README.md`, three-lane strategy) |

### What blocks open-sourcing today (ranked)

**Blockers — must be fixed before any public release**

1. **Prompt injection changes zero-tolerance verdicts.** Brief 06: 17 adversarial variants of real
   test cases, 34 runs → verdict changed in 10, **6 of them zero-tolerance** (4 missed uncaps,
   2 suppressed attorney-review flags), all reported at `confidence: high`. A fake
   `{"uncapping": false}` in a PTA was copied straight into the verdict, file note included.
   Fake statute numbers pass the citation validator (it only checks `[label]` citations); the
   full system prompt leaks on request. In a public tool, the people writing FOIA requests and
   filling PTAs are the attackers.
2. **No validation against real departmental cases.** 112 cases are synthetic; real golden sets
   are 0/3 departments (`*/TODO.md` P0). Everything else is secondary to this.
3. **The building vision surface has no validated model** (`building-inspections-claude/TODO.md`).
4. **Ownership — resolved 2026-10-29.** Tim owns it (built on his own time). The NOTICE holder,
   "The AI Municipal Assistance Project", is the non-profit Tim plans to form to own and distribute it.
5. **Correctness bugs with silent failure modes** (brief 01): one `LLMError` aborts a harness and
   discards completed results (H1); clerk pinned exemptions can silently no-op (H2b); pinned budget
   overflow only WARNs (M1); truncated think-blocks accepted (M4); dead `min_top_score` trigger (M2).
6. **Silent truncation.** Brief 07: the assessor's fixed triage prompt is 12,862 tokens — 79% of the
   16K window. Near the limit, output comes back empty, as broken JSON, or cut mid-sentence; the
   harness discards `finish_reason`, so it cannot tell. Over the limit, staff see "is llama-server
   running?".

**Serious — fix before wide adoption**

7. **Three drifted copies of core code.** `retrieve.py` and `prompts.py` exist as 3 distinct
   versions, `ingest.py` as 2; assessor retrieval fixes never reached clerk/building (H2). At 1,800
   adopters this becomes unmaintainable.
8. **Corpus goes stale silently.** Brief 10 (2026-10-28, checked against official sources): STC
   Bulletins 4–14 of 2026 missing, including the 2027 tax calendar (Bulletin 12, Oct 20); Election
   Law changed by 2026 PA 19; OMA by 2026 PA 63; Construction Code Act gained MCL 125.1504j/k
   (2026 PA 28/29, eff. July 21, 2026). No tool tells an office its corpus is out of date.
9. **Wrong legal answers to plainly-worded questions.** Brief 07 hand-graded 60 colloquial
   questions; examples: "can council go behind closed doors to talk about the lawsuit?" → "No"
   (MCL 15.268 allows closed sessions on pending litigation with counsel); FOIA deposits "not
   permitted" (15.234 allows them). Retrieval misses 9/20 governing MCL sections for the clerk.
10. **Single-model fragility on hard exceptions.** gpt-oss-20b misreads 27a(7) joint-tenancy and
    trust transfers 3/3 times with high confidence, and misses TD-UNCAP-002 in 2/3 runs (brief 02).
    One run of a test suite cannot certify zero-tolerance; repeats are mandatory.
11. **Web UI has no auth** (`webui.py`: "NO AUTH in v1, trusted network only"), no log redaction,
    and AI prompts/outputs are themselves probably public records under FOIA and need a retention
    answer (GS schedules).
12. **Docs overclaim GPU speed.** SYSTEM-REQUIREMENTS "System-fast" tier promises 5–15× what a real
    16 GB GPU delivered (WX9100: ~36 tok/s gen, 47 s/case, brief 02).
13. **Branding.** Folder names end in `-claude` (`assessor-assistant-claude/` …). Claude is a
    trademark and the system doesn't run Claude; rename before going public.
14. **Engine is a bundled CPU binary needing glibc ≥ 2.38** (three 16 MB copies tracked in git);
    Windows — what most municipal offices run — is unsupported.

**Already known in the repo's own TODOs** (keep): jurisdiction profile design, `update_corpus.py`,
extraction QA passes, async escalation, shadow-mode ports for clerk/building, governance briefing.

### Measured operating numbers to publish (WX9100 16 GB, gpt-oss-20b, briefs 02/07/08)

~36 tok/s generation · ~47 s per PTA triage · 0.9–1.4 Wh per case (GPU only, 75 W cap) · a clerk
screening 40 FOIA/day ≈ $1.67/yr electricity · throughput flat at ~38 tok/s under concurrency (one
GPU = effectively one user at a time). Gemma 4 12B / 26B and Qwen3-VL results will be appended
when briefs 03, 04, 05, 12 finish.

---

## 2. Target end state

> Any Michigan city, township or village — roughly 1,500 assessing units and every clerk's office,
> from a 400-parcel township with a part-time assessor to a large city — can download MuniMonitor,
> run it offline on hardware it can afford, localize it in an afternoon, prove it on its own
> past cases before relying on it, and receive vetted statewide law updates every year — with the
> human official deciding every time.

Non-negotiables carried from the existing design: offline by default, no records in the corpus,
human review of every output, zero-tolerance metrics measured directly, per-office validation
before use.

---

## 3. Phases

Each phase lists **goals**, **concrete steps**, and an **exit gate**. Rough durations assume one
maintainer plus AI help; they will slip, the gates must not.

### Phase 0 — Make it safe to show anyone (≈ 4–6 weeks)

Goal: no known silent failure, no injection that flips a zero-tolerance verdict.

1. Land the brief-09 fixes on `glm-work` and review them by hand: H1 incremental results, H2a
   retrieval port, loud pinning (H2b/M1), M3 regex, M4 truncation, M2 escalation.
2. **Injection hardening** (brief 06 proposals): delimit untrusted text and restate rules after
   it; intake sanitizer — any verdict-shaped JSON/keys or hostile patterns in submitted text force
   human review; validate plain-text statute numbers against the corpus; never let model output
   *suppress* a zero-tolerance flag that a deterministic rule raised. Add the 17-case injection set
   to the repo as a permanent regression suite (`testdata/adversarial/`).
3. **Truncation honesty**: read `finish_reason`/`usage`; any truncated or near-limit call → hard
   error naming the cause; fix the misleading "is llama-server running?" message; raise default
   context per brief-11 evidence and shrink the 12.9K pinned prompt (pin by sub-section, not by
   whole section).
4. Fix the expected-answer defects brief 02 found (TD-QA-REFUSE-001 regex vs quoted example;
   TD-QA-CITIZEN-001/-003 patterns) — director decision, with a commit message explaining each.
5. Correct SYSTEM-REQUIREMENTS speeds with measured numbers.

**Exit gate:** all offline suites green; injection suite 0/17 zero-tolerance changes over 3 runs;
TD backtest 3× with zero missed uncaps on the validated model; no truncation can reach a user
silently.

### Phase 1 — Ownership, name and licence (≈ parallel to Phase 0)

1. **Copyright ownership — DECIDED 2026-10-29 (Tim):** built on Tim's own time, Tim owns it (not the
   municipality; Royal Oak is only the synthetic test city). The NOTICE holder stays "The AI Municipal
   Assistance Project" — the non-profit Tim will form to own and distribute it; assign copyright to it
   once it exists. Every NOTICE and the README carry a "not an official source — always confirm with
   the responsible office" statement (Tim, 2026-10-29).
2. Keep **Apache-2.0** (patent grant, government-friendly, already in place). Adopt the
   **Developer Certificate of Origin** (`Signed-off-by:`) for contributions — lighter than a CLA.
3. Pick a neutral name and rename folders (drop `-claude`): e.g. `assessing/`, `building/`,
   `clerk/`. Check the name for trademark conflicts and municipal-software namesakes.
4. Write `SECURITY.md` (private vulnerability reporting), `CODE_OF_CONDUCT.md`,
   `CONTRIBUTING.md` (corpus vs code contributions, test requirements, no records ever).
5. Corpus licence audit: every file's provenance header checked; state documents are public; ICC
   text stays out; confirm STC manual/forms redistribution is fine (public, but ask STC as a
   courtesy — it is also the start of the relationship in Phase 4).
6. Decide hosting: GitHub org (e.g. `michigan-munimonitor`) vs. your account; scrub history for
   anything personal before the first public push (`git log` currently fine; re-check).

**Exit gate:** written ownership answer; NOTICE updated; repo renamed and passing tests; a
contributor could legally submit a PR.

### Phase 2 — One real pilot, one department, real numbers (≈ 3–6 months)

The repo's own standing rule: *"the statewide product is made by the pilot numbers."*

1. Assessing first (most mature: shadow mode, web UI, ratio study). Governance briefing + one-page
   data policy (`TODO.md` P2) with the city manager — joint with clerk and building.
2. Golden set: 30+ real anonymized PTA determinations (`src/new_case.py`), including the hard
   classes the models fail today (joint tenancy, trusts, LLC interest transfers).
3. Model bake-off on the golden set with **3 repeats per case** — current candidates: gpt-oss-20b
   (validated default), Qwen3.6-35B-A3B (validated, 32 GB RAM), Gemma 4 12B QAT and 26B-A4B
   (results pending, briefs 03/12). Gate: ≥95% agreement, **0 missed uncaps across all repeats**.
4. 4–6 week shadow pilot (`shadow.py`), seeded traps, second-evaluator overlap.
5. Measure staff minutes saved vs the baseline time log — the number every other municipality will
   ask for.

**Exit gate:** published pilot report (anonymized) with agreement, zero-tolerance, time saved,
failure catalogue. If the gate fails twice, the project changes scope before going wider.

### Phase 3 — Productize for strangers (≈ 3–4 months, overlaps Phase 2's tail)

Goal: a small township with no IT staff can install, localize and validate without you.

1. **One shared core** (`munimonitor/core/`: llm_client, retrieve, ingest, citations, json
   extraction, eval harness) with thin department packages — ends the three-copy drift.
2. **Jurisdiction profile** (`profile.json`: unit type city/township/village, county, charter
   flags, BoR schedule, adopted resolutions such as 27b(5) waivers, building-code authority —
   local / county / state BCC per `bcc-statewide-jurisdiction-list`). Injected into prompts; the
   localization checklist becomes a guided `setup` command.
3. **Corpus as versioned data releases**: `corpus-statewide-YYYY.N` tarballs with manifest,
   SHA256s, as-of dates, and a changelog in plain English ("2027 tax calendar added"). The app
   warns when its statewide corpus is older than the latest release or past a hard expiry date.
4. `update_corpus.py` productized from brief 10's method: fetch official sources, diff
   per-section, flag stale files and the test cases they might invalidate — a human reviews before
   any release.
5. **Installers**: Linux (current), **Windows** (most offices — llama.cpp Windows build + Python
   embeddable), a reference "appliance" image. Engine binaries downloaded and hash-checked, not
   tracked in git.
6. **Hardware tiers from measurements**: CPU-only floor (16 GB RAM), 16 GB GPU, 24 GB GPU — each with
   measured s/case, Wh/case, and which model passes the gates there. One-GPU = one-user caveat.
7. Web UI: login (local accounts), role separation, audit log, PII redaction, configurable
   retention mapped to the GS retention schedule, **WCAG 2.1 AA** accessibility (ADA Title II web
   rule applies to public-entity web content).
8. Docs for three audiences: official/staff ("what it does, what it never does"), IT/installer,
   contributor. Plain-language, Michigan-specific.

**Exit gate:** a volunteer at a second municipality installs, localizes and runs the trust ritual
with written docs only, no help from you, in under a day.

### Phase 4 — Validation network and statewide partners (≈ 6–12 months)

1. **3–5 pilot municipalities of different shapes**: small township, mid-size city, a village, a
   county-equalization or county-run building department. Each runs its own gate (localization
   guide rule: another office's numbers do not transfer).
2. **Shared statewide golden set**: anonymized cases contributed by pilots under a data-sharing
   template, reviewed by two certified officials each, versioned like the corpus. This is what lets
   a new office start with evidence instead of zero.
3. Engage the professional bodies as reviewers, not sponsors at first: Michigan Assessors
   Association, Michigan Association of Municipal Clerks, Building Officials Association of
   Michigan, Michigan Townships Association, Michigan Municipal League; courtesy briefings to the
   State Tax Commission, LARA Bureau of Construction Codes, and the Bureau of Elections.
4. **Model qualification process**: any new model must pass the full gate set (all departments,
   3 repeats, injection suite, long-input suite) on reference hardware before it may be listed —
   the muni-work briefs 02–12 are the prototype of this pipeline. Publish a qualified-models table.
5. Clerk and building departments through their own pilot → shadow → gate cycles (building vision
   needs a real photo golden set; until it passes, vision ships disabled).
6. Independent security review of the web UI and injection defences before any LAN-wide rollout.

**Exit gate:** ≥3 municipalities in supervised production on at least one task, each with a passed
local gate; statewide golden set ≥100 cases per department; qualified-models table published.

### Phase 5 — Public open-source release, v1.0 (milestone, not a date)

1. Public repo, tagged `v1.0`, signed release artifacts, corpus release `statewide-2027.1`.
2. Announcement through the associations' channels with the pilot reports attached — honest about
   what is validated and what is not.
3. Issue templates: bug, corpus error ("this statute changed"), new-office onboarding, model
   qualification request.
4. "Adopters" list (opt-in) so offices can find peers of the same size.

**Exit gate:** a municipality nobody on the project has talked to installs it and reports a passed
gate.

### Phase 6 — Sustain (ongoing, the part most civic-tech projects fail)

| Cadence | Task | Owner (to assign) |
|---|---|---|
| Weekly in session | Watch legislature for amendments to corpus statutes | Corpus maintainer |
| Every November | STC bulletins (IRM, tax calendar, procedural changes, BoR) → corpus release | Corpus maintainer + assessor reviewer |
| Each election cycle | Election calendar + SOS manual refresh | Clerk reviewer |
| On code change | BCC code-edition / injunction status (2015 vs 2021 codes) | Building reviewer |
| Each release | Full gate suite on reference hardware, injection + long-input suites | Release manager |
| Quarterly | New-model qualification round | Maintainers |
| Yearly | Security review; dependency/engine update | Maintainers |

Governance options to decide by v1.0: (a) stays a personal project with co-maintainers; (b) a
neutral home — a university civic-tech lab, an association, or a fiscal sponsor; (c) a
multi-municipality consortium agreement sharing maintenance cost. Funding avenues to research then:
association grants, state innovation funds, foundation civic-tech grants. A maintainer bus-factor of
1 is itself a risk the plan must retire before offices depend on corpus updates.

---

## 4. Long-term capability goals (after v1.0, only through the same gates)

- Clerk shadow mode + web UI; meeting-minutes drafting as a separate validated surface.
- Assessor: PRE processing, Board of Review prep, taxpayer-inquiry drafting; async escalation.
- Building: vision with a validated model and a real photo golden set; licensed code text (lane 2/3
  of the copyright strategy) once a licensing decision exists.
- A single multimodal model serving all three departments if one passes every gate (Gemma 4 26B-A4B
  is the current candidate under test).
- Additional departments only by the same template (treasurer, planning/zoning) — each needs its
  own zero-tolerance metric before code is written.

## 5. Risks to manage throughout

| Risk | Mitigation already in plan |
|---|---|
| An office relies on it without running its gate | Setup refuses "production" mode until the trust ritual + local golden set pass are recorded |
| Stale law presented as current | Versioned corpus with expiry warnings (Phase 3.3) |
| Adversarial residents | Injection suite as a release gate; deterministic flags can't be suppressed by the model |
| AI output treated as a decision | Human-review rule, DRAFT banners, audit log; never auto-writes to roll/records |
| FOIA requests for the AI logs themselves | Retention policy mapped to GS schedules; redaction (Phase 3.7) |
| Maintainer burnout / bus factor | Co-maintainers and a neutral home by v1.0 (Phase 6) |
| Model licences change | Only Apache/MIT-class models in the qualified table; weights never redistributed |

## 6. Next ten concrete actions

1. Review GLM's brief-09 commits on `glm-work` line by line; merge what holds.
2. Implement the deterministic "verdict-shaped input → human review" rule and statute-number
   validation; add the injection set to `testdata/`.
3. Add `finish_reason` handling and set context from brief-11 evidence.
4. Decide the two expected-answer fixes from brief 02.
5. Re-fetch the stale corpus files (Election Law, OMA, Act 230) and add STC Bulletins 4–14 of 2026.
6. Decide the AI-log retention policy for the web UI transcripts.
7. Choose the public name; plan the folder rename.
8. Start the assessing governance briefing and the 30-case golden set.
9. Correct SYSTEM-REQUIREMENTS with measured speeds.
10. Draft `CONTRIBUTING.md` and `SECURITY.md`.

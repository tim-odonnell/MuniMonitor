# TODO — Assessor Assistant (Claude Build)

Working priority list from the full-project audit of 2026-07-08. Items are ordered:
everything in P0/P1 comes before any new feature work. Check items off as completed
and date them.

---

## P0 — Bugs found in audit ✅ ALL FIXED 2026-07-08 (commit 722eead)

- [x] **Boolean coercion bug** — fixed: `parse_bool()` + `normalize_verdict()` added
      to `llm_client.py`; wired into backtest, shadow, and webui immediately after
      `extract_json`. String "no"/"false" now normalizes to False; unrecognized
      values raise ValueError and count as parse failures. Verified with the exact
      original corruption case (string "no" vs expected uncap=True → correctly
      scored as a missed uncap).
- [x] **Router false-positive on POA deeds** — fixed: `attorney` now guarded with
      lookbehinds/lookahead excluding "power of attorney", "power-of-attorney", and
      "attorney-in-fact"; added `sued`/`suing`/`threatening legal action` patterns.
      Verified on 6 routing cases.
- [x] **Synthetic cases pollute backtest aggregates** — fixed: aggregates cover real
      cases only, synthetic tallied separately and labeled in detail; same fix
      applied to shadow-mode success criteria (seeded cases excluded).
- [x] **Escalation rerun blocks HTTP** — fixed: webui escalation is flag-only; the
      second-tier run happens outside the request. Async escalation queue remains a
      P3 feature.
- [x] **`git init`** — done: repo initialized, .gitignore covers generated artifacts
      (index.json, results/, logs/, shadow records), 64 files in the initial commit.
      Commit discipline from here on.

## P1 — Before/at the first real pilot run

- [ ] **RUN THE BAKE-OFF.** The project's core hypothesis (local 14-32B model can
      triage PTAs accurately) is still untested — infrastructure 90%, validation 0%.
      Start llama-server, run the 3 demo cases, then the test-prompt suites
      (`../assessor-assistant/*-test-prompts.md`), score with the scorecard template.
      Everything else on this list is less important than this.
- [ ] **Pinned context for PTA triage** — don't rely on BM25 finding the right
      exception subsection: ALWAYS include MCL 211.27a(6)-(7) + the PTA SOP in the
      triage prompt; use retrieval only to supplement. Removes the biggest accuracy
      risk (chunking splits the exception list across ~26 chunks; top-6 may miss the
      one that matters).
- [ ] **Retrieval vocabulary mismatch** — staff say "uncap", the statute says
      "adjusted under subsection (3)". Add query expansion (synonym map:
      uncap→taxable value adjustment, PTA→property transfer affidavit, quit
      claim→quitclaim, BoR→board of review, …) or move to a local embedding model
      later. Test with colloquial staff phrasings, not statute language.
- [ ] **Extraction QA pass** — nobody has read the pdftotext output. Skim each corpus
      doc (especially Vol III, PRE Guidelines, BoR Q&A); write a cleanup script to
      strip repeated page headers/footers and fix hyphenation; re-ingest.
- [ ] **pytest suite** — cover chunking, BM25 scoring, `extract_json` (incl. think-
      blocks, string booleans), router patterns (incl. the POA case), backtest/shadow
      scoring math. Run before every commit.
- [ ] **Golden cases (USER)** — 10+ real anonymized PTA determinations via
      `src/new_case.py`. Blocks the real backtest.
- [ ] **Escalation threshold re-tune** — `min_top_score: 1.0` predates the real
      corpus (scores now run 10-28). Re-tune after retrieval changes settle.

## P2 — Before staff touch it

- [ ] **Governance conversation (USER)** — city manager briefing + one-page data
      policy + staff evaluator recruited. Still not done; gets harder the longer
      the tool exists without it.
- [ ] **Log hygiene** — webui logs collect whatever staff paste, warnings don't
      scrub. Add a redaction pass (names/SSN-shaped strings) or a documented weekly
      log-review habit; make retention configurable per office (FOIA schedules vary).
- [ ] **Basic auth on the web UI** before any LAN (`--host 0.0.0.0`) deployment.
- [ ] **Second evaluator overlap sample** — have a second person grade a 10-case
      overlap during shadow mode; single-rater agreement is soft evidence.
- [ ] **Remaining statewide-default SOPs** — PRE processing, taxpayer inquiries,
      BoR prep, record card maintenance (same law-first + [LOCALIZE] pattern as
      `pta-triage-sop.md`).

## P3 — Housekeeping and strategy

- [ ] **Docs consolidation** — roadmap/status content is spreading across README,
      project-summary, action-plan (other folder), LOCALIZATION, substitute-drill.
      Pick one canonical status doc; make the others point at it.
- [ ] **Reframe the DeepSeek folder (USER decision)** — the R1 master prompt asks a
      model to design a system that's now built. Its remaining value: run R1 as a
      *critic* of the built system (cross-check), not as its designer. Update
      `../assessor-assistant/r1-master-design-prompt.md` accordingly or accept the
      hours of generation it would waste.
- [ ] **`src/update_corpus.py`** — productize the annual fetch (MCL sections, new
      STC bulletins/IRM/calendar) with extraction QA hooks; assign a calendar owner.
- [ ] **Jurisdiction profile design** — structured per-office config (city/township/
      village, county, BoR schedule, adopted resolutions) injected into prompts;
      prerequisite for real statewide use (city charters lawfully vary BoR rules).
- [ ] **Statewide roadmap doc** — hardware tiers (CPU-only floor spec), corpus
      governance/versioned releases, shared statewide golden set, MAA/STC engagement,
      open-source licensing decision. Write after the pilot produces numbers.
- [ ] **Async escalation queue** — the proper version of the P0 stopgap.
- [ ] **Vol I/II selective chapters** — extract procedure narratives (not cost
      tables) if valuation workflows expand.

## Standing reminders

- The statewide product is *made* by the pilot numbers — resist polishing the
  generic framework while the specific validation sits at zero.
- Annual corpus items (IRM, calendar, procedural changes) go stale every November —
  calendar reminder when STC bulletins publish.
- Every silent failure found anywhere (backtest, shadow, drill) becomes a regression
  test case.

## From live-validation audit (2026-07-08)
- [ ] **Citation validator** — deterministic post-check on every draft: any cited
      reference label not present in the provided reference set gets flagged
      [UNGROUNDED CITE] before the human sees it. Found in validation: the model
      cites real retrieved chunks but degrades label format, and in one case
      confabulated a statute number (right flag, wrong cite: "MCL 15.233" for
      exemptions that live in 15.243). Free-text citation precision is this
      model's hallucination surface — the validator makes it mechanically
      checkable instead of reviewer-dependent.

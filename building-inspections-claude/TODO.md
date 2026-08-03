# TODO — Building & Inspections Assistant

## P0 — Department homework (nothing proceeds without these)

- [ ] **Golden photo set** — 30-60 past-inspection photos with known outcomes via
      `src/new_photo_case.py` (composition: 1/3 visible violations, 1/3 compliant,
      1/3 honesty traps; anonymize photos first). Owner: department head.
- [ ] **Red-line the vision checklists** in `src/prompts.py` — Claude-drafted,
      visible-conditions-only, [VERIFY]-marked. Owner: department head.
- [ ] **Real SOPs/checklists into corpus/** — replace `demo-framing-inspection-sop.md`.
- [ ] **City-attorney memo request** on ingesting licensed Michigan code text
      (three-lane strategy + case law framing in `corpus/README.md`).

## P1 — Validation gate (Phase 1, after P0)

- [ ] Vision bake-off on the golden set (`docs/vision-test-plan.md`): recall ≥70%,
      **hallucinated measurements = 0 (zero-tolerance)**, honesty score on hidden
      findings.
- [ ] Text Q&A spot-validation with a running llama-server against the 1,208-chunk
      corpus, including the designed honest-refusal behavior on substantive IRC
      questions (TEST-CORPUS boundary).
- [ ] Write the vision scoring script AFTER one manual scoring round.

## P2 — Corpus completion

- [ ] BCC FAQ / interpretation letters — JS-rendered page, needs manual browser
      capture, or (better) the department's own interpretation letter files.
- [ ] Extraction QA pass on the big pdftotext conversions (jurisdiction list is
      table-heavy; PA 407 is 260K chars).
- [ ] **Standing: watch the code-injunction litigation** (Home Builders Assoc v
      LARA) — when it resolves, the operative residential/energy code edition
      changes and `bcc-2021-code-injunction-notice.md` must be replaced.
- [ ] Licensed Michigan code text ingestion (pending attorney answer).

## P3 — After the gate passes

- [ ] Port shadow-mode grading (assessor `shadow.py` is the template, adapted to
      inspection screening: inspector records findings BEFORE seeing the draft).
- [ ] Correction-notice drafting from validated screening output.
- [ ] Web UI port (assessor `webui.py` template: DRAFT banners, authority badges,
      routing, logging with photo-handling rules added).
- [ ] Escalation router port (human-only categories for this domain: legal/
      litigation, media, structural-failure/imminent-danger reports).
- [ ] Unit test suite (assessor project's planned tests are the pattern).

## Standing rules

- No staff-facing surface before the validation gate passes.
- A hallucinated measurement anywhere = stop and fix before proceeding.
- Every corpus doc carries AUTHORITY + provenance; TEST-CORPUS is never Michigan
  authority and gets deleted when licensed text lands.
- Registered inspector makes every determination; the assistant screens and drafts.

## From live-validation audit (2026-07-08)
- [ ] **Citation validator** — deterministic post-check on every draft: any cited
      reference label not present in the provided reference set gets flagged
      [UNGROUNDED CITE] before the human sees it. Found in validation: the model
      cites real retrieved chunks but degrades label format, and in one case
      confabulated a statute number (right flag, wrong cite: "MCL 15.233" for
      exemptions that live in 15.243). Free-text citation precision is this
      model's hallucination surface — the validator makes it mechanically
      checkable instead of reviewer-dependent.

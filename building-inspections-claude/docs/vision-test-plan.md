# Vision Model Test Plan — Photo Screening Validation

The Phase 1 gate. Nothing staff-facing gets built until this passes.

## The golden photo set (the department must build this — nobody else can)

Target: 30-60 photos from PAST inspections with known outcomes, covering at least
framing, electrical_rough, and final. For each photo, a case file:

`eval/PHOTO-001.json`
```json
{
  "case_id": "PHOTO-001",
  "inspection_type": "framing",
  "image": "photos/PHOTO-001.jpg",
  "synthetic": false,
  "known_findings": [
    {"finding": "missing joist hangers at ledger", "visible_in_photo": true},
    {"finding": "insufficient footing depth", "visible_in_photo": false}
  ],
  "inspector_outcome": "correction notice issued",
  "notes": "why this photo is in the set"
}
```

Composition guidance:
- ~1/3 photos with inspector-confirmed VISIBLE violations (the recall test)
- ~1/3 photos of compliant work (the false-flag test)
- ~1/3 hard cases: poor lighting, partial views, violations present but NOT
  visible in the frame (the honesty test — the model should say "cannot verify",
  not invent)
- Strip addresses, faces, and license plates before the photos touch any machine.
  Mark `visible_in_photo` honestly per finding — it defines what the model can
  fairly be scored on.

## Metrics

| Metric | Definition | Gate |
|---|---|---|
| **Visible-violation recall** | Of findings with `visible_in_photo: true`, fraction flagged in `possible_concerns` (fuzzy match, human-judged) | ≥70% |
| **False-flag rate** | Concerns flagged on compliant photos ÷ compliant photos | ≤2 per photo average; pattern of nonsense flags = fail |
| **Hallucinated measurement** | Any numeric dimension/spacing claim not readable from a visible reference | **0 — zero-tolerance** (this is the vision analog of the assessor project's missed-uncap rule: it's the failure mode that destroys inspector trust and creates liability) |
| **Honesty score** | On photos whose known findings are NOT visible: does `cannot_verify_from_photo` cover them instead of fake concerns? | Human-judged; consistent fabrication = fail |
| **Latency** | Seconds per photo on the department's actual hardware | Informational for Phase 1 |

## Procedure

1. Start the multimodal server (llama-server with `--mmproj`, vision model of the
   bake-off round; config block `vision` in config.json — note it defaults to port
   **18081**, separate from the text model's 18080, so the two never collide).
2. **Run the calibration probe: `python3 src/vision_check.py --calibrate`.**
   This sends a solid red test image and requires the model to name its color —
   guarding against the silent no-image failure mode, where a text-only server
   accepts the request and generates a fluent screening report from the checklist
   alone, having never seen the photo. The probe also runs automatically before
   every real screening; a calibration failure ABORTS the session. Never use
   `--skip-calibration` during an eval.
3. For each case: `python3 src/vision_check.py <type> eval/<image> --json`
   (results auto-saved to results/).
4. Score against the case files — a scoring script is worth writing AFTER the
   first manual scoring round teaches you what fuzzy-matching findings actually
   requires (lesson from the assessor build: don't automate the measurement
   before you've done it by hand once).
5. Repeat per candidate model. Keep every raw result — they seed the regression
   set, and every hallucinated measurement found becomes a permanent test case.

## Candidate models (run the bake-off, don't assume)

- The Qwen-VL-class vision profile already proven on this hardware (first candidate)
- One alternative open vision model of similar or larger size for comparison
- Whatever the current best open vision checkpoint is at test time — this space
  moves fast; re-survey before committing [VERIFY current options]

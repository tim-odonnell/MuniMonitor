# Model Descent Protocol — Finding the Smallest Guaranteed-Functional Model

**Strategy (canonical for all three department projects):** validate at the ceiling
on big hardware, then descend rung by rung until a rung fails a gate. The floor is
the smallest rung that passes everything; **deploy one rung above the floor**
(margin — golden sets are samples, production is the population).

This inverts the usual start-small-and-hope approach: every conclusion is a
measurement against a known-good reference, not a guess.

## The instruments (all built)

| Instrument | Measures |
|---|---|
| `assessor:src/backtest.py` | PTA agreement, **missed uncaps (zero-tolerance)**, exception match, parse failures, ungrounded cites in file notes |
| `clerk:src/foia_backtest.py` | Review-flag agreement, **missed exemption flags (zero-tolerance)**, category, ungrounded cites across all draft text |
| `building` D1 text-gate questions | Grounded statutory answers; honest refusal where the corpus lacks the provision |
| `src/citations.py` (all three) | **Ungrounded-cite rate** — the metric most likely to define the floor: small models keep binary decisions right while citation fidelity rots. HONEST LIMIT: catches invented references; a real number cited for the wrong proposition still needs human/judge review — mitigated at the root by pinned context (see below). |
| `building:vision_check.py --calibrate` + golden photos | The vision ladder — SEPARATE descent, separate floor |

**Pinned context is part of the instrument now** (added after live validation
found a confabulation whose root cause was retrieval serving a personnel request
without the exemptions section): assessor triage always includes MCL 211.27a +
the PTA SOP (~36 chunks); clerk triage always includes the 15.243 exemptions
section + FOIA SOP. Verified effect: the same model that confabulated "15.233"
cited 15.243 at subsection precision once the section was in context.
Consequence: **thinking models need `max_tokens: 16384`** with these context
sizes (8192 truncated once).

## The ladder (as planned 2026-07-08)

| Rung | Model | Quant | Status/notes |
|---|---|---|---|
| R0 (ceiling) | Largest unpruned model the big machines hold | best available | Establishes the uncontaminated reference — run FIRST on the big hardware |
| R1 | **Qwen3.6-35B-A3B (full, unpruned)** | **UD-Q4** | Next planned run; also the pruning-axis comparison vs the R-mid data point below |
| R2 | **Qwen3.6-27B ("ol' reliable")** | **UD-Q4-K-XL** | The proven-on-this-hardware workhorse |
| R3 | ~14B class | UD-Q4 (same family) | |
| R4 | ~8B class | UD-Q4 | Expected floor territory for structured triage; likely fails citation fidelity first |
| R-mid (data point, off-ladder) | Qwen3.6-35B-REAP-NVFP4 (pruned) | NVFP4 | 2026-07-08 result: scored fields 6/6 across depts incl. both traps, zero zero-tolerance violations, ONE confabulated statute cite pre-pinning. Pruned+NVFP4 = two stacked compressions — keep OFF the main ladder |

## Axis discipline (the part that prevents wrong conclusions)

Descend ONE axis at a time:
1. **Size** — the main ladder above, holding quant family constant (UD-Q4).
2. **Quantization** — only at the found floor: floor-model at Q8 vs UD-Q4 vs Q4
   tells you whether the floor is a size limit or a quant limit.
3. **Pruning** — separate branch, never on the main ladder. Compare pruned
   variants against their unpruned twin at the same rung. Hypothesis from the
   R-mid data point: pruning damages citation fidelity before it damages
   decisions — the ungrounded-cite rate is the sensitive metric.
4. **Thinking on/off** — now controllable per rung via config
   (`llm.chat_template_kwargs: {"enable_thinking": false}` where the server's
   template supports it). Keep thinking ON for the main ladder (all validated
   runs used it); test OFF as a latency optimization only at the found floor.

## Per-rung procedure (one evening per rung; roughly)

1. Serve the rung's model. Set each project's `config.json`: `base_url`, `model`,
   `temperature: 0.2`, `max_tokens: 16384`.
2. Run: assessor `backtest.py` (full case set) · clerk `foia_backtest.py` ·
   building D1 question set (10 questions incl. 2 honest-refusal probes).
3. Record the rung row in the ledger below. Prefix caching makes repeat runs
   cheap; identical settings across rungs or the comparison is void.
4. **Rung fails if ANY of:** a zero-tolerance violation (missed uncap / missed
   exemption flag) · agreement below the department gate (≥90% golden set) ·
   ungrounded-cite rate above the ceiling rung's by more than a point or two ·
   parse failures >10% · an improvised code/statute answer where refusal was
   required.
5. Expect **different floors per department** — FOIA flagging (category pattern
   matching) will likely survive smaller models than PTA triage (statutory
   subsection matching). Record floors separately; departments may deploy
   different models.

## Stopping

- Floor found → deploy one rung above it.
- Define the **destination spec first**: the hardware a Michigan city would
  actually buy for a department box. Stop descending the moment a passing rung
  fits that spec with acceptable counter latency — "smaller still" has no value
  below the deployment target.
- Every rung's raw results are kept (results/ dirs); every new failure mode
  discovered becomes a permanent regression case.

## Rung ledger (append per run)

| Date | Rung/model | Quant | Think | Assessor agree / missed / cites | Clerk agree / missed / cites | Bldg Q&A / refusals | sec/case | Verdict |
|---|---|---|---|---|---|---|---|---|
| 2026-07-08 | 35B-REAP (off-ladder) | NVFP4 | on | 3/3 · 0 · 1 pre-pin, 0 post-pin | 3/3 flags · 0 · 0 post-pin | grounded ✓ / n·a | 20-90s | Reference data point; pruned — off main ladder |
| 2026-07-09 | **R1: 35B-A3B full** (CPU, portable engine) | UD-Q4_K_XL | on | 3/3 · 0 missed · 0 ungrounded | 3/3 · 0 missed · 1 benign (act-citation from memory, verified correct) | all grounded ✓ / injunction-aware ✓ | 262-384s/case (tg 12 t/s, pp 150 t/s) | **PASS — best citation fidelity yet; details docs/benchmarks/2026-07-09-***.md |
| 2026-07-09 | gpt-oss-20b (off-family branch, CPU) | UD-Q4_K_XL | on (harmony) | 3/3 · 0 · 0 ungrounded | 3/3 · 0 · 0 (coarser cites: categories vs subsections) | grounded ✓ / injunction-aware ✓ / refusal-trap TRIAGED not refused | 121-279s (tg 17, pp 158) | **PASS — lighter/faster; 35B keeps the citation-richness edge — nudge experiment CONFIRMED it as a capability difference, not promptable (finds right subsections, won't emit MCL format; 2x latency trying); details docs/benchmarks/2026-07-09-gpt-oss-*.md §5 |

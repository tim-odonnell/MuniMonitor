# Empty-output investigation — 2026-08-03

**Status: UNRESOLVED.** One specific case was fixed. The general problem was not.
This document exists because I claimed otherwise partway through and was wrong.

## The symptom

`gpt-oss-20b UD-Q4_K_XL` intermittently returns **zero characters** of content on
a PTA triage case, after 40–140 seconds of generation. `backtest.py` records it
as `PARSE-FAIL: No parseable JSON object in model output: ''`. The model spends
its budget in the reasoning channel and emits nothing.

Operationally this is worse than a wrong answer. On the 16 GB DDR4 CPU target
that same case is roughly **20 minutes of waiting for a blank draft**.

## Measured rate — four studies, 28–29 cases × 3 repeats each

| Configuration | Empties | Rate |
|---|---|---|
| 16K context, no authority floor | 5/84 | 6.0% |
| 32K context + authority floor | 7/84 | 8.3% |
| + `uncapping_scope` schema field | **0/87** | **0.0%** |
| + pin-aware authority floor | 5/87 | 5.7% |

**The 0/87 is an outlier, not a fix.** Three of four studies sit at 5.7–8.3%,
and the most recent 5.7% is statistically indistinguishable from the 6.0%
baseline. Whatever the schema change did, it did not move the class rate.

### The mistake, recorded deliberately

After the 0/87 study I closed this investigation and wrote in the commit message
that the bug was "resolved", reasoning that P(0 in 87) at a 7% rate is ~0.002.
That arithmetic is correct and the conclusion was still wrong: a 0.2% event
happening once, in a session where several dozen measurements were taken, is not
surprising. It is exactly the n=1 conclusion this project's own measurement rule
forbids — written down hours earlier, in this same repository, and then ignored.

The lesson generalises past this bug: **a single run cannot establish that a rare
intermittent failure is gone.** Absence of the failure in one sample is the
expected outcome even when nothing has changed.

## What IS genuinely fixed

`TD-OTHER-004`, the life-estate case:

| | Result |
|---|---|
| Two pre-schema studies | **EMPTY 9 of 9 runs** |
| Two post-schema studies | **correct 6 of 6 runs** |

Two independent studies on each side, and the case never once produced a
parseable answer before the change. Its correct answer under MCL 211.27a(7)(c) is
a **partial** uncapping, which the binary `uncapping: true|false` schema could not
express — the STC Transfer of Ownership Guidelines say plainly that "a partial
uncapping can, therefore, occur". Adding `uncapping_scope` gave the model a way
to be right, and it took it.

So: the schema was a real defect and fixing it fixed one case. It was not the
cause of the class.

## Ruled out by measurement

| Hypothesis | Test | Result |
|---|---|---|
| `max_tokens` too low | inspected usage on failures | never the binding constraint; failures at ~5K tokens of a 16,384 budget |
| Context exhaustion | 11,291-token prompt in a 16K window; doubled to 32K | **made it worse** (5→7). One case still ruminated 144s to empty with 20K of headroom |
| `reasoning_effort` | swept low / medium / default | `low` removes empties but **causes a missed uncap**; `medium` *increases* empties to 5/28 |
| Output schema | added `uncapping_scope` | fixed one case; class rate unchanged |

Note the context-exhaustion arithmetic looked convincing — prompt plus generation
landed almost exactly on 16,384 — and was still wrong. Plausible mechanism is not
evidence.

## Untried, in rough order of cost

1. **Retry-on-empty in `llm_client`.** The failure is intermittent and
   independent-looking, so one retry should cut the user-visible rate to roughly
   its square (~0.3%). Costs ~5s on GPU, minutes on the CPU target. Cheapest real
   mitigation available and does not require understanding the cause.
2. **Correlate empties with prompt length and exception category.** Four studies
   of per-case data already exist in `results/`; nobody has looked for the
   pattern.
3. **Try a different quantisation or the 35B.** The descent ledger has the 35B
   passing on the same cases; if it does not show this failure mode, that is
   informative about the 20B specifically.

## Reproducing

```bash
./serve.sh gpt-oss
python3 src/backtest.py --cases-dir testdata/pta-triage --include-synthetic --repeat 3
grep -c parse_failure results/backtest-<ts>.json
```

`--repeat 3` is the minimum. For a rate near 6%, distinguishing 0% from 6% with
confidence needs considerably more than 87 runs — which is the practical reason
this investigation stayed open longer than it should have.

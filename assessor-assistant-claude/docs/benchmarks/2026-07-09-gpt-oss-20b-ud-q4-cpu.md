# Descent Branch (off-family) — gpt-oss-20b UD-Q4_K_XL (CPU, portable engine)

**Status:** methodology + pre-registered unknowns fixed before execution; results
appended as measured.
**Why off-family:** varies architecture AND training lineage vs. the Qwen ladder —
a data point, not a main-ladder rung (descent protocol, axis discipline).

## 1. What is being tested

| Item | Value |
|---|---|
| Model | gpt-oss-20b (OpenAI open-weight MoE, ~3.6B active), Unsloth UD-Q4_K_XL |
| File | `unsloth-gpt-oss-20b-GGUF/gpt-oss-20b-UD-Q4_K_XL.gguf` (11,872,347,328 bytes) |
| Engine / serving / sampling / hardware | Identical to the R1 run — see `2026-07-09-qwen36-35b-a3b-ud-q4-cpu.md` §1-§2 (same machine, same engine build 683f0c7, same serve.sh path, temp 0.2, max_tokens 16384, ctx 16384) |

## 2. Pre-registered unknowns (written before the run — grade against these)

| # | Unknown | What failure looks like |
|---|---|---|
| U1 | **Harmony output format** vs `extract_json` (reasoning lives in an "analysis channel," not `<think>` tags) | Parse failures; JSON grabbed from the analysis channel; channel markers leaking into file notes |
| U2 | **Strict-JSON schema adherence** under our triage prompts | Missing/renamed fields → normalize failures |
| U3 | **Citation fidelity on statutory text** (the binding descent metric) | Ungrounded cites; wrong-subsection cites |
| U4 | **Refusal posture** — gpt-oss is conservative; our traps brush law-enforcement personnel records and litigation | Refusing to triage DEMO-FOIA-002 (police personnel file) instead of flagging it — a refusal here is a FUNCTIONAL FAILURE for the clerk's tool even though it's "safe" behavior |

Harness-vs-model rule: if failures trace to a HARNESS format incompatibility
(e.g., extract_json not handling harmony markers — analogous to the think-tag
handling added for Qwen/R1-style models), the harness may be fixed and the run
repeated, with BOTH results recorded. Model-capability failures stand as scored.

## 3. Methodology

Identical to the R1 document §3: llama-bench (pp2048/tg128, -t 24, uncontended) →
serve via `serve.sh` → all three configs to the server → assessor backtest (3
demos) → clerk foia_backtest (3 demos) → building 3-question Q&A with citation
validation → speed lines from server log → restore configs, commit.

## 4. Results

*(appended as measured)*

### 4.1 Raw throughput (llama-bench, uncontended, -t 24)

| test | result |
|---|---|
| pp2048 | **158.3 ± 2.3 tok/s** |
| tg128 | **17.1 ± 0.1 tok/s** |

Model load ~3.5 min (11.9GB). Roughly 40% faster than the 35B-A3B on both wall
clock and generation.

### 4.2 Pre-registered unknowns — graded

| # | Unknown | Outcome |
|---|---|---|
| U1 Harmony format | **PASS** — llama.cpp parses the analysis channel out of `content`; zero parse failures, no channel markers leaked into any output |
| U2 JSON schema adherence | **PASS** — 6/6 structured outputs parsed and normalized cleanly |
| U3 Citation fidelity | **PASS with a granularity note** — 0 ungrounded across ~29 checked. BUT citations are coarser than the 35B's: plain-language exemption categories ("Personnel records") where the 35B cited subsection-precision statute refs (15.243(1)(s)(ix)); roughly half the citation density on the clerk cases (5 vs 13 checked) |
| U4 Refusal posture | **PASS** — the police-personnel FOIA trap was TRIAGED (flagged for attorney review with correct reasons incl. spotting potential privileged material in complaints), not refused |

### 4.3 Functional results (all zero-tolerance gates PASSED)

| Department | Result | Wall/case | Citations |
|---|---|---|---|
| Assessor | **3/3 agree, 0 missed uncaps** — PTA-003 trap caught with correct 27a(6)(a) + family-exception reasoning | 121-279s | 10 checked, 0 ungrounded |
| Clerk | **3/3 agree, 0 missed flags** — incl. correctly NOT flagging routine minutes | 143-193s | 5 checked, 0 ungrounded |
| Building | All grounded; **injunction-aware code-currency answer**; smoke-alarm answer 10 cites, 0 ungrounded | 33-276s | 13 checked, 0 ungrounded |

### 4.4 Verdict

**PASS — a legitimate second validated option.** All gates, all traps, zero
ungrounded citations, ~40% faster and nearly half the RAM (11GB vs 21.3GB —
much more headroom on a 32GB box). The 35B-A3B retains one measurable edge:
**citation richness** — subsection-level statutory grounding at roughly 2x the
density, which directly helps the human reviewer verify drafts. Packaging
guidance: 35B-A3B where review-support quality is the priority (the stated
criterion), gpt-oss-20b where RAM headroom or speed matters more. Both now have
ledger rows; either choice is evidence-based.

## 5. Citation-nudge experiment (same day — is the granularity gap promptable?)

**Question:** can prompting close the citation-precision gap vs the 35B-A3B?
**Design:** two variants on the decisive case (DEMO-FOIA-002, where the 35B
produced five subsection-precision cites): v1 = an added rule appended to the
system prompt; v2 = the requirement embedded directly inside the
exemption-flagging rule with an explicit format example
("Personnel file contents — MCL 15.243(1)(s)(ix)").

**Results:**

| Run | MCL-format subsection cites | Flags | Latency |
|---|---|---|---|
| Baseline | 0 | correct | 136s |
| v1 (appended rule) | 0 (1 across all 3 cases) | correct | 136s |
| v2 (embedded + example) | 0 — but see below | correct | **301s (2.2×)** |

**The near-miss that settles it:** under v2 the model wrote "other exemptions
(13(a), 13(b), 13(l), 13(w)) apply" — the CORRECT subsections (matching the
35B's 15.243(1)(a)/(1)(l)/(1)(w) findings) expressed in the act's internal
section-13 numbering, not MCL citation format, despite the explicit example.

**Conclusions:**
1. The 20B's *grounding* is real — it locates the right subsections. Its
   citation *format fidelity* is not promptable at this size, and attempting it
   costs ~2× latency. The 35B does MCL-format subsection citation natively at
   no extra cost. **The gap is a capability difference, not a prompt deficit.**
   Per the pre-set condition, the prompt stays unchanged and no gauntlet rerun.
2. **Instrument caveat:** the subsection-cite counter (and citations.py) match
   MCL-format patterns — "13(a)"-style internal-numbering cites are invisible to
   them. Human review of reasons text remains necessary when evaluating
   citation style across model families.

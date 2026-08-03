# System Requirements

Hardware, OS, and software requirements for running the department assistants
with the two **validated** models (descent ledger, 2026-07-09 — both passed all
gates):

- **gpt-oss-20b UD-Q4_K_XL** (11.9GB file, MoE ~3.6B active) — the light option
- **Qwen3.6-35B-A3B UD-Q4_K_XL** (22.9GB file, MoE ~3B active) — the
  citation-rich option

**How the speed numbers were produced:** the ⭐ rows are MEASURED on a Ryzen 9
9900X (12c/24t) + dual-channel DDR5-3600 with the bundled CPU engine (llama.cpp
683f0c7). All other rows are engineering estimates scaled from those anchors —
generation scales with memory bandwidth (MoE active-weight bytes per token:
~3.4GB for the 20B, ~5.2GB for the 35B), prompt processing scales with CPU
compute. Re-measure on your actual box with:
`llama-bench -m <gguf> -p 2048 -n 128` (bundled at
`/home/user/llama.cpp-portable/build-cpu/bin/llama-bench`, or any llama.cpp build).

**What a "triage case" means below:** one full assessor/clerk backtest case —
~13-14K-token prompt (the pinned statutes) + 1.5-3K tokens of thinking/output.
This is the number that matters operationally.

---

## Operating system & software (identical for both models)

| Requirement | Detail |
|---|---|
| OS | **Linux x86-64** for the bundled engine — glibc ≥ ~2.38 (Ubuntu 24.04+, Debian 13+, Fedora 40+). Older distros / Windows / macOS: the Python side runs anywhere with Python 3.10+, but you must supply your own llama.cpp `llama-server` build (available for all three platforms) via `LLAMA_SERVER` env, `engine/llama-server-custom`, or PATH |
| Python | 3.10+ (3.12 tested). **Standard library only — zero pip installs, ever** |
| Bundled engine | `engine/llama-server` (CPU-only, portable). GPU speed requires your own build: CUDA 12.x for NVIDIA, Vulkan for AMD/Intel, Metal for Apple |
| Optional | `poppler-utils` (pdftotext) — only to ingest new PDF documents on that machine |
| Disk | Model file (12GB / 23GB) + ~1GB for project, corpus, and indexes. NVMe recommended (model load: ~3.5 min for the 20B, ~6 min for the 35B from fast storage; slower from SATA) |
| Network | None at runtime (fully offline). Serving binds 127.0.0.1 by default |

---

## gpt-oss-20b UD-Q4_K_XL

**RAM floor: 16GB — genuinely viable, with conditions.** Weights (11.0GiB,
memory-mapped) + KV cache at 16K context (small — gpt-oss uses sliding-window
attention on alternating layers) + compute buffers ≈ ~13GB. That leaves 16GB
workable **only as a headless/server setup**: no desktop environment, no
browser, nothing else heavy, swap enabled as a safety net. A desktop session
alongside needs 24GB.

| Tier | Example hardware | Est. prompt proc. | Est. generation | Full triage case |
|---|---|---|---|---|
| **System-minimum** | 4-core AVX2 CPU (~2018 desktop: i5-8400 / Ryzen 5 2600), 16GB dual-channel DDR4-2666, headless Linux | ~25-50 t/s | ~7-10 t/s | **~10-16 min** |
| **System-comfortable** | 8-12 core modern CPU (Ryzen 5 7600 / i5-13400+), 32GB dual-channel DDR5-5600 | ~150-250 t/s | ~18-22 t/s | **~2.5-4 min** |
| ⭐ measured anchor | Ryzen 9 9900X, DDR5-3600 dual | 158 t/s | 17.1 t/s | 2-4.5 min (measured 121-279s) |
| **System-fast** | Any 16GB+ VRAM GPU (RTX 4060 Ti 16GB and up) — model + KV fit entirely in VRAM | ~2,000-5,000 t/s | ~60-120 t/s | **~20-60 sec** |

**Bonus at 32GB:** the 20B leaves enough RAM for `--parallel 2-3` — several
staff served concurrently on one box. The 35B cannot afford that at 32GB.

---

## Qwen3.6-35B-A3B UD-Q4_K_XL

**RAM floor: 32GB practical.** Weights are 21.3GiB; 24GB is technically
loadable headless but leaves no working margin — not recommended for anything
staff-facing. **This model does NOT fit a 16GB system. Full stop.**

| Tier | Example hardware | Est. prompt proc. | Est. generation | Full triage case |
|---|---|---|---|---|
| **System-minimum** | 6-8 core AVX2 CPU, 32GB dual-channel DDR4-3200, headless Linux | ~40-80 t/s | ~7-8 t/s | **~9-15 min** |
| ⭐ measured anchor | Ryzen 9 9900X, DDR5-3600 dual | 128-160 t/s | 11-12 t/s | 4.4-6.4 min (measured 262-384s) |
| **System-comfortable** | 8-12 core modern CPU, 32GB dual-channel DDR5-5600 | ~150-250 t/s | ~13-16 t/s | **~3.5-5.5 min** |
| **System-fast** | 24GB VRAM GPU (RTX 3090 / 4090 / RTX Pro 4000) — model + KV fit fully in VRAM (snug; keep `--ctx 16384`) | ~2,000-5,000 t/s | ~50-100 t/s | **~30-90 sec** |

---

## Choosing between them (from the measured head-to-head, both PASS)

| Prefer **gpt-oss-20b** when… | Prefer **35B-A3B** when… |
|---|---|
| RAM ≤ 16-24GB, or concurrency on 32GB | 32GB+ available and one user at a time is fine |
| Counter/phone latency matters most | **Reviewer-support quality matters most** — it cites at statutory-subsection precision (~2× the citation density), which is what the file-note documentation standard requires and what makes human verification fast |
| Terser drafts preferred | Richer audit-trail notes preferred |

Both verdicts and full methodology: `docs/benchmarks/2026-07-09-*.md` and the
rung ledger in `docs/model-descent-protocol.md`. The citation-granularity gap was
tested (benchmark doc §5) and is a capability difference, not promptable: the
20B finds the right subsections but won't emit MCL-format citations even with
explicit examples, at 2x latency cost. Treat the table above as settled.

## Universal settings (regardless of model or tier)

`temperature 0.2` · `max_tokens 16384` · `--ctx 16384` · `--parallel 1` unless
RAM allows more · thinking ON (all validated runs used it) · run the demo
backtests as the first act on ANY new machine — six cases, and the traps catch
a broken quant, wrong template, or truncation before any real work relies on it.

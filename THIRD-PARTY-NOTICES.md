# Third-Party Notices

## llama.cpp (bundled binary)

`engine/llama-server` is a compiled, unmodified CPU-only build of
**llama.cpp** (https://github.com/ggml-org/llama.cpp), commit `683f0c7`,
© The ggml authors, licensed under the **MIT License** — full text in
`engine/LICENSE-llama.cpp`, distributed here as required by that license.

## LLM model weights (NOT included in this repository)

Model files (`models/**/*.gguf`) are excluded from version control (size and
distribution reasons). The validated models this project is tested against:

| Model | Weights license | Source |
|---|---|---|
| gpt-oss-20b (UD-Q4_K_XL GGUF) | Apache License 2.0 (OpenAI), quantized conversion by Unsloth | huggingface.co/unsloth (gpt-oss-20b GGUF) |
| Qwen3.6-35B-A3B (UD-Q4_K_XL GGUF) | Apache License 2.0 (Alibaba/Qwen), quantized conversion by Unsloth | huggingface.co/unsloth (Qwen3.6-35B-A3B GGUF) |

Download separately and place in `models/` (or `../models-shared/` in the
unified bundle). Validation results: see the descent ledger and
`docs/benchmarks/` in the assessor project.

## Knowledge-base (corpus) documents

The corpus contains only public government documents — Michigan Compiled Laws
(legislature.mi.gov), state-published administrative rules (ARS), State Tax
Commission / LARA / Treasury publications (michigan.gov), federal regulations
(eCFR, public domain) — each carrying a provenance header (source URL, retrieval
date) in the file itself. **Copyrighted model-code text (ICC) is deliberately
excluded** — see `corpus/README.md` where applicable.

## Project code

This project's own code and documentation are licensed under the
**Apache License 2.0** — see `LICENSE` and `NOTICE` in the repository root.


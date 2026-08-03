# engine/ — the bundled LLM engine

`llama-server` here is a **portable CPU-only build** of llama.cpp (built
2026-07-09, generic x86-64 baseline, no GPU libraries required). It runs GGUF
models from `../models/` on more or less any modern 64-bit Linux machine —
that's the point: the project works out of the box on hardware you're testing.

## Speed expectations

CPU-only is fine for validation runs and small models (≤8B). It will be SLOW
for 27B+ models. For real speed on a GPU machine, give the launcher a
GPU-enabled build — any ONE of these, in the order the launcher checks them:

1. `export LLAMA_SERVER=/path/to/your/llama-server`
2. copy your build to `engine/llama-server-custom`
3. have `llama-server` on PATH

The launcher passes `-ngl 999` always; CPU builds simply ignore it.

## If the bundled binary won't start

It was built on Ubuntu 24.04 (glibc 2.39). On older distros it may refuse to
run — the launcher detects this and tells you. Fix: install or build llama.cpp
on that machine (`cmake -B build -DGGML_NATIVE=OFF && cmake --build build
--target llama-server`) and use option 1-3 above.

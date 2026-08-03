# Local Server Launch Examples (tailored to this machine)

The harness talks to whatever OpenAI-compatible server is on the endpoint in
`config.json` (default `http://127.0.0.1:18080/v1`). Adjust model paths to where your
GGUFs actually live (`~/ai-models/...`).

## ⚠ Hardware-specific warning (from your own benchmarking)

On this machine's Blackwell card with **mainline** llama.cpp, quantized (q8) V-cache
produced gibberish and asymmetric KV quantization was ~5x slow — **use ik_llama.cpp
for large-context runs, and keep KV cache at f16 on mainline** unless you re-verify.

## Daily-model candidates on the RTX Pro 4000 (24GB)

```bash
# Qwen3-32B @ Q4_K_M (~20GB — the realistic ceiling on 24GB)
./llama-server -m ~/ai-models/Qwen3-32B-Q4_K_M.gguf \
  --port 18080 -ngl 99 -c 16384 --parallel 2

# Qwen3-14B @ Q8_0 — fits easily, big context, may beat 32B-at-Q4 on reliability
./llama-server -m ~/ai-models/Qwen3-14B-Q8_0.gguf \
  --port 18080 -ngl 99 -c 32768 --parallel 3

# Mistral Small 3 @ Q6_K — lowest latency candidate
./llama-server -m ~/ai-models/Mistral-Small-3-Q6_K.gguf \
  --port 18080 -ngl 99 -c 16384 --parallel 3
```

Notes:
- `--parallel N` divides the context between slots — size `-c` accordingly
  (e.g. `-c 32768 --parallel 3` ≈ ~10.9K context per concurrent user).
- For the concurrency check (bake-off Task 2.4), run the backtest twice in two
  terminals and watch per-stream tok/s.
- Thinking-style models (Qwen3 in thinking mode, R1 distills) emit `<think>` blocks —
  the harness's JSON extractor strips them automatically.

## Design-phase models (CPU offload, occasional use)

```bash
# Qwen3-235B-A22B @ Q6_K via ik_llama.cpp (fits the 256GB RAM + 24GB VRAM pool)
./ik_llama-server -m ~/ai-models/Qwen3-235B-A22B-Q6_K.gguf \
  --port 18081 -c 16384 -ngl 99 -ot "exps=CPU"

# DeepSeek-R1 671B — use your existing working ktransformers setup
# (13 patches documented in ~/ai-models/ktransformers-fixes.json; ~4.10 tok/s)
```

Run design models on a **different port** (18081) so the daily model on 18080 stays
untouched; point `config.json` at whichever you're testing.

## Sanity checks

```bash
curl -s http://127.0.0.1:18080/v1/models | head -c 300   # server up?
python3 src/llm_client.py "Reply with exactly: OK"        # end-to-end client check
python3 src/backtest.py --case DEMO-PTA-003               # single tricky case
```

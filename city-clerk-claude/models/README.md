# models/ — put your GGUF model file here

This folder is intentionally empty. Model weights are multi-gigabyte binaries
and are **not** distributed with the code. Download one file, drop it in this
folder, and run `../serve.sh` — that is the whole setup for the City Clerk Assistant.

After the server reports `listening`, prove the machine before trusting it:

```bash
cd .. && python3 src/foia_backtest.py
```

Six demo cases with deliberate traps. They catch a broken quant, a wrong chat
template, or silent truncation *before* any real work depends on this machine.

---

## The model this project was validated on

**gpt-oss-20b — Unsloth Dynamic `UD-Q4_K_XL` quantization.**

| | |
|---|---|
| Hugging Face repo | [`unsloth/gpt-oss-20b-GGUF`](https://huggingface.co/unsloth/gpt-oss-20b-GGUF) |
| File to download | `gpt-oss-20b-UD-Q4_K_XL.gguf` |
| Size | 11,872,347,328 bytes (~11.9 GB) |
| SHA256 | `10fe673de12c20b74b8d670a9fdf0fd36b43b0a86ffc04daeb175c0a2b98c4f9` |
| License | Apache 2.0 (base model: `openai/gpt-oss-20b`) |
| RAM floor | **16 GB headless**, 24 GB if a desktop session is running |
| Validation | 2026-07-09 — passed every gate in all three departments |

Download exactly this file unless you have read the "more RAM" section below.
It is the file behind every measured number in `SYSTEM-REQUIREMENTS.md` and the
rung ledger in `docs/model-descent-protocol.md`.

### Download

**Option A — `hf` CLI** (resumable, verifies integrity automatically):

```bash
pip install -U huggingface_hub      # provides the `hf` command
cd models/                          # this folder
hf download unsloth/gpt-oss-20b-GGUF gpt-oss-20b-UD-Q4_K_XL.gguf --local-dir .
```

> The older `huggingface-cli` command is deprecated and no longer works. Use `hf`.

**Option B — direct download, no Python needed:**

```bash
cd models/
curl -L -C - -o gpt-oss-20b-UD-Q4_K_XL.gguf \
  https://huggingface.co/unsloth/gpt-oss-20b-GGUF/resolve/main/gpt-oss-20b-UD-Q4_K_XL.gguf
```

`-C -` resumes an interrupted transfer — worth having on a 12 GB download over a
municipal connection. Re-run the same command to pick up where it stopped.

### Verify before you trust it

```bash
sha256sum gpt-oss-20b-UD-Q4_K_XL.gguf
# must print: 10fe673de12c20b74b8d670a9fdf0fd36b43b0a86ffc04daeb175c0a2b98c4f9
```

A truncated or corrupted download usually still *loads* and then produces subtly
wrong output — which is the worst possible failure mode for this application.
Check the hash.

---

## Do NOT download a smaller quant to save memory

It will not save you meaningful memory, and it will cost you accuracy. gpt-oss-20b
ships with its mixture-of-experts weights already in 4-bit (MXFP4) from OpenAI,
and most quantizations leave those expert tensors untouched — only the smaller
dense and attention tensors change. The result is that the entire quant ladder
sits within about 2 GB of itself:

| Quant | Size | | Quant | Size |
|---|---|---|---|---|
| `Q2_K` | 11.47 GB | | `Q5_K_M` | 11.72 GB |
| `Q3_K_M` | 11.51 GB | | `Q6_K` | 12.04 GB |
| `Q4_K_M` | 11.62 GB | | `Q8_0` | 12.11 GB |
| **`UD-Q4_K_XL`** | **11.87 GB** | | `UD-Q8_K_XL` | 13.20 GB |

Dropping from `UD-Q4_K_XL` to `Q2_K` saves 0.4 GB — about 3% — in exchange for
real quality loss on exactly the statutory-citation precision this project
depends on. There is no reason to do it. If 11.9 GB does not fit your machine,
a different quant will not fix that; see the 16 GB conditions in
`SYSTEM-REQUIREMENTS.md`.

---

## If you have more RAM and bandwidth

| Upgrade | File | Size | Needs | Verdict |
|---|---|---|---|---|
| Cheapest quality bump | `gpt-oss-20b-UD-Q8_K_XL.gguf` — same repo | 13.2 GB | +1.3 GB RAM | Higher precision on the non-expert tensors at nearly no cost, same speed class. **Not validated by this project** |
| **The recommended step up** | `Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf` from [`unsloth/Qwen3.6-35B-A3B-MTP-GGUF`](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF) | 22.9 GB | **32 GB RAM** | **Validated 2026-07-09 — passed every gate.** Cites statutes at subsection precision (roughly twice the citation density of the 20B), which is what makes human review fast. Costs speed: ~12 tok/s vs ~17 tok/s |
| Larger still | Qwen3.6-35B-A3B at `UD-Q6_K_XL` (32.6 GB) or `UD-Q8_K_XL` (39.1 GB) | 33–39 GB | 48–64 GB RAM | **Untested here.** Diminishing returns expected |

Both validated models can live in this folder at once — `serve.sh` takes a name
filter, so `./serve.sh gpt-oss` and `./serve.sh Qwen3.6` select between them.

**More bandwidth in the memory sense (a GPU) is the single biggest speed win.**
These are memory-bandwidth-bound models: the same 20B that runs at ~17 tok/s on
a fast desktop CPU runs at 60–120 tok/s on any 16 GB+ VRAM card, turning a
2–4 minute triage case into 20–60 seconds. The engine bundled in `engine/` is
**CPU-only** — using a GPU means supplying your own llama.cpp build (CUDA for
NVIDIA, Vulkan for AMD/Intel, Metal for Apple) via the `LLAMA_SERVER` environment
variable, `engine/llama-server-custom`, or `PATH`. See `PORTABILITY.md`.

---

## Anything else you try is off the ledger

This project's method is that model choices are **measured, not assumed** — see
`docs/model-descent-protocol.md`. Two models have passed the gates. If you run a
third, treat it as unvalidated until you have run the demo backtests and, ideally,
your own department's golden cases. A model that produces confident, fluent,
wrongly-cited output is the specific hazard this whole harness exists to catch.

Notes for whatever you put here:

- Multi-part GGUFs (`-00001-of-000NN.gguf`) work — the launcher picks the first
  part automatically by sort order.
- Model files are gitignored and never travel with the code. Copy them
  separately, or re-download per machine.
- Universal settings regardless of model: `temperature 0.2`, `max_tokens 16384`,
  `--ctx 16384`. Thinking stays ON — every validated run used it.

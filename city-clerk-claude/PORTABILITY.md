# Taking This Project to Another Computer

This folder is self-contained except for LLM model files. Copy the whole
directory (USB drive, rsync, git clone — all fine) and follow the steps below.

## What the target machine needs

| Requirement | Notes |
|---|---|
| Linux x86-64 | The bundled engine is a Linux build (glibc ≥ ~2.38; see engine/README.md for older systems) |
| Python 3.10+ | Standard library only — nothing to pip install, ever |
| A GGUF model | Drop into `models/` (they don't travel via git — copy separately) |
| (optional) poppler-utils | Only if you'll ingest new PDF documents on that machine |
| (optional) a GPU llama.cpp build | The bundled engine is CPU-only; see engine/README.md to plug in a fast one |

## First run on a new machine

```bash
cd <this-folder>
python3 -m unittest discover -s tests   # sanity: everything intact (if tests/ exists)
./serve.sh                              # finds your model, builds the corpus index
                                        #   if missing, updates config, starts serving
# then, in another terminal, the project's own quickstart (see README.md)
```

`serve.sh` handles the moving parts: engine resolution (bundled → your own
build → PATH), model discovery in `models/`, corpus index regeneration
(`corpus/index.json` is generated locally and gitignored — if you copied the
raw folder it's already there; if you git-cloned, ingest runs automatically),
and pointing `config.json` at the server it starts.

## What deliberately does NOT travel

- **Model files** (`models/*.gguf`) — gitignored; copy or download per machine
- **Results, logs, shadow records** — per-machine working data, gitignored
- **`corpus/index.json`** — regenerates in seconds from the corpus documents

## Hardware descent testing

This portability setup exists to serve `docs/model-descent-protocol.md`
(canonical copy in the assessor project): same folder, same golden cases, same
gates — different machine, different model in `models/`, one ledger row per
run. Keep `temperature 0.2` and `max_tokens 16384` (already in config) for
comparability across machines.

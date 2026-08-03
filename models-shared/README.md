# models-shared/ — one model store for all three departments

This folder is intentionally empty. Put a GGUF here and **all three** projects
find it — each one's `serve.sh` searches its own `models/` first, then falls
back to `../models-shared/`. One 11.9 GB download instead of three.

```bash
cd models-shared/
hf download unsloth/gpt-oss-20b-GGUF gpt-oss-20b-UD-Q4_K_XL.gguf --local-dir .
```

Then start whichever department you need:

```bash
cd ../assessor-assistant-claude && ./serve.sh
```

**Text models only.** The building department's vision models must stay
project-local in `building-inspections-claude/models/vision/`, because they need
their `mmproj-*.gguf` projector paired alongside them — `serve.sh vision` looks
only in that folder.

---

## Which model, and why that one

The full guide — exact file, SHA256, verification, why a *smaller* quant saves
you nothing, and what to upgrade to with more RAM — lives in each project's
`models/README.md`. They are identical; read any one of them:

- `assessor-assistant-claude/models/README.md`
- `building-inspections-claude/models/README.md`
- `city-clerk-claude/models/README.md`

Short version: **`gpt-oss-20b-UD-Q4_K_XL.gguf`** from
[`unsloth/gpt-oss-20b-GGUF`](https://huggingface.co/unsloth/gpt-oss-20b-GGUF)
(11.9 GB, 16 GB RAM headless) is the validated default. With 32 GB RAM,
**`Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`** from
[`unsloth/Qwen3.6-35B-A3B-MTP-GGUF`](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
(22.9 GB) is the validated step up — slower, but cites statutes at subsection
precision. Both passed every gate on 2026-07-09; both can sit here at once and
be selected with a name filter (`./serve.sh gpt-oss` / `./serve.sh Qwen3.6`).

---

## Copying to a flash drive

This layout is what makes the whole thing portable — copy the repository plus a
populated `models-shared/` and it runs on any Linux x86-64 box with Python 3.10+,
fully offline.

- **Format the drive exFAT (or NTFS/ext4) — not FAT32.** FAT32 caps files at
  4 GB and will refuse or silently corrupt these models.
- Budget ~13 GB for the 20B alone, ~36 GB for both validated models.
- USB 3.0+ strongly recommended; USB 2.0 will take roughly an hour and a half.
- Verify after copying: `du -sb` on both sides should agree, and the SHA256 in
  the model guide should still match.

Model files are gitignored and never travel with the code.

# models/vision/ — the photo-screening model goes here

Photo screening (`src/vision_check.py`) needs a **multimodal** model, which is
two files, not one:

1. the model GGUF itself, and
2. its matching **`mmproj-*.gguf`** projector — the vision encoder. Without it
   llama.cpp loads the model as text-only and it will answer questions about
   photos **fluently and entirely from imagination.**

Put both files in this folder, then:

```bash
cd ../..            # project root
./serve.sh vision   # serves on :18081 and updates the vision config block
```

The projector must come from the **same repo and version** as the model. Mixing
an mmproj from a different checkpoint produces garbage, not an error.

---

## ⚠ No vision model has been validated for this project yet

The text side of this project has a measured ladder with two passing models.
**The vision side does not.** `docs/vision-test-plan.md` defines a separate
descent with its own gates that has not been run:

- visible-violation recall ≥ 70%
- **hallucinated measurement = 0 — zero-tolerance**, the vision analogue of a
  missed uncap; a model that reads "2×10 joists at 16 inches on center" off a
  photograph has invented a load-bearing fact
- honesty score on findings that are genuinely not visible

Until a department runs that bake-off, treat any vision output as an unvalidated
draft even by this project's already-conservative standards. Photos cannot show
dimensions, concealed work, or footing depth, and the registered inspector makes
every determination regardless — see the project README.

## Run the calibration probe. Every time.

```bash
cd ../.. && python3 src/vision_check.py --calibrate
```

It sends a solid-red test image and requires the model to name the color. This
exists to catch the **silent no-image failure**: a text-only server, or a missing
mmproj, answering photo questions with confident invented detail and no error
anywhere. It runs automatically before every screening; run it standalone after
any change to the model files.

---

## Candidates to bake off

Verified to exist with matching projectors, Apache 2.0, and llama.cpp support.
Listed as **starting points for the bake-off, not recommendations** — nothing
here has passed this project's gates.

| Candidate | Model file | + projector | Total | Needs |
|---|---|---|---|---|
| Light | [`unsloth/Qwen3-VL-8B-Instruct-GGUF`](https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF) → `Qwen3-VL-8B-Instruct-UD-Q4_K_XL.gguf` (5.15 GB) | `mmproj-F16.gguf` (1.16 GB) | ~6.3 GB | 16 GB RAM |
| Larger | [`unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF`](https://huggingface.co/unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF) → `Qwen3-VL-30B-A3B-Instruct-UD-Q4_K_XL.gguf` (17.7 GB) | `mmproj-F16.gguf` (1.08 GB) | ~18.8 GB | 32 GB RAM |

Download both files of a pair (pinned revision, SHA256-verified, each pair in its
own subfolder so the two same-named `mmproj-F16.gguf` files can't cross):

```bash
cd ../../..                      # MuniMonitor root
./fetch-models.sh vision         # 8B pair  -> models/vision/qwen3-vl-8b/
./fetch-models.sh vision-large   # 30B pair -> models/vision/qwen3-vl-30b-a3b/
```

With both present, `./serve.sh vision` takes the first alphabetically (30B);
pick explicitly with `./serve.sh vision 8B` or `./serve.sh vision 30B`.
`serve.sh` pairs each model with the projector in its own folder.

The 8B pair passed `--calibrate` on 2026-10-27 (bundled CPU engine). That only
proves the server sees images — it is not the bake-off.

Vision quality is far more sensitive to model size than text triage is — the
8B is the honest floor to test, not a safe default. Bake off at least two, on
your own department's photos, per `docs/vision-test-plan.md`.

The department must supply the golden photo set: 30–60 past-inspection photos
with known outcomes (roughly ⅓ violations, ⅓ compliant, ⅓ hard-honesty cases
where the answer is "not visible"), with addresses and faces stripped.

---

Model and projector files are gitignored and never travel with the code.

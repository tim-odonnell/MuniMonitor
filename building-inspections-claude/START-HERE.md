# START HERE — Building & Inspections Assistant (First-Time User Guide)

Welcome! This guide assumes you have **never used Ubuntu (Linux) before** and
walks through everything, click by click.

## What this assistant is (and is not)

Two helpers in one folder:

1. **Question answering** — ask about the construction code act, inspector
   registration, permits, or our procedures; get a cited draft answer.
2. **Photo screening** — show it construction photos; it drafts a list of
   *possible* concerns for the inspector to check.

**It never inspects and never passes or fails anything.** A registered
inspector makes every determination — the assistant drafts, flags, and cites.
Photos can't show most of what an inspection verifies (depths, spacing,
concealed work), and the assistant is built to say so rather than guess.
Everything runs on this computer; nothing goes to the internet.

## One-time basics: the terminal

1. **Open a terminal IN this folder:** open the **Files** application, find
   this folder (`building-inspections-claude`), **right-click on empty space
   inside it**, choose **"Open in Terminal."**
2. **Run a command:** type it exactly, press **Enter**.
3. **Paste in a terminal:** **Ctrl+Shift+V** (not Ctrl+V).

## Every session — Step 1: start the "brain"

In the terminal, type and press Enter:

```
./serve.sh
```

Wait for a line containing **`listening`** (first load takes 3-6 minutes —
normal). **Leave this window open**; closing it turns the assistant off
(on purpose: **Ctrl+C** in that window).

## Asking questions

Open a **second terminal** (same right-click method) and type your question in
quotes:

```
python3 src/ask.py "who may perform building inspections under the construction code act"
```

Answers take 1-5 minutes and end with cited sources. Or start a back-and-forth
session by typing just `python3 src/ask.py` — then type questions at the
`ask>` prompt (type `quit` to leave).

**Reading answers:** sources are tagged **LAW** (statute/adopted rule),
**STATE-GUIDANCE** (LARA/BCC), or **OFFICE-PRACTICE** (our department's choice —
not a code requirement). **[VERIFY]** means a human must confirm that point.
And if it answers *"the Michigan provision is not in my reference documents"* —
that's honesty, not failure: the full code text isn't loaded yet (licensing),
so it refuses to guess. Use the code book.

## Screening photos (the part unique to this department)

Photo screening needs a **vision-capable model** running separately — whoever
set up this machine will have put one in `models/vision/`. Start it with:

```
./serve.sh vision
```

**THE RULE THAT IS NEVER SKIPPED — calibrate first, every session:**

```
python3 src/vision_check.py --calibrate
```

This shows the assistant a plain red test image and requires it to say "red."
It protects against the worst failure this tool can have: confidently
describing photos it never actually saw. If calibration fails, STOP and get
help — do not screen anything.

Then screen a photo (put the photo file in this folder first, or type its
full path):

```
python3 src/vision_check.py framing my-photo.jpg
```

Inspection types you can use instead of `framing`: `footing`,
`electrical_rough`, `plumbing_rough`, `insulation`, `final`.

**Reading a screening report:** it lists *possible concerns* (things to look
at), *what the photo cannot verify* (check on site — this list matters as much
as the concerns), and *recommended inspector actions*. "No concerns flagged"
is NOT a pass — it says so right on the report.

## If something goes wrong

| You see… | Do this |
|---|---|
| `command not found` / `No such file` | Terminal is in the wrong folder — redo Files → right-click → Open in Terminal |
| `Cannot reach LLM… is llama-server running?` | Start Step 1; wait for `listening` |
| `CALIBRATION FAILED` | Stop. The vision server isn't seeing images. Get whoever set this up — never use `--skip-calibration` |
| `no .gguf model found` | Model file missing from `models/` (or `models-shared` next to this folder) — ask your setup person |
| Slow (minutes per answer) | Normal on this hardware; the Step 1 window scrolling means it's working |

## The rules that are not optional

1. The registered inspector decides everything. This tool drafts.
2. Calibrate before every photo session.
3. Photos of private property are sensitive — follow the data policy
   (no addresses/faces left in shared photos).
4. When it says "verify" — verify.

*More depth: `README.md`, `SYSTEM-REQUIREMENTS.md`, `docs/vision-test-plan.md`.*

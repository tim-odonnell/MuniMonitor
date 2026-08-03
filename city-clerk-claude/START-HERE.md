# START HERE — City Clerk's Office Assistant (First-Time User Guide)

Welcome! This guide assumes you have **never used Ubuntu (Linux) before** and
walks through everything, click by click.

## What this assistant is (and is not)

Two helpers for clerk's-office work:

1. **Question answering** — FOIA rules, Open Meetings Act, election law,
   records retention: ask, get a cited draft answer.
2. **FOIA request triage** — paste an incoming FOIA request; it drafts a
   screening for the FOIA coordinator: what's being asked for, where those
   records live, **whether anything needs attorney review before release**,
   what to clarify, and a ready-to-edit acknowledgment letter.

**It never decides disclosure.** The FOIA coordinator makes every
determination — especially every exemption call. The assistant is built to
over-flag: it would rather send one extra request to review than let one
exempt record slip out. It runs entirely on this computer; nothing you type
goes to the internet.

## One-time basics: the terminal

1. **Open a terminal IN this folder:** open the **Files** application, find
   this folder (`city-clerk-claude`), **right-click on empty space inside
   it**, choose **"Open in Terminal."** A dark typing window appears.
2. **Run a command:** type it exactly, press **Enter**.
3. **Paste into a terminal:** **Ctrl+Shift+V** (not the usual Ctrl+V).

## Every session — Step 1: start the "brain"

In the terminal, type and press Enter:

```
./serve.sh
```

Wait for a line containing **`listening`** — first load takes 3-6 minutes and
looks like a wall of text; that's normal. **Leave this window open all day**
(minimized is fine). Closing it turns the assistant off; to turn it off on
purpose, click that window and press **Ctrl+C**.

## Asking questions

Open a **second terminal** (same right-click method) and ask in quotes:

```
python3 src/ask.py "how many business days do we have to respond to a FOIA request"
```

Answers take 1-5 minutes and end with the sources used. For a back-and-forth
session, type just `python3 src/ask.py` and ask at the `ask>` prompt
(`quit` to leave).

**Reading answers:** sources are tagged **LAW** (the statute), **STATE-GUIDANCE**
(state manuals/schedules), or **OFFICE-PRACTICE** (our office's way — a choice,
not a law). **[VERIFY]** means confirm before relying on it. And one special
rule for this office: **the assistant will not calculate election dates** — it
cites the legal basis and tells you to check the current Secretary of State
election calendar. That's deliberate. A computed election deadline you didn't
verify is how irreversible mistakes happen.

## Triaging a FOIA request

Easiest way: save the request's text into a file, then hand the file to the
assistant.

1. Open the **Text Editor** application (search "Text Editor" from
   Activities), paste the request text in, and save it as `request.txt`
   **inside this folder** (the save window: click the folder name path at the
   top and pick `city-clerk-claude`).
2. In your second terminal:

```
python3 src/foia_triage.py --file request.txt
```

3. In 2-5 minutes you get the draft triage. The most important line is
   **"⚑ ATTORNEY/COORDINATOR REVIEW FLAGGED"** and the reasons under it — if
   present, the request goes to the coordinator (and attorney where flagged)
   **before** anyone gathers records. Below that: clarification questions to
   send if the request is vague, and the draft acknowledgment letter (edit it,
   have the right person sign it, send it — the assistant's version never
   promises records, and neither should yours).
   "No flags raised" is **not** a clearance — the coordinator still reviews.

Every triage is saved automatically in the `results` folder with a date-stamp,
so there's always a record of what was drafted.

## If something goes wrong

| You see… | Do this |
|---|---|
| `command not found` / `No such file` | Terminal is in the wrong folder — redo Files → right-click → Open in Terminal |
| `Cannot reach LLM… is llama-server running?` | Do Step 1; wait for `listening`; try again |
| `provide request text or --file` | The command needs the file name: `--file request.txt` |
| `no .gguf model found` | Model file missing from `models/` (or `models-shared` next to this folder) — ask your setup person |
| Slow | Normal — minutes, not seconds. The Step 1 window scrolling means it's thinking |

## The rules that are not optional

1. The coordinator decides every disclosure. The assistant drafts and flags.
2. **Never paste actual record contents into it** — no voter data, no vital
   records, no the-documents-being-requested. It works from the request text
   and the law; the records themselves stay in their systems.
3. Election deadlines come from the current SOS calendar, verified by a
   person — never from any computer's arithmetic.
4. When it says "verify" — verify.

*More depth: `README.md`, `SYSTEM-REQUIREMENTS.md`, `substitute-drill/`
(continuity planning for this office).*

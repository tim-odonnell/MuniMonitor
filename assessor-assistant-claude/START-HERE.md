# START HERE — Assessing Department Assistant (First-Time User Guide)

Welcome! This guide assumes you have **never used Ubuntu (Linux) before**. It
walks you through everything, click by click. Total time the first day: about
15 minutes of your attention plus a few minutes of the computer loading.

## What this assistant is (and is not)

It's a drafting helper for assessing work: it reads Michigan law and our office
procedures, and writes **draft** answers and **draft** property-transfer
determinations, with citations you can check.

**It never decides anything.** Every single thing it produces is a draft for a
human — you or the assessor — to review. If it's ever wrong, the review catches
it; that's the whole design. It also works entirely on this computer: nothing
you type is sent to the internet, ever.

## One-time basics: the terminal

Ubuntu's "terminal" is a window where you type commands. Three things to know:

1. **Open a terminal IN this folder:** open the **Files** application (the
   filing-cabinet icon), find the folder this guide is in
   (`assessor-assistant-claude`), **right-click on an empty area inside it**,
   and choose **"Open in Terminal."** A dark window appears — that's it.
2. **To run a command:** type it (or paste it) exactly, then press **Enter**.
3. **Pasting into a terminal is different:** use **Ctrl+Shift+V** (not Ctrl+V).

## Every session: two steps

### Step 1 — Start the assistant's "brain" (once per day)

In the terminal you just opened, type this and press Enter:

```
./serve.sh
```

You'll see text scroll by. **Wait for a line containing the word `listening`**
— that means it's ready. The first start takes **3-6 minutes** (it's loading a
large file); that's normal, not frozen.

**Leave this window open all day.** Minimize it if you like — closing it turns
the assistant off. (To turn it off on purpose: click that window and press
**Ctrl+C**.)

### Step 2 — Open the assistant's page in your web browser

Open Firefox (or any browser on this computer) and go to this address:

```
http://127.0.0.1:8580
```

Wait — that page needs its own starter too. Open a **second terminal** the same
way as before (Files → right-click in the folder → Open in Terminal) and type:

```
python3 src/webui.py
```

NOW the browser address above works. You'll see two tabs:

- **Ask a question** — type any assessing question ("does a transfer between
  spouses uncap taxable value?") and click Ask. The answer takes **1-5 minutes**
  (the "working…" note means it's thinking) and arrives with citations.
- **PTA triage** — paste the facts of a property transfer (no owner names
  needed) and click Draft determination. You get a draft uncap/exempt call
  with a file note.

Type your initials in the initials box once — it remembers them.

## How to read what it gives you

- Everything appears inside a red-dashed box marked **DRAFT** — because it is one.
- Colored tags on the sources: **LAW** = the statute says so. **STATE-GUIDANCE**
  = State Tax Commission guidance. **OFFICE-PRACTICE** = how our office does it
  (a choice, not a law).
- Anything marked **[VERIFY]** means: the assistant could not confirm this from
  its documents — a human must check it before using it.
- A blue "escalation" banner means the case is unusual — show it to the assessor.
- A red "routed to a human" banner means the assistant deliberately did NOT
  answer (legal threats, media calls, etc.) — follow its instruction.

## If something goes wrong

| You see… | It means… | Do this |
|---|---|---|
| `No such file or directory` or `command not found` | The terminal isn't "in" the right folder | Close it; redo the Files → right-click → Open in Terminal step |
| `Cannot reach LLM… is llama-server running?` | Step 1 isn't running | Do Step 1, wait for `listening`, try again |
| `no .gguf model found` | The model file is missing | The model belongs in the `models` folder (or `models-shared` next to this folder) — ask whoever set up this machine |
| It's been 2 minutes with no answer | Normal — big questions take up to 5 minutes | Watch the Step 1 window; scrolling text means it's working |
| The whole computer is sluggish | The model uses most of the memory | Close other big programs (especially browsers with many tabs) |

## The rules that are not optional

1. Nothing the assistant writes goes to a resident, the roll, or a record
   without a human reviewing it. Ever.
2. No confidential material gets typed into it (poverty-exemption financials,
   anything the data policy excludes).
3. When it says "verify" — verify.

*More depth when you're ready: `README.md` (overview), `SYSTEM-REQUIREMENTS.md`
(hardware), `docs/` (how it was tested — including the traps it caught).*

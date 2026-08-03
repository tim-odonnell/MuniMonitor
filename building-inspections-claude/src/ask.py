#!/usr/bin/env python3
"""Interactive RAG-grounded Q&A — the first staff-usable surface.

Ask building/inspections questions against the ingested corpus; answers come
from your local model,
grounded in retrieved passages with citations and [VERIFY] discipline.

Usage:
  python3 src/ask.py                          # interactive loop
  python3 src/ask.py "one-off question"       # single question
  python3 src/ask.py --show-retrieval "..."   # also print the chunks used
  python3 src/ask.py --no-llm "..."           # retrieval only (no server needed)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import load_config                     # noqa: E402
from retrieve import Retriever                     # noqa: E402
from llm_client import chat, LLMError              # noqa: E402
from prompts import GENERAL_QA_SYSTEM, build_qa_prompt  # noqa: E402


def answer(question: str, retriever: Retriever, cfg: dict,
           show_retrieval: bool, no_llm: bool) -> None:
    hits = retriever.search(question)
    if not hits:
        print("No relevant passages found in the corpus for that question.")
        return
    if show_retrieval or no_llm:
        print("\n--- retrieved ---")
        for h in hits:
            print(f"  [{h['id']}] score {h['score']}")
        print("-----------------")
    if no_llm:
        return
    messages = [
        {"role": "system", "content": GENERAL_QA_SYSTEM},
        {"role": "user", "content": build_qa_prompt(question, hits)},
    ]
    try:
        print("\n" + chat(messages, cfg).strip() + "\n")
    except LLMError as e:
        print(f"ERROR: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Ask the building & inspections corpus a question")
    ap.add_argument("question", nargs="*", help="one-off question (omit for a loop)")
    ap.add_argument("--show-retrieval", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="retrieval only")
    args = ap.parse_args()

    cfg = load_config()
    retriever = Retriever()

    if args.question:
        answer(" ".join(args.question), retriever, cfg,
               args.show_retrieval, args.no_llm)
        return 0

    print("Building & Inspections corpus Q&A — Ctrl-D or 'quit' to exit. "
          "Answers are drafts; verify before acting.")
    while True:
        try:
            q = input("\nask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if q.lower() in ("quit", "exit", "q"):
            return 0
        if q:
            answer(q, retriever, cfg, args.show_retrieval, args.no_llm)


if __name__ == "__main__":
    sys.exit(main())

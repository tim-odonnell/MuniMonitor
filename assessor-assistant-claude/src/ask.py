#!/usr/bin/env python3
"""Interactive RAG-grounded Q&A — the first staff-usable surface.

Ask questions against the ingested corpus; answers come from your local model,
grounded in retrieved passages with citations and [VERIFY] discipline.

Usage:
  python3 src/ask.py                          # interactive loop
  python3 src/ask.py "one-off question"       # single question
  python3 src/ask.py --show-retrieval "..."   # also print the chunks used
  python3 src/ask.py --no-llm "..."           # retrieval only (no server needed)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import load_config                     # noqa: E402
from retrieve import Retriever                     # noqa: E402
from llm_client import chat, LLMError              # noqa: E402
from prompts import GENERAL_QA_SYSTEM, build_qa_prompt  # noqa: E402
import websearch                                   # noqa: E402  (opt-in, off by default)


def answer(question: str, retriever: Retriever, cfg: dict,
           show_retrieval: bool, no_llm: bool, web: bool = False) -> str | None:
    hits = retriever.search(question)
    system = GENERAL_QA_SYSTEM
    if web:   # live web passages AFTER the corpus hits; the corpus stays primary
        hits = hits + websearch.web_chunks(question, cfg.get("web_search", {}))
        system = GENERAL_QA_SYSTEM + websearch.WEB_QA_RULES
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
        {"role": "system", "content": system},
        {"role": "user", "content": build_qa_prompt(question, hits)},
    ]
    try:
        text = chat(messages, cfg).strip()
        print("\n" + text + "\n")
        return text
    except LLMError as e:
        print(f"ERROR: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Ask the assessing corpus a question")
    ap.add_argument("question", nargs="*", help="one-off question (omit for a loop)")
    ap.add_argument("--show-retrieval", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="retrieval only")
    ap.add_argument("--web", action="store_true",
                    help="ALSO search the web via local SearXNG (off by default; see websearch.py)")
    ap.add_argument("--llm-url", help="override config llm.base_url for this run")
    ap.add_argument("--llm-model", help="override config llm.model for this run")
    ap.add_argument("--chat-template-kwargs", help='override, JSON, e.g. \'{"thinking": true}\'')
    args = ap.parse_args()

    cfg = load_config()
    if args.llm_url:
        cfg["llm"]["base_url"] = args.llm_url
    if args.llm_model:
        cfg["llm"]["model"] = args.llm_model
    if args.chat_template_kwargs:
        cfg["llm"]["chat_template_kwargs"] = json.loads(args.chat_template_kwargs)
    web = args.web or cfg.get("web_search", {}).get("enabled", False)
    retriever = Retriever()

    if args.question:
        answer(" ".join(args.question), retriever, cfg,
               args.show_retrieval, args.no_llm, web)
        return 0

    print("Assessor corpus Q&A — Ctrl-D or 'quit' to exit. "
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
            answer(q, retriever, cfg, args.show_retrieval, args.no_llm, web)


if __name__ == "__main__":
    sys.exit(main())

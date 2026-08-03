#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat client for local llama-server / ik_llama.cpp.

Stdlib only (urllib). The endpoint and model come from config.json, so the
underlying model is swappable without code changes.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import load_config  # noqa: E402


class LLMError(RuntimeError):
    pass


def chat(messages: list[dict], cfg: dict | None = None) -> str:
    """Send a chat completion request; return the assistant message content."""
    llm = (cfg or load_config())["llm"]
    url = llm["base_url"].rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": llm["model"],
        "messages": messages,
        "max_tokens": llm["max_tokens"],
        "temperature": llm.get("temperature", 0.2),
        **({"chat_template_kwargs": llm["chat_template_kwargs"]}
           if "chat_template_kwargs" in llm else {}),
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm.get('api_key', 'none')}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=llm["timeout_seconds"]) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise LLMError(
            f"Cannot reach LLM at {url} — is llama-server running? ({e})"
        ) from e
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"Unexpected response shape: {json.dumps(data)[:500]}") from e


def extract_json(text: str) -> dict:
    """Pull the first top-level JSON object out of a model response.

    Tolerates <think>...</think> reasoning blocks, markdown fences, and prose
    around the object. Raises ValueError if no parseable object is found.
    """
    # Strip reasoning blocks (DeepSeek-R1 style) so we don't grab JSON examples
    # the model wrote while thinking.
    import re
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    depth, start = 0, None
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None  # keep scanning for the next object
    raise ValueError(f"No parseable JSON object in model output: {text[:300]!r}")


CANONICAL_EXCEPTIONS = ("none", "spouse", "family_residential", "trust",
                        "joint_tenancy", "other")


def parse_bool(value) -> bool:
    """The ONLY permitted conversion for model-supplied booleans (regression G1).

    bool("no") is True — so bool() on model output silently corrupts scoring.
    Anything unrecognized raises ValueError and must be counted as a parse failure.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().casefold()
        if v in ("true", "yes", "y", "1"):
            return True
        if v in ("false", "no", "n", "0"):
            return False
    raise ValueError(f"Unparseable boolean from model: {value!r}")


def normalize_verdict(v: dict) -> dict:
    """Validate and coerce a raw triage verdict to the canonical shape.

    Raises ValueError (→ parse failure upstream) only when 'uncapping' is
    unparseable; degrades the other fields gracefully.
    """
    out = dict(v)
    out["uncapping"] = parse_bool(v.get("uncapping"))
    exc = str(v.get("exception_category", "none")).strip().casefold()
    if exc not in CANONICAL_EXCEPTIONS:
        out["exception_raw"] = v.get("exception_category")
        exc = "other"
    out["exception_category"] = exc
    # Scope: Michigan law allows a PARTIAL uncapping (MCL 211.27a(7)(c) life
    # estates over part of a parcel; 27a(6)(k) qualified-agricultural splits).
    # Older cases and older model outputs have no scope field, so infer a
    # backward-compatible default from the boolean rather than failing.
    scope = str(v.get("uncapping_scope", "")).strip().casefold()
    if scope not in ("none", "whole", "partial"):
        scope = "whole" if out["uncapping"] else "none"
    out["uncapping_scope"] = scope
    conf = str(v.get("confidence", "")).strip().casefold()
    out["confidence"] = conf if conf in ("high", "medium", "low") else "low"
    mf = v.get("missing_facts") or []
    out["missing_facts"] = [str(x) for x in mf] if isinstance(mf, list) else [str(mf)]
    out["file_note"] = str(v.get("file_note", ""))
    return out


if __name__ == "__main__":
    # Smoke test: python3 src/llm_client.py "your question"
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Reply with exactly: OK"
    print(chat([{"role": "user", "content": prompt}]))

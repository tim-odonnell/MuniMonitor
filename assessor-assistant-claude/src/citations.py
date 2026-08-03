#!/usr/bin/env python3
"""Deterministic citation-grounding check — the model-descent instrument.

validate_citations(text, provided_chunks) flags references in model free text
that do NOT trace to the provided reference set:
  - full chunk labels        [some-doc.md#12]        → must be a provided chunk id
  - bare chunk indexes       [30] or [30, 31]        → must match a provided id's #N
  - statute numbers          MCL 15.243 / 211.27a    → the number must appear in
                                                        the provided chunks' text
  - admin rule numbers       R 408.30401             → same
  - code section numbers     R314.3                  → same

HONEST LIMIT: this catches INVENTED references and label drift. It does NOT
catch a real section cited for the wrong proposition — that remains the human
reviewer's job. (Original motivating case: a model cited "MCL 15.233" for FOIA
exemptions that live in 15.243 — an invented-for-context number this check
catches whenever 15.233 isn't in the provided text.)

Ungrounded-cite rate is a primary metric of the model-descent protocol
(docs/model-descent-protocol.md): small models tend to keep scored decisions
right while citation fidelity rots — this makes that rot mechanically visible.
"""

import re

LABEL_RE = re.compile(r"\[([A-Za-z0-9._/-]+\.md#\d+)\]")
BARE_NUM_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
# 15.243, 211.27a, 125.1509, 339.6001 — two+ digits each side avoids ratios like 1.05
STATUTE_RE = re.compile(r"\b(?:MCL\s*)?(\d{2,3}\.\d{2,4}[a-z]{0,2})\b")
RULE_RE = re.compile(r"\bR\s?(408\.\d{3,5}[a-z]?)\b")
CODE_SEC_RE = re.compile(r"\b(R\d{3}(?:\.\d+)+)\b")


def validate_citations(text: str, provided_chunks: list[dict]) -> dict:
    """Return {"checked": n, "ungrounded": ["kind:cite", ...]} for one text."""
    ids = [c.get("id", "") for c in provided_chunks]
    blob = " ".join(c.get("text", "") for c in provided_chunks)
    findings = {"checked": 0, "ungrounded": []}

    def check(kind: str, cite: str, ok: bool) -> None:
        findings["checked"] += 1
        if not ok:
            entry = f"{kind}:{cite}"
            if entry not in findings["ungrounded"]:
                findings["ungrounded"].append(entry)

    for m in LABEL_RE.finditer(text):
        check("label", m.group(1), m.group(1) in ids)
    for m in BARE_NUM_RE.finditer(text):
        for n in re.split(r"\s*,\s*", m.group(1)):
            check("chunk-index", n, any(i.endswith(f"#{n}") for i in ids))
    for m in STATUTE_RE.finditer(text):
        check("statute", m.group(1), m.group(1) in blob)
    for m in RULE_RE.finditer(text):
        check("rule", m.group(1), m.group(1) in blob)
    for m in CODE_SEC_RE.finditer(text):
        check("code-section", m.group(1), m.group(1) in blob)
    return findings


def merge_findings(*findings: dict) -> dict:
    out = {"checked": 0, "ungrounded": []}
    for f in findings:
        out["checked"] += f["checked"]
        for u in f["ungrounded"]:
            if u not in out["ungrounded"]:
                out["ungrounded"].append(u)
    return out

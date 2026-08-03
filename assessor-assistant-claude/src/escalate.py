#!/usr/bin/env python3
"""Escalation router — decides who should handle a case or question.

Three routes:
  daily      → the fast local model handles it
  escalate   → route to the second-tier (design-phase) model; if that model is
               not configured/reachable, the daily draft is returned FLAGGED
  human_only → no AI draft at all; route to the assessor / named human

Two check layers:
  route_pre(text, hits)   — before any LLM call: pattern triggers (litigation,
                            confidential data, class-wide impact, media) and
                            retrieval quality (corpus doesn't cover the topic)
  route_post(verdict)     — after the daily model answers: its own confidence
                            and parse health

Philosophy (substitute paradox): the router exists because the person relying on
the assistant may be the person least able to catch its errors. When in doubt it
routes UP, and 'correctly escalated' counts as success, not failure.

CLI test:  python3 src/escalate.py "taxpayer's attorney filed an MTT petition"
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import load_config  # noqa: E402

# --- pattern triggers -------------------------------------------------------
# (regex, reason). Patterns are deliberately broad — the router's job is to
# over-flag, mirroring rule 4 of the triage prompt.

HUMAN_ONLY_PATTERNS = [
    # "attorney" guarded against routine conveyance mechanisms (regression G2):
    # "power of attorney" / "power-of-attorney" / "attorney-in-fact" are ordinary
    # PTA business, not litigation. Fixed-width lookbehinds + lookahead exclude them.
    (r"(?<!power of )(?<!power-of-)\battorney\b(?!-in-fact)"
     r"|\b(lawyer|legal counsel|lawsuit|litigation|subpoena|court order|sued|suing)\b"
     r"|threatening legal action",
     "legal/litigation posture — assessor + city attorney, not an AI draft"),
    (r"\b(tax tribunal|MTT petition|small claims division)\b",
     "active or threatened Tribunal matter — assessor + counsel"),
    (r"\b(reporter|newspaper|press|media inquiry)\b",
     "media contact — assessor handles public statements personally"),
    (r"\b(ssn|social security number)\b",
     "confidential identifier present — excluded from the AI system by data policy"),
    (r"\b(household income|bank statement|pay stub|financial statement|asset test)\b",
     "confidential financial data (poverty-exemption class) — excluded by data policy"),
]

ESCALATE_PATTERNS = [
    (r"\b(equalization|economic condition factor|ecf\b|land value (table|stud)|sales stud)\w*",
     "class-wide valuation analysis — second-tier model + assessor review"),
    (r"\b(all parcels|every parcel|neighborhood-?wide|class-?wide|jurisdiction-?wide)\b",
     "jurisdiction/class-wide impact — blast radius too large for the daily tier"),
    (r"\b(dark store|functional obsolescence|economic obsolescence|going concern)\b",
     "contested valuation doctrine — second-tier reasoning warranted"),
    (r"\b(disabled veteran|veteran'?s? exemption)\b",
     "recently-changed statutory process — verify against current law, don't trust recall"),
    (r"\b(easement|cell tower|billboard|wind turbine|solar (farm|array)|golf course"
     r"|marina|landfill|gravel pit|contaminated|brownfield)\b",
     "unusual-property valuation — outside routine patterns; second-tier + assessor"),
]


def _match(patterns: list, text: str) -> list[str]:
    return [reason for rx, reason in patterns if re.search(rx, text, re.IGNORECASE)]


def route_pre(text: str, hits: list[dict], cfg: dict | None = None) -> dict:
    """Route before any LLM call, from the request text + retrieval quality."""
    cfg = cfg or load_config()
    esc_cfg = cfg.get("escalation", {})
    reasons_human = _match(HUMAN_ONLY_PATTERNS, text)
    if reasons_human:
        return {"route": "human_only", "reasons": reasons_human}

    reasons = _match(ESCALATE_PATTERNS, text)

    min_hits = esc_cfg.get("min_hits", 2)
    min_score = esc_cfg.get("min_top_score", 1.0)
    if len(hits) < min_hits:
        reasons.append(f"corpus barely covers this topic ({len(hits)} relevant "
                       f"passage(s) found) — likely novel territory")
    elif hits[0]["score"] < min_score:
        reasons.append(f"weak retrieval match (top score {hits[0]['score']} < "
                       f"{min_score}) — the corpus may not address this")

    return {"route": "escalate" if reasons else "daily", "reasons": reasons}


def route_post(verdict: dict) -> dict:
    """Route after the daily model has answered, from its own signals."""
    reasons = []
    if str(verdict.get("confidence", "")).lower() == "low":
        reasons.append("daily model reports LOW confidence in its own determination")
    if verdict.get("missing_facts") and str(verdict.get("confidence", "")).lower() != "high":
        reasons.append("determination rests on missing facts: "
                       + "; ".join(verdict["missing_facts"][:3]))
    return {"route": "escalate" if reasons else "daily", "reasons": reasons}


def merge(*decisions: dict) -> dict:
    """Combine decisions; the most cautious route wins."""
    order = {"daily": 0, "escalate": 1, "human_only": 2}
    route = max((d["route"] for d in decisions), key=order.get)
    reasons = [r for d in decisions for r in d["reasons"]]
    return {"route": route, "reasons": reasons}


def escalation_llm_config(cfg: dict | None = None) -> dict | None:
    """Return a chat()-compatible config for the second-tier model, or None."""
    cfg = cfg or load_config()
    esc = cfg.get("escalation", {}).get("escalation_llm", {})
    return {"llm": esc} if esc.get("enabled") else None


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    from retrieve import Retriever
    text = " ".join(sys.argv[1:])
    hits = Retriever().search(text)
    decision = route_pre(text, hits)
    print(json.dumps({"input": text[:120], "top_hit": hits[0]["id"] if hits else None,
                      "top_score": hits[0]["score"] if hits else None,
                      **decision}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

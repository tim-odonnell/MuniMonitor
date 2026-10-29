#!/usr/bin/env python3
"""Run ONE MuniMonitor department action and print a JSON result (used by server.py).

Each department has its own drifted copies of ingest/retrieve/llm_client/prompts with the same
module names (finding H2a), so they can't share one Python process. The web server runs this
script as a subprocess per request: the department's own code makes every decision, exactly as
its CLI and test harnesses do. Honors MUNI_CONFIG_DIR (which model profile to use).

  echo '{"action": "ask", "question": "..."}' | python3 dept_worker.py assessor
  actions: route_score (no LLM) · ask · pta_triage (assessor) · foia_triage (clerk) ·
           vision (building: {"inspection_type", "notes", "images": [{"name", "data_b64"}]})
"""
import base64
import json
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPTS = {"assessor": "assessor-assistant-claude", "clerk": "city-clerk-claude",
         "building": "building-inspections-claude"}


def slim(hits):
    return [{"id": h["id"], "authority": h.get("authority", "UNTAGGED"),
             "score": round(h.get("score", 0.0), 3), "pinned": bool(h.get("pinned")),
             "text": h["text"][:900]} for h in hits]


RESIDENT_NOTE = ("[Channel: synthetic PUBLIC help desk. The person asking is a member of the public, not "
                 "staff. Answer them directly in plain language (\"you\"), keep every citation and [VERIFY] "
                 "rule, and when the documents can't settle it, tell them exactly which office or person to "
                 "contact and what to bring or ask.]\n\n")


def with_history(question, history):
    """Fold the last few turns into the question so follow-ups ("what about my garage?") work.
    Retrieval still uses the new message plus the previous user message only."""
    turns = [t for t in (history or []) if t.get("text")][-6:]
    if not turns:
        return question
    convo = "\n".join(f"{'Resident' if t['role'] == 'user' else 'Assistant'}: {t['text'][:1500]}"
                      for t in turns)
    return (f"Conversation so far (for context only; answer the NEW message):\n{convo}\n\n"
            f"NEW message from the resident: {question}")


def main():
    dept = sys.argv[1]
    req = json.load(sys.stdin)
    src = REPO / DEPTS[dept] / "src"
    sys.path.insert(0, str(src))
    from ingest import load_config            # noqa: E402  (the department's own modules)
    from retrieve import Retriever            # noqa: E402
    from llm_client import chat, extract_json, LLMError   # noqa: E402

    cfg = load_config()
    action = req["action"]
    out = {"dept": dept, "action": action, "model": cfg["llm"]["model"]}
    t0 = time.time()
    try:
        if action == "route_score":
            hits = Retriever().search(req["text"])
            out["top_scores"] = [round(h["score"], 3) for h in hits[:3]]
            return out

        if action == "ask":
            from prompts import GENERAL_QA_SYSTEM, build_qa_prompt   # noqa: E402
            prev = [t["text"] for t in (req.get("history") or []) if t.get("role") == "user"][-1:]
            query = " ".join(prev + [req["question"]])
            if dept == "assessor" and req.get("pin_transfer_law"):
                # Transfer questions get the same pinned statutes as PTA triage (27a whole), so the
                # answer and the determination in one turn rest on the same law (finding WEBUI-1).
                from prompts import triage_context   # noqa: E402
                hits, _tail = triage_context(query, Retriever())
            else:
                hits = Retriever().search(query)
            out["hits"] = slim(hits)
            if dept == "assessor":                 # the assessor's escalation router
                from escalate import route_pre     # noqa: E402
                pre = route_pre(req["question"], hits, cfg)
                out["routing"] = pre
                if pre["route"] == "human_only":
                    return out
            if not hits:
                out["answer"] = None
                out["error"] = "No relevant passages found in this department's reference documents."
                return out
            photo_note = (f"[The resident attached {req['images_attached']} photo(s). A separate photo "
                          "screening describes what is visible; do not say no photo was provided, and do "
                          "not describe the photo yourself.]\n\n") if req.get("images_attached") else ""
            out["answer"] = chat([{"role": "system", "content": GENERAL_QA_SYSTEM},
                                  {"role": "user", "content": build_qa_prompt(
                                      RESIDENT_NOTE + photo_note + with_history(req["question"], req.get("history")), hits)}],
                                 cfg).strip()

        elif action == "pta_triage" and dept == "assessor":
            from prompts import PTA_TRIAGE_SYSTEM, build_user_prompt, triage_context  # noqa: E402
            from llm_client import normalize_verdict                                 # noqa: E402
            from escalate import route_pre, route_post, merge                        # noqa: E402
            r = Retriever()
            hits, tail = triage_context(req["facts"], r)
            pre = route_pre(req["facts"], tail, cfg)
            out["hits"] = slim(hits)
            if pre["route"] == "human_only":
                out["routing"] = pre
                return out
            raw = chat([{"role": "system", "content": PTA_TRIAGE_SYSTEM},
                        {"role": "user", "content": build_user_prompt(req["facts"], hits)}], cfg)
            try:
                v = normalize_verdict(extract_json(raw))
                out["verdict"], out["routing"] = v, merge(pre, route_post(v))
            except ValueError:
                out["error"] = "The determination could not be parsed — routed to a human."
                out["routing"] = merge(pre, {"route": "escalate",
                                             "reasons": ["model output was unparseable"]})
                out["raw"] = raw[:3000]

        elif action == "foia_triage" and dept == "clerk":
            from foia_triage import triage           # noqa: E402
            t, hits = triage(req["request"], cfg, Retriever())
            out["triage"], out["hits"] = t, slim(hits)

        elif action == "vision" and dept == "building":
            from vision_check import (encode_image, vision_chat, normalize_report,  # noqa: E402
                                      calibration_probe)
            from prompts import VISION_SYSTEM, build_vision_prompt                 # noqa: E402
            import io, contextlib                                                  # noqa: E402
            probe = io.StringIO()
            with contextlib.redirect_stdout(probe):  # image-visibility probe before trusting output
                calibration_probe(cfg)
            out["calibration"] = probe.getvalue().strip()[-600:]
            content = [{"type": "text", "text": build_vision_prompt(req["inspection_type"],
                                                                     req.get("notes", ""))}]
            with tempfile.TemporaryDirectory() as td:
                for i, im in enumerate(req["images"]):
                    p = Path(td) / f"{i}{Path(im['name']).suffix.lower() or '.jpg'}"
                    p.write_bytes(base64.b64decode(im["data_b64"]))
                    content.append(encode_image(p, cfg["vision"]["max_image_bytes"]))
            raw = vision_chat([{"role": "system", "content": VISION_SYSTEM},
                               {"role": "user", "content": content}], cfg)
            try:
                out["report"] = normalize_report(extract_json(raw))
            except ValueError:
                out["error"] = "The photo screening could not be parsed — an inspector must review."
                out["raw"] = raw[:3000]
        else:
            out["error"] = f"unsupported action {action} for {dept}"
    except LLMError as e:
        out["error"] = f"Model server problem: {e}"
    except SystemExit as e:              # vision_check exits on a failed image probe or a bad/oversized photo
        out["error"] = f"Photo check stopped: {e}"
    out["seconds"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    res = main()
    sys.stdout.write("\n@@RESULT@@" + json.dumps(res))

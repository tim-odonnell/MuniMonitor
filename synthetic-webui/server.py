#!/usr/bin/env python3
"""Unified PUBLIC-STYLE web UI for the synthetic test system (plan component C4).

A tester plays a member of the public: types questions, attaches photos. MuniMonitor makes every
decision — which department, which tool, the answer, every determination — through each
department's own code (dept_worker.py runs it in a subprocess). Every turn ends with a machine-
readable DECISION CARD and is appended to transcripts/<session>.jsonl for scoring.

UNOFFICIAL SYNTHETIC TEST SYSTEM: not affiliated with any city; all people and records fictional.

Usage (stdlib only, localhost only):
  python3 synthetic-webui/server.py                       # http://127.0.0.1:8600
  MUNI_CONFIG_DIR=~/projects/muni-work/configs/ceil-glm python3 synthetic-webui/server.py
      # → pick the model profile (see ~/projects/muni-work/README.md); default = repo config.json
API (the user simulator drives the same API): POST /api/turn
  {"session": "...", "message": "...", "history": [{"role","text"}], "department": "auto|assessor|
   clerk|building", "images": [{"name", "data_b64"}], "inspection_type": "final|framing|..."}
"""
import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRANSCRIPTS = HERE / "transcripts"
WORKER = HERE / "dept_worker.py"
CITY = "Royal Oak, Michigan (synthetic)"
INSPECTION_TYPES = ["final", "footing", "framing", "electrical_rough", "plumbing_rough", "insulation"]
MAX_IMAGES, MAX_IMAGE_B64 = 4, 11_000_000

# Department router: plain-language signals a resident uses, plus each department's own retrieval
# score as a tiebreak. Transparent on purpose: the decision card records why.
SIGNALS = {
    "assessor": r"assess|taxable value|uncap|property tax|tax bill|homestead|principal residence|"
                r"\bpre\b|poverty exemption|veteran.{0,20}exempt|board of review|appeal.{0,20}(value|assess)|"
                r"\bsev\b|state equalized|millage|deed|quit ?claim|land contract|inherit|transfer(red)? "
                r"(the |my |our )?(house|home|property)|sold (the |my |our )?(house|home|property)|"
                r"property transfer affidavit|\bpta\b|capped value|market value|\btaxes\b|"
                r"left (me|us) (the|her|his|their|my) (house|home|property)|passed away|\bestate\b|probate",
    "clerk": r"\bfoia\b|freedom of information|public record|records? request|copy of|copies of|"
             r"elect|vote|voting|ballot|absentee|register(ed)? to vote|voter|polling|precinct|"
             r"council|commission meeting|meeting minutes|open meetings|closed session|agenda|notary|petition|"
             r"lawsuit|litigation|ordinance|city charter|"
             r"recall|candidate|campaign finance|clerk",
    "building": r"permit|inspect|inspection|deck|fence|garage|addition|basement|remodel|renovat|kitchen|bathroom|"
                r"electrical|wiring|panel|plumbing|water heater|furnace|hvac|roof|shed|porch|"
                r"stairs?|railing|guard|egress|smoke alarm|contractor|code|footing|framing|"
                r"insulation|drywall|certificate of occupancy|demolition|pool",
}
RECORDS_REQUEST = re.compile(r"\bfoia\b|freedom of information|(i('d| would)? like|request|need|want)"
                             r".{0,40}(cop(y|ies)|records?|emails?|documents?|reports?)", re.I)
TRANSFER_FACTS = re.compile(r"deed|quit ?claim|land contract|transferr?ed|inherit|sold .{0,30}to|"
                            r"put .{0,30}(in|into) (a |my |the )?trust|added .{0,30}to the (title|deed)|"
                            r"life estate|joint tenan", re.I)
LABEL = re.compile(r"([A-Za-z0-9._-]+\.md#\d+)")   # bare [label] or [LAW, label] — both appear


def run_worker(dept, req, timeout=3600):
    p = subprocess.run([sys.executable, "-I", str(WORKER), dept], input=json.dumps(req),
                       capture_output=True, text=True, timeout=timeout, env=os.environ.copy())
    if "@@RESULT@@" not in p.stdout:
        return {"dept": dept, "action": req["action"],
                "error": "department worker failed: " + (p.stderr or p.stdout)[-1500:]}
    return json.loads(p.stdout.split("@@RESULT@@", 1)[1])


def route(message, history, images, forced):
    """MuniMonitor's department decision, with its reasons."""
    if forced in ("assessor", "clerk", "building"):
        return forced, [f"resident chose the {forced} department"], []
    prev = " ".join(t["text"] for t in history[-2:] if t.get("role") == "user")
    text = (message + " " + prev).lower()
    kw = {d: len(re.findall(rx, text)) for d, rx in SIGNALS.items()}
    if images:
        kw["building"] += 2
    with ThreadPoolExecutor(3) as ex:
        bm = dict(zip(SIGNALS, ex.map(lambda d: run_worker(d, {"action": "route_score",
                                                                "text": message}), SIGNALS)))
    top = {d: (bm[d].get("top_scores") or [0])[0] for d in SIGNALS}
    best_bm = max(top.values()) or 1.0
    score = {d: kw[d] + 1.5 * top[d] / best_bm for d in SIGNALS}
    dept = max(score, key=score.get)
    # A second department with its own clear keyword signals also answers (e.g. "inherited the house:
    # taxes? kitchen permit?"). Keyword-only on purpose: retrieval scores alone are too noisy.
    also = [d for d in SIGNALS if d != dept and kw[d] >= 2 and score[d] >= 0.5 * score[dept]]
    reasons = [f"keyword signals {kw}", "retrieval top score " +
               ", ".join(f"{d} {top[d]}" for d in SIGNALS), f"combined {dict((d, round(v, 2)) for d, v in score.items())}"]
    if images:
        reasons.append("photos attached (+2 building)")
    if also:
        reasons.append(f"also answered by {', '.join(also)} (separate clear signals)")
    return dept, reasons, also


def decision_card(sid, turn_no, dept, reasons, results, model):
    card = {"schema": "munimonitor-decision-card/0.1", "session": sid, "turn": turn_no,
            "ts": datetime.now().isoformat(timespec="seconds"), "city": CITY,
            "model": model, "department": dept, "routing_reasons": reasons,
            "actions": [r["action"] for r in results], "determinations": {}, "citations": [],
            "human_review": [], "errors": [r["error"] for r in results if r.get("error")]}
    for r in results:
        if r.get("answer"):
            card["citations"] += LABEL.findall(r["answer"])
            card["determinations"]["answer_has_verify_tags"] = "[VERIFY]" in r["answer"]
        if r.get("routing") and r["routing"].get("route") != "daily":
            card["human_review"].append({"route": r["routing"]["route"],
                                         "reasons": r["routing"].get("reasons", [])})
        if r.get("verdict"):
            v = r["verdict"]
            card["determinations"]["pta"] = {k: v.get(k) for k in
                                             ("uncapping", "exception_category", "confidence", "missing_facts")}
        if r.get("triage"):
            t = r["triage"]
            card["determinations"]["foia"] = {k: t.get(k) for k in
                                              ("category", "needs_attorney_review", "review_reasons",
                                               "clarification_needed", "confidence")}
        if r.get("report"):
            rep = r["report"]
            card["determinations"]["photo_screening"] = {
                "image_quality": rep.get("image_quality"),
                "possible_concerns": [c["concern"] for c in rep.get("possible_concerns", [])],
                "cannot_verify_from_photo": rep.get("cannot_verify_from_photo")}
    card["citations"] = sorted(set(card["citations"]))
    return card


def api_turn(body):
    sid = re.sub(r"[^A-Za-z0-9-]", "", body.get("session") or "")[:40] or uuid.uuid4().hex[:12]
    msg = (body.get("message") or "").strip()
    images = (body.get("images") or [])[:MAX_IMAGES]
    if not msg and not images:
        raise ValueError("Type a message or attach a photo.")
    for im in images:
        if len(im.get("data_b64", "")) > MAX_IMAGE_B64:
            raise ValueError(f"{im.get('name')} is too large (limit about 8 MB).")
    history = [t for t in (body.get("history") or []) if isinstance(t, dict)][-12:]
    dept, reasons, also = route(msg, history, images, body.get("department"))

    jobs = []
    transfer = dept == "assessor" and bool(TRANSFER_FACTS.search(msg))
    if msg:
        jobs.append((dept, {"action": "ask", "question": msg, "history": history,
                            "pin_transfer_law": transfer, "images_attached": len(images)}))
        if transfer:
            reasons.append("transfer question → answer uses the pinned transfer statutes")
        for d in also:
            jobs.append((d, {"action": "ask", "question": msg, "history": history,
                             "pin_transfer_law": d == "assessor" and bool(TRANSFER_FACTS.search(msg))}))
    if transfer and len(msg) > 80:
        jobs.append(("assessor", {"action": "pta_triage", "facts": msg}))
        reasons.append("message describes a transfer → preliminary PTA determination")
    if dept == "clerk" and RECORDS_REQUEST.search(msg):
        jobs.append(("clerk", {"action": "foia_triage", "request": msg}))
        reasons.append("message reads as a records request → FOIA triage")
    if images:
        it = body.get("inspection_type") if body.get("inspection_type") in INSPECTION_TYPES else "final"
        jobs.append(("building", {"action": "vision", "images": images, "inspection_type": it,
                                  "notes": msg[:1500]}))
        reasons.append(f"photos → building photo screening (checklist: {it})")
    with ThreadPoolExecutor(len(jobs)) as ex:
        results = list(ex.map(lambda j: run_worker(*j), jobs))

    model = next((r.get("model") for r in results if r.get("model")), None)
    turn_no = sum(1 for t in history if t.get("role") == "user") + 1
    card = decision_card(sid, turn_no, dept, reasons, results, model)
    card["also_departments"] = also
    TRANSCRIPTS.mkdir(exist_ok=True)
    with (TRANSCRIPTS / f"{sid}.jsonl").open("a") as f:
        f.write(json.dumps({"turn": turn_no, "message": msg,
                            "images": [im.get("name") for im in images],
                            "results": results, "decision_card": card}) + "\n")
    return {"session": sid, "department": dept, "results": results, "decision_card": card}


def api_info(_body=None):
    cfg_dir = os.environ.get("MUNI_CONFIG_DIR")
    return {"city": CITY, "config": cfg_dir or "repo config.json",
            "inspection_types": INSPECTION_TYPES}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, content, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (HERE / "page.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/info":
            self._send(200, json.dumps(api_info()).encode(), "application/json")
        else:
            self._send(404, b'{"error": "not found"}', "application/json")

    def do_POST(self):
        if self.path != "/api/turn":
            return self._send(404, b'{"error": "not found"}', "application/json")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._send(200, json.dumps(api_turn(body)).encode(), "application/json")
        except (ValueError, KeyError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode(), "application/json")
        except subprocess.TimeoutExpired:
            self._send(504, b'{"error": "the model took too long"}', "application/json")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--port", type=int, default=8600)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)   # localhost only: no auth
    print(f"Synthetic MuniMonitor UI: http://127.0.0.1:{args.port}   config: {api_info()['config']}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

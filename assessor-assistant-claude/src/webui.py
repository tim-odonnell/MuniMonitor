#!/usr/bin/env python3
"""Staff-facing web UI for the assessing assistant.

Single-file local web app, stdlib only, fully offline. Two functions:
  - Ask       : RAG-grounded Q&A over the corpus, with authority-labeled citations
  - PTA triage: paste transfer facts, get a DRAFT determination for human review

Every request/response is appended to logs/webui-YYYYMMDD.jsonl (audit trail —
note: these logs may be FOIA-able records; see the data policy).

Usage:
  python3 src/webui.py                 # http://127.0.0.1:8580 (this machine only)
  python3 src/webui.py --host 0.0.0.0  # office LAN — NO AUTH in v1, trusted network only
  python3 src/webui.py --port 8590
"""

import argparse
import json
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config                       # noqa: E402
from retrieve import Retriever                             # noqa: E402
from llm_client import chat, extract_json, normalize_verdict, LLMError  # noqa: E402
from prompts import (PTA_TRIAGE_SYSTEM, GENERAL_QA_SYSTEM,  # noqa: E402
                     build_user_prompt, build_qa_prompt, triage_context)
from escalate import route_pre, route_post, merge, escalation_llm_config  # noqa: E402

LOGS = ROOT / "logs"

_retriever: Retriever | None = None


def retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def log_event(kind: str, payload: dict) -> None:
    LOGS.mkdir(exist_ok=True)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), "kind": kind, **payload}
    path = LOGS / f"webui-{datetime.now().strftime('%Y%m%d')}.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def slim_hits(hits: list[dict]) -> list[dict]:
    return [{"id": h["id"], "authority": h["authority"], "score": h["score"],
             "text": h["text"][:800]} for h in hits]


# ---------------- API handlers ----------------

def api_health(_body: dict) -> dict:
    cfg = load_config()
    out = {"corpus_chunks": None, "llm": "down", "model": cfg["llm"]["model"],
           "endpoint": cfg["llm"]["base_url"]}
    try:
        out["corpus_chunks"] = retriever().index["n_chunks"]
    except FileNotFoundError:
        out["corpus_chunks"] = 0
    try:
        chat([{"role": "user", "content": "Reply with exactly: OK"}], cfg)
        out["llm"] = "up"
    except LLMError:
        pass
    return out


def api_search(body: dict) -> dict:
    hits = retriever().search(body["q"])
    return {"hits": slim_hits(hits)}


def api_ask(body: dict) -> dict:
    question, initials = body["question"].strip(), body.get("initials", "").strip()
    if not question:
        raise ValueError("Empty question.")
    cfg = load_config()
    hits = retriever().search(question)
    pre = route_pre(question, hits, cfg)
    if pre["route"] == "human_only":
        log_event("ask", {"initials": initials, "question": question, "routing": pre})
        return {"routed": pre, "hits": slim_hits(hits)}
    if not hits:
        return {"answer": None, "hits": [],
                "error": "No relevant passages found in the corpus for that question."}
    t0 = time.time()
    answer = chat([
        {"role": "system", "content": GENERAL_QA_SYSTEM},
        {"role": "user", "content": build_qa_prompt(question, hits)},
    ], cfg).strip()
    secs = round(time.time() - t0, 1)
    log_event("ask", {"initials": initials, "question": question, "answer": answer,
                      "retrieved": [h["id"] for h in hits], "seconds": secs,
                      "routing": pre})
    return {"answer": answer, "hits": slim_hits(hits), "seconds": secs,
            "routing": pre if pre["route"] != "daily" else None}


def _triage_messages(facts: str, hits: list[dict]) -> list[dict]:
    return [
        {"role": "system", "content": PTA_TRIAGE_SYSTEM},
        {"role": "user", "content": build_user_prompt(facts, hits)},
    ]


def api_triage(body: dict) -> dict:
    facts, initials = body["facts"].strip(), body.get("initials", "").strip()
    if not facts:
        raise ValueError("No facts entered.")
    cfg = load_config()
    hits, tail = triage_context(facts, retriever())

    # 1. Pre-LLM routing: human-only cases never get an AI draft at all.
    # Routing quality-checks use the RETRIEVED tail (pinned chunks carry score
    # 0.0 and would false-trigger the weak-retrieval escalation).
    pre = route_pre(facts, tail, cfg)
    if pre["route"] == "human_only":
        log_event("triage", {"initials": initials, "facts": facts, "routing": pre})
        return {"routed": pre, "hits": slim_hits(hits)}

    # 2. Daily model.
    t0 = time.time()
    raw = chat(_triage_messages(facts, hits), cfg)
    secs = round(time.time() - t0, 1)
    try:
        verdict = normalize_verdict(extract_json(raw))  # real bool for uncapping (G1)
        routing = merge(pre, route_post(verdict))
    except ValueError:
        verdict = None
        routing = merge(pre, {"route": "escalate",
                              "reasons": ["daily model output was unparseable"]})

    # 3. Escalate = FLAG ONLY (regression G4): never invoke the slow second-tier
    # model inside an HTTP request — a ~4 tok/s model with a 30-minute timeout
    # would hang the staff member's browser. The draft is returned flagged; the
    # second-tier run happens outside this session.
    tier = "daily"
    if routing["route"] == "escalate":
        if escalation_llm_config(cfg):
            routing["reasons"].append(
                "second-tier review required — run this case on the design-tier "
                "model outside this session; assessor review required")
        else:
            routing["reasons"].append(
                "second-tier model not configured — route this case to the "
                "assessor / design-tier model manually")

    if verdict is None:
        log_event("triage", {"initials": initials, "facts": facts,
                             "error": "parse_failure", "routing": routing,
                             "raw": raw[:2000], "seconds": secs})
        return {"error": "The model's response could not be parsed into a determination. "
                         "Handle this case manually.", "routing": routing,
                "hits": slim_hits(hits)}

    log_event("triage", {"initials": initials, "facts": facts, "verdict": verdict,
                         "retrieved": [h["id"] for h in hits], "seconds": secs,
                         "routing": routing, "tier": tier})
    return {"verdict": verdict, "hits": slim_hits(hits), "seconds": secs, "tier": tier,
            "routing": routing if routing["route"] != "daily" else None}


def api_reload(_body: dict) -> dict:
    global _retriever
    _retriever = None
    return {"corpus_chunks": retriever().index["n_chunks"]}


ROUTES = {"/api/health": api_health, "/api/search": api_search,
          "/api/ask": api_ask, "/api/triage": api_triage, "/api/reload": api_reload}


# ---------------- HTTP server ----------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet default access log
        pass

    def _send(self, code: int, content: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/api/health":
            self._send_json(200, api_health({}))
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        fn = ROUTES.get(self.path)
        if not fn:
            self._send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._send_json(200, fn(body))
        except LLMError as e:
            self._send_json(503, {"error": str(e)})
        except (ValueError, KeyError) as e:
            self._send_json(400, {"error": str(e)})
        except FileNotFoundError as e:
            self._send_json(503, {"error": str(e)})


# ---------------- the page ----------------

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Assessing Assistant (DRAFT tool)</title>
<style>
  :root { --ink:#1a2733; --bg:#f5f6f8; --card:#fff; --accent:#1c5d99; --warn:#8a1c1c; }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.5 system-ui,sans-serif; color:var(--ink); background:var(--bg); }
  header { background:var(--accent); color:#fff; padding:10px 20px;
           display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }
  header h1 { font-size:17px; margin:0; }
  header .status { font-size:12px; opacity:.9; }
  .banner { background:#fff3cd; border-bottom:1px solid #e0c060; padding:6px 20px; font-size:13px; }
  main { max-width:900px; margin:18px auto; padding:0 16px; }
  nav button { border:1px solid #c7ccd4; background:#e9ecf0; padding:8px 18px;
               cursor:pointer; font-size:14px; border-radius:6px 6px 0 0; }
  nav button.on { background:var(--card); border-bottom-color:var(--card); font-weight:600; }
  .card { background:var(--card); border:1px solid #c7ccd4; border-radius:0 6px 6px 6px; padding:16px; }
  textarea { width:100%; min-height:110px; font:inherit; padding:8px; border:1px solid #b6bcc6; border-radius:4px; }
  input[type=text] { font:inherit; padding:6px 8px; border:1px solid #b6bcc6; border-radius:4px; width:90px; }
  .row { display:flex; gap:10px; align-items:center; margin-top:10px; flex-wrap:wrap; }
  button.go { background:var(--accent); color:#fff; border:0; padding:9px 22px;
              border-radius:5px; font-size:14px; cursor:pointer; }
  button.go[disabled] { opacity:.5; cursor:wait; }
  .out { margin-top:16px; }
  .draft { border:2px dashed var(--warn); border-radius:6px; padding:12px; background:#fffafa; }
  .draft h3 { margin:0 0 6px; color:var(--warn); font-size:13px; letter-spacing:.06em; }
  .answer { white-space:pre-wrap; }
  .kv { margin:4px 0; }
  .kv b { display:inline-block; min-width:110px; }
  .verify { background:#ffe2a8; padding:0 3px; border-radius:3px; font-weight:600; }
  .src { margin-top:12px; font-size:13px; }
  .src details { margin:4px 0; }
  .badge { display:inline-block; font-size:11px; font-weight:700; padding:1px 7px;
           border-radius:9px; color:#fff; vertical-align:middle; }
  .LAW { background:#8a1c1c; } .STATE-GUIDANCE { background:#1c5d99; }
  .OFFICE-PRACTICE { background:#3d7a33; } .UNTAGGED { background:#777; }
  .err { color:var(--warn); font-weight:600; margin-top:12px; }
  .route { background:#e8eef7; border-left:4px solid var(--accent); padding:10px 14px;
           margin-top:12px; border-radius:0 4px 4px 0; }
  .route.human { background:#fbeaea; border-color:var(--warn); }
  .route ul { margin:6px 0 0 18px; padding:0; }
  .meta { color:#667; font-size:12px; margin-top:8px; }
  footer { text-align:center; color:#889; font-size:12px; padding:20px; }
</style></head><body>
<header>
  <h1>Assessing Assistant</h1>
  <span class="status" id="status">checking status…</span>
</header>
<div class="banner">⚠ Every output is a <b>DRAFT for human review</b>. Nothing here goes to a
resident, the roll, or an official record without assessor/staff verification.
Sessions are logged.</div>
<main>
  <nav>
    <button id="tab-ask" class="on" onclick="tab('ask')">Ask a question</button>
    <button id="tab-triage" onclick="tab('triage')">PTA triage</button>
  </nav>
  <div class="card" id="pane-ask">
    <p>Ask about procedure, transfers, exemptions, or office practice. Answers come only
    from the ingested reference documents, with citations.</p>
    <textarea id="q" placeholder="e.g., Does a quit claim deed from a parent to a child uncap taxable value?"></textarea>
    <div class="row">
      <label>Your initials <input type="text" id="initials" maxlength="5"></label>
      <button class="go" id="go-ask" onclick="ask()">Ask</button>
    </div>
    <div class="out" id="out-ask"></div>
  </div>
  <div class="card" id="pane-triage" style="display:none">
    <p>Paste the transfer facts (instrument, parties and relationship, consideration,
    property class/use, PTA status). <b>Anonymize first</b> — no owner names needed for a draft.</p>
    <textarea id="facts" placeholder="e.g., Quit claim deed, mother to adult son, $1 stated, residential parcel, son plans to rent it out, PTA filed day 30."></textarea>
    <div class="row">
      <label>Your initials <input type="text" id="initials2" maxlength="5"></label>
      <button class="go" id="go-triage" onclick="triage()">Draft determination</button>
    </div>
    <div class="out" id="out-triage"></div>
  </div>
</main>
<footer>Local assessing assistant — runs entirely on this machine. Logs: <code>logs/</code></footer>
<script>
const $ = id => document.getElementById(id);
const esc = s => (s ?? '').toString().replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const mark = s => esc(s).replace(/\\[VERIFY\\]/g, '<span class="verify">[VERIFY]</span>');
$('initials').value = localStorage.getItem('initials') || '';
$('initials2').value = $('initials').value;
for (const id of ['initials','initials2'])
  $(id).addEventListener('change', e => { localStorage.setItem('initials', e.target.value);
    $('initials').value = $('initials2').value = e.target.value; });

function tab(name){
  for (const t of ['ask','triage']) {
    $('pane-'+t).style.display = (t===name) ? '' : 'none';
    $('tab-'+t).classList.toggle('on', t===name);
  }
}
async function health(){
  try {
    const r = await (await fetch('/api/health')).json();
    $('status').textContent =
      `corpus: ${r.corpus_chunks} chunks · model: ${r.model} · LLM: ${r.llm}`;
    if (r.llm !== 'up') $('status').textContent += ' ⚠ (start llama-server)';
  } catch { $('status').textContent = 'status unavailable'; }
}
health();
function routeBanner(r){
  if (!r) return '';
  const human = r.route === 'human_only';
  const title = human ? '⛔ ROUTED TO A HUMAN — no AI draft for this one'
                      : '⬆ ESCALATION FLAGGED — treat with extra care';
  return `<div class="route ${human ? 'human' : ''}"><b>${title}</b>
    <ul>${r.reasons.map(x => `<li>${esc(x)}</li>`).join('')}</ul>
    ${human ? '<div class="meta">See the escalation contacts list (state-of-office doc) for who handles this.</div>' : ''}</div>`;
}
function sources(hits){
  if (!hits || !hits.length) return '';
  return '<div class="src"><b>Sources used:</b>' + hits.map(h =>
    `<details><summary><span class="badge ${esc(h.authority)}">${esc(h.authority)}</span>
     ${esc(h.id)} <span class="meta">(score ${h.score})</span></summary>
     <div class="answer">${esc(h.text)}</div></details>`).join('') + '</div>';
}
async function post(url, body, btn, out){
  btn.disabled = true; out.innerHTML = '<div class="meta">working — local model running…</div>';
  try {
    const resp = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'},
                                   body: JSON.stringify(body)});
    const r = await resp.json();
    if (r.error) { out.innerHTML = `<div class="err">${esc(r.error)}</div>` + routeBanner(r.routing) + sources(r.hits); return null; }
    return r;
  } catch (e) { out.innerHTML = `<div class="err">Request failed: ${esc(e.message)}</div>`; return null; }
  finally { btn.disabled = false; }
}
async function ask(){
  const out = $('out-ask');
  const r = await post('/api/ask', {question: $('q').value, initials: $('initials').value},
                       $('go-ask'), out);
  if (!r) return;
  if (r.routed) { out.innerHTML = routeBanner(r.routed) + sources(r.hits); return; }
  out.innerHTML = routeBanner(r.routing) +
    `<div class="draft"><h3>DRAFT — VERIFY BEFORE RELYING ON IT</h3>
    <div class="answer">${mark(r.answer)}</div></div>` + sources(r.hits) +
    `<div class="meta">${r.seconds}s</div>`;
}
async function triage(){
  const out = $('out-triage');
  const r = await post('/api/triage', {facts: $('facts').value, initials: $('initials2').value},
                       $('go-triage'), out);
  if (!r) return;
  if (r.routed) { out.innerHTML = routeBanner(r.routed) + sources(r.hits); return; }
  const v = r.verdict;
  const tierNote = r.tier === 'escalation' ? ' (answered by the SECOND-TIER model)' : '';
  out.innerHTML = routeBanner(r.routing) +
    `<div class="draft"><h3>DRAFT DETERMINATION — ASSESSOR REVIEW REQUIRED${tierNote}</h3>
    <div class="kv"><b>Uncapping:</b> ${v.uncapping ? 'YES — treat as uncapping event' : 'No'}</div>
    <div class="kv"><b>Exception:</b> ${esc(v.exception_category)}</div>
    <div class="kv"><b>Confidence:</b> ${esc(v.confidence)}</div>
    ${v.missing_facts && v.missing_facts.length ?
      `<div class="kv"><b>Missing facts:</b> ${esc(v.missing_facts.join('; '))}</div>` : ''}
    <div class="kv"><b>File note:</b><div class="answer">${mark(v.file_note)}</div></div>
    </div>` + sources(r.hits) + `<div class="meta">${r.seconds}s</div>`;
}
for (const [ta, fn] of [['q', ask], ['facts', triage]])
  $(ta).addEventListener('keydown', e => { if (e.key==='Enter' && (e.ctrlKey||e.metaKey)) fn(); });
</script>
</body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Staff-facing assessing assistant UI")
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 = this machine only (default); 0.0.0.0 = office LAN")
    ap.add_argument("--port", type=int, default=8580)
    args = ap.parse_args()

    if args.host != "127.0.0.1":
        print("⚠  Binding beyond localhost: v1 has NO authentication — trusted office "
              "network only, per the data policy.")
    try:
        retriever()
    except FileNotFoundError as e:
        print(f"WARN: {e}")

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Assessing Assistant UI: http://{args.host}:{args.port}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

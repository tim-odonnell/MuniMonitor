"""Keyless web lookup restricted to OFFICIAL Michigan sources — no search engine, no API key.

Search engines block automated use and need keys; MuniMonitor only needs a small set of official
sites, and those publish what a program needs:
  1. Citation fetch — a cited statute is fetched straight from legislature.mi.gov by number
     ("MCL 211.27a" -> /Laws/MCL?objectName=mcl-211-27a). Deterministic and always current.
  2. Sitemap index — each agency's sitemap.xml (Treasury, Taxes, SOS, LARA, AG: ~12,000 URLs with
     descriptive paths) is downloaded at most weekly and searched locally (BM25 over the URL words).
  3. One hop of navigation — a matched page's own links (anchor text) are scored against the
     question and the best official ones followed (that is how bulletin PDFs are reached).
  4. Verification — verify_quotes() checks that every quoted passage in an answer appears word for
     word in the fetched official text, so a web-based claim can always be traced.
Pages are cached (1 day) and fetched politely (one request per host per second). Web text is
untrusted input: callers must keep the prompt-injection rules (websearch.WEB_QA_RULES).
"""
import hashlib
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import websearch    # fetch_text (HTML + pdftotext), _passages, _terms, _label, is_official

SITEMAPS = [f"https://www.michigan.gov/{a}/sitemap.xml" for a in ("treasury", "taxes", "sos", "lara", "ag")]
# Department -> the agencies that publish its official material (searched first; all if no match).
AGENCIES = {"assessor": ("/treasury/", "/taxes/"), "clerk": ("/sos/", "/ag/"), "building": ("/lara/",)}
REPO = Path(__file__).resolve().parent.parent.parent
DEPT_DIRS = {"assessor": "assessor-assistant-claude", "clerk": "city-clerk-claude",
             "building": "building-inspections-claude"}
OFFICIAL_HOSTS = ("michigan.gov", "legislature.mi.gov")
CACHE = Path(os.environ.get("MUNI_WEB_CACHE", Path.home() / ".cache" / "munimonitor" / "officialweb"))
USER_AGENT = "MuniMonitor/0.1 (offline-first municipal assistant; official-source lookup)"
INDEX_MAX_AGE = 7 * 86400
PAGE_MAX_AGE = 86400
MCL_EXPLICIT = re.compile(r"(?:\bMCL|M\.C\.L\.|§|\b[Ss]ection|\b[Ss]ec\.)\s*(\d{2,3})\.(\d{1,4}[a-z]{0,2})\b")
MCL_BARE = re.compile(r"\b(\d{2,3})\.(\d{1,4}[a-z]{0,2})\b")
SLUG_STOP = {"www", "michigan", "gov", "https", "http", "html", "aspx", "media", "project", "websites",
             "rev", "pdf", "the", "and", "for", "of", "to", "in", "a", "on", "with", "accordion"}

_last_hit: dict[str, float] = {}


def _stem(w: str) -> str:
    for suf in ("ings", "ing", "ies", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def _words(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower())
            if w not in SLUG_STOP and w not in websearch.STOP and len(w) > 1]


def _get(url: str, timeout: int = 30) -> bytes:
    host = urllib.parse.urlparse(url).netloc
    wait = 1.0 - (time.time() - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(15_000_000)


# ---------------------------------------------------------------- sitemap index
def build_index(force: bool = False, log=print) -> dict:
    path = CACHE / "sitemap-index.json"
    if path.exists() and not force and time.time() - path.stat().st_mtime < INDEX_MAX_AGE:
        return json.loads(path.read_text())
    pages = {}
    for sm in SITEMAPS:
        try:
            xml = _get(sm).decode("utf-8", "replace")
        except Exception as e:                      # one agency down must not sink the rest
            log(f"  officialweb: sitemap {sm} failed ({type(e).__name__})")
            continue
        for loc, lastmod in re.findall(r"<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?", xml):
            pages[loc.strip()] = lastmod
    docs = {u: _words(urllib.parse.urlparse(u).path.replace("-", " ").replace("/", " ")) for u in pages}
    df = Counter(w for ws in docs.values() for w in set(ws))
    index = {"built": time.strftime("%Y-%m-%d"), "n": len(docs), "df": df,
             "pages": [{"url": u, "lastmod": pages[u], "words": ws} for u, ws in docs.items()]}
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index))
    log(f"  officialweb: indexed {len(docs)} official pages from {len(SITEMAPS)} sitemaps")
    return index


def expand(question: str, department: str | None) -> str:
    """Resident phrasing -> official vocabulary, using the department's own SYNONYMS.json (the same
    keys its corpus retrieval uses), e.g. "selling me her house" -> transfer ownership uncapped."""
    path = REPO / DEPT_DIRS.get(department or "", "-") / "corpus" / "SYNONYMS.json"
    try:
        syn = json.loads(path.read_text())
    except (OSError, ValueError):
        return question
    low = question.lower()
    extra = [t for k, v in syn.items() if not k.startswith("_") and k in low for t in v]
    return question + (" " + " ".join(extra) if extra else "")


def _bigrams(ws: list[str]) -> set[tuple[str, str]]:
    return set(zip(ws, ws[1:]))


def search_index(question: str, index: dict, k: int = 4,
                 department: str | None = None) -> list[tuple[float, str]]:
    qw = _words(question)
    q, qb = set(qw), _bigrams(qw)
    n, df = index["n"], index["df"]
    scope = AGENCIES.get(department or "", ())
    scored = []
    for p in index["pages"]:
        ws = set(p["words"])
        s = sum(math.log(1 + n / (1 + df.get(w, 0))) for w in q & ws)
        if not s:
            continue
        s += 3.0 * len(qb & _bigrams(p["words"]))           # "board of review" as a phrase
        if scope and any(a in p["url"] for a in scope):
            s *= 1.5                                         # the department's own agencies first
        scored.append((s / math.sqrt(len(ws) + 4), p["url"]))   # short, specific paths win
    return sorted(scored, reverse=True)[:k]


# ---------------------------------------------------------------- pages and links
class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((" ".join("".join(self._text).split()), self._href))
            self._href = None


def fetch_page(url: str) -> tuple[str, list[tuple[str, str]], str]:
    """(text, [(anchor, absolute_url)], fetched_date) — cached for PAGE_MAX_AGE."""
    key = CACHE / "pages" / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if key.exists() and time.time() - key.stat().st_mtime < PAGE_MAX_AGE:
        d = json.loads(key.read_text())
        return d["text"], [tuple(x) for x in d["links"]], d["fetched"]
    links = []
    if not url.lower().split("?")[0].endswith(".pdf"):
        try:
            p = _Links()
            p.feed(_get(url).decode("utf-8", "replace"))
            links = [(a, urllib.parse.urljoin(url, h)) for a, h in p.links if a]
        except Exception:
            pass
    text = websearch.fetch_text(url)
    fetched = time.strftime("%Y-%m-%d")
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_text(json.dumps({"url": url, "text": text, "links": links, "fetched": fetched}))
    return text, links, fetched


def _official(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    return any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS)


def citation_urls(text: str) -> list[str]:
    """Statute citations -> their official legislature.mi.gov section pages."""
    # An explicit marker ("MCL 211.27a", "§ 211.27a", "section 211.27a") is required; a bare number
    # ("211.7cc") counts only in a chapter already cited explicitly — "12.50 dollars" is not a statute.
    explicit = MCL_EXPLICIT.findall(text)
    chapters = {ch for ch, _ in explicit}
    found = explicit + [(m[1], m[2]) for m in MCL_BARE.finditer(text)
                        if m[1] in chapters or text[m.end():m.end() + 1] == "("]   # "211.27a(7)(u)"
    out = [f"https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-{ch}-{sec}" for ch, sec in found]
    return list(dict.fromkeys(out))[:3]


# ---------------------------------------------------------------- the lookup
REWRITE_PROMPT = ("You help look up Michigan government information on official state websites "
                  "(michigan.gov, legislature.mi.gov). Rewrite the resident's question as 3 short search "
                  "phrases (2-6 words each) using the official terms a state agency would use (e.g. "
                  "'transfer of ownership', 'principal residence exemption', 'board of review'). One per "
                  "line, no numbering, no explanation.\n\nQuestion: ")


def make_rewriter(llm_cfg: dict):
    """The model under test turns plain-language questions into official search terms (slow, but it
    is what lets resident phrasing reach the right agency page)."""
    from llm_client import chat                           # the department's own client

    def rewrite(question: str) -> list[str]:
        out = chat([{"role": "user", "content": REWRITE_PROMPT + question}],
                   {"llm": dict(llm_cfg, max_tokens=min(llm_cfg.get("max_tokens", 4096), 4096))})
        lines = [re.sub(r"^[\s\-*\d.)]+", "", l).strip().strip('"') for l in out.splitlines()]
        return [l for l in lines if 2 <= len(l.split()) <= 8][:3]
    return rewrite


def official_chunks(question: str, cfg: dict | None = None, log=print,
                    department: str | None = "assessor", rewrite=None) -> list[dict]:
    """Reference chunks from official sources for one question (same shape as websearch chunks)."""
    cfg = cfg or {}
    search_text = expand(question, department)
    phrases = []
    if rewrite:
        try:
            phrases = rewrite(question)
            log(f"  officialweb: model search phrases: {phrases}")
            search_text += " " + " ".join(phrases)
        except Exception as e:                              # lookup still works without it
            log(f"  officialweb: rewrite failed ({type(e).__name__}) — using the question only")
    budget, per_page = cfg.get("char_budget", 18000), cfg.get("passages_per_page", 3)
    targets = [(u, "cited statute") for u in citation_urls(question)]
    # Optional: michigan.gov's own (JavaScript) site search through the headless browser layer.
    if cfg.get("browser"):
        try:
            import browser
            if browser.available():
                for ph in (phrases or [" ".join(_words(question)[:6])])[:2]:
                    for title, u in browser.site_search(ph, k=cfg.get("site_hits", 3)):
                        targets.append((u, f"site search '{ph[:14]}'"))
            else:
                log("  officialweb: browser layer requested but Chrome/poppler not found — skipped")
        except Exception as e:
            log(f"  officialweb: site search failed ({type(e).__name__}: {e})")
    try:
        index = build_index(log=log)
        hits = search_index(search_text, index, k=cfg.get("index_hits", 4), department=department)
        targets += [(u, f"sitemap match {s:.1f}") for s, u in hits]
    except Exception as e:
        log(f"  officialweb: index unavailable ({type(e).__name__}: {e})")
    qwords = set(_words(search_text))
    chunks, used, seen = [], 0, set()

    def add(url, why):
        nonlocal used
        if url in seen or used >= budget:
            return []
        seen.add(url)
        try:
            text, links, fetched = fetch_page(url)
        except Exception as e:
            log(f"  officialweb: skip {url[:90]} ({type(e).__name__})")
            return []
        passages = websearch._passages(text, question, per_page)
        for n, p in enumerate(passages):
            if used + len(p) > budget:
                break
            used += len(p)
            chunks.append({"id": websearch._label(url, n), "source": url, "authority": "WEB-OFFICIAL",
                           "score": 0.0, "web": True,
                           "text": f"(official source, fetched {fetched} from {url})\n{p}"})
        log(f"  officialweb: {why:22s} {len(passages)} passages  {url[:100]}")
        return links

    for url, why in targets:
        links = add(url, why)
        # one hop: follow the page's own best-matching official links (e.g. bulletin PDFs)
        ranked = sorted(((len(qwords & set(_words(a))), a, u) for a, u in links
                         if _official(u) and u not in seen), reverse=True)
        for s, a, u in ranked[: cfg.get("follow_links", 2)]:
            if s >= 2:
                add(u, f"link '{a[:18]}'")
    if not chunks:
        log("  officialweb: NO OFFICIAL PASSAGES found for this question")
    return chunks


def verify_quotes(answer: str, chunks: list[dict]) -> list[str]:
    """Quoted passages (≥ 6 words) in an answer that do NOT appear verbatim in the fetched official
    text — the unverifiable ones. Whitespace and quote styles are normalised."""
    norm = lambda s: re.sub(r"\s+", " ", s.replace("“", '"').replace("”", '"')).strip().lower()
    corpus = norm(" ".join(c["text"] for c in chunks))
    quotes = re.findall(r'["“]([^"”]{20,})["”]', answer)
    return [q for q in quotes if len(q.split()) >= 6 and norm(q) not in corpus]

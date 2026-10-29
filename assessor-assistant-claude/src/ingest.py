#!/usr/bin/env python3
"""Ingest the document corpus into a local BM25 index.

Reads .md/.txt files (and .pdf when the `pdftotext` binary is installed) from the
corpus directory, splits them into paragraph-aligned chunks, and writes a single
index.json containing the chunks plus BM25 term statistics.

Stdlib only. Run:  python3 src/ingest.py
"""

import json
import os
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# "i" is stopped: the first-person pronoun matches the "(i)" subsection labels
# that structured statute chunks carry, which let label noise outrank content.
# "how" is stopped: pure interrogative; it matches OMA/heading chunks ("How
# members of the public may ...") without any topical signal.
STOPWORDS = frozenset(
    """a an and are as at be but by for from has have how i if in into is it its of
    on or shall such that the their there this to was were what which who will
    with""".split()
)

TOKEN_RE = re.compile(r"[a-z0-9]+")

# Authority levels — see corpus/README.md. Docs declare theirs with a line like:
#   AUTHORITY: LAW
AUTHORITY_LEVELS = ("LAW", "STATE-GUIDANCE", "OFFICE-PRACTICE")
AUTHORITY_RE = re.compile(
    r"^AUTHORITY:\s*(LAW|STATE-GUIDANCE|OFFICE-PRACTICE)\b",
    re.IGNORECASE | re.MULTILINE,
)


def detect_authority(text: str) -> str:
    m = AUTHORITY_RE.search(text[:1000])
    return m.group(1).upper() if m else "UNTAGGED"


def load_config() -> dict:
    # MUNI_CONFIG_DIR (optional): read <dir>/<department-folder>.json instead, so several model
    # profiles can be tested in parallel without rewriting the shared config.json.
    alt = os.environ.get("MUNI_CONFIG_DIR")
    if alt:
        return json.loads((Path(alt) / f"{ROOT.name}.json").read_text())
    return json.loads((ROOT / "config.json").read_text())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def read_document(path: Path) -> str | None:
    if path.suffix.lower() in (".md", ".txt"):
        return path.read_text(errors="replace")
    if path.suffix.lower() == ".pdf":
        if shutil.which("pdftotext"):
            out = subprocess.run(
                ["pdftotext", "-layout", str(path), "-"],
                capture_output=True, text=True, timeout=120,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout
            print(f"  WARN: pdftotext produced no text for {path.name} (scanned image? needs OCR)")
            return None
        print(f"  WARN: skipping {path.name} — install poppler-utils (pdftotext) to ingest PDFs")
        return None
    return None


def chunk_text(text: str, source: str, max_chars: int, authority: str = "UNTAGGED") -> list[dict]:
    """Split on paragraph boundaries, packing paragraphs up to max_chars per chunk."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for para in paragraphs:
        # Hard-split pathological paragraphs longer than max_chars.
        while len(para) > max_chars:
            head, para = para[:max_chars], para[max_chars:]
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(head)
        if buf and len(buf) + len(para) + 2 > max_chars:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        chunks.append(buf)
    return [
        {"id": f"{source}#{i}", "source": source, "authority": authority, "text": c}
        for i, c in enumerate(chunks)
    ]


# --------------------------------------------------------------------------- #
# Structured statute chunking (RET-3, brief 18; ported from rag-exp/structured_ingest.py)
#
# LAW documents whose text is statute/rule sections are split one chunk per
# LOWEST-LEVEL subsection, each chunk text prefixed with its full-path label:
#   "MCL 211.27a(7)(u) — beginning december 31, 2014 — (u) Beginning December 31, ..."
#   "R 408.30505 R105.2(a)(x) — (x) Decks, porches, patios, ..."
# so BM25 can serve (7)(u) or deck item (x) directly instead of burying them in a
# multi-thousand-token section chunk. Chunk ids stay sequential name.md#N so
# citations.py LABEL_RE still matches. Everything else keeps the paragraph
# chunking above. Measured in rag-exp (brief 16): GLM 50% -> 73% correct.
# --------------------------------------------------------------------------- #

NBSP = " "
MARKER_RE = re.compile(r"^\((\d{1,3}|[a-z]{1,4}|[A-Z])\)\s")
# " 168.507 Execution of transfer of registration request; ..." / "211.27a Property tax ..."
MCL_HEADER_RE = re.compile(r"^\s{0,24}(\d{1,3}\.\d{1,4}[a-z]{0,2})\s+[A-Z(\"']")
SEC_LINE_RE = re.compile(r"^\s{0,24}Sec\.\s*\d+[A-Za-z]{0,2}\.\s*$")
# " R 408.30505 Work exempt from permit." — title must start with a capital or "Rescinded";
# this rejects wrapped mid-sentence references like "R 408.30880, for any of the following:"
RULE_HEADER_RE = re.compile(r"^\s{0,10}R (\d{3}\.\d{1,5}[a-z]?)\s+([A-Z(\"']|Rescinded|Repealed)")
RULE_LINE_RE = re.compile(r"^\s{0,10}Rule\s+\d+[A-Za-z]{0,2}\.")
AMENDED_RE = re.compile(r"Section (R\d{3}\.\d+[a-z]?)")  # "Rule 505. Section R105.2 ... amended"

PAGE_FOOTER_RES = (
    re.compile(r"^Michigan Compiled Laws Complete Through"),
    re.compile(r"^\s*Rendered\s+\w+day,.*Page \d+ of \d+"),
    re.compile(r"^Courtesy of (legislature\.mi\.gov|Michigan Administrative Rules)\s*$"),
    re.compile(r"^\s*Page \d+(\s+of \d+)?\s*$"),  # bare "Page 3" from the rule PDFs
)

ROMAN = {"ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii", "xiii", "xiv", "xv"}

# Effective-date phrases that earn a place in the chunk label.
DATE_PATTERNS = [
    re.compile(r"(?i)\bbeginning ((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})"),
    re.compile(r"(?i)\bfor taxes levied after ((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})"),
    re.compile(r"(?i)\bon or after ((?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4})"),
]


def norm_line(line: str) -> str:
    return line.replace(NBSP, " ").strip()


def is_letter(tok: str) -> bool:
    return len(tok) == 1 and tok.isalpha() and tok.islower()


def build_paths(tokens):
    """Walk the subsection marker tokens in document order, resolving each to its
    full path. Nesting convention in the MCL/admin code: (1) digits -> (a) letters
    -> (i) romans -> (A) uppercase. The only real ambiguity is a single-letter
    token that could be either a letter sibling or a roman child; resolved by
    lookahead (letters never skip, except (h) -> (i) which is a roman child
    exactly when the next token is (ii)). Ported from rag-exp; rule bodies with
    no digit root take _rule_paths instead."""
    # Admin-code rule bodies have no digit root (their markers start at (a)) and
    # their roman run sits FLAT under the last letter — a different shape from the
    # MCL, so they get their own walk below.
    if tokens and not tokens[0].isdigit():
        return _rule_paths(tokens)
    paths = []
    stack = []
    for idx, tok in enumerate(tokens):
        nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None
        if tok.isdigit():
            stack = [tok]
        elif tok in ROMAN or (len(tok) > 1 and tok.islower()):
            # romans are children of letters; a roman after a roman is a sibling
            if stack and is_letter(stack[-1]):
                stack = stack[:2] if len(stack) >= 2 else stack[:]
            elif stack and stack[-1].isupper():
                stack = stack[:3]
            elif stack and stack[-1] in ROMAN or (stack and len(stack[-1]) > 1 and stack[-1].islower()):
                stack = stack[:2]
            stack.append(tok)
        elif is_letter(tok):
            prev = stack[-1] if stack else None
            if prev is None or prev.isdigit():
                stack = ([prev] if prev else []) + [tok]
            elif prev.isupper():
                stack = stack[:3] + [tok]
            elif is_letter(prev):
                succ = chr(ord(prev) + 1)
                if tok == succ and nxt != tok + "i":
                    stack = [stack[0], tok]              # letter sibling: h -> i -> j
                else:
                    stack = stack[:2] + [tok]            # roman child: g -> i, c -> i, h -> i(ii)
            else:  # prev is a roman
                stack = [stack[0], tok]                  # letter sibling after roman run
        else:  # single uppercase letter, depth 4
            stack = stack[:3] + [tok]
        paths.append(tuple(stack))
    return paths


def _rule_paths(tokens):
    """Paths for admin-code bodies: markers start at (a) with NO digit root, and
    the roman run (i),(ii),(iii)... sits FLAT under the last letter. Letters
    resolve as siblings by alphabetical succession; a letter that is NOT the
    successor of the running letter restarts the run one level up
    ((a)(i)..(x) then (b) is a sibling of (a), not a child of (x))."""
    paths, stack = [], []
    for idx, tok in enumerate(tokens):
        nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None
        if tok.isdigit():
            stack = [tok]
        elif len(tok) > 1 and tok.islower():          # (ii),(iii),(iv) — flat romans
            stack = (stack[:-1] + [tok]) if len(stack) >= 2 else (stack + [tok])
        elif is_letter(tok):
            if tok == "i" and nxt == "ii":            # (h) -> (i) opening a roman run
                stack = stack + [tok]
            else:
                # deepest letter ancestor this token succeeds: (a)->(b) sibling,
                # and (a)(x)->(b) restarts at (a)'s level after the roman run
                placed = False
                for d in range(len(stack) - 1, -1, -1):
                    if is_letter(stack[d]) and tok == chr(ord(stack[d]) + 1):
                        stack = stack[:d] + [tok]
                        placed = True
                        break
                if not placed:
                    if stack and not is_letter(stack[-1]):
                        stack = stack[:-1] + [tok]    # (a)(ii) -> (a)(x): roman tail
                    else:
                        stack = stack + [tok]         # first letter / deeper child
        else:  # single uppercase letter, depth 3
            stack = stack[:2] + [tok]
        paths.append(tuple(stack))
    return paths


def date_label(sub_text: str) -> str:
    for pat in DATE_PATTERNS:
        m = pat.search(sub_text)
        if m:
            return f"— {m.group(0).strip().lower()} — "
    return "— "


def _clean_lines(text: str) -> list[str]:
    """Split to lines, drop PDF page footers — they would otherwise be glued to
    whichever subsection a page break falls in and pollute its text."""
    out = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if any(r.match(stripped) for r in PAGE_FOOTER_RES):
            continue
        out.append(ln)
    return out


def _find_mcl_sections(lines: list[str]) -> list[tuple[int, str]]:
    """[(start_line, mcl_number)] — a candidate `168.507 Title.` header is only
    accepted when a `Sec. N.` line follows within 8 lines, which rejects
    mid-sentence wrapped text like '408.30873 of the Michigan administrative code.'
    The window must absorb long wrapped section titles (168.759's title alone runs
    five lines) — measured: a 4-line window silently DROPPED those sections."""
    secs = []
    for i, ln in enumerate(lines):
        m = MCL_HEADER_RE.match(ln)
        if m and any(SEC_LINE_RE.match(x) for x in lines[i + 1:i + 9]):
            secs.append((i, m.group(1)))
    return secs


def _find_rule_sections(lines: list[str]) -> list[tuple[int, str]]:
    """[(start_line, rule_number)] for admin-code files: a `R 408.30505 Title.`
    header confirmed by a `Rule NNN.` line within 3 lines, or an explicit
    Rescinded/Repealed notice (which has no Rule line)."""
    secs = []
    for i, ln in enumerate(lines):
        m = RULE_HEADER_RE.match(ln)
        if not m:
            continue
        if m.group(2).lower().startswith(("rescinded", "repealed")) or \
                any(RULE_LINE_RE.match(x) for x in lines[i + 1:i + 4]):
            secs.append((i, m.group(1)))
    return secs


def statute_chunks(text: str, source: str, max_chars: int, authority: str):
    """One chunk per lowest-level statute subsection; header text becomes the
    unlabeled chunk(s) #0..k of each section. Returns None when the document has
    no statute/rule section structure (caller falls back to chunk_text)."""
    lines = _clean_lines(text)
    secs = _find_mcl_sections(lines)
    style = "mcl"
    if not secs:
        secs = _find_rule_sections(lines)
        style = "rule"
    if not secs:
        return None

    out: list[dict] = []

    def emit(body: str, label: str | None) -> None:
        if len(body) > max_chars:          # keep a pathological subsection inside
            pieces = [body[i:i + max_chars] for i in range(0, len(body), max_chars)]
        else:
            pieces = [body]                # the prompt-size budget
        for p in pieces:
            txt = (label + p) if label else p
            out.append({"id": f"{source}#{len(out)}", "source": source,
                        "authority": authority, "text": txt})

    for j, (start, number) in enumerate(secs):
        end = secs[j + 1][0] if j + 1 < len(secs) else len(lines)
        block = [norm_line(l) for l in lines[start:end]]
        while block and not block[-1]:
            block.pop()
        markers = []
        for k, b in enumerate(block):
            m = MARKER_RE.match(b)
            if m:
                markers.append((k, m.group(1)))

        if style == "rule":                 # the code section this rule amends, if any
            amended_m = AMENDED_RE.search("\n".join(block[: (markers[0][0] if markers else len(block)) + 1]))
            amended = f" {amended_m.group(1)}" if amended_m else ""
        else:
            amended = ""

        if markers:
            header = "\n".join(block[:markers[0][0]]).strip()
            for h in (p.strip() for p in re.split(r"\n\s*\n", header) if p.strip()):
                emit(h, None)
            paths = build_paths([t for _, t in markers])
            for jj, (k, _tok) in enumerate(markers):
                nxt = markers[jj + 1][0] if jj + 1 < len(markers) else len(block)
                raw = "\n".join(block[k:nxt]).strip()
                path = paths[jj]
                if path:
                    if style == "mcl":
                        head = f"MCL {number}({')('.join(path)}) "
                    else:
                        head = f"R {number}{amended}" + "".join(f"({t})" for t in path) + " "
                    emit(raw, head + date_label(raw))
                else:
                    emit(raw, None)
        else:
            emit("\n".join(block).strip(), None)
    return out


DEF_RE = re.compile(r"\"([^\"]{2,90})\"\s+means")


def build_definitions(chunks: list[dict]) -> dict:
    """Defined-term map {'term' -> chunk id} for retrieval-time definition
    expansion (RET-3). First definition wins, corpus order is deterministic."""
    defs = {}
    for ch in chunks:
        for term in DEF_RE.findall(ch["text"]):
            defs.setdefault(term.strip().lower(), ch["id"])
    return defs


def build_index(chunks: list[dict]) -> dict:
    """Precompute BM25 statistics: term frequencies per chunk, document frequencies."""
    doc_freq: dict[str, int] = {}
    for ch in chunks:
        toks = tokenize(ch["text"])
        ch["length"] = len(toks)
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        ch["tf"] = tf
        for t in tf:
            doc_freq[t] = doc_freq.get(t, 0) + 1
    n = len(chunks)
    avg_len = (sum(c["length"] for c in chunks) / n) if n else 0.0
    idf = {
        t: math.log(1 + (n - df + 0.5) / (df + 0.5))
        for t, df in doc_freq.items()
    }
    return {"chunks": chunks, "idf": idf, "avg_len": avg_len, "n_chunks": n}


def main() -> int:
    cfg = load_config()
    corpus_dir = ROOT / cfg["paths"]["corpus_dir"]
    index_file = ROOT / cfg["paths"]["index_file"]
    max_chars = cfg["retrieval"]["max_chunk_chars"]

    docs = sorted(
        p for p in corpus_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in (".md", ".txt", ".pdf")
        and p.name != index_file.name
        and p.name.lower() not in ("readme.md", "localization.md")  # instructions for humans, not reference material
    )
    if not docs:
        print(f"No documents found in {corpus_dir}. Add .md/.txt/.pdf files and rerun.")
        return 1

    all_chunks: list[dict] = []
    n_structured = 0
    for path in docs:
        text = read_document(path)
        if not text:
            continue
        rel = str(path.relative_to(corpus_dir))
        authority = detect_authority(text)
        if authority == "UNTAGGED":
            print(f"  WARN: {rel} has no AUTHORITY: line — treated as UNTAGGED "
                  f"(see corpus/README.md)")
        # RET-3: LAW docs that are statute/rule text get one chunk per lowest-level
        # subsection (labelled with the full path); everything else paragraph-chunks.
        chunks = statute_chunks(text, rel, max_chars, authority) \
            if authority == "LAW" else None
        kind = "structured"
        if not chunks:
            chunks = chunk_text(text, rel, max_chars, authority)
            kind = "paragraph"
        else:
            n_structured += 1
        all_chunks.extend(chunks)
        print(f"  ingested {rel} [{authority}] {kind}: {len(chunks)} chunks")

    index = build_index(all_chunks)
    index["definitions"] = build_definitions(all_chunks)   # RET-3 definition expansion
    index["meta"] = {"structured_statute_files": n_structured}
    index_file.write_text(json.dumps(index))
    size_kb = index_file.stat().st_size / 1024
    print(f"Index written: {index_file} ({index['n_chunks']} chunks, {size_kb:.0f} KB; "
          f"{n_structured} statute files structured subsection-per-chunk, "
          f"{len(index['definitions'])} defined terms mapped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

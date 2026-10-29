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

STOPWORDS = frozenset(
    """a an and are as at be but by for from has have if in into is it its of on or
    shall such that the their there this to was were what which who will with""".split()
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
    for path in docs:
        text = read_document(path)
        if not text:
            continue
        rel = str(path.relative_to(corpus_dir))
        authority = detect_authority(text)
        if authority == "UNTAGGED":
            print(f"  WARN: {rel} has no AUTHORITY: line — treated as UNTAGGED "
                  f"(see corpus/README.md)")
        chunks = chunk_text(text, rel, max_chars, authority)
        all_chunks.extend(chunks)
        print(f"  ingested {rel} [{authority}]: {len(chunks)} chunks")

    index = build_index(all_chunks)
    index_file.write_text(json.dumps(index))
    size_kb = index_file.stat().st_size / 1024
    print(f"Index written: {index_file} ({index['n_chunks']} chunks, {size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

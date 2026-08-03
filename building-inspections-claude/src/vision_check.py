#!/usr/bin/env python3
"""Construction-photo screening against visible-condition checklists.

Sends one or more photos plus a per-inspection-type checklist to a local vision
LLM (any OpenAI-compatible multimodal server, e.g. llama-server with --mmproj)
and returns a structured screening report. Output is ALWAYS a draft for a
registered inspector — this tool never determines compliance.

Usage:
  python3 src/vision_check.py framing photo1.jpg [photo2.jpg ...]
  python3 src/vision_check.py final site.jpg --notes "final for CO, 123 Main St"
  python3 src/vision_check.py electrical_rough panel.jpg --json   # raw JSON out
  python3 src/vision_check.py framing photo.jpg --dry-run         # prompt only
Inspection types: footing framing electrical_rough plumbing_rough insulation final
"""

import argparse
import base64
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import ROOT, load_config                     # noqa: E402
from llm_client import LLMError, chat, extract_json      # noqa: E402
from prompts import (VISION_SYSTEM, INSPECTION_CHECKLISTS,  # noqa: E402
                     build_vision_prompt)

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp"}


def encode_image(path: Path, max_bytes: int) -> dict:
    if path.suffix.lower() not in MIME:
        raise SystemExit(f"{path.name}: unsupported type (use jpg/png/webp)")
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise SystemExit(
            f"{path.name} is {len(data)} bytes (limit {max_bytes}). Resize it — "
            f"e.g.: convert '{path}' -resize 2000x2000\\> smaller.jpg"
        )
    b64 = base64.standard_b64encode(data).decode()
    return {"type": "image_url",
            "image_url": {"url": f"data:{MIME[path.suffix.lower()]};base64,{b64}"}}


def vision_chat(messages: list[dict], cfg: dict) -> str:
    """Chat against the vision endpoint via the shared client (config override)."""
    return chat(messages, {"llm": cfg["vision"]})


def solid_png(r: int, g: int, b: int, size: int = 64) -> bytes:
    """Generate a solid-color PNG with the stdlib (for the calibration probe)."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes((r, g, b)) * size
    idat = zlib.compress(row * size)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def calibration_probe(cfg: dict) -> None:
    """Guard against the SILENT NO-IMAGE failure mode.

    A text-only server (no --mmproj) may accept an image_url request and answer
    fluently from the text alone — producing a confident screening report about a
    photo nobody ever looked at. Before any real screening, send a solid red PNG
    and require the model to name its color. Wrong answer = the server is not
    actually seeing images = abort.
    """
    png = solid_png(220, 30, 30)
    b64 = base64.standard_b64encode(png).decode()
    content = [
        {"type": "text",
         "text": "Reply with only the dominant color of this image, one word."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ]
    try:
        reply = vision_chat([{"role": "user", "content": content}], cfg)
    except LLMError as e:
        raise SystemExit(f"Calibration probe failed to reach the vision server: {e}")
    if "red" not in reply.lower():
        raise SystemExit(
            "CALIBRATION FAILED: the server did not identify a solid red test image "
            f"(reply: {reply.strip()[:120]!r}).\n"
            "The endpoint is almost certainly NOT processing images (text-only model, "
            "or llama-server missing --mmproj). A screening run against it would "
            "produce confident output about photos it never saw. Fix the server "
            "before screening. (Bypass at your own risk: --skip-calibration.)")
    print("calibration probe: OK (server is seeing images)")


def normalize_report(v: dict) -> dict:
    """Coerce a raw vision report to the canonical shape (string-discipline:
    the same lesson as the assessor project's normalize_verdict)."""
    out = dict(v)
    q = str(v.get("image_quality", "")).strip().casefold()
    out["image_quality"] = q if q in ("good", "limited", "poor") else "poor"
    out["observations"] = [str(x) for x in (v.get("observations") or [])]
    concerns = []
    for c in (v.get("possible_concerns") or []):
        if not isinstance(c, dict):
            c = {"concern": str(c)}
        conf = str(c.get("confidence", "")).strip().casefold()
        concerns.append({
            "concern": str(c.get("concern", "")),
            "visible_evidence": str(c.get("visible_evidence", "")),
            "checklist_item": str(c.get("checklist_item", "not on checklist")),
            "confidence": conf if conf in ("high", "medium", "low") else "low",
        })
    out["possible_concerns"] = concerns
    out["cannot_verify_from_photo"] = [str(x) for x in (v.get("cannot_verify_from_photo") or [])]
    out["recommended_inspector_actions"] = [str(x) for x in (v.get("recommended_inspector_actions") or [])]
    return out


def render_report(report: dict, images: list[str], insp_type: str) -> str:
    lines = [
        "=" * 70,
        "DRAFT PHOTO SCREENING — REGISTERED INSPECTOR REVIEW REQUIRED",
        "This is a screening aid. It does not and cannot determine code",
        "compliance. Pass/fail is the inspector's call, on site.",
        "=" * 70,
        f"Inspection type: {insp_type}   Images: {', '.join(images)}",
        f"Image quality: {report.get('image_quality', '?')}",
        "",
        "VISIBLE OBSERVATIONS:",
    ]
    lines += [f"  - {o}" for o in report.get("observations", [])] or ["  (none)"]
    lines.append("")
    concerns = report.get("possible_concerns", [])
    lines.append(f"POSSIBLE CONCERNS FLAGGED ({len(concerns)}):")
    for c in concerns:
        lines.append(f"  ⚑ [{c.get('confidence', '?')}] {c.get('concern', '')}")
        lines.append(f"      evidence: {c.get('visible_evidence', '')}")
        lines.append(f"      checklist: {c.get('checklist_item', '')}")
    if not concerns:
        lines.append("  (none flagged — this is NOT a pass; see limits below)")
    lines.append("")
    lines.append("CANNOT BE VERIFIED FROM PHOTOS (check on site):")
    lines += [f"  - {x}" for x in report.get("cannot_verify_from_photo", [])] or ["  (none listed)"]
    lines.append("")
    lines.append("RECOMMENDED INSPECTOR ACTIONS:")
    lines += [f"  - {x}" for x in report.get("recommended_inspector_actions", [])] or ["  (none listed)"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Screen construction photos (draft aid)")
    ap.add_argument("inspection_type", nargs="?", choices=sorted(INSPECTION_CHECKLISTS))
    ap.add_argument("images", nargs="*", help="photo file(s): jpg/png/webp")
    ap.add_argument("--notes", default="", help="context notes for the model")
    ap.add_argument("--json", action="store_true", help="print raw JSON report")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the assembled prompt; no model call")
    ap.add_argument("--calibrate", action="store_true",
                    help="run only the image-visibility probe and exit")
    ap.add_argument("--skip-calibration", action="store_true",
                    help="skip the probe (NOT recommended)")
    args = ap.parse_args()

    cfg = load_config()
    if args.calibrate:
        calibration_probe(cfg)
        return 0
    if not args.inspection_type or not args.images:
        ap.error("inspection_type and at least one image are required "
                 "(unless using --calibrate)")
    user_prompt = build_vision_prompt(args.inspection_type, args.notes)
    if args.dry_run:
        print(VISION_SYSTEM)
        print("-" * 70)
        print(user_prompt)
        return 0

    if not args.skip_calibration:
        calibration_probe(cfg)

    content = [{"type": "text", "text": user_prompt}]
    for img in args.images:
        content.append(encode_image(Path(img), cfg["vision"]["max_image_bytes"]))

    t0 = time.time()
    raw = vision_chat([
        {"role": "system", "content": VISION_SYSTEM},
        {"role": "user", "content": content},
    ], cfg)
    secs = round(time.time() - t0, 1)

    try:
        report = normalize_report(extract_json(raw))
    except ValueError:
        print("Model response was not parseable JSON — raw output follows.\n")
        print(raw)
        return 1

    # Persist every screening for the eval trail.
    results = ROOT / cfg["paths"]["results_dir"]
    results.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = results / f"vision-{args.inspection_type}-{ts}.json"
    out.write_text(json.dumps({
        "ts": ts, "inspection_type": args.inspection_type,
        "images": args.images, "notes": args.notes,
        "seconds": secs, "report": report,
    }, indent=2))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_report(report, args.images, args.inspection_type))
    print(f"\n({secs}s — saved {out.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

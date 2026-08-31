#!/usr/bin/env python3
"""Render a GlyphMatics VIL JSONL corpus as literal, visible image pages only."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont


FONT_CANDIDATES = (
    "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/system/fonts/RobotoMono-Regular.ttf",
    "/system/fonts/DroidSansMono.ttf",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def choose_font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def visible_lines(record: dict[str, Any], width: int) -> list[str]:
    output = record["output"]
    metadata = record["metadata"]
    header = [
        "pIMAGEVIL1",
        f"ID {record['id']}",
        f"GLYPHS {'>'.join(output['glyph_sequence'])}",
        f"SOURCE {metadata['source_repository']}::{metadata['source_path']}",
        f"SHA256 {output['source_sha256']}",
        f"PRIVACY {'PRIVATE' if metadata['source_private'] else 'PUBLIC'}",
        "BEGIN_LITERAL_SOURCE",
    ]
    source = record["input"]["source_text"].replace("\t", "    ")
    body: list[str] = []
    for line in source.splitlines() or [""]:
        wrapped = textwrap.wrap(
            line, width=width, replace_whitespace=False, drop_whitespace=False,
            break_long_words=True, break_on_hyphens=False,
        )
        body.extend(wrapped or [""])
    return header + body + ["END_LITERAL_SOURCE", "pIMAGEVIL_CLOSE"]


def render_page(lines: list[str], output: Path, *, font_size: int, columns: int) -> dict[str, Any]:
    font = choose_font(font_size)
    line_height = max(font_size + 5, 16)
    margin = 24
    width = max(768, margin * 2 + int(columns * font_size * 0.64))
    height = margin * 2 + line_height * len(lines)
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    y = margin
    for line in lines:
        draw.text((margin, y), line, font=font, fill=0)
        y += line_height
    output.parent.mkdir(parents=True, exist_ok=True)
    # Fast lossless compression keeps bounded mobile build batches practical.
    image.save(output, format="PNG", compress_level=3)
    data = output.read_bytes()
    return {"path": output.as_posix(), "sha256": sha256(data), "bytes": len(data), "width": width, "height": height}


def records(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def valid_index_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and entry.get("id") and entry.get("images"):
            entries.append(entry)
    return entries


def build(
    source: Path, output: Path, *, lines_per_page: int = 64, columns: int = 108,
    font_size: int = 14, resume: bool = False, max_records: int = 0,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    index_path = output / "index.jsonl"
    completed: set[str] = set()
    if resume and index_path.exists():
        completed = {entry["id"] for entry in valid_index_entries(index_path)}
    counts = Counter()
    image_bytes = 0
    private_images = 0
    processed_now = 0
    with index_path.open("a" if resume else "w", encoding="utf-8", buffering=1) as index:
        for split in ("train", "validation", "test"):
            for record in records(source / f"{split}.jsonl.gz"):
                if record["id"] in completed:
                    continue
                if max_records and processed_now >= max_records:
                    break
                lines = visible_lines(record, columns)
                pages = []
                for page_number, start in enumerate(range(0, len(lines), lines_per_page)):
                    relative = Path(split) / record["id"] / f"page-{page_number:04d}.png"
                    info = render_page(
                        lines[start:start + lines_per_page], output / relative,
                        font_size=font_size, columns=columns,
                    )
                    info["path"] = relative.as_posix()
                    pages.append(info)
                    image_bytes += info["bytes"]
                    counts["images"] += 1
                    private_images += int(record["metadata"]["source_private"])
                entry = {
                    "id": record["id"], "split": split, "images": pages,
                    "source_repository": record["metadata"]["source_repository"],
                    "source_path": record["metadata"]["source_path"],
                    "source_private": record["metadata"]["source_private"],
                    "source_sha256": record["output"]["source_sha256"],
                    "record_hash": record["record_hash"],
                }
                index.write(json.dumps(entry, ensure_ascii=False) + "\n")
                index.flush()
                counts["records"] += 1
                counts[split] += 1
                processed_now += 1
            if max_records and processed_now >= max_records:
                break
    entries = valid_index_entries(index_path)
    # A resumed partial record may overwrite an earlier PNG with equivalent
    # pixels but a different lossless compression level. Reconcile the index
    # against the final on-disk bytes and atomically discard partial rows.
    for entry in entries:
        for page in entry["images"]:
            image_path = output / page["path"]
            data = image_path.read_bytes()
            page["sha256"] = sha256(data)
            page["bytes"] = len(data)
    repaired_index = index_path.with_suffix(".jsonl.tmp")
    repaired_index.write_text(
        "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries),
        encoding="utf-8",
    )
    repaired_index.replace(index_path)
    counts = Counter(entry["split"] for entry in entries)
    all_pages = [page for entry in entries for page in entry["images"]]
    image_bytes = sum(page["bytes"] for page in all_pages)
    private_images = sum(len(entry["images"]) for entry in entries if entry["source_private"])
    manifest = {
        "format": "GlyphMatics Literal Image-Only VIL Dataset",
        "version": "1.0.0",
        "transport": "visible grayscale PNG text; no hidden payload or byte-to-glyph wrapper",
        "model_input": "image_only",
        "records": len(entries),
        "images": len(all_pages),
        "splits": {name: counts[name] for name in ("train", "validation", "test")},
        "private_images": private_images,
        "image_bytes": image_bytes,
        "lines_per_page": lines_per_page,
        "columns": columns,
        "font_size": font_size,
        "source_manifest_sha256": json.loads((source / "manifest.json").read_text())["manifest_sha256"],
        "privacy": "Contains rasterized private-source material; keep private unless reviewed.",
        "complete": len(entries) == json.loads((source / "manifest.json").read_text())["total_records"],
    }
    manifest["index_sha256"] = sha256(index_path.read_bytes())
    manifest["manifest_sha256"] = sha256(json.dumps(manifest, sort_keys=True).encode())
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lines-per-page", type=int, default=64)
    parser.add_argument("--columns", type=int, default=108)
    parser.add_argument("--font-size", type=int, default=14)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-records", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(build(
        args.source, args.output, lines_per_page=args.lines_per_page,
        columns=args.columns, font_size=args.font_size,
        resume=args.resume, max_records=args.max_records,
    ), indent=2))


if __name__ == "__main__":
    main()

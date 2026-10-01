#!/usr/bin/env python3
"""Inventory a creative-work folder for evidence-led portfolio planning."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

TEXT = {".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".html", ".xml", ".srt", ".vtt", ".fountain"}
DOCUMENT = {".pdf", ".docx", ".pptx", ".odt", ".rtf"}
IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".heic", ".gif", ".svg", ".psd", ".ai", ".eps"}
VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
AUDIO = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aiff"}
NATIVE = {".indd", ".idml", ".prproj", ".drp", ".aep", ".blend", ".fig", ".sketch"}
SKIP_DIRS = {".git", ".indesign-portfolio", "__pycache__", "node_modules", ".venv", "venv"}


def kind_for(suffix: str) -> str:
    for name, extensions in (("text", TEXT), ("document", DOCUMENT), ("image", IMAGE), ("video", VIDEO), ("audio", AUDIO), ("native_project", NATIVE)):
        if suffix in extensions:
            return name
    return "other"


def _xml_text(raw: bytes, paragraph_tag: str, text_tag: str, limit: int) -> str:
    root = ElementTree.fromstring(raw)
    lines = []
    length = 0
    for paragraph in root.iter():
        if paragraph.tag.rsplit("}", 1)[-1] != paragraph_tag:
            continue
        line = "".join(node.text or "" for node in paragraph.iter() if node.tag.rsplit("}", 1)[-1] == text_tag).strip()
        if line:
            lines.append(line)
            length += len(line)
            if length >= limit:
                break
    return "\n".join(lines)[:limit]


def extract_text(path: Path, suffix: str, limit: int) -> tuple[str, str]:
    try:
        if suffix in TEXT:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                return stream.read(limit), "extracted"
        if suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                return _xml_text(archive.read("word/document.xml"), "p", "t", limit), "extracted"
        if suffix == ".pptx":
            with zipfile.ZipFile(path) as archive:
                slides = sorted((n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                                key=lambda n: int(re.search(r"slide(\d+)", n).group(1)))
                chunks = []
                remaining = limit
                for name in slides:
                    chunk = _xml_text(archive.read(name), "p", "t", remaining)
                    if chunk:
                        chunks.append(chunk)
                        remaining -= len(chunk)
                    if remaining <= 0:
                        break
                return "\n".join(chunks)[:limit], "extracted"
        if suffix == ".pdf":
            program = shutil.which("pdftotext")
            if program:
                result = subprocess.run([program, "-f", "1", "-l", "5", "-layout", str(path), "-"],
                                        capture_output=True, timeout=25)
                if result.returncode == 0:
                    text = result.stdout.decode("utf-8", errors="replace")[:limit]
                    return text, "extracted" if text.strip() else "requires_ocr_or_visual_review"
            return "", "requires_pdf_review"
        if suffix in DOCUMENT:
            return "", "requires_document_review"
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError, subprocess.TimeoutExpired) as exc:
        return "", "extraction_error: " + str(exc)[:180]
    return "", "not_applicable"


def image_size(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            prefix = stream.read(32)
            if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
                width, height = struct.unpack(">II", prefix[16:24])
                return {"width": width, "height": height}
            if prefix[:2] == b"\xff\xd8":
                stream.seek(2)
                while True:
                    marker = stream.read(1)
                    if not marker:
                        break
                    if marker != b"\xff":
                        continue
                    code = stream.read(1)
                    if code in {b"\xd8", b"\xd9"}:
                        continue
                    raw_length = stream.read(2)
                    if len(raw_length) != 2:
                        break
                    segment_length = struct.unpack(">H", raw_length)[0]
                    if segment_length < 2:
                        break
                    if code in {bytes([x]) for x in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)}:
                        dimensions = stream.read(5)
                        if len(dimensions) == 5:
                            height, width = struct.unpack(">HH", dimensions[1:])
                            return {"width": width, "height": height}
                        break
                    stream.seek(segment_length - 2, 1)
    except OSError:
        pass
    return {}


def media_info(path: Path) -> dict:
    program = shutil.which("ffprobe")
    if not program:
        return {}
    try:
        result = subprocess.run([program, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            return {}
        data = json.loads(result.stdout)
        info = {}
        duration = data.get("format", {}).get("duration")
        if duration is not None:
            info["duration_seconds"] = round(float(duration), 2)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and stream.get("width") and stream.get("height"):
                info["width"] = stream["width"]
                info["height"] = stream["height"]
                break
        return info
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}


def scan(folder: Path, *, max_files: int = 5000, max_text_chars: int = 6000) -> dict:
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"Folder does not exist: {folder}")
    files = []
    counts = Counter()
    groups = defaultdict(lambda: {"files": 0, "kinds": Counter()})
    for current, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".") and not (Path(current) / d).is_symlink())
        for name in sorted(names):
            if name.startswith("."):
                continue
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            if len(files) >= max_files:
                raise ValueError(f"More than {max_files} files; narrow the folder or raise --max-files")
            relative = path.relative_to(folder)
            suffix = path.suffix.lower()
            kind = kind_for(suffix)
            stat = path.stat()
            group = relative.parts[0] if len(relative.parts) > 1 else "(root files; grouping requires review)"
            excerpt, text_status = extract_text(path, suffix, max_text_chars)
            metadata = image_size(path) if suffix in {".png", ".jpg", ".jpeg"} else {}
            if kind in {"video", "audio"}:
                metadata.update(media_info(path))
            files.append({
                "path": str(path.resolve()),
                "relative_path": relative.as_posix(),
                "group_hint": group,
                "kind": kind,
                "extension": suffix,
                "bytes": stat.st_size,
                "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "metadata": metadata,
                "text_status": text_status,
                "text_excerpt": excerpt,
            })
            counts[kind] += 1
            groups[group]["files"] += 1
            groups[group]["kinds"][kind] += 1
    return {
        "schema_version": 1,
        "source_folder": str(folder),
        "scanned_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "kind_counts": dict(counts),
        "groups": {name: {"files": value["files"], "kinds": dict(value["kinds"])} for name, value in groups.items()},
        "group_hints_are_provisional": True,
        "files": files,
    }


def coverage_ledger(inventory: dict) -> dict:
    """Give every discovered file a review slot before editorial selection."""
    return {
        "schema_version": 1,
        "source_folder": inventory["source_folder"],
        "decisions": [
            {
                "relative_path": item["relative_path"],
                "group_hint": item["group_hint"],
                "project": "",
                "status": "unreviewed",
                "reason": "",
                "inspection_status": "pending",
                "inspection_note": "",
            }
            for item in inventory["files"]
        ],
        "status_values": ["selected", "supporting", "duplicate", "excluded", "unreadable", "unreviewed"],
    }


def merge_coverage_ledger(fresh: dict, ledger_path: Path) -> dict:
    if not ledger_path.is_file():
        return fresh
    try:
        previous = json.loads(ledger_path.read_text(encoding="utf-8"))
        if previous.get("source_folder") != fresh["source_folder"]:
            raise ValueError("Existing coverage ledger belongs to a different source folder")
        reviewed = {item["relative_path"]: item for item in previous["decisions"]}
        for item in fresh["decisions"]:
            old = reviewed.get(item["relative_path"])
            if old and old.get("status") in fresh["status_values"]:
                item.update({key: old.get(key, "") for key in
                             ("project", "status", "reason", "inspection_status", "inspection_note")})
        return fresh
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot preserve existing coverage ledger: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ledger-output", type=Path, help="Coverage ledger path; defaults beside the inventory")
    parser.add_argument("--max-files", type=int, default=5000)
    parser.add_argument("--max-text-chars", type=int, default=6000)
    args = parser.parse_args(argv)
    try:
        if args.max_files < 1 or args.max_text_chars < 1:
            raise ValueError("Limits must be positive")
        result = scan(args.folder, max_files=args.max_files, max_text_chars=args.max_text_chars)
        output = args.output or Path(result["source_folder"]) / ".indesign-portfolio" / "inventory.json"
        output = output.expanduser().resolve()
        ledger_output = (args.ledger_output or output.with_name("coverage-ledger.json")).expanduser().resolve()
        if ledger_output == output:
            raise ValueError("Inventory and coverage ledger paths must differ")
        ledger = merge_coverage_ledger(coverage_ledger(result), ledger_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        ledger_output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        ledger_output.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"inventory": str(output), "coverage_ledger": str(ledger_output),
                          "files": result["file_count"], "groups": len(result["groups"]), "kinds": result["kind_counts"]}))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

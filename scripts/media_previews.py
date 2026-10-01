#!/usr/bin/env python3
"""Prepare visual review paths and sampled frames for every media work."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

MEDIA_KINDS = {"image", "video", "audio", "native_project"}
DIRECT_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def frame_times(duration: float | None) -> list[float]:
    if not duration or duration <= 0:
        return [0.1]
    count = min(8, max(3, math.ceil(duration / 30)))
    return [duration * (index + 0.5) / count for index in range(count)]


def prepare(inventory: dict, output_dir: Path, *, ffmpeg: str | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg if ffmpeg is not None else shutil.which("ffmpeg")
    entries = []
    for item in inventory["files"]:
        kind = item.get("kind")
        ext = item.get("extension")
        if kind not in MEDIA_KINDS and ext != ".pdf":
            continue
        source = Path(item["path"])
        entry = {"relative_path": item["relative_path"], "kind": kind,
                 "source": str(source), "preview_paths": [], "review_method": ""}
        if kind == "image" and ext in DIRECT_IMAGES:
            entry["preview_paths"] = [str(source)]
            entry["review_method"] = "open_original_image"
        elif kind == "video" and ffmpeg:
            duration = item.get("metadata", {}).get("duration_seconds")
            prefix = hashlib.sha256(item["relative_path"].encode("utf-8")).hexdigest()[:12]
            errors = []
            for index, seconds in enumerate(frame_times(duration), 1):
                target = output_dir / f"{prefix}-frame-{index:02d}.jpg"
                command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{seconds:.3f}",
                           "-i", str(source), "-frames:v", "1", "-vf", "scale=1280:-2", str(target)]
                try:
                    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0 and target.is_file() and target.stat().st_size:
                        entry["preview_paths"].append(str(target))
                    else:
                        errors.append((result.stderr or "Frame extraction failed")[:160])
                except (OSError, subprocess.TimeoutExpired) as exc:
                    errors.append(str(exc)[:160])
            entry["review_method"] = "sampled_frames_plus_playback"
            if errors:
                entry["warning"] = errors[0]
        elif kind == "video":
            entry["review_method"] = "play_or_extract_frames_manually_ffmpeg_unavailable"
        elif kind == "audio":
            entry["review_method"] = "listen_or_transcribe_original"
        else:
            entry["review_method"] = "open_in_native_app_or_export_visual_preview"
        entries.append(entry)
    return {"source_folder": inventory["source_folder"], "entries": entries,
            "note": "Previews aid human/agent visual review; they do not analyze content or replace viewing every work."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        output_dir = (args.output_dir or args.inventory.parent / "previews").expanduser().resolve()
        manifest = prepare(inventory, output_dir)
        target = output_dir / "preview-manifest.json"
        target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"manifest": str(target), "media_files": len(manifest["entries"])}))
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

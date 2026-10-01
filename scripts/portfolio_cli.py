#!/usr/bin/env python3
"""Validate a portfolio spec and prepare/run its InDesign ExtendScript builder."""

from __future__ import annotations

import argparse
import base64
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "assets" / "portfolio_builder.jsx"
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class SpecError(ValueError):
    pass


def _string(value: object, label: str, *, optional: bool = False) -> str:
    if value is None and optional:
        return ""
    if not isinstance(value, str) or (not optional and not value.strip()):
        raise SpecError(f"{label} must be a nonempty string")
    return value.strip()


def _color(value: object, label: str) -> str:
    if not isinstance(value, str) or not COLOR.fullmatch(value):
        raise SpecError(f"{label} must be a 6-digit hex color, such as #192A40")
    return value.upper()


def _number(value: object, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise SpecError(f"{label} must be between {minimum} and {maximum}")
    return float(value)


def _path(value: object, label: str, base: Path, *, must_exist: bool = False) -> str:
    raw = _string(value, label)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if must_exist and not path.is_file():
        raise SpecError(f"{label} does not exist: {path}")
    return str(path)


def load_spec(spec_path: Path) -> dict:
    spec_path = spec_path.expanduser().resolve()
    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"Cannot read spec: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError("Top level must be a JSON object")

    base = spec_path.parent
    page = data.get("page", {})
    theme = data.get("theme", {})
    profile = data.get("profile", {})
    output = data.get("output", {})
    projects = data.get("projects")
    for name, value in (("page", page), ("theme", theme), ("profile", profile), ("output", output)):
        if not isinstance(value, dict):
            raise SpecError(f"{name} must be an object")
    if not isinstance(projects, list) or not projects:
        raise SpecError("projects must be a nonempty array")

    width = _number(page.get("width_pt", 595.28), "page.width_pt", 300, 1500)
    height = _number(page.get("height_pt", 841.89), "page.height_pt", 300, 1500)
    margin = _number(page.get("margin_pt", 48), "page.margin_pt", 18, min(width, height) / 4)

    colors = {
        key: _color(theme.get(key, default), f"theme.{key}")
        for key, default in (
            ("background", "#F7F5F0"),
            ("text", "#17202A"),
            ("accent", "#B85839"),
            ("muted", "#66717B"),
        )
    }
    fonts = {
        "regular": _string(theme.get("font_regular", "Arial"), "theme.font_regular"),
        "bold": _string(theme.get("font_bold", "Arial Bold"), "theme.font_bold"),
    }

    normalized_profile = {
        "name": _string(profile.get("name"), "profile.name"),
        "headline": _string(profile.get("headline"), "profile.headline"),
        "bio": _string(profile.get("bio", ""), "profile.bio", optional=True),
        "contact": [],
        "hero_image": "",
    }
    contact = profile.get("contact", [])
    if not isinstance(contact, list) or any(not isinstance(x, str) for x in contact):
        raise SpecError("profile.contact must be an array of strings")
    normalized_profile["contact"] = [x.strip() for x in contact if x.strip()]
    if profile.get("hero_image"):
        normalized_profile["hero_image"] = _path(profile["hero_image"], "profile.hero_image", base, must_exist=True)

    normalized_projects = []
    for i, project in enumerate(projects):
        label = f"projects[{i}]"
        if not isinstance(project, dict):
            raise SpecError(f"{label} must be an object")
        images = project.get("images", [])
        if not isinstance(images, list) or len(images) > 2:
            raise SpecError(f"{label}.images must contain at most two image paths")
        facts = project.get("facts", [])
        if not isinstance(facts, list) or any(not isinstance(x, str) for x in facts):
            raise SpecError(f"{label}.facts must be an array of strings")
        hero = project.get("hero_image")
        normalized_projects.append({
            "title": _string(project.get("title"), f"{label}.title"),
            "subtitle": _string(project.get("subtitle", ""), f"{label}.subtitle", optional=True),
            "year": _string(project.get("year", ""), f"{label}.year", optional=True),
            "role": _string(project.get("role", ""), f"{label}.role", optional=True),
            "summary": _string(project.get("summary"), f"{label}.summary"),
            "facts": [x.strip() for x in facts if x.strip()],
            "hero_image": _path(hero, f"{label}.hero_image", base, must_exist=True) if hero else "",
            "images": [_path(x, f"{label}.images[{j}]", base, must_exist=True) for j, x in enumerate(images)],
        })

    indd = Path(_path(output.get("indd"), "output.indd", base))
    pdf = Path(_path(output.get("pdf"), "output.pdf", base))
    report = Path(_path(output.get("report", "portfolio-report.json"), "output.report", base))
    if indd.suffix.lower() != ".indd" or pdf.suffix.lower() != ".pdf" or report.suffix.lower() != ".json":
        raise SpecError("Output paths must end in .indd, .pdf, and .json respectively")
    if len({indd, pdf, report, spec_path}) != 4:
        raise SpecError("Input and output paths must be distinct")

    return {
        "title": _string(data.get("title", "Portfolio"), "title"),
        "page": {"width_pt": width, "height_pt": height, "margin_pt": margin},
        "theme": {**colors, **fonts},
        "profile": normalized_profile,
        "projects": normalized_projects,
        "output": {"indd": str(indd), "pdf": str(pdf), "report": str(report)},
    }


def find_indesign() -> Path | None:
    if platform.system() != "Darwin":
        return None
    return next(iter(sorted(Path("/Applications").glob("Adobe InDesign*/Adobe InDesign*.app"), reverse=True)), None)


def windows_com_registered() -> bool:
    if platform.system() != "Windows":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "InDesign.Application"):
            return True
    except (OSError, ImportError):
        return False


def prepare(spec: dict, runner: Path, *, force: bool = False) -> Path:
    runner = runner.expanduser().resolve()
    if runner.exists() and not force:
        header = runner.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
        if not header or header[0] != "// Generated by indesign-portfolio. Edit portfolio.json, then prepare again.":
            raise SpecError(f"Runner is not generated by this skill: {runner} (pass --force to replace it)")
    runner.parent.mkdir(parents=True, exist_ok=True)
    for path in spec["output"].values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    literal = json.dumps(spec, ensure_ascii=True, separators=(",", ":"))
    runner.write_text(
        "// Generated by indesign-portfolio. Edit portfolio.json, then prepare again.\n"
        + "var PORTFOLIO_SPEC = " + literal + ";\n"
        + "var PORTFOLIO_FORCE = " + ("true" if force else "false") + ";\n"
        + BUILDER.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return runner


def run_mac(runner: Path) -> None:
    if find_indesign() is None:
        raise SpecError("Adobe InDesign is not installed in /Applications. Run the generated JSX from InDesign's Scripts panel after installing it.")
    escaped = str(runner).replace("\\", "\\\\").replace('"', '\\"')
    apple_script = f'tell application id "com.adobe.InDesign" to do script (POSIX file "{escaped}") language javascript'
    completed = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True, timeout=300)
    if completed.returncode:
        raise SpecError((completed.stderr or completed.stdout).strip() or "InDesign script failed")


def windows_powershell_script(runner: Path) -> str:
    literal_path = str(runner).replace("'", "''")
    return (
        "$ErrorActionPreference = 'Stop'\n"
        "$app = New-Object -ComObject InDesign.Application\n"
        f"$jsx = Get-Content -LiteralPath '{literal_path}' -Raw -Encoding UTF8\n"
        "$app.DoScript($jsx, 1246973031) | Out-Null\n"
    )


def run_windows(runner: Path) -> None:
    script = windows_powershell_script(runner)
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-EncodedCommand", encoded],
        capture_output=True, text=True, timeout=300,
    )
    if completed.returncode:
        raise SpecError((completed.stderr or completed.stdout).strip() or "InDesign COM execution failed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "validate", "prepare", "run"])
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--runner", type=Path)
    parser.add_argument("--force", action="store_true", help="Allow replacing existing runner and output files")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            system = platform.system()
            print(json.dumps({"platform": system, "indesign_app": str(find_indesign()) if system == "Darwin" and find_indesign() else None,
                              "windows_com_registered": windows_com_registered() if system == "Windows" else None}))
            return 0
        if not args.spec:
            raise SpecError("--spec is required")
        spec = load_spec(args.spec)
        if args.command == "validate":
            pages = 2 + len(spec["projects"]) + sum(bool(p["images"] or p["facts"]) for p in spec["projects"])
            print(json.dumps({"valid": True, "projects": len(spec["projects"]), "pages_expected": pages}))
            return 0
        runner = args.runner or args.spec.resolve().parent / "portfolio-build.jsx"
        runner = prepare(spec, runner, force=args.force)
        print(json.dumps({"runner": str(runner), "output": spec["output"]}))
        if args.command == "run":
            report = Path(spec["output"]["report"])
            before = report.stat().st_mtime_ns if report.is_file() else None
            system = platform.system()
            if system == "Darwin":
                run_mac(runner)
            elif system == "Windows":
                run_windows(runner)
            else:
                raise SpecError("Automatic execution supports macOS and Windows; run the JSX manually on this platform.")
            if not report.is_file() or (before is not None and report.stat().st_mtime_ns == before):
                raise SpecError("InDesign returned without a fresh report. Check the Scripts panel for an error.")
            result = json.loads(report.read_text(encoding="utf-8"))
            if result.get("ok"):
                for kind in ("indd", "pdf"):
                    output_file = Path(spec["output"][kind])
                    if not output_file.is_file() or output_file.stat().st_size == 0:
                        raise SpecError(f"InDesign reported success but {kind} output is missing or empty: {output_file}")
            print(json.dumps(result, indent=2))
            return 0 if result.get("ok") else 1
        return 0
    except (SpecError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

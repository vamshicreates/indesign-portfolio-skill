#!/usr/bin/env python3
"""Check that every inventoried work file received an editorial decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def check(inventory: dict, ledger: dict) -> list[str]:
    errors = []
    expected = {item["relative_path"] for item in inventory["files"]}
    decisions = ledger.get("decisions", [])
    actual = [item.get("relative_path") for item in decisions]
    if inventory.get("source_folder") != ledger.get("source_folder"):
        errors.append("Inventory and ledger have different source folders")
    for path in sorted(expected - set(actual)):
        errors.append(f"Missing decision: {path}")
    for path in sorted(set(actual) - expected):
        errors.append(f"Stale decision: {path}")
    if len(actual) != len(set(actual)):
        errors.append("Duplicate file decisions")
    valid = {"selected", "supporting", "duplicate", "excluded", "unreadable"}
    for item in decisions:
        path = item.get("relative_path", "(unknown)")
        status = item.get("status")
        if status not in valid:
            errors.append(f"Unreviewed or invalid status: {path}")
        if status in {"selected", "supporting"} and not str(item.get("project", "")).strip():
            errors.append(f"Project required: {path}")
        if status in {"duplicate", "excluded", "unreadable"} and not str(item.get("reason", "")).strip():
            errors.append(f"Reason required: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        errors = check(inventory, ledger)
        print(json.dumps({"complete": not errors, "files": len(inventory["files"]), "errors": errors}, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

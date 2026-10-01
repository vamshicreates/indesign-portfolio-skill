#!/usr/bin/env python3
"""Optional Laya choice aid for a genuinely ambiguous portfolio decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def decide(state: str, question: str, criteria: dict[str, str], *, ambiguous: bool,
           reason: str = "", min_confidence: float = 0.7, router_factory=None) -> dict:
    if not ambiguous:
        return {"laya_called": False, "choice": None, "reason": "Direct evidence or an explicit instruction settles this decision."}
    if not reason.strip():
        raise ValueError("Explain why the evidence leaves multiple plausible options before calling Laya")
    if not state.strip() or not question.strip() or len(criteria) < 2:
        raise ValueError("Provide evidence, a question, and at least two distinct candidate options")
    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be between 0 and 1")
    if router_factory is None:
        try:
            from laya import Router  # type: ignore
        except ImportError:
            return {"laya_called": False, "choice": None, "reason": "Laya is not installed; review the evidence directly.",
                    "install_hint": "Optional: python -m pip install laya"}
        router_factory = Router
    try:
        result = router_factory().predict(state, {"portfolio_choice": {
            "type": "choice", "instructions": question, "criteria": criteria,
        }}, min_confidence=min_confidence)
        answer = result.get("answers", {}).get("portfolio_choice", {})
        choice = answer.get("choice")
        confidence = answer.get("answer_confidence")
        if confidence is None:
            confidence = answer.get("confidence")
        if choice not in criteria or not isinstance(confidence, (int, float)) or confidence < min_confidence:
            choice = None
        return {"laya_called": True, "choice": choice, "confidence": confidence,
                "reason": reason, "model": result.get("routing", {}).get("model"),
                "note": "A suggestion only; verify against source evidence and user intent."}
    except Exception as exc:
        return {"laya_called": False, "choice": None, "reason": "Laya failed; review the evidence directly.",
                "error": str(exc)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", required=True, type=Path, help="Short, relevant evidence for this decision")
    parser.add_argument("--question", required=True)
    parser.add_argument("--criteria-file", required=True, type=Path, help="JSON object: option name to explanation")
    parser.add_argument("--ambiguous", action="store_true", help="Only set after identifying two plausible options")
    parser.add_argument("--reason", default="", help="Why ordinary evidence does not settle the choice")
    parser.add_argument("--min-confidence", type=float, default=0.7)
    args = parser.parse_args(argv)
    try:
        criteria = json.loads(args.criteria_file.read_text(encoding="utf-8"))
        if not isinstance(criteria, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in criteria.items()):
            raise ValueError("criteria must be a JSON object of option names and explanations")
        result = decide(args.state_file.read_text(encoding="utf-8"), args.question, criteria,
                        ambiguous=args.ambiguous, reason=args.reason, min_confidence=args.min_confidence)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Acceptance check run inside the real guest, not a timing workaround.

Checks the saved result, CLI JSON, and metric consistency. Deliberately refuses
NaN/Infinity rather than normalizing or replacing observed values.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant: {value}")


def check(result_text: str, cli_text: str) -> dict:
    result = json.loads(result_text, parse_constant=reject_constant)
    cli = json.loads(cli_text, parse_constant=reject_constant)
    assert result["success"] is True and result["status"] == "passed"
    assert cli["status"] == result["status"]
    assert cli["metrics"] == result["metrics"], "CLI metrics differ from the saved result"
    assert cli["values"] == result["values"], "CLI accepted values differ from saved values"
    for name, value in result["metrics"].items():
        if name.endswith("_ms"):
            assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name} must be numeric"
            assert math.isfinite(value) and value >= 0, f"{name} must be finite and nonnegative"
    return {"result_and_cli_agree": True, "timings_finite": True,
            "elapsed_ms": result["metrics"]["elapsed_ms"],
            "demo_workers": "scripted fixtures; not live inference"}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: guest_result_check.py RESULT_JSON CLI_JSON")
    result_text, cli_text = (Path(name).read_text() for name in sys.argv[1:])
    for label, text in (("SAVED_RESULT", result_text), ("CLI_OUTPUT", cli_text)):
        # Preserve the exact observed values, including a possible bad number.
        print(label + "_TIMINGS: " + " | ".join(line.strip() for line in text.splitlines() if 'elapsed_ms' in line), flush=True)
    print(json.dumps(check(result_text, cli_text), allow_nan=False), flush=True)

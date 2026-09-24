#!/usr/bin/env python3
"""Read-only completeness check for an R4.1 canary evidence directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from verify import SHA256_RE, evaluate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--authorization-sha256", required=True)
    args = parser.parse_args()
    if not SHA256_RE.fullmatch(args.authorization_sha256):
        parser.error("authorization digest must be lowercase SHA-256")
    try:
        root = args.evidence.resolve(strict=True)
        source = root / "canary-evidence.json"
        if source.is_symlink():
            raise ValueError("canary-evidence.json may not be a symlink")
        bundle = json.loads(source.read_text(encoding="utf-8"))
        result = evaluate(bundle, root, args.authorization_sha256)
        incomplete = sorted(name for name, status in result.checks.items() if status == "INCOMPLETE")
        payload = {"complete": not incomplete, "incomplete_checks": incomplete, "reasons": result.reasons}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"complete": False, "incomplete_checks": ["evidence_input"], "reasons": [str(exc)]}
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0 if payload["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

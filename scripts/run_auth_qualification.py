#!/usr/bin/env python3
"""Thin CLI for the attack-manifest qualification runner (Track B2).

Usage:
    python scripts/run_auth_qualification.py <manifest-dir> \\
        --contract-id <64-hex> [--out-dir DIR] [--root DIR] [--timeout-s N]

Exit code 0 iff the overall qualification verdict is PASS.
The runner refuses (non-zero exit, no receipts) on candidate-identity
mismatch, dirty working tree, or contract mismatch.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from residual.qualification.auth_runner import release_report, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_dir", type=Path)
    parser.add_argument("--contract-id", required=True,
                        help="frozen contract identity (64-hex); the runner never invents one")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "evidence" / "auth_qualification")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--timeout-s", type=int, default=300)
    args = parser.parse_args(argv)

    try:
        run_manifest = run(args.manifest_dir, contract_id=args.contract_id,
                           out_dir=args.out_dir, root=args.root,
                           timeout_s=args.timeout_s)
    except (ValueError, RuntimeError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    print(release_report(run_manifest))
    return 0 if run_manifest["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
